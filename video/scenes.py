"""쇼츠 각 장면의 렌더링. 모든 함수는 (캔버스, 씬 로컬 시간, 리포트)를 받는다."""

from render_kit import (C, SAFE_L, SAFE_R, appear, clamp, ease_out, fng_color,
                        lerp_color, signal_style)

MID = (SAFE_L + SAFE_R) // 2


def _delta_style(pct):
    """등락률 → (색, 아이콘). 색은 항상 부호·아이콘과 함께 쓴다."""
    if pct is None:
        return C["muted"], "·"
    if pct > 0:
        return C["good"], "▲"
    if pct < 0:
        return C["critical"], "▼"
    return C["muted"], "■"


def _fmt_pct(pct, digits=1):
    return "—" if pct is None else f"{pct:+.{digits}f}%"


def _count(target, t, start, dur=1.2):
    """0에서 target까지 감속하며 올라가는 카운터."""
    return target * ease_out((t - start) / dur)


# ---------------------------------------------------------------- 1. 훅

def hook(c, t, r):
    a, dy = appear(t, 0.0, 0.45)
    c.text((MID, 470 + dy), f"{r.date} 비트코인", 44, "r", C["ink2"], a, "ma")

    a, dy = appear(t, 0.15, 0.45)
    c.text((MID, 545 + dy), "오늘의 온체인 신호", 82, "b", C["ink"], a, "ma")

    # 가격 카운트업
    a, _ = appear(t, 0.4, 0.35)
    digits = "".join(ch for ch in (r.price_usd or "") if ch.isdigit())
    if digits:
        shown = int(_count(int(digits), t, 0.4, 1.3))
        c.text((MID, 760), f"${shown:,}", 148, "b", C["ink"], a, "ma")

    color, icon = _delta_style(r.change_24h)
    a, dy = appear(t, 1.5, 0.4)
    if r.change_24h is not None:
        label = f"{icon} 24시간 {_fmt_pct(r.change_24h)}"
        pw = c.width(label, 52) + 76
        c.pill(MID - pw // 2, 960 + dy, pw, 96, None, a, outline=color, ow=4)
        c.text((MID, 1008 + dy), label, 52, "b", color, a, "mm")

    a, dy = appear(t, 1.8, 0.4)
    c.text((MID, 1110 + dy), r.price_krw or "", 50, "r", C["ink2"], a, "ma")

    a, dy = appear(t, 2.1, 0.4)
    c.text((MID, 1215 + dy),
           f"7일 {_fmt_pct(r.change_7d)}   ·   30일 {_fmt_pct(r.change_30d)}",
           42, "r", C["muted"], a, "ma")

    if r.ath_gap is not None:
        a, dy = appear(t, 2.4, 0.4)
        c.text((MID, 1300 + dy), f"사상 최고가 대비 {_fmt_pct(r.ath_gap)}",
               40, "r", C["muted"], a, "ma")


# ------------------------------------------------------- 2. 공포탐욕지수

def fear_greed(c, t, r):
    a, dy = appear(t, 0.0, 0.4)
    c.text((MID, 450 + dy), "시장 심리", 64, "b", C["ink"], a, "ma")
    c.text((MID, 540 + dy), "공포탐욕지수 (Fear & Greed Index)", 38, "r", C["muted"], a, "ma")

    cx, cy, rad, thick = MID, 1080, 300, 52
    box = [cx - rad, cy - rad, cx + rad, cy + rad]

    a, _ = appear(t, 0.35, 0.4)
    c.arc(box, 180, 360, C["grid"], thick, a)              # 트랙

    value = r.fng if r.fng is not None else 0
    p = ease_out((t - 0.5) / 1.3)
    c.arc(box, 180, 180 + 180 * (value / 100.0) * p, fng_color(value), thick, a)

    a2, _ = appear(t, 0.7, 0.5)
    c.text((cx, cy - 40), str(int(round(value * p))), 168, "b", C["ink"], a2, "ms")
    if r.fng_label:
        c.text((cx, cy + 30), r.fng_label, 52, "b", fng_color(value), a2, "ma")

    a3, dy = appear(t, 1.9, 0.4)
    c.text((cx - rad + 10, cy + 46 + dy), "0", 34, "r", C["muted"], a3, "ma")
    c.text((cx + rad - 10, cy + 46 + dy), "100", 34, "r", C["muted"], a3, "ma")
    c.text((MID, cy + 190 + dy), "0 = 극단적 공포    ·    100 = 극단적 탐욕",
           38, "r", C["ink2"], a3, "ma")

    if r.fng_avg30 is not None:
        a4, dy = appear(t, 2.3, 0.4)
        c.text((MID, cy + 265 + dy), f"최근 30일 평균 {r.fng_avg30}",
               40, "r", C["muted"], a4, "ma")


# ------------------------------------------------------ 3. 온체인 30일 추세

def onchain(c, t, r):
    a, dy = appear(t, 0.0, 0.4)
    c.text((MID, 450 + dy), "네트워크 상태", 64, "b", C["ink"], a, "ma")
    c.text((MID, 540 + dy), "30일 전 대비 변화율", 38, "r", C["muted"], a, "ma")

    rows = [("해시레이트", r.hashrate_trend, "채굴자가 투입한 연산력"),
            ("활성 주소 수", r.active_addr_trend, "실제로 움직인 지갑 수"),
            ("트랜잭션 수", r.tx_trend, "네트워크 위 거래 건수")]
    rows = [row for row in rows if row[1] is not None]
    if not rows:
        return

    span = max(12.0, max(abs(v) for _, v, _ in rows) * 1.25)
    base_x, half = MID, (SAFE_R - SAFE_L) // 2 - 30
    top, gap, bh = 700, 230, 58

    c.d.line([base_x, top - 40, base_x, top + gap * (len(rows) - 1) + bh + 40],
             fill=C["axis"] + (int(255 * clamp(a)),), width=2)     # 0 기준선

    for i, (name, pct, desc) in enumerate(rows):
        ra, rdy = appear(t, 0.5 + i * 0.35, 0.4)
        y = top + i * gap + rdy
        c.text((SAFE_L, y - 62), name, 44, "b", C["ink"], ra)
        c.text((SAFE_L, y - 14), desc, 30, "r", C["muted"], ra)

        grow = ease_out((t - (0.7 + i * 0.35)) / 0.9)
        w = int(half * (abs(pct) / span) * grow)
        color = C["blue"] if pct >= 0 else C["red"]
        if pct >= 0:
            c.bar(base_x + 2, y + 34, w, bh, color, ra)
            c.text((base_x + w + 26, y + 34 + bh // 2), _fmt_pct(pct), 46, "b",
                   C["ink"], ra * grow, "lm")
        else:
            c.bar(base_x - 2 - w, y + 34, w, bh, color, ra)
            c.text((base_x - w - 26, y + 34 + bh // 2), _fmt_pct(pct), 46, "b",
                   C["ink"], ra * grow, "rm")

    a2, dy = appear(t, 2.4, 0.4)
    c.text((MID, top + gap * len(rows) + 60 + dy),
           "세 지표가 함께 오르면 네트워크 사용이 늘고 있다는 뜻입니다.",
           36, "r", C["ink2"], a2, "ma")


# ------------------------------------------------------------ 4. 밸류에이션

def valuation(c, t, r):
    a, dy = appear(t, 0.0, 0.4)
    c.text((MID, 470 + dy), "밸류에이션", 64, "b", C["ink"], a, "ma")
    c.text((MID, 560 + dy), "MVRV", 40, "r", C["muted"], a, "ma")

    a2, _ = appear(t, 0.35, 0.4)
    value = r.mvrv or 0.0
    shown = _count(value, t, 0.35, 1.1)
    c.text((MID, 660), f"{shown:.2f}", 210, "b", C["ink"], a2, "ma")

    # 값의 위치를 보여주는 눈금 띠 (0.5 ~ 3.7)
    lo, hi = 0.5, 3.7
    a3, dy = appear(t, 1.4, 0.45)
    x0, x1, y = SAFE_L + 20, SAFE_R - 20, 990 + dy
    c.bar(x0, y, x1 - x0, 22, C["grid"], a3, radius=11)
    pos = x0 + (x1 - x0) * clamp((value - lo) / (hi - lo))
    fill = lerp_color(C["blue"], C["orange"], clamp((value - lo) / (hi - lo)))
    c.bar(x0, y, int(pos - x0), 22, fill, a3, radius=11)
    c.d.ellipse([pos - 20, y - 9, pos + 20, y + 31],
                fill=C["ink"] + (int(255 * clamp(a3)),))
    for tick, label in ((0.5, "0.5"), (1.0, "1.0"), (2.0, "2.0"), (3.7, "3.7")):
        tx = x0 + (x1 - x0) * (tick - lo) / (hi - lo)
        c.text((tx, y + 52), label, 32, "r", C["muted"], a3, "ma")
    c.text((x0, y - 60), "저평가 구간", 34, "r", C["muted"], a3, "ls")
    c.text((x1, y - 60), "과열 구간", 34, "r", C["muted"], a3, "rs")

    a4, dy = appear(t, 2.1, 0.45)
    c.text((MID, 1180 + dy),
           "MVRV = 시가총액 ÷ 실현 시가총액\n"
           "1.0 아래면 시장 평균 매입가보다 낮은 가격,\n"
           "3 이상이면 역사적으로 과열 구간이었습니다.",
           42, "r", C["ink2"], a4, "ma", spacing=22)


# ------------------------------------------------------------- 5. 점수표

def scoreboard(c, t, r):
    a, dy = appear(t, 0.0, 0.4)
    c.text((MID, 430 + dy), "오늘의 점수표", 64, "b", C["ink"], a, "ma")
    c.text((MID, 520 + dy), "5개 항목 · 각 -2 ~ +2점 · 총점 범위 -7 ~ +7",
           38, "r", C["muted"], a, "ma")

    top, gap = 650, 148
    for i, (name, basis, score) in enumerate(r.scores[:5]):
        ra, rdy = appear(t, 0.5 + i * 0.5, 0.4)
        y = top + i * gap + rdy
        c.card(SAFE_L, y, SAFE_R - SAFE_L, 120, ra)
        c.text((SAFE_L + 36, y + 30), name, 44, "b", C["ink"], ra)
        c.text((SAFE_L + 36, y + 78), basis, 30, "r", C["muted"], ra)

        color = C["blue"] if score > 0 else (C["red"] if score < 0 else C["muted"])
        chip = f"{score:+d}"
        cw = max(112, int(c.width(chip, 52)) + 60)
        c.pill(SAFE_R - 36 - cw, y + 26, cw, 68, None, ra, outline=color, ow=4)
        c.text((SAFE_R - 36 - cw // 2, y + 60), chip, 52, "b", color, ra, "mm")

    a2, dy = appear(t, 3.2, 0.5)
    ry = top + gap * min(len(r.scores), 5) + 30
    c.rule(SAFE_L, ry + dy, SAFE_R, a2)

    total = r.total_score or 0
    a3, _ = appear(t, 3.4, 0.4)
    shown = int(round(_count(abs(total), t, 3.4, 0.9))) * (1 if total >= 0 else -1)
    c.text((SAFE_L, ry + 70), "총점", 52, "b", C["ink2"], a3, "ls")
    tcolor = C["blue"] if total > 0 else (C["red"] if total < 0 else C["muted"])
    c.text((SAFE_R, ry + 60), f"{shown:+d}", 108, "b", tcolor, a3, "rs")


# -------------------------------------------------------------- 6. 신호

def signal(c, t, r):
    color, icon = signal_style(r.signal or "")

    a, dy = appear(t, 0.0, 0.4)
    c.text((MID, 520 + dy), "오늘의 신호", 56, "r", C["ink2"], a, "ma")

    a2, dy = appear(t, 0.4, 0.5, rise=54)
    label = f"{icon} {r.signal}"
    pw = c.width(label, 92) + 120
    c.pill(MID - pw // 2, 640 + dy, pw, 168, None, a2, outline=color, ow=6)
    c.text((MID, 726 + dy), label, 92, "b", color, a2, "mm")

    a3, dy = appear(t, 1.1, 0.4)
    total = r.total_score or 0
    c.text((MID, 880 + dy), f"총점 {total:+d}", 60, "b", C["ink"], a3, "ma")
    c.text((MID, 965 + dy), "+3 이상 매수 우위 · -3 이하 매도 우위 · 그 사이 중립",
           36, "r", C["muted"], a3, "ma")

    drivers = sorted([s for s in r.scores if s[2] != 0], key=lambda s: -abs(s[2]))[:3]
    for i, (name, basis, score) in enumerate(drivers):
        ra, rdy = appear(t, 1.7 + i * 0.4, 0.4)
        y = 1090 + i * 100 + rdy
        dot = C["blue"] if score > 0 else C["red"]
        c.d.ellipse([SAFE_L + 6, y + 18, SAFE_L + 26, y + 38],
                    fill=dot + (int(255 * clamp(ra)),))
        c.text((SAFE_L + 52, y + 6), f"{name} {score:+d}", 44, "b", C["ink"], ra)
        c.text((SAFE_L + 52, y + 56), basis, 30, "r", C["muted"], ra)


# --------------------------------------------------------------- 7. 아웃트로

def outro(c, t, r):
    a, dy = appear(t, 0.0, 0.5)
    c.text((MID, 620 + dy), "매일 정오, 같은 규칙으로", 58, "b", C["ink"], a, "ma")
    c.text((MID, 710 + dy), "비트코인 온체인 데이터를 기록합니다", 46, "r", C["ink2"], a, "ma")

    a2, dy = appear(t, 0.7, 0.5)
    c.card(SAFE_L, 850 + dy, SAFE_R - SAFE_L, 250, a2)
    c.text((MID, 890 + dy),
           "본 영상은 공개 데이터를 정해진 규칙으로\n"
           "자동 분석한 정보 제공용 콘텐츠이며,\n"
           "투자 자문이 아닙니다.",
           40, "r", C["ink2"], a2, "ma", spacing=20)

    a3, dy = appear(t, 1.3, 0.5)
    c.text((MID, 1180 + dy), "데이터 출처", 34, "r", C["muted"], a3, "ma")
    c.text((MID, 1235 + dy),
           "CoinGecko · blockchain.com · mempool.space\nalternative.me · CoinMetrics",
           36, "r", C["ink2"], a3, "ma", spacing=16)
