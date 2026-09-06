"""reports/YYYY-MM-DD.md 리포트에서 영상 제작에 필요한 값을 추출한다."""

import re
from dataclasses import dataclass, field

FAIL_TOKENS = ("데이터 수집 실패", "수집실패", "미수집", "데이터 소스 제한")


def _clean(value):
    """수집 실패/미수집 값을 None으로 정규화한다."""
    if value is None:
        return None
    value = value.strip().strip("*")
    if not value or any(token in value for token in FAIL_TOKENS):
        return None
    return value


def _table_row(text, label):
    """| 라벨 | 값 | 형태의 표에서 값을 뽑는다."""
    m = re.search(r"^\|\s*%s\s*\|\s*([^|]+?)\s*\|" % re.escape(label), text, re.M)
    return _clean(m.group(1)) if m else None


def _bullet(text, label):
    """- 라벨: 값 형태의 목록에서 값을 뽑는다."""
    m = re.search(r"^-\s*%s\s*:\s*(.+)$" % re.escape(label), text, re.M)
    return _clean(m.group(1)) if m else None


def _trend(value):
    """'951,623,032 (30일 추세: ▲ +2.0%)' → (본값, 추세 퍼센트)."""
    if not value:
        return None, None
    m = re.search(r"30일 추세:\s*[▲▼]?\s*([+-]?\d+(?:\.\d+)?)%", value)
    pct = float(m.group(1)) if m else None
    return value.split("(")[0].strip(), pct


def _pct(value):
    if not value:
        return None
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", value)
    return float(m.group(1)) if m else None


def _num(value):
    if not value:
        return None
    m = re.search(r"([+-]?[\d,]+(?:\.\d+)?)", value)
    return float(m.group(1).replace(",", "")) if m else None


@dataclass
class Report:
    date: str = ""
    price_usd: str = None
    price_krw: str = None
    change_24h: float = None
    change_7d: float = None
    change_30d: float = None
    ath_gap: float = None
    hashrate_trend: float = None
    active_addr: str = None
    active_addr_trend: float = None
    tx_count: str = None
    tx_trend: float = None
    mvrv: float = None
    fng: int = None
    fng_label: str = None
    fng_avg30: float = None
    scores: list = field(default_factory=list)  # [(항목명, 근거, 점수)]
    total_score: int = None
    signal: str = None

    @property
    def has_price(self):
        return self.price_usd is not None

    def missing(self):
        """영상 제작에 반드시 필요한데 비어 있는 항목."""
        required = {"현재가": self.price_usd, "총점": self.total_score, "신호": self.signal}
        return [name for name, value in required.items() if value is None]


def parse(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()

    r = Report()
    m = re.search(r"—\s*(\d{4}-\d{2}-\d{2})", text)
    r.date = m.group(1) if m else ""

    r.price_usd = _table_row(text, "현재가 (USD)")
    r.price_krw = _table_row(text, "현재가 (KRW)")
    r.change_24h = _pct(_table_row(text, "24h 변동"))
    r.change_7d = _pct(_table_row(text, "7d 변동"))
    r.change_30d = _pct(_table_row(text, "30d 변동"))
    r.ath_gap = _pct(_table_row(text, "ATH 대비"))

    _, r.hashrate_trend = _trend(_bullet(text, "해시레이트"))
    r.active_addr, r.active_addr_trend = _trend(_bullet(text, "활성 주소수"))
    r.tx_count, r.tx_trend = _trend(_bullet(text, "트랜잭션 수"))
    r.mvrv = _num(_bullet(text, "MVRV"))

    fng = _bullet(text, "Fear & Greed Index")
    if fng:
        m = re.match(r"(\d+)\s*\(([^)]+)\)", fng)
        if m:
            r.fng, r.fng_label = int(m.group(1)), m.group(2)
        m = re.search(r"30일 평균:\s*([\d.]+)", fng)
        r.fng_avg30 = float(m.group(1)) if m else None

    for label, basis, score in re.findall(
        r"^\|\s*([A-E]\.\s*[^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([+-]?\d+)\s*\|", text, re.M
    ):
        r.scores.append((label.split(".", 1)[1].strip(), _clean(basis) or "", int(score)))

    m = re.search(r"\|\s*\*\*총점\*\*\s*\|[^|]*\|\s*\*\*([+-]?\d+)\*\*\s*\|", text)
    if m:
        r.total_score = int(m.group(1))
    m = re.search(r"종합 신호:\s*\[([^\]]+)\]", text)
    if m:
        r.signal = m.group(1).strip()

    return r
