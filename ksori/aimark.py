# -*- coding: utf-8 -*-
"""만든 소리 파일 안에 "AI로 만든 음성" 표시를 넣어 저장 (귀에는 안 들리고 파일 정보에만 들어감).

AI 기본법(2026.1.22 시행)의 생성물 표시 취지에 맞추려는 것 — 공개할 때 영상·글에도 따로 알려 주세요."""
import soundfile as sf
from . import __version__

COMMENT = "AI-generated speech made with K-Sori / AI 합성 음성 (K-Sori)"


def write(path, data, sr, subtype="PCM_16"):
    with sf.SoundFile(path, "w", samplerate=sr, channels=1 if data.ndim == 1 else data.shape[1],
                      subtype=subtype, format="WAV") as f:
        f.comment = COMMENT
        f.software = f"K-Sori {__version__}"
        f.title = "AI-generated speech"
        f.write(data)
