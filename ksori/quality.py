# -*- coding: utf-8 -*-
"""테이크 점수 매기기와 자동 검사.

- 안정 점수: 음높이(pyin)가 튀거나 흔들리는 정도. 낮을수록 좋음.
- 깨진 소리: '목소리다움(유성 확률)'이 같은 배역 평균의 quality_ratio 배 미만이면 버림.
- 성별 튐: 남자 배역인데 배역 가운데 음높이보다 pitch_tol 반음 넘게 높으면(여자는 낮으면) 버림 — 남녀 목소리를 섞은 배역에서 생김.
- 뭉개짐: 이어 붙인 뒤 문장마다 스펙트럼 변화량이 평균의 0.9배 미만이면 경고."""
import numpy as np
from .script import hang


def trim(w, sr, lead=0.05, tail=0.10, thr=0.02):
    nz = np.where(np.abs(w) > thr)[0]
    if not len(nz):
        return w
    a = max(0, nz[0] - int(lead * sr)); b = min(len(w), nz[-1] + int(tail * sr))
    w = w[a:b].copy(); f = min(int(0.015 * sr), len(w) // 4)
    if f > 0:
        w[:f] *= np.linspace(0, 1, f); w[-f:] *= np.linspace(1, 0, f)
    return w


def level_db(w):
    x = w[np.abs(w) > 0.01]
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else -40.0


def analyze(w, sr):
    """(가운데 음높이(반음), 안정 점수, 끝 소리 세기 비율, 길이(초))"""
    import librosa
    y = librosa.resample(w.astype(np.float32), orig_sr=sr, target_sr=16000) if sr != 16000 else w.astype(np.float32)
    f0, _, _ = librosa.pyin(y, fmin=60, fmax=400, sr=16000, frame_length=1024, hop_length=160)
    ok = ~np.isnan(f0); sec = len(w) / sr; h = int(sr * 0.02)
    r = np.array([np.sqrt(np.mean(w[i:i + h] ** 2)) for i in range(0, max(1, len(w) - h), h)]) if len(w) > h else np.array([0.0])
    endr = float(r[-2:].mean() / (np.percentile(r, 90) + 1e-9)) if len(r) > 3 else 0.0
    if ok.sum() < 15:
        return [0.0, 5.0, round(endr, 3), round(sec, 2)]
    st = 12 * np.log2(f0[ok] / 100.0); idx = np.where(ok)[0]; med = float(np.median(st))
    d = np.abs(np.diff(st))[np.diff(idx) == 1]; jump = float((d > 2.0).mean()) if len(d) else 0.0
    sm = np.convolve(st, np.ones(25) / 25, "same")[:len(st)] if len(st) >= 25 else np.full(len(st), float(np.mean(st)))
    wob = float(np.std(st - sm)); outl = float((np.abs(st - med) > 7).mean())
    return [med, round(8 * jump + 1.2 * wob + 6 * outl, 3), round(endr, 3), round(sec, 2)]


def voice_quality(w, sr):
    import librosa
    w = trim(np.asarray(w, dtype=np.float32), sr)
    y = librosa.resample(w, orig_sr=sr, target_sr=16000) if sr != 16000 else w
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=160)) + 1e-9
    rms = np.sqrt((S ** 2).mean(0)); loud = rms > rms.max() * 0.12
    _, _, vp = librosa.pyin(y, fmin=60, fmax=400, sr=16000, frame_length=1024, hop_length=160)
    n = min(len(vp), len(loud))
    return float(np.nanmean(vp[:n][loud[:n]])) if loud[:n].any() else 0.0


def smear(w, sr):
    import librosa
    S = np.abs(librosa.stft(np.asarray(w, dtype=np.float32), n_fft=2048, hop_length=256)); e = S.sum(0); loud = e > e.max() * 0.1
    if loud.sum() < 5:
        return 0.35
    d = np.abs(np.diff(np.log(S[20:400, :] + 1e-6), axis=1))[:, loud[1:]]
    return float(np.median(d))


def references(pieces, takes):
    """배역마다 가운데 음높이·말 빠르기(초/글자). takes = {id: {k: [med, score, endr, sec]}}"""
    ref, rate = {}, {}
    for s in {p["spk"] for p in pieces}:
        meds, rs = [], []
        for p in pieces:
            if p["spk"] != s:
                continue
            n = max(1, len(hang(p["text"])))
            for c in takes.get(p["id"], {}).values():
                if c[1] < 90 and c[0] != 0:
                    meds.append(c[0])
                if n >= 6:
                    rs.append(c[3] / n)
        ref[s] = float(np.median(meds)) if meds else 0.0; rate[s] = float(np.median(rs)) if rs else 0.17
    return ref, rate


def take_score(p, c, ref, rate, bad=False):
    med, sc, endr, sec = c; n = max(1, len(hang(p["text"]))); pen = 50.0 if bad else 0.0
    if n >= 6:
        pen += 6 * max(0.0, abs(np.log((sec / n) / rate[p["spk"]])) - 0.25)   # 너무 빠르거나 느림
    if endr > 0.4:
        pen += 3.0                                                           # 끝이 잘린 듯 끝소리가 큼
    return sc + 0.8 * abs(med - ref[p["spk"]]) + pen
