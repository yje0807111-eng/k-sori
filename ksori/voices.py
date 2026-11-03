# -*- coding: utf-8 -*-
"""목소리 폴더 다루기.

voices/<이름>/
    clips/*.wav     목소리 조각(24kHz 모노, 2~12초, 잡음 없이)
    list.csv        file,sec,text  (조각 파일 이름, 길이(초), 그 조각에서 말한 글)
    voice.json      {"gender": "남"} 또는 {"gender": "여"}
조각은 `python -m ksori add-voice` 로 녹음 파일에서 자동으로 만들 수 있다."""
import csv, json, os


def _read_list(d):
    f = os.path.join(d, "list.csv")
    if not os.path.isfile(f):
        return []
    rows = []
    for r in csv.DictReader(open(f, encoding="utf-8-sig")):
        try:
            rows.append({"file": r["file"], "sec": float(r["sec"]), "text": r["text"].strip()})
        except (KeyError, ValueError):
            continue
    return [r for r in rows if r["text"] and os.path.isfile(os.path.join(d, "clips", r["file"]))]


def list_voices(root):
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        rows = _read_list(d)
        if not rows:
            continue
        meta = json.load(open(os.path.join(d, "voice.json"), encoding="utf-8-sig")) if os.path.isfile(os.path.join(d, "voice.json")) else {}
        ref = next((r for r in rows if 5 <= r["sec"] <= 10), None) or max(rows, key=lambda r: r["sec"])
        out[name] = {"name": name, "dir": d, "rows": rows, "ref": ref, "gender": meta.get("gender", "")}
    return out


def clip_path(v, row):
    return os.path.join(v["dir"], "clips", row["file"])


def average_rows(v, n=30):
    """평균 숫자에 쓸 조각: 2초 이상, 고르게 n개"""
    rows = [r for r in v["rows"] if r["sec"] >= 2.0]
    if len(rows) > n:
        step = len(rows) / n
        rows = [rows[int(i * step)] for i in range(n)]
    return rows
