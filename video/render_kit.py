"""쇼츠 프레임 렌더링 기본 도구 — 팔레트, 폰트, 이징, 그리기 헬퍼."""

import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920          # 유튜브 쇼츠 9:16
FPS = 30
SAFE_L, SAFE_R = 88, 992   # 좌우 안전 여백
TOP = 300                  # 상단 UI 회피
BOTTOM = 1560              # 하단 UI(제목·버튼) 회피

# dataviz 레퍼런스 팔레트의 다크 스텝 (surface #0d0d0d 기준 6항목 검증 통과)
C = {
    "bg": (13, 13, 13),
    "surface": (26, 26, 25),
    "ink": (255, 255, 255),
    "ink2": (195, 194, 183),
    "muted": (137, 135, 129),
    "grid": (44, 44, 42),
    "axis": (56, 56, 53),
    "blue": (57, 135, 229),      # 카테고리 1 / 다이버징 양(+)극
    "orange": (217, 89, 38),     # 카테고리 2
    "aqua": (25, 158, 112),      # 카테고리 3
    "red": (230, 103, 103),      # 다이버징 음(-)극
    "good": (12, 163, 12),       # 상태색(고정) — 아이콘·라벨과 항상 함께
    "warning": (250, 178, 25),
    "critical": (208, 59, 59),
}

FONTS = {
    "b": "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
    "r": "/usr/share/fonts/truetype/nanum/NanumSquareR.ttf",
    "gb": "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "g": "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
}
_font_cache = {}


def font(size, weight="b"):
    key = (size, weight)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONTS[weight], size)
    return _font_cache[key]


# ---------- 이징 ----------

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def ease_out(t):
    """부드러운 감속 (cubic)."""
    return 1 - (1 - clamp(t)) ** 3


def ease_in_out(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def appear(t, start, dur=0.5, rise=34):
    """등장 애니메이션: (알파 0~1, y 오프셋). t·start는 씬 로컬 초."""
    p = ease_out((t - start) / dur) if dur > 0 else 1.0
    return p, int(round((1 - p) * rise))


def fade_out(t, start, dur=0.4):
    return 1.0 - ease_out((t - start) / dur)


def rgba(color, alpha):
    return color + (int(round(255 * clamp(alpha))),)


def lerp_color(a, b, t):
    t = clamp(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


# ---------- 캔버스 ----------

class Canvas:
    """RGBA 오버레이에 그린 뒤 배경과 합성하는 한 장의 프레임."""

    def __init__(self):
        self.img = Image.new("RGB", (W, H), C["bg"])
        self._glow()
        self.layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.layer)

    def _glow(self):
        """상단에 아주 옅은 광원 — 평면 배경의 단조로움만 덜어낸다."""
        sw, sh = W // 8, H // 8
        g = Image.new("L", (sw, sh), 0)
        ImageDraw.Draw(g).ellipse([-sw // 3, -sh // 5, sw + sw // 3, sh // 3], fill=52)
        g = g.filter(ImageFilter.GaussianBlur(sh // 8)).resize((W, H), Image.BICUBIC)
        self.img.paste(Image.new("RGB", (W, H), (30, 44, 64)), (0, 0), g)

    def finish(self):
        base = self.img.convert("RGBA")
        return Image.alpha_composite(base, self.layer).convert("RGB")

    # --- 텍스트 ---
    def text(self, xy, s, size=48, weight="b", color=None, alpha=1.0, anchor="la",
             spacing=None):
        if alpha <= 0.003 or not s:
            return
        f = font(size, weight)
        kw = {"font": f, "fill": rgba(color or C["ink"], alpha), "anchor": anchor}
        if spacing is not None:
            kw["spacing"] = spacing
            self.d.multiline_text(xy, s, align="center", **kw)
        else:
            self.d.text(xy, s, **kw)

    def width(self, s, size, weight="b"):
        return self.d.textlength(s, font=font(size, weight))

    # --- 도형 ---
    def bar(self, x, y, w, h, color, alpha=1.0, radius=None):
        """데이터 막대 — 끝단만 둥글게, 베이스라인에 붙는다."""
        if w <= 0 or alpha <= 0.003:
            return
        r = radius if radius is not None else min(h // 2, 10)
        r = max(0, min(r, int(w // 2)))
        self.d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=rgba(color, alpha))

    def pill(self, x, y, w, h, color, alpha=1.0, outline=None, ow=3):
        self.d.rounded_rectangle(
            [x, y, x + w, y + h], radius=h // 2,
            fill=rgba(color, alpha) if color else None,
            outline=rgba(outline, alpha) if outline else None, width=ow)

    def card(self, x, y, w, h, alpha=1.0, radius=28, fill=None):
        self.d.rounded_rectangle(
            [x, y, x + w, y + h], radius=radius,
            fill=rgba(fill or C["surface"], alpha * 0.92),
            outline=rgba((255, 255, 255), alpha * 0.10), width=2)

    def arc(self, box, start, end, color, width, alpha=1.0):
        if end <= start or alpha <= 0.003:
            return
        self.d.arc(box, start, end, fill=rgba(color, alpha), width=width)

    def rule(self, x1, y, x2, alpha=1.0, color=None):
        self.d.line([x1, y, x2, y], fill=rgba(color or C["grid"], alpha), width=2)


def fng_color(value):
    """공포탐욕지수의 다이버징 색 — 공포(붉은) ↔ 탐욕(파랑), 50이 중립.

    중립 회색은 팔레트의 #383835 대신 영상 배경에서도 보이는 밝은 회색을 쓴다.
    색은 항상 숫자·라벨과 함께 표시되므로 의미를 단독으로 지지 않는다.
    """
    mid = (107, 106, 102)
    t = abs(value - 50) / 50.0
    pole = C["red"] if value < 50 else C["blue"]
    return lerp_color(mid, pole, t)


def signal_style(signal):
    """신호 → (색, 아이콘). 색 단독이 아니라 아이콘+라벨과 함께 쓴다."""
    if "매수" in signal:
        return C["good"], "▲"
    if "매도" in signal or "차익" in signal:
        return C["critical"], "▼"
    return C["muted"], "■"
