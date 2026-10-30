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


## 검증

```sh
python3 -m unittest discover -s tests -v
python3 -m budget_app delete --id 없는ID
echo $?
```

마지막 명령은 macOS/Linux에서 오류 종료 코드 1을 확인합니다. PowerShell에서는 `$LASTEXITCODE`를 사용합니다.
테스트는 임시 폴더에서 실행하므로 실제 거래 데이터에 영향을 주지 않습니다.

# 용돈 기입장 실행 예시

프로젝트 폴더에서 실행합니다. Python 3.10 이상이 필요하며, Windows에서는 `python3` 대신 `python`을 사용합니다.

## 1. 도움말

```sh
python3 -m budget_app --help
```

## 2. 거래 추가

```sh
python3 -m budget_app add
```

질문에 따라 다음 값을 한 줄씩 입력합니다.

수입 예시:

```text
2026-10-01
income
salary
300000
용돈
allowance
```

같은 명령을 다시 실행하여 지출도 입력합니다.

```text
2026-10-02
expense
food
15000
점심
meal,school
```

## 3. 거래 목록

```sh
python3 -m budget_app list
python3 -m budget_app list --limit 5
```

## 4. 거래 검색

```sh
python3 -m budget_app search --from 2026-10-01 --to 2026-10-31
python3 -m budget_app search --category food
python3 -m budget_app search --type expense
python3 -m budget_app search --q 점심
python3 -m budget_app search --tag meal
```

여러 조건을 동시에 적용할 수도 있습니다.

```sh
python3 -m budget_app search --from 2026-10-01 --to 2026-10-31 --category food --type expense --q 점심 --tag meal
```

## 5. 월별 요약

```sh
python3 -m budget_app summary --month 2026-10 --top 3
```

## 6. 예산 설정과 확인

```sh
python3 -m budget_app budget set --month 2026-10 --amount 10000
python3 -m budget_app summary --month 2026-10
```

요약에서 예산 사용률과 초과 여부를 확인합니다.

## 7. 카테고리 관리

```sh
python3 -m budget_app category add
```

카테고리 이름으로 `books`를 입력합니다.

```sh
python3 -m budget_app category list
python3 -m budget_app category remove
```

삭제할 이름으로 `books`를 입력합니다. 사용 중인 카테고리를 입력하면 삭제가 거부됩니다.

## 8. 거래 수정

`TX-실제ID`를 목록에서 확인한 거래 id로 바꿉니다.

```sh
python3 -m budget_app update --id TX-실제ID --amount 12000
python3 -m budget_app list
```

다른 항목도 수정할 수 있습니다.

```sh
python3 -m budget_app update --id TX-실제ID --memo "점심값 수정" --tags "meal,school"
```

## 9. CSV 내보내기

월 기준:

```sh
python3 -m budget_app export --out october.csv --month 2026-10
```

기간 기준:

```sh
python3 -m budget_app export --out period.csv --from 2026-10-01 --to 2026-10-15
```

## 10. CSV 가져오기

별도 폴더에 가져와 원래 데이터와 구분합니다.

```sh
python3 -m budget_app --data-dir ./import-demo import --from october.csv
python3 -m budget_app --data-dir ./import-demo list
```

CSV 헤더는 다음과 같습니다.

```csv
date,type,category,amount,memo,tags
```

같은 CSV를 반복해서 가져오면 거래가 중복 등록됩니다.

## 11. 거래 삭제

```sh
python3 -m budget_app delete --id TX-실제ID
python3 -m budget_app list
```

## 12. 오류 처리 확인

잘못된 날짜:

```sh
python3 -m budget_app search --from 2026-13-01
```

잘못된 금액:

```sh
python3 -m budget_app budget set --month 2026-10 --amount -100
```

없는 파일:

```sh
python3 -m budget_app import --from 없는파일.csv
```

없는 거래와 오류 종료 코드 확인(macOS/Linux):

```sh
python3 -m budget_app delete --id 없는ID
echo $?
```

오류 종료 코드 `1`이 출력됩니다. PowerShell에서는 `echo $?` 대신 `$LASTEXITCODE`를 사용합니다.

## 13. 자동 테스트

```sh
python3 -m unittest discover -s tests -v
```
