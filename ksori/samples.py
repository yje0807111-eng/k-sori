# -*- coding: utf-8 -*-
"""감정 견본 — 목소리 하나로 같은 문장을 감정마다 만들어 듣기 페이지까지(세기 고르기용).

세기는 성별·나이(voice.json 의 "age": "아이")에 맞춘 추천값으로 시작하고, 낮게·높게 두 단계를 더 만든다."""
import html, os
from . import aimark
from .emotion import NAMES, out_path

BASE = {"남": {"sad": 5, "happy": 3.5, "angry": 2.5, "calm": 3, "fearful": 3, "disgust": 2.5, "surprised": 3},
        "여": {"sad": 2, "happy": 1.5, "angry": 1.5, "calm": 1.5, "fearful": 1.5, "disgust": 1.5, "surprised": 1.5}}
TEXT = "정말 너였구나. 내가 얼마나 보고 싶었는지 아니?"


def alphas(gender, age=""):
    a = dict(BASE.get(gender[:1], BASE["여"]))
    if age == "아이":                     # 감정 자료가 어른이라 아이는 낮게(높이면 어른처럼 들림)
        a = {k: round(v * 0.75, 2) for k, v in a.items()}
    return a


def make(cfg, voice, text=TEXT, steps=(0.7, 1.0, 1.3), log=print):
    import json, torch
    from .tts import Engine
    eng = Engine(cfg, log)
    if voice not in eng.voices:
        raise SystemExit(f"[견본] 목소리 '{voice}' 가 없어요 ({cfg['voices_dir']})")
    v = eng.voices[voice]; g = v.get("gender") or "여"
    meta = json.load(open(os.path.join(v["dir"], "voice.json"), encoding="utf-8-sig")) if os.path.isfile(os.path.join(v["dir"], "voice.json")) else {}
    have = set(torch.load(out_path(cfg))["mean"]) if os.path.isfile(out_path(cfg)) else set()
    if not have:
        log("[견본] 감정 숫자가 없어서 평소 목소리만 만들어요 (emotion-build 를 먼저 하면 감정 견본도 생겨요)")
    rec = alphas(g, meta.get("age", ""))
    plan = [("평소", None, 0)]
    for emo, a in rec.items():
        if emo in have:
            plan += [(f"{NAMES[emo]}_{round(a * s, 2):g}", emo, round(a * s, 2)) for s in steps]
    base = {"mix": [[voice, 100]], "method": "average", "gender": g}
    for nm, emo, a in plan:
        cfg["speakers"][nm] = dict(base, **({"emotion": {"type": emo, "alpha": a}} if emo else {}))
    eng.load()
    out = os.path.join(cfg["output_dir"], f"감정견본_{voice}"); os.makedirs(out, exist_ok=True)
    rows = []
    for nm, emo, a in plan:
        w, sr = eng.say(text, nm, seed=1234, temp=0.5)
        aimark.write(os.path.join(out, nm + ".wav"), w, sr)
        rows.append((nm, emo, a)); log(f"  {nm}")
    cards = "".join(
        f'<div class="c"><b>{html.escape(nm.split("_")[0])}</b> <span>{"세기 " + format(a, "g") + (" (추천)" if emo and abs(a - rec[emo]) < 1e-6 else "") if emo else "감정 없음"}</span>'
        f'<audio controls preload="none" src="{html.escape(nm)}.wav"></audio></div>' for nm, emo, a in rows)
    page = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>감정 견본 {html.escape(voice)}</title><style>'
            'body{font-family:"Malgun Gothic",sans-serif;max-width:760px;margin:auto;padding:20px 16px;background:#1c1c1c;color:#eee}'
            '.c{background:#262626;border-radius:10px;padding:10px 14px;margin:8px 0}span{color:#aaa;font-size:14px;margin-left:8px}audio{width:100%;margin-top:6px}'
            f'</style></head><body><h1>감정 견본 — {html.escape(voice)}</h1><p>문장: “{html.escape(text)}”<br>'
            '세기는 추천값과 그보다 낮게·높게 세 가지예요. 목소리가 바뀌거나 기계음이 나면 낮은 쪽을 고르세요.</p>'
            f'{cards}</body></html>')
    open(os.path.join(out, "듣기.html"), "w", encoding="utf-8").write(page)
    log(f"[견본 완성] {os.path.join(out, '듣기.html')}")
    return out
