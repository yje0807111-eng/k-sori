# -*- coding: utf-8 -*-
"""대본 읽기 → 녹음할 문장 조각 목록.

대본 규칙
- 한 줄 = 한 문장(또는 쉼표로 이어지는 한 덩이). 빈 줄 = 문단 쉼.
- 큰따옴표/작은따옴표 안은 대사 → 설정의 quote_speakers 순서대로 배역이 바뀜.
- 줄에 `//` 만 있으면 큰 쉼(이야기 → 설교처럼 장면이 바뀌는 곳).
- 쉼표로 끝나지 않는 줄 끝에는 숨 고르는 쉼표가 자동으로 붙음."""
import re


def hang(s):
    return re.sub(r"[^가-힣]", "", s)


def parse(text, cfg):
    P = cfg["pause"]; qspk = list(cfg["quote_speakers"]); nar = cfg["narrator"]
    raw = text.replace("\r\n", "\n")
    for w in cfg["word_quotes"]:
        raw = raw.replace(w, w.strip("'\""))
    raw = re.sub(r"\s*//\s*$", "\n//", raw, flags=re.M)
    ev = []; in_q = False; qn = 0; spk = nar
    for ln in raw.split("\n"):
        s = ln.strip()
        if s == "//":
            ev.append(("section",)); continue
        if not s:
            ev.append(("para", in_q)); continue
        if not re.search(r"[,\.\!\?…'\"”’]$", s):
            s += ","
        buf = ""
        for ch in s:
            if ch in "\"“”'‘’":
                if buf.strip():
                    ev.append(("text", spk, buf.strip()))
                buf = ""
                if not in_q:
                    if qn >= len(qspk):
                        raise SystemExit(f"[대본 오류] 따옴표 대사가 quote_speakers({len(qspk)}개)보다 많아요")
                    in_q = True; spk = qspk[qn]; qn += 1
                else:
                    in_q = False; spk = nar
            else:
                buf += ch
        if buf.strip():
            ev.append(("text", spk, buf.strip()))
    if qn != len(qspk):
        raise SystemExit(f"[대본 오류] 따옴표 대사 {qn}개인데 quote_speakers 는 {len(qspk)}개예요")
    runs = []; cur = None

    def close(kind):
        nonlocal cur
        if cur is not None:
            cur["end"] = kind; runs.append(cur); cur = None
    for e in ev:
        if e[0] == "text":
            if cur is not None and cur["spk"] != e[1]:
                close("spk")
            if cur is None:
                cur = dict(spk=e[1], frags=[], end="spk")
            cur["frags"].append(e[2])
        elif e[0] == "para":
            if cur is not None:
                close("qpara" if e[1] else "para")
        elif e[0] == "section":
            if runs and cur is None:
                runs[-1]["end"] = "section"
            elif cur is not None:
                close("section")
    close("para")
    pieces = []
    for r in runs:
        text = re.sub(r",\s*$", ".", " ".join(r["frags"]).strip())
        fixes = [(a, b) for a, b in cfg["tts_fix"] if a in text]
        for a, b in fixes:
            text = text.replace(a, b)
        sents = [x.strip() for x in re.split(r"(?<=[\.\!\?…])\s+", text) if x.strip()]
        flat = []
        for st in sents:      # 60자 넘는 문장만 쉼표에서 나눔
            if len(st) <= 60:
                flat.append([st, "sent"]); continue
            c = ""
            for w in re.split(r"(?<=[,，])\s+", st):
                if c and len(c) + len(w) > 60:
                    flat.append([c, "comma"]); c = w
                else:
                    c = (c + " " + w).strip()
            if c:
                flat.append([c, "sent"])
        mg = []
        for s, k in flat:     # 8자 안 되는 짧은 문장은 앞뒤와 붙여 읽음(혼자 읽으면 억양이 어색)
            if mg and (len(mg[-1][0]) < 8 or len(s) < 8):
                mg[-1] = [mg[-1][0] + " " + s, k]
            else:
                mg.append([s, k])
        for i, (s, k) in enumerate(mg):
            kind = r["end"] if i == len(mg) - 1 else k
            orig = s
            for x, y in fixes:            # 받아쓰기는 숫자로 적으므로 원래 글(고치기 전)도 같이 둠
                orig = orig.replace(y, x)
            pieces.append(dict(id=len(pieces) + 1, spk=r["spk"], text=s, orig=orig, kind=kind, pause=P[kind],
                               verse=any(v in s for v in cfg["verse"])))
    for a, b in zip(pieces, pieces[1:]):
        if a["text"].endswith("절입니다."):
            a["pause"] = 0.75
    return pieces
