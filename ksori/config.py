# -*- coding: utf-8 -*-
"""설정 파일(JSON) 읽기. 없는 값은 아래 기본값을 쓴다."""
import json, os

DEFAULTS = {
    "model": "1.7",                 # "1.7"(권장, 그래픽 메모리 약 4GB) 또는 "0.6"(가벼움)
    "device": "cuda:0",
    "language": "Korean",
    "voices_dir": "voices",         # 목소리 폴더(voices/<이름>/clips, list.csv, voice.json)
    "output_dir": "output",
    "emotions_dir": "emotions",     # 감정 숫자(emotion-build 결과)를 두는 곳
    "narrator": "나레",             # 기준 목소리(다른 배역 크기를 이 목소리에 맞춤)
    # 배역 = 목소리 섞기. method: average(조각 평균, 안정적) / single(참고 녹음 한 개)
    # 감정: "emotion": {"type": "sad"/"happy"/"angry", "alpha": 세기} (emotion-build 먼저, 1.7B 권장)
    "speakers": {
        "나레": {"mix": [["내목소리", 100]], "method": "average", "gender": ""}
    },
    "quote_speakers": [],           # 대본의 따옴표 대사가 나오는 순서대로 배역 이름
    "word_quotes": [],              # 따옴표지만 대사가 아닌 말(예: "'가족'") — 나레이션이 읽음
    "tts_fix": [],                  # 읽기 고치기 [["21장 4절", "이십일 장 사 절"], ...] (자막은 그대로, 소리만)
    "verse": [],                    # 이 말로 시작하는 문장은 성경 구절로 표시(로그용)
    "pause": {"sent": 0.90, "comma": 0.55, "para": 1.15, "qpara": 0.70, "spk": 0.60, "section": 1.50},
    "takes": 3,                     # 문장마다 기본 녹음 수
    "max_takes": 5,                 # 점수 나쁜 문장은 이만큼까지
    "retry_frac": 0.3,              # 점수 나쁜 문장 비율(이만큼 더 녹음)
    "asr": True,                    # 받아쓰기 검사
    "asr_model": "medium",          # Whisper 크기(small/medium/large)
    "asr_rounds": 2,
    "quality_ratio": 0.58,          # 깨진 소리 기준(같은 배역 평균 '목소리다움'의 이 배 미만이면 버림)
    "pitch_tol": 2.5,               # 성별 튐 기준(반음)
    "avg_clips": 30,                # average 방식에서 쓰는 조각 수
}


def load(path=None):
    cfg = json.loads(json.dumps(DEFAULTS))
    base = os.getcwd()
    if path:
        user = json.load(open(path, encoding="utf-8-sig"))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict) and k != "speakers":
                cfg[k].update(v)
            else:
                cfg[k] = v
        base = os.path.dirname(os.path.abspath(path))
    for k in ("voices_dir", "output_dir", "emotions_dir"):
        if not os.path.isabs(cfg[k]):
            cfg[k] = os.path.join(base, cfg[k])
    if cfg["narrator"] not in cfg["speakers"]:
        cfg["narrator"] = next(iter(cfg["speakers"]))
    for name, s in cfg["speakers"].items():
        tot = sum(r for _, r in s["mix"])
        if abs(tot - 100) > 0.6:
            raise SystemExit(f"[설정 오류] 배역 '{name}' 섞기 비율 합이 100이 아니에요 ({tot})")
    return cfg
