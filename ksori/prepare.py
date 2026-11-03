# -*- coding: utf-8 -*-
"""녹음 파일 → 목소리 폴더(voices/<이름>) 자동 만들기.

1) 녹음(wav/mp3/m4a…)을 24kHz 모노로 읽고  2) Whisper 로 말한 구간·글을 받아쓰고
3) 2~12초 구간만 조각(clips/*.wav)으로 저장  4) list.csv · voice.json 작성
좋은 목소리를 만들려면: 배경 음악·잡음 없는 녹음 5분 이상(조각 30개 이상)이 좋다.
받아쓴 글이 틀리면 list.csv 의 text 를 직접 고치면 된다(틀린 글은 목소리 숫자를 흐리게 함)."""
import csv, json, os
import numpy as np, soundfile as sf

SR = 24000
EXT = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".wma")


def build(name, src, voices_dir, gender="", asr_model="medium", log=print):
    import librosa, whisper, torch
    files = [os.path.join(src, f) for f in sorted(os.listdir(src)) if f.lower().endswith(EXT)] if os.path.isdir(src) else [src]
    if not files:
        raise SystemExit(f"[목소리 만들기] 녹음 파일이 없어요: {src}")
    d = os.path.join(voices_dir, name); cd = os.path.join(d, "clips"); os.makedirs(cd, exist_ok=True)
    model = whisper.load_model(asr_model, device="cuda" if torch.cuda.is_available() else "cpu")
    rows, n = [], 0
    for f in files:
        log(f"[받아쓰기] {os.path.basename(f)}")
        y, _ = librosa.load(f, sr=SR, mono=True)
        r = model.transcribe(librosa.resample(y, orig_sr=SR, target_sr=16000), language="ko", fp16=torch.cuda.is_available(),
                             condition_on_previous_text=False, temperature=0.0)
        segs = [(s["start"], s["end"], s["text"].strip()) for s in r["segments"] if s["text"].strip()]
        merged = []
        for a, b, t in segs:             # 2초 안 되는 구간은 뒤 구간과 붙임(12초까지)
            if merged and merged[-1][1] - merged[-1][0] < 2.0 and b - merged[-1][0] <= 12.0:
                merged[-1] = (merged[-1][0], b, merged[-1][2] + " " + t)
            else:
                merged.append((a, b, t))
        for a, b, t in merged:
            if not (2.0 <= b - a <= 12.0) or len(t) < 4:
                continue
            seg = y[max(0, int((a - 0.05) * SR)):int((b + 0.15) * SR)]
            pk = float(np.abs(seg).max())
            if pk < 0.02:
                continue
            n += 1; fn = f"{name}_{n:03d}.wav"
            sf.write(os.path.join(cd, fn), seg * (0.89 / pk), SR, subtype="PCM_16")
            rows.append([fn, round(len(seg) / SR, 2), t])
    with open(os.path.join(d, "list.csv"), "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.writer(fp); w.writerow(["file", "sec", "text"]); w.writerows(rows)
    json.dump({"gender": gender}, open(os.path.join(d, "voice.json"), "w", encoding="utf-8"), ensure_ascii=False)
    tot = sum(r[1] for r in rows)
    log(f"[완성] {name}: 조각 {len(rows)}개 · {tot / 60:.1f}분 → {d}")
    if len(rows) < 15:
        log("  ⚠ 조각이 적어요(15개 미만). 녹음을 더 넣으면 목소리가 안정적이에요.")
    return d
