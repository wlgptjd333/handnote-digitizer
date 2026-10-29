# 종이 점검일지 디지털화 (가칭 InkLog)

현장에서는 종이 점검일지를 지금처럼 쓰고, **사진만 찍으면 칸별 데이터로 쌓이고 이상값은 바로 경고**되게 한다. 문서는 외부로 보내지 않고 로컬에서 처리한다.
자습시간 미니프로젝트 (교과 9 머신비전 기간에 시작).

**왜 기존 OCR(구글렌즈, 삼성노트 등)로는 부족한가:** 기존 도구는 페이지를 글자 덩어리로 돌려줄 뿐, 어느 숫자가 온도인지, 체크박스가 체크됐는지, 값이 기준을 넘었는지는 모른다. 이 프로젝트는 그 부분을 맡는다.
- 양식 정렬 → 칸별 인식 → 체크박스·서명 판정 → 범위 검증 → CSV
- 같은 데이터로 기존 도구를 baseline 삼아 정확도·시간을 비교한다

| 양식 | 내용 | 상태 |
|---|---|---|
| `worklog_v1` | 설비 일일 점검표 (칸 19개) | 양식 완성, 엔진 개발 전 |

## 시작하기

```bash
cd ~/ai_vision/handnote-digitizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 양식 만들기

```bash
python scripts/make_form.py   # templates/ profiles/ labels/ 를 다시 만든다
pytest                        # 양식 그림과 칸 좌표가 맞는지 확인
```

| 파일 | 내용 |
|---|---|
| `templates/worklog_v1.pdf` | 인쇄용 빈 양식 |
| `templates/worklog_v1.png` | 사진을 맞출 기준 이미지 (A4, 200dpi, 1654x2339) |
| `templates/worklog_v1_fields.png` | 칸 위치 확인용 (빨강 숫자 · 파랑 글자 · 초록 체크 · 보라 자유기재 · 주황 서명) |
| `profiles/worklog_v1.json` | 칸 좌표 `[x, y, w, h]`, 종류, 검증 규칙 |
| `labels/answers_template.csv` | 정답 입력 틀 |

양식을 바꾸려면 JSON을 직접 고치지 말고 `scripts/make_form.py`를 고친 뒤 다시 실행한다. 그래야 그림과 좌표가 어긋나지 않는다.

## 데이터 모으기

1. `templates/worklog_v1.pdf`를 A4에 **실제 크기(100%)**로 인쇄한다. "용지에 맞춤"은 끈다.
2. 친구들에게 그럴듯한 가상 값으로 채워 달라고 부탁한다. 실제 개인정보는 쓰지 않는다.
3. 네 귀퉁이 검은 사각형이 모두 나오게 찍거나 스캔해서 `data/raw/worklog_v1/S001.jpg` 형식으로 저장한다.
4. `labels/answers_template.csv`를 `labels/answers_worklog_v1.csv`로 복사하고, 한 장에 한 줄씩 실제로 쓴 값을 적는다.
   - `sample_id`: 파일 이름 (S001) / `writer_id`: 쓴 사람 번호 (W01 …)
   - 숫자칸: 적힌 그대로 / 체크칸: `양호`·`불량`·빈칸 / 서명칸: `1`(있음)·`0`(없음)

**원본 사진은 Git에 올리지 않는다** (`data/`는 gitignore). 정답 CSV는 커밋한다.

## 폴더

```
scripts/make_form.py  양식·프로필 생성
src/profile.py        프로필 읽기, 칸 좌표 꺼내기
src/                  엔진 (전처리 → 정렬 → 칸별 인식 → 검증)
profiles/             양식 하나 = JSON 하나
templates/            빈 양식 이미지
labels/               정답 CSV
reports/              OCR 엔진 비교, 정확도 결과
web/                  결과·수정 화면
tests/
```

## 로드맵

- [x] 단계 0: 저장소, 점검표 양식
- [ ] 손글씨 30장 수집 + 정답 CSV, 기존 도구에 한 장 넣어 보기
- [ ] 단계 1: 전처리 + 귀퉁이 표식 정렬 + 칸 자르기 + OCR 엔진 비교
- [ ] 단계 2: 숫자·체크박스·서명 판정, 범위 검증, CSV 출력, 정확도 측정
- [ ] 단계 3: FastAPI 업로드·결과·수정 화면
- [ ] 단계 4: baseline 비교 리포트 (`reports/`)
- [ ] 선택: 합성 손글씨 증강, 라즈베리파이 스캔함, 두 번째 양식
