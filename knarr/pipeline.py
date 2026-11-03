# -*- coding: utf-8 -*-
"""대본 하나를 끝까지: 여러 번 녹음 → 고르기 → 깨진 소리·성별 튐 검사 → 받아쓰기 검사 → 쉼 넣어 이어 붙이기.

결과 폴더(output/<이름>/)
    narration.wav   완성 나레이션          timeline.csv  문장마다 시작·끝 시각(자막·영상 맞추기용)
    report.csv      받아쓰기 검사 결과      takes/        문장별 테이크(지우지 않으면 다음에 이어서 함)
    log.txt
이미 만든 테이크는 다시 만들지 않으므로 중간에 멈췄다가 다시 실행해도 이어서 한다."""
import csv, difflib, json, os, re, time, traceback
import numpy as np, soundfile as sf
from . import quality as Q
from .script import parse, hang
from .tts import Engine

SR = 24000


class Job:
    def __init__(self, cfg, script_path, name=None):
        self.cfg = cfg
        self.name = name or os.path.splitext(os.path.basename(script_path))[0]
        self.out = os.path.join(cfg["output_dir"], self.name); self.tk = os.path.join(self.out, "takes")
        os.makedirs(self.tk, exist_ok=True)
        self.logf = open(os.path.join(self.out, "log.txt"), "a", encoding="utf-8", buffering=1)
        self.pieces = parse(open(script_path, encoding="utf-8-sig").read(), cfg)
        self.cache = self._load("analysis.json"); self.qc = self._load("quality.json"); self.asr = self._load("asr.json")
        self.sel = self._load("selection.json"); self.bad = set(); self.eng = None; self.t0 = time.time()

    # ── 기록 ──
    def log(self, *a):
        s = " ".join(str(x) for x in a)
        try:
            print(s, flush=True)
        except Exception:
            pass
        self.logf.write(s + "\n")

    def _load(self, f):
        p = os.path.join(self.out, f)
        return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}

    def _save(self, f, v):
        json.dump(v, open(os.path.join(self.out, f), "w", encoding="utf-8"), ensure_ascii=False)

    def tf(self, pid, k):
        return os.path.join(self.tk, f"{pid:03d}_t{k}.wav")

    def takes(self, pid):
        return sorted(int(n.split("_t")[1][:-4]) for n in self.cache if n.startswith(f"{pid:03d}_t"))

    def tdict(self):
        return {p["id"]: {k: self.cache[os.path.basename(self.tf(p["id"], k))] for k in self.takes(p["id"])} for p in self.pieces}

    # ── 녹음 ──
    def engine(self):
        if self.eng is None or self.eng.m is None:
            self.eng = Engine(self.cfg, self.log).load()
        return self.eng

    def take(self, p, k):
        f = self.tf(p["id"], k); nm = os.path.basename(f)
        if not os.path.isfile(f):
            seed = 1000 * p["id"] + 37 * k + 11; temp = 0.6 if k <= 2 else 0.5 if k <= 4 else 0.45
            for _ in range(2):
                try:
                    w, sr = self.engine().say(p["text"], p["spk"], seed, temp); sec = len(w) / sr
                    if sec > len(p["text"]) * 0.6 + 5 or sec < 0.3:
                        raise RuntimeError(f"비정상 길이 {sec:.1f}초")
                    pk = float(np.abs(w).max()); w = w * (0.89 / pk) if pk > 1e-4 else w
                    sf.write(f, w, sr, subtype="PCM_16"); break
                except Exception as e:
                    self.log(f"  [실패] {p['id']}번 테이크{k}: {str(e)[:100]}"); seed += 7
            else:
                return
        if nm not in self.cache:
            w, sr = sf.read(f, dtype="float32"); self.cache[nm] = Q.analyze(w, sr); self._save("analysis.json", self.cache)

    def record(self, targets, upto, start, tag):
        self.log(f"[{tag}] 테이크 {upto}번까지 · 문장 {len(targets)}개")
        for i, p in enumerate(targets, 1):
            for k in range(start + 1, upto + 1):
                self.take(p, k)
            if i % 10 == 0 or i == len(targets):
                self.log(f"  {i}/{len(targets)} · 경과 {(time.time() - self.t0) / 60:.0f}분")

    def more(self, p, n=3):
        top = max(self.takes(p["id"]), default=0)
        for k in range(top + 1, top + n + 1):
            self.take(p, k)

    # ── 고르기·검사 ──
    def choose(self):
        T = self.tdict(); ref, rate = Q.references(self.pieces, T); out = {}
        for p in self.pieces:
            ks = self.takes(p["id"]); s = self.sel.get(str(p["id"]), {})
            pin = s.get("pin")
            if pin in ks and (s.get("ok") or os.path.basename(self.tf(p["id"], pin)) not in self.bad):
                out[p["id"]] = pin; continue
            best = min(((Q.take_score(p, T[p["id"]][k], ref, rate, os.path.basename(self.tf(p["id"], k)) in self.bad), k) for k in ks), default=None)
            if best:
                out[p["id"]] = best[1]
        return out, ref

    def quality_check(self):
        for p in self.pieces:
            for k in self.takes(p["id"]):
                nm = os.path.basename(self.tf(p["id"], k))
                if nm not in self.qc:
                    w, sr = sf.read(self.tf(p["id"], k), dtype="float32"); self.qc[nm] = Q.voice_quality(w, sr)
        self._save("quality.json", self.qc); self.bad.clear(); allbad = []; nb = 0
        gender = {s: self.cfg["speakers"][s].get("gender", "") for s in self.cfg["speakers"]}
        for s in {p["spk"] for p in self.pieces}:
            mine = [p for p in self.pieces if p["spk"] == s]
            vs = [self.qc[os.path.basename(self.tf(p["id"], k))] for p in mine if len(hang(p["text"])) >= 5 for k in self.takes(p["id"])]
            meds = [self.cache[os.path.basename(self.tf(p["id"], k))][0] for p in mine for k in self.takes(p["id"])]
            meds = [m for m in meds if m != 0]
            vref = float(np.median(vs)) if len(vs) >= 4 else None; pref = float(np.median(meds)) if len(meds) >= 4 else None
            sign = {"남": 1, "여": -1}.get(gender.get(s, "")[:1], 0)
            for p in mine:
                ks = self.takes(p["id"]); nbad = 0
                for k in ks:
                    nm = os.path.basename(self.tf(p["id"], k)); bad = False
                    if vref and len(hang(p["text"])) >= 5 and self.qc[nm] < self.cfg["quality_ratio"] * vref:
                        bad = True
                    m = self.cache[nm][0]
                    if pref and sign and m != 0 and sign * (m - pref) > self.cfg["pitch_tol"]:
                        bad = True; nb += 1
                    if bad:
                        self.bad.add(nm); nbad += 1
                if ks and nbad == len(ks):
                    allbad.append(p)
        self.log(f"[음질 검사] 깨진 소리·성별 튐 테이크 {len(self.bad)}개(성별 튐 {nb}) · 모든 테이크가 나쁜 문장 {len(allbad)}개")
        return allbad

    @staticmethod
    def check_text(p, hyp):
        ok, why = Job._check(hang(p["text"]), hang(hyp))
        if not ok and p.get("orig", p["text"]) != p["text"]:     # 읽기 고친 문장: 숫자까지 남겨 원래 글과 비교
            keep = lambda x: re.sub(r"[^가-힣0-9]", "", x)
            ok2, why2 = Job._check(keep(p["orig"]), keep(hyp))
            nums = re.findall(r"\d+", hyp)
            if ok2 and re.findall(r"\d+", p["orig"]) != nums:   # 장·절 숫자는 정확히 같아야(21장을 12장으로 읽는 사고)
                return False, "숫자가 달라요 (" + " ".join(nums) + ")"
            if ok2:
                return True, why2 + " (숫자 글과 비교)"
        return ok, why

    @staticmethod
    def _check(eh, hh):
        if len(eh) < 5:
            return len(hh) > 0, "짧은 문장(검사 생략)"
        if hh.endswith("네") and not eh.endswith("네") and len(hh) > len(eh):
            return False, "끝에 '네' 소리"
        r = difflib.SequenceMatcher(None, eh, hh).ratio()
        if r < 0.88:
            return False, f"글이 달라요 ({r:.0%})"
        if eh[-3:] not in hh[-9:]:
            return False, "끝이 잘린 듯해요"
        if eh[:2] not in hh[:9]:
            return False, "앞이 잘린 듯해요"
        return True, f"일치 {r:.0%}"

    def asr_check(self, result):
        import whisper, torch, librosa
        model = whisper.load_model(self.cfg["asr_model"], device="cuda" if torch.cuda.is_available() else "cpu")

        def tr(f):
            nm = os.path.basename(f)
            if nm not in self.asr:
                w, sr = sf.read(f, dtype="float32")
                r = model.transcribe(librosa.resample(w, orig_sr=sr, target_sr=16000), language="ko",
                                     fp16=torch.cuda.is_available(), condition_on_previous_text=False, temperature=0.0)
                self.asr[nm] = r["text"].strip(); self._save("asr.json", self.asr)
            return self.asr[nm]
        chosen, _ = self.choose(); T = self.tdict(); ref, rate = Q.references(self.pieces, T); bad = []
        for i, p in enumerate(self.pieces, 1):
            k = chosen[p["id"]]; ok, why = self.check_text(p, tr(self.tf(p["id"], k)))
            result[p["id"]] = (k, ok, why, self.asr.get(os.path.basename(self.tf(p["id"], k)), ""))
            if not ok:
                alts = sorted((Q.take_score(p, T[p["id"]][a], ref, rate), a) for a in self.takes(p["id"]) if a != k)
                for _, a in alts:
                    if os.path.basename(self.tf(p["id"], a)) in self.bad:
                        continue
                    ok2, why2 = self.check_text(p, tr(self.tf(p["id"], a)))
                    if ok2:
                        self.sel[str(p["id"])] = {"pin": a}; ok = True
                        result[p["id"]] = (a, True, f"테이크{a}로 교체 · {why2}", self.asr.get(os.path.basename(self.tf(p["id"], a)), ""))
                        break
            if not ok:
                bad.append(p)
            if i % 10 == 0:
                self.log(f"  받아쓰기 {i}/{len(self.pieces)} · 이상한 문장 {len(bad)}개")
        self._save("selection.json", self.sel); del model
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
        return bad

    # ── 이어 붙이기 ──
    def assemble(self):
        chosen, _ = self.choose(); W = {}
        miss = [p["id"] for p in self.pieces if p["id"] not in chosen]
        if miss:
            raise SystemExit(f"[멈춤] 녹음이 하나도 안 된 문장이 있어요: {miss} — log.txt 의 [실패] 줄을 보고, 그 문장을 나누거나 고쳐서 다시 실행하세요.")
        for p in self.pieces:
            k = chosen[p["id"]]; w, sr = sf.read(self.tf(p["id"], k), dtype="float32")
            W[p["id"]] = (Q.trim(w if w.ndim == 1 else w[:, 0], sr), k)
        nar = np.median([Q.level_db(W[p["id"]][0]) for p in self.pieces if p["spk"] == self.cfg["narrator"]] or [-20])
        seq, t = [], 0.0
        rows = [["번호", "목소리", "시작(초)", "끝(초)", "테이크", "쉼(초)", "글"]]
        for p in self.pieces:
            w, k = W[p["id"]]
            if p["spk"] != self.cfg["narrator"]:
                d = Q.level_db(w) - (nar + 1.0)
                if d > 0:
                    w = w * 10 ** (-d / 20)        # 대사 배역이 나레이션보다 1dB 넘게 크면 낮춤
            rows.append([p["id"], p["spk"], round(t, 3), round(t + len(w) / SR, 3), k, p["pause"], p["text"]])
            seq += [w, np.zeros(int(SR * p["pause"]), dtype="float32")]; t += len(w) / SR + p["pause"]
        full = np.concatenate(seq); pk = np.abs(full).max()
        if pk > 0.97:
            full *= 0.97 / pk
        sf.write(os.path.join(self.out, "narration.wav"), full, SR, subtype="PCM_16")
        csv.writer(open(os.path.join(self.out, "timeline.csv"), "w", encoding="utf-8-sig", newline="")).writerows(rows)
        vals = {}
        for p, r in zip(self.pieces, rows[1:]):
            x = full[int(r[2] * SR):int(r[3] * SR)]
            if len(x) > SR * 0.8:
                vals[p["id"]] = (p["spk"], Q.smear(x, SR))
        warn = []
        for s in {a for a, _ in vals.values()}:
            v = [b for a, b in vals.values() if a == s]
            if len(v) >= 4:
                m = float(np.median(v)); warn += [pid for pid, (a, b) in vals.items() if a == s and b < 0.9 * m]
        self.log(f"[뭉개짐 검사] 이상한 문장 {len(warn)}개" + (": " + ", ".join(map(str, sorted(warn))) if warn else ""))
        return len(full) / SR

    # ── 전체 ──
    def run(self):
        c = self.cfg
        self.log(f"===== [시작] {time.strftime('%Y-%m-%d %H:%M:%S')} · {self.name} · 문장 {len(self.pieces)}개")
        self.record(self.pieces, c["takes"], 0, "1라운드")
        T = self.tdict(); ref, rate = Q.references(self.pieces, T)
        sc = sorted(self.pieces, key=lambda p: -min((Q.take_score(p, T[p["id"]][k], ref, rate) for k in T[p["id"]]), default=99))
        self.record(sc[:max(1, int(len(sc) * c["retry_frac"]))], c["max_takes"], c["takes"], "2라운드(점수 나쁜 문장)")
        for _ in range(2):
            allbad = self.quality_check()
            if not allbad:
                break
            for p in allbad:
                self.more(p); self.log(f"  {p['id']}번 깨진 소리뿐이라 새 테이크 3개")
        result = {}
        if c["asr"]:
            for rnd in range(1, c["asr_rounds"] + 1):
                if self.eng:
                    self.eng.unload()          # 그래픽 메모리를 비우고 받아쓰기
                self.log(f"[받아쓰기 {rnd}바퀴] · 경과 {(time.time() - self.t0) / 60:.0f}분")
                try:
                    bad = self.asr_check(result)
                except Exception:
                    self.log("[받아쓰기 건너뜀]\n" + traceback.format_exc()); bad = []
                self.log(f"[받아쓰기 {rnd}바퀴 끝] 이상한 문장 {len(bad)}개")
                if not bad or rnd == c["asr_rounds"]:
                    break
                for p in bad:
                    self.more(p); self.sel.pop(str(p["id"]), None); self.log(f"  {p['id']}번 새 테이크 3개: \"{p['text'][:24]}\"")
                self._save("selection.json", self.sel); self.quality_check()
        if self.eng:
            self.eng.unload()
        self.quality_check()
        tot = self.assemble(); chosen, _ = self.choose()
        rows = [["번호", "목소리", "테이크", "합격", "결과", "받아쓴 글", "대본"]]
        for p in self.pieces:
            k, ok, why, hyp = result.get(p["id"], (chosen[p["id"]], None, "검사 안 함", ""))
            rows.append([p["id"], p["spk"], k, "O" if ok else ("X" if ok is False else "-"), why, hyp, p["text"]])
        csv.writer(open(os.path.join(self.out, "report.csv"), "w", encoding="utf-8-sig", newline="")).writerows(rows)
        bad = [r for r in rows[1:] if r[3] == "X"]
        self.log(f"===== [완성] narration.wav · {tot / 60:.1f}분 · 이상한 문장 {len(bad)}개 · 총 {(time.time() - self.t0) / 60:.0f}분")
        for r in bad:
            self.log(f"  ⚠ {r[0]}번 [{r[1]}] {r[4]} — {r[6][:30]}")
        return os.path.join(self.out, "narration.wav")
