"""명령 해석 및 사용자 출력. update는 옵션 방식으로 고정한다."""
import argparse
import csv
import sys
from functools import wraps
from itertools import islice
from pathlib import Path
from typing import Callable, Iterable
from .models import AppError, Transaction, positive
from .service import BudgetService


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AppError(message, "해당 명령 뒤에 --help를 붙여 사용법을 확인하세요.")


def handle_errors(function: Callable[[], int]) -> Callable[[], int]:
    @wraps(function)
    def wrapper() -> int:
        try:
            return function()
        except AppError as error:
            print(f"[오류] {error}\n[힌트] {error.hint}", file=sys.stderr)
        except (OSError, UnicodeError, csv.Error) as error:
            print(f"[오류] 파일 처리 실패: {error}\n[힌트] 경로·권한·UTF-8 인코딩·CSV 따옴표를 확인하세요. 가져오기는 전체 취소됩니다.", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            print("\n[오류] 입력 취소\n[힌트] 명령을 다시 실행해 입력을 완료하세요.", file=sys.stderr)
        return 1
    return wrapper


def parser() -> Parser:
    root = Parser(description="나만의 용돈 기입장 (Python 표준 라이브러리)")
    root.add_argument("--data-dir", default="./data", help="저장 폴더 (기본 ./data)")
    sub = root.add_subparsers(dest="command", required=True, parser_class=Parser)
    commands = {}
    for name in ("add", "list", "search", "summary", "budget", "category", "update", "delete", "import", "export"):
        commands[name] = sub.add_parser(name)
    commands["list"].add_argument("--limit", type=positive, default=20)
    for name in ("search", "export"):
        commands[name].add_argument("--from", dest="start")
        commands[name].add_argument("--to", dest="end")
    for name in ("category", "type", "q", "tag"):
        commands["search"].add_argument("--" + name)
    commands["summary"].add_argument("--month", required=True)
    commands["summary"].add_argument("--top", type=positive, default=3)
    budgets = commands["budget"].add_subparsers(dest="action", required=True, parser_class=Parser)
    setter = budgets.add_parser("set")
    setter.add_argument("--month", required=True)
    setter.add_argument("--amount", required=True)
    categories = commands["category"].add_subparsers(dest="action", required=True, parser_class=Parser)
    for action in ("add", "list", "remove"):
        categories.add_parser(action)
    commands["delete"].add_argument("--id", required=True)
    commands["update"].add_argument("--id", required=True)
    for name in ("date", "type", "category", "amount", "memo", "tags"):
        commands["update"].add_argument("--" + name)
    commands["import"].add_argument("--from", dest="source", required=True)
    commands["export"].add_argument("--out", required=True)
    commands["export"].add_argument("--month")
    return root


def tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def show(rows: Iterable[Transaction]) -> None:
    count = 0
    for item in rows:
        # repr로 메모의 줄바꿈/제어 문자가 표를 깨지 않게 한다.
        print(f"{item.id} | {item.date} | {item.type:7} | {item.category} | {item.amount:,} | {item.memo!r} | {','.join(item.tags)!r}")
        count += 1
    if not count:
        print("데이터 없음")


@handle_errors
def main() -> int:
    args = parser().parse_args()
    service = BudgetService(Path(args.data_dir))
    command = args.command
    if command == "add":
        print("카테고리: " + ", ".join(service.category_names()))
        item = Transaction(date=input("날짜(YYYY-MM-DD): ").strip(),
                           type=input("타입(income/expense): ").strip(),
                           category=input("카테고리: ").strip(),
                           amount=positive(input("금액(양수 정수): ").strip()),
                           memo=input("메모(선택): "), tags=tags(input("태그(쉼표 구분, 선택): ")))
        service.add(item)
        print(f"[저장 완료] id={item.id}")
    elif command == "list":
        show(islice(service.repo.all(), args.limit))
    elif command == "search":
        rows = service.search(args.start, args.end, args.category, args.type, args.q, args.tag)
        show(rows)
    elif command == "summary":
        service.summary(args.month, args.top)
    elif command == "category":
        if args.action == "list":
            print("\n".join(service.category_names()))
        else:
            service.category_change(args.action, input("카테고리명: "))
            print("[완료] 카테고리 " + args.action)
    elif command == "budget":
        service.set_budget(args.month, args.amount)
        print("[저장 완료] 예산")
    elif command == "update":
        changes = {name: getattr(args, name) for name in ("date", "type", "category", "amount", "memo", "tags")
                   if getattr(args, name) is not None}
        if not changes:
            raise AppError("수정할 항목이 없습니다.", "--amount 1000 등 수정할 항목을 지정하세요.")
        if "tags" in changes:
            changes["tags"] = tags(changes["tags"])
        service.update(args.id, changes)
        print("[수정 완료] " + args.id)
    elif command == "delete":
        service.delete(args.id)
        print("[삭제 완료] " + args.id)
    elif command == "import":
        print(f"[완료] imported={service.import_csv(Path(args.source))}, skipped=0")
    elif command == "export":
        if not args.month and not (args.start and args.end):
            raise AppError("내보내기 기간이 필요합니다.", "--month YYYY-MM 또는 --from 날짜 --to 날짜를 지정하세요.")
        if args.month and (args.start or args.end):
            raise AppError("월과 날짜 범위 중 하나만 선택하세요.")
        count = service.export_csv(Path(args.out), month=args.month, start=args.start, end=args.end)
        print(f"[완료] {args.out} ({count} records)")
    return 0
