# -*- coding: utf-8 -*-
"""Qwen3-TTS 로 소리 만들기 + 목소리 섞기 + 끝소리 보호.

목소리 = 화자 특징 숫자(ref_spk_embedding). 섞기 = 비율대로 더한 뒤 크기를 가중 평균 크기로 맞춤.
average 방식 = 조각 최대 30개의 숫자 평균(한 조각보다 훨씬 안정적, 계산 결과는 목소리 폴더에 저장해 둠).
끝소리 보호 = 문장 끝에 " 네." 를 붙여 만든 뒤 잘라냄(Qwen 계열은 마지막 음절이 끊기는 일이 잦음)."""
import dataclasses, os, re
import numpy as np
from . import voices as V

MODELS = {"0.6": ("Qwen/Qwen3-TTS-12Hz-0.6B-Base", "float32"), "1.7": ("Qwen/Qwen3-TTS-12Hz-1.7B-Base", "float16")}
FILLER = " 네."


def cap(text):
    """한 문장이 끝없이 길어지는 것 막기(보통 속도의 약 2배까지)"""
    return int((len(text) * 0.6 + 5) * 12.5) + 30


def trim_tail(w, sr):
    """끝에 남은 '네' 같은 짧은 꼬리 정리"""
    w = np.asarray(w, dtype=np.float32); h = int(sr * 0.02)
    if len(w) < h * 20:
        return w
    r = np.array([np.sqrt(np.mean(w[i:i + h] ** 2)) for i in range(0, len(w) - h, h)])
    loud = r > max(0.02 * np.percentile(r, 99), 0.003); idx = np.where(loud)[0]
    if len(idx) < 10:
        return w
    end = idx[-1]; st = end
    while st > 0 and (loud[st - 1] or (st >= 3 and loud[st - 3:st].any())):
        st -= 1
    g = st - 1
    while g > 0 and not loud[g - 1]:
        g -= 1
    if (end - st + 1) * 0.02 <= 0.6 and (st - g) * 0.02 >= 0.2 and g > 5:
        return w[:int((g + (st - g) / 2) * h)]
    return w


def cut_filler(w, sr, text, filler=FILLER):
    """덧붙인 말을 잘라냄: 끝쪽 '조용한 틈 + 짧고 작은 소리'가 있으면 그 틈에서, 없으면 끝쪽에서 가장 조용한 곳에서"""
    w = np.asarray(w, dtype="float32"); hop = int(sr * 0.01); n = len(w) // hop
    rms = np.sqrt(np.convolve(w[:n * hop] ** 2, np.ones(hop) / hop, "valid")[::hop][:n] + 1e-12)
    cut = None
    if n > 80:
        peak = float(np.percentile(rms, 99)); loud = rms > max(peak * 0.02, 0.003)
        i = n - 1
        while i > 0 and not loud[i]:
            i -= 1
        j = i
        while j > 0 and loud[j - 1]:
            j -= 1
        tail_len = (i - j + 1) * 0.01; tail_peak = float(rms[j:i + 1].max()) if i >= j else 0.0
        g = j - 1
        while g > 0 and not loud[g]:
            g -= 1
        gap = (j - 1 - g) * 0.01
        if j > 0 and gap >= 0.3 and tail_len <= min(1.2, 0.25 * n * 0.01) and tail_peak < peak * 0.9 and g > 10:
            cut = (g + 1 + (j - 1 - g) // 2) * hop
    if cut is None:
        cnt = lambda t: max(1, len(re.sub(r"[\s\.,!?~…]", "", t)))
        per = (len(w) / sr) / (cnt(text) + cnt(filler)); est = per * cnt(filler); k = 3
        lo = max(1, int((len(w) / sr - est * 2.0) / 0.01)); hi = max(lo + 1, int((len(w) / sr - est * 0.5) / 0.01))
        seg = np.convolve(rms[lo:hi], np.ones(k) / k, "same") if hi - lo > k else rms[lo:hi]
        if len(seg) == 0:
            return w
        cut = (lo + int(np.argmin(seg))) * hop
    out = w[:cut].copy(); f = min(len(out), int(sr * 0.01))
    if f:
        out[-f:] *= np.linspace(1, 0, f, dtype="float32")
    return out


class Engine:
    def __init__(self, cfg, log=print):
        self.cfg, self.log = cfg, log
        self.voices = V.list_voices(cfg["voices_dir"])
        self.m = None; self._prompts = {}; self.items = {}

    def load(self):
        import torch
        from qwen_tts import Qwen3TTSModel
        name, dt = MODELS[self.cfg["model"]]
        self.torch = torch
        self.log(f"[모델] {name} 불러오는 중… (처음엔 내려받느라 몇 분 걸려요)")
        self.m = Qwen3TTSModel.from_pretrained(name, device_map=self.cfg["device"], dtype=getattr(torch, dt), attn_implementation="sdpa")
        return self

    def unload(self):
        import gc
        self.m = None; self._prompts.clear(); self.items.clear(); gc.collect()
        try:
            self.torch.cuda.empty_cache()
        except Exception:
            pass

    def _prompt(self, v, row=None):
        row = row or v["ref"]; k = (v["name"], row["file"])
        if k not in self._prompts:
            self._prompts[k] = self.m.create_voice_clone_prompt(ref_audio=V.clip_path(v, row), ref_text=row["text"])[0]
        return self._prompts[k]

    def _embedding(self, v, method):
        torch = self.torch
        if method == "single":
            return self._prompt(v).ref_spk_embedding.float()
        cache = os.path.join(v["dir"], f"emb_{self.cfg['model']}.pt")
        if os.path.isfile(cache):
            return torch.load(cache).float().to(self._prompt(v).ref_spk_embedding.device)
        es = []
        for r in V.average_rows(v, self.cfg["avg_clips"]):
            try:
                es.append(self._prompt(v, r).ref_spk_embedding.float())
            except Exception as e:
                self.log(f"  [조각 건너뜀] {v['name']} {r['file']}: {e}")
        if not es:
            raise SystemExit(f"[목소리 오류] {v['name']} 조각에서 숫자를 못 만들었어요")
        m = sum(es) / len(es); m = m * (sum(e.norm() for e in es) / len(es) / (m.norm() + 1e-9))
        torch.save(m.cpu(), cache); self.log(f"[평균 숫자] {v['name']}: 조각 {len(es)}개 → {os.path.basename(cache)}")
        return m

    def speaker(self, name):
        """배역(섞기)을 화자 숫자 하나로"""
        if name in self.items:
            return self.items[name]
        s = self.cfg["speakers"][name]; parts = []
        for vn, r in s["mix"]:
            if vn not in self.voices:
                raise SystemExit(f"[목소리 없음] '{vn}' — {self.cfg['voices_dir']} 안에 폴더가 있는지 확인하세요")
            parts.append((self.voices[vn], r / 100))
        es = [self._embedding(v, s.get("method", "average")) for v, _ in parts]; ws = [w for _, w in parts]
        emo = s.get("emotion")
        if emo and float(emo.get("alpha", 0)):        # 감정: 목소리마다 그 성별의 감정 숫자를 세기만큼 더함
            from .emotion import tau, KO, NAMES
            for i, (v, _) in enumerate(parts):
                g = v.get("gender") or s.get("gender", "")
                if not g:
                    raise SystemExit(f"[감정] '{v['name']}' 성별을 몰라요 — voices/{v['name']}/voice.json 에 gender 를 적어 주세요")
                es[i] = es[i] + float(emo["alpha"]) * tau(self.cfg, emo["type"], g).to(es[i].device).reshape(es[i].shape)
            self.log(f"[감정] {name}: {NAMES.get(emo['type'], emo['type'])} 세기 {emo['alpha']}")
        m = sum(w * e for w, e in zip(ws, es)); m = m * (sum(w * e.norm() for w, e in zip(ws, es)) / (m.norm() + 1e-9))
        p0 = self._prompt(parts[0][0])
        it = dataclasses.replace(p0, ref_spk_embedding=m.to(p0.ref_spk_embedding.dtype).reshape(p0.ref_spk_embedding.shape),
                                 ref_code=None, x_vector_only_mode=True, icl_mode=False)
        self.items[name] = it
        return it

    def say(self, text, speaker, seed=1234, temp=0.6):
        """한 문장 → (소리, 표본율). 끝소리 보호 + 꼬리 정리까지"""
        torch = self.torch; t = text.rstrip()
        if not re.search(r"[\.\!\?…]$", t):
            t += "."
        torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
        kw = dict(max_new_tokens=cap(t + FILLER), do_sample=True, temperature=temp, top_k=30, top_p=0.9,
                  subtalker_dosample=True, subtalker_temperature=temp, subtalker_top_k=30, subtalker_top_p=0.9)
        try:
            wavs, sr = self.m.generate_voice_clone(text=t + FILLER, language=self.cfg["language"], voice_clone_prompt=[self.speaker(speaker)], **kw)
        except TypeError:   # 옛 qwen-tts 는 샘플링 값을 못 받음
            wavs, sr = self.m.generate_voice_clone(text=t + FILLER, language=self.cfg["language"], voice_clone_prompt=[self.speaker(speaker)], max_new_tokens=kw["max_new_tokens"])
        w = trim_tail(cut_filler(wavs[0], sr, t), sr)
        return np.asarray(w, dtype="float32"), sr
