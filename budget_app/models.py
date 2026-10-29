"""거래 구조와 입력 검증."""
import re
from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4


class AppError(Exception):
    def __init__(self, message: str, hint: str = "입력값과 --help를 확인하세요."):
        super().__init__(message)
        self.hint = hint


def valid_date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise AppError("날짜 형식 오류", "YYYY-MM-DD 형식으로 입력하세요.")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise AppError("존재하지 않는 날짜", "달력의 실제 날짜를 입력하세요.") from None
    return value


def valid_month(value: str) -> str:
    valid_date(value + "-01")
    return value


def positive(value: str | int) -> int:
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)) or int(value) <= 0:
        raise AppError("금액/개수는 양수 정수여야 합니다.", "예: 15000 (쉼표 없이 입력)")
    return int(value)


@dataclass
class Transaction:
    date: str
    type: str
    category: str
    amount: int
    memo: str = ""
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: "TX-" + uuid4().hex)

    def __post_init__(self) -> None:
        valid_date(self.date)
        self.amount = positive(self.amount)
        if self.type not in ("income", "expense"):
            raise AppError("거래 타입 오류", "income 또는 expense를 입력하세요.")
        if not isinstance(self.category, str) or not self.category.strip():
            raise AppError("카테고리가 비어 있습니다.")
        if not isinstance(self.memo, str) or not isinstance(self.tags, list):
            raise AppError("메모 또는 태그 형식 오류")
        if any(not isinstance(tag, str) for tag in self.tags):
            raise AppError("태그는 문자열 목록이어야 합니다.")
        if not isinstance(self.id, str) or not self.id:
            raise AppError("거래 id가 비어 있습니다.")
