#!/usr/bin/env python3
"""일일 온체인 리포트 → 유튜브 쇼츠(9:16 MP4) 생성기.

사용법:
    python3 video/make_short.py                     # 가장 최근 리포트
    python3 video/make_short.py reports/2026-07-02.md
    python3 video/make_short.py --out out/btc.mp4
"""

import argparse
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metadata                                                   # noqa: E402
import scenes                                                    # noqa: E402
from render_kit import (BOTTOM, C, FPS, H, SAFE_L, SAFE_R, TOP, W,  # noqa: E402
                        Canvas, clamp, ease_out)
from report_parser import parse                                  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (렌더 함수, 길이(초)) — 합계가 60초를 넘지 않게 유지한다.
TIMELINE = [
    (scenes.hook, 5.0),
    (scenes.fear_greed, 7.5),
    (scenes.onchain, 8.5),
    (scenes.valuation, 8.0),
    (scenes.scoreboard, 10.5),
    (scenes.signal, 8.5),
    (scenes.outro, 5.5),
]
FADE = 0.35   # 씬 전환 크로스페이드 길이


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def chrome(c, gt, total, r):
    """모든 씬 위에 공통으로 올라가는 머리글과 진행 막대."""
    c.text((SAFE_L, TOP - 90), "비트코인 온체인 리포트", 34, "b", C["muted"], 0.9)
    c.text((SAFE_R, TOP - 90), r.date, 34, "r", C["muted"], 0.9, "ra")
    c.rule(SAFE_L, TOP - 34, SAFE_R, 0.55)
    y = BOTTOM + 60
    c.bar(SAFE_L, y, SAFE_R - SAFE_L, 8, C["grid"], 0.9, radius=4)
    c.bar(SAFE_L, y, int((SAFE_R - SAFE_L) * clamp(gt / total)), 8, C["blue"], 1.0,
          radius=4)


def render_frames(r, total):
    """타임라인을 프레임 단위로 순회하며 RGB 바이트를 만들어 낸다."""
    for i in range(int(round(total * FPS))):
        gt = i / FPS
        c = Canvas()
        elapsed = 0.0
        for fn, dur in TIMELINE:
            if elapsed <= gt < elapsed + dur:
                fn(c, gt - elapsed, r)
                break
            elapsed += dur
        else:
            TIMELINE[-1][0](c, TIMELINE[-1][1], r)
        chrome(c, gt, total, r)

        img = c.finish()
        # 첫/끝 0.35초는 검정에서 페이드
        k = None
        if gt < FADE:
            k = ease_out(gt / FADE)
        elif gt > total - FADE:
            k = ease_out((total - gt) / FADE)
        if k is not None:
            from PIL import Image
            img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, clamp(k))
        yield img.tobytes()


def main():
    ap = argparse.ArgumentParser(description="일일 리포트로 유튜브 쇼츠를 만든다")
    ap.add_argument("report", nargs="?", help="리포트 마크다운 경로 (기본: 최신)")
    ap.add_argument("--out", help="출력 mp4 경로 (기본: video/out/shorts-<날짜>.mp4)")
    ap.add_argument("--force", action="store_true",
                    help="데이터가 비어 있어도 만든다")
    args = ap.parse_args()

    path = args.report
    if not path:
        found = sorted(glob.glob(os.path.join(REPO, "reports", "20*.md")))
        if not found:
            sys.exit("reports/ 에 리포트가 없습니다.")
        path = found[-1]
    if not os.path.exists(path):
        sys.exit(f"리포트를 찾을 수 없습니다: {path}")

    r = parse(path)
    missing = r.missing()
    if missing and not args.force:
        sys.exit(
            f"'{os.path.basename(path)}' 에 {', '.join(missing)} 값이 없어 영상을 "
            "만들 수 없습니다 (데이터 수집 실패한 날짜입니다).\n"
            "데이터가 있는 날짜를 지정하거나 --force 로 강행하세요.")

    total = sum(d for _, d in TIMELINE)
    out = args.out or os.path.join(REPO, "video", "out", f"shorts-{r.date}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = int(round(total * FPS))
    for i, buf in enumerate(render_frames(r, total)):
        proc.stdin.write(buf)
        if i % 60 == 0:
            print(f"  렌더링 {i}/{frames} 프레임", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg 인코딩에 실패했습니다.")

    meta = metadata.write(r, os.path.splitext(out)[0] + ".txt")
    size = os.path.getsize(out) / 1024 / 1024
    print(f"완료: {out}  ({total:.0f}초, {size:.1f}MB, {W}x{H})")
    print(f"업로드 정보: {meta}")


if __name__ == "__main__":
    main()
