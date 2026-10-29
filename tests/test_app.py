import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from budget_app.models import AppError, Transaction
from budget_app.service import BudgetService, COLUMNS


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.service = BudgetService(self.data)

    def run_cli(self, *args, input=None):
        return subprocess.run([sys.executable, "-m", "budget_app", "--data-dir", str(self.data), *args],
                              input=input, text=True, capture_output=True)

    def transaction(self, date="2026-10-01", **kwargs):
        return Transaction(date=date, type="expense", category="food", amount=15000, **kwargs)

    def test_crud_restart_sort_search(self):
        first = self.transaction(memo="점심", tags=["meal"])
        self.service.add(first)
        self.service.add(self.transaction("2026-10-03"))
        self.service.add(self.transaction("2026-09-01"))
        reloaded = BudgetService(self.data)
        self.assertEqual([x.date for x in reloaded.repo.all()], ["2026-10-03", "2026-10-01", "2026-09-01"])
        self.assertEqual([x.id for x in reloaded.search("2026-10-01", "2026-10-02", "food", "expense", "점심", "meal")], [first.id])
        reloaded.update(first.id, {"date": "2026-10-05", "amount": 20000})
        self.assertEqual(next(reloaded.repo.all()).id, first.id)
        reloaded.delete(first.id)
        with self.assertRaises(AppError):
            reloaded.delete(first.id)

    def test_categories_budgets_persist(self):
        self.service.category_change("add", "books")
        self.service.set_budget("2026-10", "10000")
        self.service.add(self.transaction())
        other = BudgetService(self.data)
        self.assertIn("books", other.category_names())
        self.assertEqual(other.budget_values()["2026-10"], 10000)
        with self.assertRaises(AppError):
            other.category_change("remove", "food")
        other.category_change("remove", "books")
        summary = self.run_cli("summary", "--month", "2026-10")
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertIn("150.0%", summary.stdout)
        self.assertIn("초과", summary.stdout)
        self.assertIn("데이터 없음", self.run_cli("summary", "--month", "2026-11").stdout)

    def test_csv_roundtrip_and_rollback(self):
        self.service.add(self.transaction(memo='한글, "메모"\n둘째 줄', tags=["meal", "school"]))
        path = self.root / "export.csv"
        self.assertEqual(self.service.export_csv(path, month="2026-10"), 1)
        target = BudgetService(self.root / "other")
        self.assertEqual(target.import_csv(path), 1)
        self.assertEqual(next(target.repo.all()).memo, next(self.service.repo.all()).memo)
        self.assertEqual(next(target.repo.all()).tags, ["meal", "school"])
        before = (self.data / "transactions.jsonl").read_bytes()
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(COLUMNS)
            writer.writerow(["2026-10-02", "expense", "food", "10", "", ""])
            writer.writerow(["2026-10-03", "expense", "food", "-1", "", ""])
        with self.assertRaises(AppError):
            self.service.import_csv(path)
        self.assertEqual(before, (self.data / "transactions.jsonl").read_bytes())

    def test_atomic_failure_preserves_data(self):
        item = self.transaction()
        self.service.add(item)
        before = (self.data / "transactions.jsonl").read_bytes()
        with patch("budget_app.storage.os.replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.service.update(item.id, {"amount": 10})
        self.assertEqual(before, (self.data / "transactions.jsonl").read_bytes())
        self.assertEqual(list(self.data.glob(".tmp-*")), [])

    def test_cli_interactive_errors_help(self):
        result = self.run_cli("add", input="2026-10-01\nexpense\nfood\n100\n점심\nmeal\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TX-", self.run_cli("list", "--limit", "1").stdout)
        failures = [("delete", "--id", "missing"), ("list", "--limit", "0"),
                    ("search", "--from", "2026-13-01"), ("export", "--out", "out.csv"),
                    ("import", "--from", str(self.root / "missing.csv")),
                    ("budget", "set", "--month", "2026-10", "--amount", "-2"),
                    ("update", "--id", "missing"), ("unknown",)]
        for args in failures:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("힌트", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
        for command in ("add", "list", "search", "summary", "category", "budget", "update", "delete", "import", "export"):
            self.assertEqual(self.run_cli(command, "--help").returncode, 0)

    def test_list_limit_does_not_read_entire_file(self):
        self.service.add(self.transaction())
        with (self.data / "transactions.jsonl").open("a", encoding="utf-8") as stream:
            stream.write("invalid tail\n")
        limited = self.run_cli("list", "--limit", "1")
        self.assertEqual(limited.returncode, 0, limited.stderr)
        self.assertNotEqual(self.run_cli("list", "--limit", "2").returncode, 0)

    def test_corrupt_file_no_traceback_no_overwrite(self):
        path = self.data / "transactions.jsonl"
        path.write_text('{broken}\n', encoding="utf-8")
        result = self.run_cli("list")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        with self.assertRaises(AppError):
            self.service.add(self.transaction())
        self.assertEqual(path.read_text(encoding="utf-8"), '{broken}\n')


if __name__ == "__main__":
    unittest.main()
