# K-Sori (케이소리) — 내 컴퓨터에서 만드는 한국어 목소리·나레이션

> **소리(Sori)** = 한국어로 "목소리, 소리". 내 목소리를 섞고, 감정을 담고, 긴 대본을 자연스러운 나레이션으로.

**무료 · 횟수 제한 없음 · 인터넷에 목소리를 올리지 않음.**
내 목소리(또는 허락받은 가족 목소리)로, 대본 한 편을 사람이 다듬은 것처럼 자연스러운 나레이션으로 만들어 줍니다.
[Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)(Apache-2.0)를 바탕으로, 실제 유튜브 설교·이야기 영상을 매일 만들면서 다듬은 "나레이션 공정"을 담았습니다.

> English summary: **K-Sori** ("sori" = voice/sound in Korean) is a local, free Korean voice & narration pipeline on top of Qwen3-TTS. Mix voices, add emotions (calm, happy, sad, angry, fearful, disgust, surprised), record several takes per sentence, auto-reject broken / gender-flipped takes, verify with Whisper and re-record only the wrong sentences, then assemble with natural pauses and a timeline CSV for subtitles.

## 🎬 K-Sori 로 만든 영상
매일 올라가는 복음 이야기·설교 영상의 나레이션을 **모두 K-Sori 로 만들고 있습니다.** 어떤 소리가 나는지 영상으로 직접 들어 보세요.

[![YouTube 호세아 @천국메신저](https://img.shields.io/badge/YouTube-%ED%98%B8%EC%84%B8%EC%95%84%20%40%EC%B2%9C%EA%B5%AD%EB%A9%94%EC%8B%A0%EC%A0%80-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/@%EC%B2%9C%EA%B5%AD%EB%A9%94%EC%8B%A0%EC%A0%80)
[![TikTok @gi7777gi](https://img.shields.io/badge/TikTok-%40gi7777gi-000000?logo=tiktok&logoColor=white)](https://www.tiktok.com/@gi7777gi)
[![Instagram @parkgisun777](https://img.shields.io/badge/Instagram-%40parkgisun777-E4405F?logo=instagram&logoColor=white)](https://www.instagram.com/parkgisun777/)

- **YouTube — 호세아 (@천국메신저)**: https://www.youtube.com/@천국메신저
- **TikTok — @gi7777gi**: https://www.tiktok.com/@gi7777gi
- **Instagram — @parkgisun777**: https://www.instagram.com/parkgisun777/

> 이 도구가 도움이 됐다면 채널 **구독·좋아요**와 이 저장소의 **⭐ Star** 가 큰 힘이 됩니다.
> K-Sori 로 영상을 만드셨다면 설명란에 "나레이션: K-Sori" 와 이 저장소 주소를 적어 주세요 — 서로의 채널을 알리는 데 도움이 돼요.

## 무엇이 다른가요?
TTS 프로그램은 많지만, 긴 대본을 그대로 넣으면 중간에 소리가 깨지거나, 말끝이 잘리거나, 글을 틀리게 읽는 문장이 꼭 섞입니다. K-Sori 는 그걸 사람이 일일이 듣고 고치지 않아도 되게 만든 **공정**입니다.

| 단계 | 하는 일 |
|---|---|
| 목소리 만들기 | 녹음 파일만 주면 받아쓰기로 2~12초 조각을 자동으로 만듦 |
| 목소리 섞기 | 여러 목소리를 비율대로 섞어 새 목소리(예: A 60 + B 40) |
| 안정적인 목소리 | 조각 30개의 '목소리 숫자' 평균(average) — 한 조각보다 훨씬 고르게 |
| 여러 번 녹음 | 문장마다 3번, 점수 나쁜 30% 는 5번까지 녹음해서 음높이가 가장 안정적인 것을 고름 |
| 깨진 소리 거르기 | '목소리다움'이 평균보다 크게 떨어진 테이크는 버림 |
| 성별 튐 거르기 | 남녀를 섞은 배역이 갑자기 반대 성별처럼 들리는 테이크는 버림 |
| 받아쓰기 검사 | Whisper 로 받아써서 글이 다르거나 끝이 잘린 문장만 다시 녹음(장·절 숫자는 정확히 비교) |
| 끝소리 보호 | 문장 끝에 잠깐 " 네." 를 붙여 만든 뒤 잘라내서 마지막 음절이 끊기지 않게 |
| 이어 붙이기 | 문장 0.9초 · 쉼표 0.55초 · 문단 1.15초 · 장면 1.5초 쉼, 대사 배역 크기 맞춤 |
| 감정 넣기 | 같은 목소리로 차분함·기쁨·슬픔·분노·두려움·혐오·놀람(감정 숫자 × 세기), 배역마다 또는 줄마다, 감정 견본 페이지 |
| 결과 | `narration.wav` + 문장마다 시각이 적힌 `timeline.csv`(자막·영상 맞추기용) + 검사표 |

## 필요한 것
- Windows 10/11 (리눅스도 파이썬 명령으로 돌아감)
- **엔비디아 그래픽카드 6GB 이상** (1.7B 모델이 약 4GB 사용. RTX 2060 에서 개발·시험)
- 파이썬 3.10 이상, 저장 공간 약 15GB(모델·라이브러리)
- 처음 실행할 때 인터넷(모델 내려받기). 그다음부터는 인터넷 없이도 됩니다.

## 설치
1. 이 저장소를 내려받아 압축을 풉니다(한글·띄어쓰기 없는 경로 권장, 예: `D:\k-sori`).
2. `설치.bat` 을 더블클릭합니다. (가상환경 · 그래픽카드용 torch · 나머지를 자동으로 깝니다)

## 바로 써 보기 (공개 목소리 42명 들어 있음)
녹음이 없어도 됩니다. [Mozilla Common Voice](https://commonvoice.mozilla.org) 한국어(CC0, 누구나 자유롭게 사용)에서 고른 **목소리 42명**(남 25 · 여 17)이 `voices\` 에 들어 있어요. 목록과 성별·나이·높이는 [`voices/목록.md`](voices/목록.md).
```bat
ksori.bat voices -c examples\설정_견본.json
ksori.bat narrate examples\대본_견본.txt -c examples\설정_견본.json
```
→ 남자 목소리 나레이션 + 여자 목소리 대사 + 두 목소리를 섞은 문장이 `output\대본_견본\narration.wav` 로 나옵니다.
공개 목소리는 사람마다 녹음이 4개(20초 안팎)뿐이라, 마음에 드는 목소리 2~3개를 섞어 쓰면 더 안정적이에요. 예: `"mix": [["CV001_세훈", 50], ["CV012_형준", 50]]`

## 처음 해 보기 (내 목소리로)
```bat
:: 1) 내 목소리 만들기 (녹음 파일 또는 폴더, 잡음 없는 5분 이상 권장)
ksori.bat add-voice 내목소리 D:\녹음\내목소리.mp3 --gender 남

:: 2) 설정 파일 만들기: examples\설정_예시.json 을 이 폴더에 "설정.json" 으로 복사하고
::    speakers 의 목소리 이름을 "내목소리" 로 바꿉니다. (아래 '설정' 참고)

:: 3) 한 문장 들어 보기
ksori.bat say "안녕하세요, 오늘도 좋은 하루 되세요."

:: 4) 대본 전체 나레이션
ksori.bat narrate examples\대본_예시.txt
```
결과는 `output\<대본 이름>\narration.wav` 에 생깁니다. 중간에 멈춰도 다시 실행하면 만든 테이크는 건너뛰고 이어서 합니다.

## 대본 쓰는 법
- 한 줄 = 한 문장(또는 쉼표로 이어지는 한 덩이). **빈 줄 = 문단 쉼.**
- `"대사"`, `'속마음'` 처럼 따옴표 안은 대사 → 설정의 `quote_speakers` 순서대로 배역이 바뀝니다.
- 따옴표지만 대사가 아닌 말(예: `'가족'`)은 `word_quotes` 에 적으면 나레이션이 그대로 읽습니다.
- 줄에 `//` 만 쓰면 장면이 바뀌는 큰 쉼(1.5초).
- 줄 앞에 `[배역이름]` 을 쓰면 그 줄만 그 배역으로 읽습니다(감정 나레이션 등).
- 숫자는 소리로 읽는 법을 `tts_fix` 에 적으세요. 예: `["21장 4절", "이십일 장 사 절"]` (받아쓰기 검사는 숫자 그대로 비교해서 12장으로 잘못 읽으면 걸러 냄)

## 설정 (설정.json)
| 이름 | 뜻 | 기본 |
|---|---|---|
| `model` | `"1.7"`(권장) 또는 `"0.6"`(가벼움, 품질 낮음) | `"1.7"` |
| `voices_dir`, `output_dir` | 목소리 폴더, 결과 폴더(설정 파일 기준 경로) | `voices`, `output` |
| `speakers` | 배역 = `{"mix": [[목소리, 비율], ...], "method": "average"/"single", "gender": "남"/"여"}` | |
| `narrator` | 기준 배역(대사 배역 크기를 여기에 맞춤) | `나레` |
| `quote_speakers` | 따옴표 대사가 나오는 순서대로 배역 | `[]` |
| `takes`, `max_takes`, `retry_frac` | 기본 녹음 수, 나쁜 문장 최대 녹음 수, 나쁜 문장 비율 | `3, 5, 0.3` |
| `asr`, `asr_model` | 받아쓰기 검사 사용, Whisper 크기 | `true, medium` |
| `pause` | 쉼(초) `sent comma para qpara spk section` | `0.9 0.55 1.15 0.7 0.6 1.5` |
| `quality_ratio`, `pitch_tol` | 깨진 소리 기준, 성별 튐 기준(반음) | `0.58, 2.5` |

`gender` 를 적어 두면 그 배역의 성별 튐 검사를 합니다. 남녀 목소리를 섞은 배역일수록 꼭 적으세요.

## 감정 넣기 (차분함 · 기쁨 · 슬픔 · 분노 · 두려움 · 혐오 · 놀람)
목소리 숫자에 **감정 방향**을 더해서, 같은 목소리로 감정을 실어 읽게 합니다. (1.7B 모델 권장 — 0.6B 는 감정이 잘 안 실려요)

**1) 감정 숫자 만들기 (처음 한 번, 내 컴퓨터에서만)**
감정 자료는 저장소에 들어 있지 않습니다. 둘 중 하나를 준비하세요.
- **RAVDESS** — https://zenodo.org/records/1188976 에서 `Audio_Speech_Actors_01-24.zip`(또는 노래판 `Audio_Song_Actors_01-24.zip`)을 받아 압축을 풉니다.
  ⚠ RAVDESS 는 **CC BY-NC-SA 4.0(비상업용)** 입니다. 이것으로 만든 감정 소리를 돈 버는 데 쓰지 마세요.
- **내 감정 녹음** — 상업용으로 쓰려면 이 방법. 여러 사람이 같은 글을 평소·감정으로 읽은 녹음을 이렇게 둡니다.
  ```
  감정녹음/
    철수__남/neutral/*.wav  sad/*.wav  happy/*.wav  angry/*.wav
    영희__여/neutral/*.wav  sad/*.wav  ...
  ```
```bat
ksori.bat emotion-build D:\자료\RAVDESS
```
→ `emotions\emotions_1.7.pt` 가 생깁니다(같은 성별 사람들의 "감정 − 평소" 평균).

**2) 감정 배역 만들기 (설정.json)**
```json
"speakers": {
  "나레":     {"mix": [["내목소리", 100]], "gender": "남"},
  "슬픈나레": {"mix": [["내목소리", 100]], "gender": "남", "emotion": {"type": "sad",   "alpha": 5}},
  "기쁜아이": {"mix": [["딸목소리", 100]], "gender": "여", "emotion": {"type": "happy", "alpha": 1.5}}
}
```
**3) 대본에서 쓰기**
- 대사는 `quote_speakers` 에 감정 배역 이름을 넣으면 됩니다.
- 나레이션 한 줄만 감정을 넣으려면 줄 앞에 `[슬픈나레]` 를 붙이세요: `[슬픈나레] 그날 밤 그는 홀로 울었습니다.`

**세기(alpha) 고르는 법** — 사람마다 한계가 달라요. 견본 명령으로 한 번에 들어 보고 고르세요.
```bat
ksori.bat emotion-samples 내목소리
```
→ `output\감정견본_내목소리\듣기.html` : 같은 문장을 감정마다 세기 3단계(추천값·낮게·높게)로 만들어 줍니다. 아이 목소리는 `voice.json` 에 `"age": "아이"` 를 적으면 낮은 세기로 시작해요.
| 감정 | 남자 어른 | 여자 어른 | 아이 |
|---|---|---|---|
| 슬픔 `sad` | 4.5 ~ 5 | 2 ~ 2.5 | 1.5 ~ 2 |
| 기쁨 `happy` | 3 ~ 4 | 1.5 ~ 2 | 1 ~ 1.5 |
| 분노 `angry` | 2 ~ 3 | 1 ~ 3 | 1 ~ 2 |
| 차분함 `calm` · 두려움 `fearful` · 혐오 `disgust` · 놀람 `surprised` | 2.5 ~ 3 | 1.5 | 1 ~ 1.5 |

`type` 은 영어(`sad`)나 한국어(`슬픔`) 둘 다 됩니다.
- 너무 세면 목소리가 다른 사람처럼 바뀌거나 기계음이 납니다. 한 문장은 좋은데 다음 문장에서 목소리가 변하면 세기를 0.5 낮추세요.
- 감정 배역을 감정 없는 목소리와 섞으면 감정이 옅어지고, 센 감정(8 이상) 두 개를 섞으면 소리가 찢어집니다.
- 아이 목소리는 감정 자료가 어른이라 세기를 올리면 어른처럼 들려요 → 낮게.

## 결과 폴더
```
output/<이름>/
  narration.wav   완성 나레이션 (24kHz)
  timeline.csv    번호, 목소리, 시작(초), 끝(초), 테이크, 쉼, 글
  report.csv      받아쓰기 검사 결과(합격 O/X, 받아쓴 글)
  takes/          문장별 테이크 — 마음에 안 드는 문장은 selection.json 에 {"번호": {"pin": 테이크, "ok": true}} 로 고정 가능
  log.txt
```

## 속도
RTX 2060(6GB) 기준, 문장 67개(약 5분 나레이션)에 녹음·검사까지 약 1시간 30분. 그래픽카드가 좋을수록 빨라집니다.

## 알려진 한계
- 한국어로만 다듬고 시험했습니다(다른 언어는 `language` 를 바꾸면 돌아가지만 검사 기준은 한국어용).
- Qwen 계열은 가끔 말끝을 흐리거나 문장 끝에 군소리를 붙입니다 — 끝소리 보호와 받아쓰기 검사로 대부분 걸러 내지만 완벽하지는 않아요. `report.csv` 의 X 표시 문장은 직접 들어 보세요.
- 감정 자료는 직접 준비해야 합니다(위 '감정 넣기'). RAVDESS 노래판에는 혐오·놀람이 없어요.

## 지켜 주세요
- **본인 목소리 또는 사용을 허락받은 목소리만** 쓰세요. 다른 사람인 척하거나 속이는 데 쓰면 안 됩니다.
- 이 저장소에 들어 있는 목소리는 Common Voice(CC0) 공개 목소리뿐입니다. 이름은 구별용 별명이며 기증자를 찾아내려 하면 안 됩니다.

## 응원하기 💛
K-Sori 는 무료입니다. 도움이 됐다면 이렇게 응원해 주세요.
- 이 저장소에 **⭐ Star** 누르기 (다른 사람들이 찾기 쉬워져요)
- 유튜브 **[호세아 @천국메신저](https://www.youtube.com/@%EC%B2%9C%EA%B5%AD%EB%A9%94%EC%8B%A0%EC%A0%80)** · 틱톡 **[@gi7777gi](https://www.tiktok.com/@gi7777gi)** · 인스타그램 **[@parkgisun777](https://www.instagram.com/parkgisun777/)** 구독·좋아요·팔로우
- 저장소 위쪽 **Sponsor(후원)** 버튼
- 고장 신고·좋은 생각은 [Issues](../../issues) 에 남겨 주세요

## 라이선스
Apache License 2.0 (`LICENSE`). 쓰는 모델·라이브러리의 라이선스는 `NOTICE` 를 보세요.
