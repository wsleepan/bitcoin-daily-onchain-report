"""영상과 함께 쓸 유튜브 업로드용 제목·설명·태그를 만든다."""

TAGS = ["비트코인", "비트코인전망", "온체인분석", "공포탐욕지수", "MVRV",
        "코인", "암호화폐", "BTC", "비트코인시세", "온체인데이터"]

DISCLAIMER = ("본 영상은 공개 데이터를 정해진 규칙으로 자동 분석한 정보 제공용 "
              "콘텐츠이며, 투자 자문이 아닙니다. 제시된 신호는 단순 점수 규칙에 "
              "의한 휴리스틱 해석이며 미래 수익을 보장하지 않습니다. 투자 결정과 "
              "그 결과에 대한 책임은 전적으로 투자자 본인에게 있습니다.")

SOURCES = "CoinGecko · blockchain.com · mempool.space · alternative.me · CoinMetrics"


def title(r):
    parts = []
    if r.fng is not None:
        parts.append(f"공포탐욕 {r.fng}")
    if r.mvrv is not None:
        parts.append(f"MVRV {r.mvrv}")
    head = ", ".join(parts)
    return f"[{r.date}] 비트코인 온체인 점수 {r.total_score:+d} · {r.signal}" + (
        f" | {head}" if head else "")


def description(r):
    lines = [f"{r.date} 비트코인 온체인 일일 리포트입니다.",
             "매일 같은 규칙, 같은 지표로 기록합니다.", ""]

    lines.append("■ 가격")
    if r.price_usd:
        lines.append(f"· 현재가 {r.price_usd}" + (f" ({r.price_krw})" if r.price_krw else ""))
    for label, value in (("24시간", r.change_24h), ("7일", r.change_7d), ("30일", r.change_30d)):
        if value is not None:
            lines.append(f"· {label} {value:+.1f}%")
    if r.ath_gap is not None:
        lines.append(f"· 사상 최고가 대비 {r.ath_gap:+.1f}%")

    lines += ["", "■ 온체인 30일 추세"]
    for label, value in (("해시레이트", r.hashrate_trend), ("활성 주소 수", r.active_addr_trend),
                         ("트랜잭션 수", r.tx_trend)):
        if value is not None:
            lines.append(f"· {label} {value:+.1f}%")

    lines += ["", "■ 심리 · 밸류에이션"]
    if r.fng is not None:
        avg = f" (최근 30일 평균 {r.fng_avg30})" if r.fng_avg30 is not None else ""
        lines.append(f"· 공포탐욕지수 {r.fng} — {r.fng_label}{avg}")
    if r.mvrv is not None:
        lines.append(f"· MVRV {r.mvrv}")

    lines += ["", "■ 점수표"]
    for name, basis, score in r.scores:
        lines.append(f"· {name} {score:+d}" + (f" — {basis}" if basis else ""))
    lines.append(f"· 총점 {r.total_score:+d} → {r.signal}")
    lines.append("  (+3 이상 매수 우위 / -3 이하 매도 우위 / 그 사이 중립)")

    lines += ["", f"■ 데이터 출처", SOURCES, "", "■ 유의사항", DISCLAIMER, "",
              " ".join("#" + tag for tag in TAGS)]
    return "\n".join(lines)


def write(r, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("=== 제목 ===\n" + title(r) + "\n\n")
        f.write("=== 설명 ===\n" + description(r) + "\n\n")
        f.write("=== 태그 ===\n" + ", ".join(TAGS) + "\n")
    return path
