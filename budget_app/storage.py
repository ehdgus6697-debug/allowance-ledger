"""JSONL 스트리밍과 원자적 파일 교체. 단일 실행 프로세스를 전제로 한다."""
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator, Iterable, TextIO
from .models import AppError, Transaction


@contextmanager
def atomic_writer(path: Path) -> Iterator[TextIO]:
    # 같은 디렉터리의 임시 파일을 사용해야 os.replace가 원자적으로 동작한다.
    fd, name = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class JsonlStore:
    def __init__(self, path: Path):
        self.path = path

    def read(self) -> Iterator[dict]:
        with self.path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError("객체가 아님")
                except (ValueError, TypeError):
                    raise AppError(f"저장 파일 오류: {self.path}, {number}행",
                                   "원본을 보관하고 해당 행을 수정하거나 백업을 복원하세요.") from None
                yield row

    def write(self, rows: Iterable[dict]) -> None:
        with atomic_writer(self.path) as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")


class TransactionRepository:
    def __init__(self, path: Path):
        self.store = JsonlStore(path)

    def all(self) -> Iterator[Transaction]:
        for row in self.store.read():
            try:
                yield Transaction(**row)
            except (TypeError, AppError) as error:
                raise AppError(f"거래 파일 오류: {error}", "transactions.jsonl을 확인하거나 백업을 복원하세요.") from None

    def merge(self, incoming: list[Transaction], remove_id: str | None = None) -> None:
        incoming.sort(key=lambda item: item.date, reverse=True)

        def rows() -> Iterator[dict]:
            index = 0
            for old in self.all():
                if old.id == remove_id:
                    continue
                while index < len(incoming) and incoming[index].date >= old.date:
                    yield asdict(incoming[index])
                    index += 1
                yield asdict(old)
            for item in incoming[index:]:
                yield asdict(item)

        self.store.write(rows())

    def get(self, transaction_id: str) -> Transaction:
        for item in self.all():
            if item.id == transaction_id:
                return item
        raise AppError(f"없는 데이터: {transaction_id}", "list에서 실제 id를 확인하세요.")
