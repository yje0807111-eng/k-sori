# -*- coding: utf-8 -*-
"""K-Narrator 명령

  python -m knarr add-voice <이름> <녹음 파일 또는 폴더> --gender 남|여 [-c 설정.json]
  python -m knarr voices [-c 설정.json]                        목소리 목록
  python -m knarr say "<문장>" [-s 배역] [-o 결과.wav] [-c 설정.json]   한 문장 빨리 들어 보기
  python -m knarr narrate <대본.txt> [-c 설정.json] [--name 이름]     대본 전체 나레이션"""
import argparse, io, os, sys

from . import config, __version__


def main(argv=None):
    if str(getattr(sys.stdout, "encoding", "")).lower().replace("-", "") != "utf8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    ap = argparse.ArgumentParser(prog="knarr", description=f"K-Narrator {__version__} — 내 컴퓨터에서 만드는 한국어 나레이션")
    ap.add_argument("-c", "--config", help="설정 파일(JSON). 없으면 기본값")
    cp = argparse.ArgumentParser(add_help=False); cp.add_argument("-c", "--config", dest="config2", help="설정 파일(JSON)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add-voice", parents=[cp], help="녹음으로 목소리 폴더 만들기")
    a.add_argument("name"); a.add_argument("src"); a.add_argument("--gender", default="", choices=["", "남", "여"])
    sub.add_parser("voices", parents=[cp], help="목소리 목록")
    s = sub.add_parser("say", parents=[cp], help="한 문장 만들어 보기")
    s.add_argument("text"); s.add_argument("-s", "--speaker"); s.add_argument("-o", "--out", default="say.wav"); s.add_argument("--seed", type=int, default=1234)
    n = sub.add_parser("narrate", parents=[cp], help="대본 전체 나레이션")
    n.add_argument("script"); n.add_argument("--name")
    args = ap.parse_args(argv)
    cfg = config.load(args.config2 or args.config)   # 명령 뒤에 준 -c 가 우선

    if args.cmd == "add-voice":
        from .prepare import build
        build(args.name, args.src, cfg["voices_dir"], args.gender, cfg["asr_model"])
    elif args.cmd == "voices":
        from .voices import list_voices
        vs = list_voices(cfg["voices_dir"])
        if not vs:
            print(f"목소리가 없어요. {cfg['voices_dir']} 에 넣거나 add-voice 로 만드세요.")
        for v in vs.values():
            print(f"- {v['name']} ({v['gender'] or '성별?'}) · 조각 {len(v['rows'])}개 · {sum(r['sec'] for r in v['rows']) / 60:.1f}분")
    elif args.cmd == "say":
        import soundfile as sf
        from .tts import Engine
        e = Engine(cfg).load(); w, sr = e.say(args.text, args.speaker or cfg["narrator"], args.seed)
        sf.write(args.out, w, sr); print("저장:", os.path.abspath(args.out))
    elif args.cmd == "narrate":
        from .pipeline import Job
        print("완성:", Job(cfg, args.script, args.name).run())


if __name__ == "__main__":
    main()
