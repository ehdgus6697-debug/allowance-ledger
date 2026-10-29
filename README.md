# 용돈 기입장

Python 3.10 이상. 표준 라이브러리만 사용하며 별도 설치는 없습니다.

## 실행 방법

이 폴더에서 실행합니다. Windows에서는 `python3` 대신 `python`을 사용합니다.

```sh
python3 -m budget_app add
python3 -m budget_app list --limit 10
python3 -m budget_app --help
```

`add`는 날짜, 타입, 카테고리, 금액, 메모, 태그를 차례로 입력합니다.
타입은 income/expense, 금액은 양수 정수, 태그는 쉼표로 구분합니다.
각 명령에 `--help`를 붙이면 사용법이 나옵니다.

## 필수 명령

```sh
python3 -m budget_app category add
python3 -m budget_app category list
python3 -m budget_app category remove

python3 -m budget_app search --from 2026-10-01 --to 2026-10-31 --category food --type expense --q 점심 --tag meal
python3 -m budget_app summary --month 2026-10 --top 3
python3 -m budget_app budget set --month 2026-10 --amount 300000

python3 -m budget_app update --id TX-실제ID --amount 12000 --memo "점심"
python3 -m budget_app delete --id TX-실제ID

python3 -m budget_app export --out october.csv --month 2026-10
python3 -m budget_app export --out period.csv --from 2026-10-01 --to 2026-10-15
python3 -m budget_app import --from examples/sample.csv
```

- 카테고리 추가·삭제는 이름을 대화형으로 입력합니다. 사용 중인 카테고리는 삭제할 수 없습니다.
- `list`의 기본 출력은 20건입니다. 검색은 모든 조건을 만족하는 결과를 출력합니다.
- 목록과 검색은 날짜 최신순입니다. 같은 날짜는 새로 추가한 거래가 먼저 나옵니다.
- 수정은 **옵션 방식**입니다. `--date`, `--type`, `--category`, `--amount`, `--memo`, `--tags` 중 지정한 항목만 수정합니다. `--memo ""`, `--tags ""`로 비울 수 있습니다.
- 예산 조회는 `summary`에서 합니다. 사용률은 지출/예산이며 초과 시 경고합니다.
- 내보내기는 월 또는 시작일+종료일을 지정합니다. 기존 출력 파일은 교체됩니다.

## 저장 파일

실행 위치의 `./data`에 UTF-8 JSONL 파일 3개를 자동 생성합니다.

| 파일 | 저장 내용 |
|---|---|
| transactions.jsonl | id, date, type, category, amount, memo, tags |
| categories.jsonl | name |
| budgets.jsonl | month, amount |

카테고리 파일이 비어 있으면 food, transport, rent, salary, etc를 생성합니다.
거래 파일은 날짜순으로 유지되므로 직접 편집하지 말고 명령으로 수정합니다.
저장 폴더를 바꾸려면 **명령 앞에** 옵션을 둡니다.

```sh
python3 -m budget_app --data-dir ./my-data add
```

## CSV 형식

UTF-8(BOM 없음), 헤더 포함, 아래 6개 열의 순서를 고정합니다.
메모와 태그는 값만 비워 둘 수 있습니다. 카테고리는 미리 등록해야 합니다.

```csv
date,type,category,amount,memo,tags
2026-10-01,income,salary,300000,용돈,
2026-10-02,expense,food,15000,"점심, 음료","meal,school"
```

날짜는 YYYY-MM-DD, 타입은 income/expense, 금액은 양수 정수입니다.
쉼표가 들어간 값은 큰따옴표로 감쌉니다. 태그는 쉼표로 구분합니다.
가져오기는 한 행이라도 잘못되면 **전체 취소**하고 행 번호와 원인을 출력합니다.
CSV에 id가 없으므로 가져올 때 새 id를 만들며, 같은 파일을 반복해서 가져오면 중복 등록됩니다.

## 평가 때 설명할 내용

- **모듈/클래스**: models의 Transaction은 거래와 입력 검증, storage의 JsonlStore/TransactionRepository는 파일 저장과 조회, service의 BudgetService는 검색·요약·카테고리·예산 규칙, cli는 명령어 입력과 출력을 담당합니다.
- **제너레이터**: 파일을 한 줄씩 읽어 `yield`하고 검색 조건을 통과한 거래만 전달합니다. 저장 시 날짜순을 유지하므로 조회 때 전체를 메모리에 올려 정렬하지 않습니다.
- **안전한 수정/삭제**: 임시 파일에 변경 결과를 모두 쓴 후 `os.replace`로 원본을 교체합니다. 교체 전 오류가 발생하면 원본을 유지합니다.
- **데코레이터**: `@handle_errors`가 공통 예외 처리를 맡아 원인·해결 힌트와 오류 종료 코드 1을 반환합니다. 정상 종료는 0입니다.
- **타입 힌트**: `all() -> Iterator[Transaction]`은 거래를 하나씩 생성한다는 계약입니다. `tags: list[str]`은 태그의 구조를 나타냅니다. 힌트는 실행 중 검증을 대신하지 않으므로 금액·날짜 등은 별도로 검사합니다.
- **저장 형식 선택**: JSONL은 한 줄씩 읽기 쉽고 태그 목록을 그대로 저장합니다. CSV는 표 교환에 편리하지만 타입 정보가 없어 변환이 필요합니다. 내부 저장은 JSONL, 외부 교환은 CSV를 사용합니다.
- **10만 건의 한계**: 조회는 스트리밍이지만 추가·수정·삭제는 파일 전체 재작성, 요약은 전체 스캔이 필요합니다. 가져올 CSV는 검증·정렬을 위해 메모리에 보관합니다. 개선 방법은 월별 파일 분할, 외부 정렬 또는 파일 제약이 없을 때 SQLite입니다.
- **실행 조건**: 한 번에 한 명령씩 실행합니다. 동시 수정 잠금과 백업 기능은 없습니다.

## 검증

```sh
python3 -m unittest discover -s tests -v
python3 -m budget_app delete --id 없는ID
echo $?
```

마지막 명령은 macOS/Linux에서 오류 종료 코드 1을 확인합니다. PowerShell에서는 `$LASTEXITCODE`를 사용합니다.
테스트는 임시 폴더에서 실행하므로 실제 거래 데이터에 영향을 주지 않습니다.
