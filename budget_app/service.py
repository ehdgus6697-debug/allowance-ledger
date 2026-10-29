"""카테고리, 예산, 거래, CSV의 업무 규칙."""
import csv
from dataclasses import replace
from pathlib import Path
from typing import Iterator
from .models import AppError, Transaction, positive, valid_date, valid_month
from .storage import JsonlStore, TransactionRepository, atomic_writer

COLUMNS = ["date", "type", "category", "amount", "memo", "tags"]


class BudgetService:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        for name in ("transactions", "categories", "budgets"):
            path = directory / f"{name}.jsonl"
            if not path.exists():
                JsonlStore(path).write([])
        self.repo = TransactionRepository(directory / "transactions.jsonl")
        self.categories = JsonlStore(directory / "categories.jsonl")
        self.budgets = JsonlStore(directory / "budgets.jsonl")
        if not list(self.categories.read()):
            self.categories.write({"name": name} for name in ("food", "transport", "rent", "salary", "etc"))

    def category_names(self) -> list[str]:
        names = []
        for row in self.categories.read():
            if set(row) != {"name"} or not isinstance(row["name"], str) or not row["name"].strip():
                raise AppError("categories.jsonl 형식 오류", '각 행은 {"name": "food"} 형식이어야 합니다.')
            names.append(row["name"])
        return names

    def check_category(self, name: str) -> None:
        if name not in self.category_names():
            raise AppError(f"등록되지 않은 카테고리: {name}", "category list로 확인하거나 category add로 등록하세요.")

    def category_change(self, action: str, name: str) -> None:
        name = name.strip()
        names = self.category_names()
        if not name:
            raise AppError("카테고리 이름이 비어 있습니다.")
        if action == "add":
            if name in names:
                raise AppError("이미 등록된 카테고리입니다.")
            names.append(name)
        else:
            self.check_category(name)
            if any(item.category == name for item in self.repo.all()):
                raise AppError("사용 중인 카테고리는 삭제할 수 없습니다.", "해당 거래를 수정하거나 삭제한 뒤 다시 시도하세요.")
            if len(names) == 1:
                raise AppError("최소 한 개의 카테고리를 유지해야 합니다.")
            names.remove(name)
        self.categories.write({"name": value} for value in names)

    def add(self, item: Transaction) -> None:
        self.check_category(item.category)
        self.repo.merge([item])

    def update(self, transaction_id: str, changes: dict) -> None:
        item = replace(self.repo.get(transaction_id), **changes)
        self.check_category(item.category)
        self.repo.merge([item], transaction_id)

    def delete(self, transaction_id: str) -> None:
        self.repo.get(transaction_id)
        self.repo.merge([], transaction_id)

    def search(self, start: str | None = None, end: str | None = None,
               category: str | None = None, type: str | None = None,
               q: str | None = None, tag: str | None = None,
               month: str | None = None) -> Iterator[Transaction]:
        if start:
            valid_date(start)
        if end:
            valid_date(end)
        if start and end and start > end:
            raise AppError("시작일이 종료일보다 늦습니다.")
        if month:
            valid_month(month)
        if type is not None and type not in ("income", "expense"):
            raise AppError("타입은 income 또는 expense를 입력하세요.")
        if category is not None:
            self.check_category(category)
        for item in self.repo.all():
            if start and item.date < start or end and item.date > end:
                continue
            if month and not item.date.startswith(month):
                continue
            if category is not None and item.category != category:
                continue
            if type and item.type != type:
                continue
            if q and q.casefold() not in item.memo.casefold():
                continue
            if tag and tag not in item.tags:
                continue
            yield item

    def budget_values(self) -> dict[str, int]:
        result = {}
        for row in self.budgets.read():
            if set(row) != {"month", "amount"} or not isinstance(row["month"], str):
                raise AppError("budgets.jsonl 형식 오류")
            result[valid_month(row["month"])] = positive(row["amount"])
        return result

    def set_budget(self, month: str, amount: str) -> None:
        values = self.budget_values()
        values[valid_month(month)] = positive(amount)
        self.budgets.write({"month": key, "amount": value} for key, value in sorted(values.items()))

    def summary(self, month: str, top: int) -> None:
        income = expense = count = 0
        categories: dict[str, int] = {}
        for item in self.search(month=month):
            count += 1
            if item.type == "income":
                income += item.amount
            else:
                expense += item.amount
                categories[item.category] = categories.get(item.category, 0) + item.amount
        if count == 0:
            print("데이터 없음")
        print(f"총수입: {income:,}원\n총지출: {expense:,}원\n잔액: {income - expense:,}원")
        budget = self.budget_values().get(month)
        if budget is not None:
            print(f"예산: {budget:,}원 / 사용률: {expense / budget * 100:.1f}%")
            print(f"경고: 예산 {expense - budget:,}원 초과" if expense > budget else "예산 초과 없음")
        print(f"지출 TOP {top}")
        for index, (name, amount) in enumerate(sorted(categories.items(), key=lambda pair: pair[1], reverse=True)[:top], 1):
            print(f"{index}) {name}: {amount:,}원")

    def import_csv(self, path: Path) -> int:
        incoming = []
        names = set(self.category_names())
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != COLUMNS:
                raise AppError("CSV 헤더 오류", "헤더 순서: " + ",".join(COLUMNS))
            for row in reader:
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise AppError("열 개수가 맞지 않습니다.")
                    item = Transaction(date=row["date"], type=row["type"], category=row["category"],
                                       amount=positive(row["amount"]), memo=row["memo"],
                                       tags=[tag.strip() for tag in row["tags"].split(",") if tag.strip()])
                    if item.category not in names:
                        raise AppError(f"등록되지 않은 카테고리: {item.category}")
                except AppError as error:
                    raise AppError(f"CSV {reader.line_num}행: {error}. 전체 가져오기 취소(0건 반영).",
                                   "해당 행을 수정한 뒤 다시 가져오세요.") from None
                incoming.append(item)
        if incoming:
            self.repo.merge(incoming)
        return len(incoming)

    def export_csv(self, path: Path, **filters) -> int:
        if path.resolve() in {self.directory.joinpath(name + ".jsonl").resolve()
                              for name in ("transactions", "categories", "budgets")}:
            raise AppError("저장 파일을 내보내기 대상으로 사용할 수 없습니다.", "다른 CSV 경로를 지정하세요.")
        count = 0
        with atomic_writer(path) as stream:
            writer = csv.writer(stream)
            writer.writerow(COLUMNS)
            for item in self.search(**filters):
                writer.writerow([item.date, item.type, item.category, item.amount, item.memo, ",".join(item.tags)])
                count += 1
        return count
