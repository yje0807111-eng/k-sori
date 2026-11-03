# -*- coding: utf-8 -*-
"""감정 넣기 — 감정 숫자(τ) 만들기와 쓰기.

원리: 여러 사람이 '평소'와 '감정'으로 읽은 녹음에서 화자 숫자를 구해, 같은 성별끼리 (감정 − 평소)의 평균을 낸다.
배역 숫자 + 세기(alpha) × 감정 숫자 = 그 감정으로 말하는 목소리. (1.7B 모델 권장 — 0.6B 는 감정이 잘 안 실림)

감정 자료(이 저장소에는 들어 있지 않음 — 직접 준비해서 내 컴퓨터에서만 계산)
1) RAVDESS (https://zenodo.org/records/1188976 의 Audio_Speech_Actors_01-24.zip, 영어 배우 24명 · 감정 7가지)
   노래판(Audio_Song_Actors)에는 혐오·놀람이 없음(차분함·기쁨·슬픔·분노·두려움만).
   ⚠ CC BY-NC-SA 4.0 = 비상업용. 이것으로 만든 감정 숫자·소리를 돈 버는 데 쓰면 안 됨.
   파일 이름 03-01-감정-세기-문장-반복-배우.wav 를 그대로 알아봄(배우 홀수=남, 짝수=여).
2) 내 감정 녹음 (상업용으로 쓰려면 이 방법)
   폴더/<사람이름>__남/neutral/*.wav, sad/*.wav, happy/*.wav, angry/*.wav, calm, fearful, disgust, surprised  (한 사람이 평소·감정을 모두 읽은 녹음)
결과: emotions/emotions_<모델>.pt  (설정 파일 옆 emotions 폴더, 공개 저장소에는 올리지 않음)"""
import os, re

EMOS = {"01": "neutral", "02": "calm", "03": "happy", "04": "sad", "05": "angry", "06": "fearful", "07": "disgust", "08": "surprised"}   # RAVDESS 감정 번호
NAMES = {"sad": "슬픔", "happy": "기쁨", "angry": "분노", "calm": "차분함", "fearful": "두려움", "disgust": "혐오", "surprised": "놀람"}
KO = {**NAMES, **{v: k for k, v in NAMES.items()}}   # 영어 ↔ 한국어 (설정에 둘 다 쓸 수 있음)
AUDIO = (".wav", ".mp3", ".flac", ".ogg", ".m4a")


def _scan(src):
    """[(경로, 감정, 강하게?, 사람키, 성별 M/F)]"""
    out = []
    for r, _, fs in os.walk(src):
        for f in fs:
            if not f.lower().endswith(AUDIO):
                continue
            p = os.path.splitext(f)[0].split("-")
            if len(p) == 7 and p[0] == "03" and p[2] in EMOS:            # RAVDESS 음성
                a = int(p[6]); out.append((os.path.join(r, f), EMOS[p[2]], p[3] == "02", f"rav{a:02d}", "M" if a % 2 else "F"))
                continue
            rel = os.path.relpath(os.path.join(r, f), src).replace("\\", "/").split("/")
            if len(rel) >= 3 and (rel[-2] == "neutral" or rel[-2] in NAMES) and "__" in rel[-3]:   # 내 감정 녹음
                who, g = rel[-3].rsplit("__", 1)
                out.append((os.path.join(r, f), rel[-2], True, who, {"남": "M", "여": "F"}.get(g[:1], "")))
    return sorted(out)


def out_path(cfg):
    return os.path.join(cfg["emotions_dir"], f"emotions_{cfg['model']}.pt")


def build(src, cfg, log=print):
    from .tts import Engine
    files = _scan(src)
    if not files:
        raise SystemExit(f"[감정] 알아볼 수 있는 감정 녹음이 없어요: {src}\n  RAVDESS 압축을 푼 폴더, 또는 <이름>__남/neutral·sad·happy·angry 폴더 모양인지 확인하세요")
    eng = Engine(cfg, log).load(); torch = eng.torch; acc = {}; meta = {}
    files = [f for f in files if f[1] == "neutral" or f[2]]     # 감정은 강하게 연기한 것만(RAVDESS 세기 02), 평소는 모두
    log(f"[감정] 녹음 {len(files)}개에서 목소리 숫자 구하는 중…")
    for i, (p, emo, strong, who, g) in enumerate(files, 1):
        try:
            e = eng.m.create_voice_clone_prompt(ref_audio=p, ref_text="네.")[0].ref_spk_embedding.float().flatten().cpu()
        except Exception as ex:
            log(f"  [건너뜀] {os.path.basename(p)}: {str(ex)[:80]}"); continue
        acc.setdefault((emo, who), []).append(e)
        meta[who] = g
        if i % 100 == 0 or i == len(files):
            log(f"  {i}/{len(files)}")
    data = {"actors": meta, "mean": {}}
    for (emo, who), es in acc.items():
        data["mean"].setdefault(emo, {})[who] = torch.stack(es).mean(0)
    os.makedirs(cfg["emotions_dir"], exist_ok=True); torch.save(data, out_path(cfg))
    have = {k: len(v) for k, v in data["mean"].items()}
    log(f"[감정 완성] {out_path(cfg)} · 사람 수 {have}")
    return out_path(cfg)


_TAU = {}


def tau(cfg, emo, gender):
    """같은 성별 사람들의 (감정 − 평소) 평균. gender = 남/여"""
    import torch
    emo = emo if emo in NAMES else KO.get(emo, emo); g = {"남": "M", "여": "F"}.get(str(gender)[:1], str(gender)[:1].upper())   # 한국어로 적어도 영어 이름으로
    key = (out_path(cfg), emo, g)
    if key in _TAU:
        return _TAU[key]
    if not os.path.isfile(out_path(cfg)):
        raise SystemExit(f"[감정] 감정 숫자가 없어요({out_path(cfg)}). 먼저 `ksori emotion-build <감정 녹음 폴더>` 를 실행하세요.")
    d = torch.load(out_path(cfg)); n = d["mean"].get("neutral", {}); e = d["mean"].get(emo, {})
    who = [w for w in e if w in n and (not g or d["actors"].get(w, "") == g)]
    if not who:
        raise SystemExit(f"[감정] '{NAMES.get(emo, emo)}' 감정과 평소 녹음을 함께 가진 {gender or ''} 사람이 없어요")
    _TAU[key] = torch.stack([e[w] - n[w] for w in who]).mean(0)
    return _TAU[key]
