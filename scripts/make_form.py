"""설비 일일 점검표(WL-v1) 빈 양식과 프로필 JSON 만들기.

양식 그림과 칸 좌표를 같은 코드에서 만들기 때문에, 양식을 고치면 JSON 도 저절로 맞춰진다.
(손으로 좌표를 재서 JSON 에 적으면 그림과 어긋나기 쉽다.)

실행 (프로젝트 폴더에서):
    python scripts/make_form.py

결과:
    templates/worklog_v1.png         빈 양식 (A4, 200dpi) - 사진을 맞출 기준 이미지
    templates/worklog_v1.pdf         인쇄용
    templates/worklog_v1_fields.png  칸 위치 확인용 (칸 종류별 색 상자 + id)
    profiles/worklog_v1.json         칸 좌표·종류·검증 규칙
    labels/answers_template.csv      정답 입력용 엑셀 틀
"""
import argparse
import csv
import json
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.profile import iter_boxes  # noqa: E402

FORM_ID = "worklog_v1"
DPI = 200
W, H = 1654, 2339          # A4 (210 x 297 mm) at 200dpi
LEFT, RIGHT = 150, W - 150  # 본문 좌우 여백
MARKER = 60                 # 네 귀퉁이 정렬 표식 (검은 정사각형) 한 변
LABEL_X = LEFT + 200        # 기본정보 행에서 라벨 다음 입력칸이 시작하는 x

FONT_CANDIDATES = {
    False: [
        "/mnt/c/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    ],
    True: [
        "/mnt/c/Windows/Fonts/malgunbd.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    ],
}

# 측정값: (id, 항목, 단위, 정상 범위 하한, 상한) - 범위를 벗어나면 경고
MEASUREMENTS = [
    ("m_temp", "온도", "℃", 20, 60),
    ("m_pressure", "압력", "bar", 4.0, 6.0),
    ("m_vibration", "진동", "mm/s", 0, 4.5),
    ("m_noise", "소음", "dB", 0, 85),
    ("m_runtime", "가동시간", "h", 0, 24),
]

# 점검 항목: (id, 문구) - 양호/불량 중 하나에 체크
CHECKLIST = [
    ("chk_lubricant", "윤활유 수준 적정"),
    ("chk_cover", "안전커버 체결 상태"),
    ("chk_estop", "비상정지 버튼 작동"),
    ("chk_housekeeping", "작업장 주변 정리정돈"),
    ("chk_abnormal", "이상 소음·냄새 없음"),
]

OVERLAY_COLORS = {
    "number": (220, 40, 40),
    "text": (30, 110, 230),
    "choice": (20, 160, 60),
    "freetext": (160, 60, 200),
    "signature": (230, 140, 0),
}


@lru_cache(maxsize=None)
def load_font(size, bold=False, custom=None):
    paths = ([custom] if custom else []) + FONT_CANDIDATES[bold]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise SystemExit("한글 폰트를 못 찾았습니다. --font 로 .ttf 경로를 지정하세요.")


class Form:
    def __init__(self, font_path=None):
        self.img = Image.new("L", (W, H), 255)
        self.draw = ImageDraw.Draw(self.img)
        self.font_path = font_path
        self.fields = []
        self.markers = []

    def font(self, size, bold=False):
        return load_font(size, bold, self.font_path)

    def text(self, xy, s, size=30, bold=False, anchor="la", fill=0):
        self.draw.text(xy, s, font=self.font(size, bold), fill=fill, anchor=anchor)

    def text_width(self, s, size=30, bold=False):
        left, _, right, _ = self.draw.textbbox((0, 0), s, font=self.font(size, bold))
        return right - left

    def rect(self, box, width=2, fill=None):
        x, y, w, h = box
        self.draw.rectangle([x, y, x + w - 1, y + h - 1], outline=0, width=width, fill=fill)

    def hline(self, y, x0=LEFT, x1=RIGHT, width=2, fill=0):
        self.draw.line([x0, y, x1, y], fill=fill, width=width)

    def add_field(self, fid, label, ftype, box=None, **extra):
        field = {"id": fid, "label": label, "type": ftype}
        if box is not None:
            field["box"] = list(box)
        field.update(extra)
        self.fields.append(field)


def draw_markers(form):
    """네 귀퉁이에 검은 정사각형. 찍은 사진을 양식에 맞출 때 기준점으로 쓴다."""
    for x, y in [(60, 60), (W - 60 - MARKER, 60), (60, H - 60 - MARKER), (W - 60 - MARKER, H - 60 - MARKER)]:
        form.rect((x, y, MARKER, MARKER), fill=0)
        form.markers.append([x, y, MARKER, MARKER])


def draw_header(form):
    form.text((W // 2, 150), "설비 일일 점검표", 64, bold=True, anchor="mt")
    form.text((RIGHT, 80), "양식 WL-v1", 24, anchor="ra")
    form.hline(250, width=4)


def draw_basic_info(form):
    # 점검일자: [    ] 년 [  ] 월 [  ] 일
    y = 290
    form.text((LEFT, y + 35), "점검일자", 32, bold=True, anchor="lm")
    x = LABEL_X
    for fid, label, w, unit, lo, hi in [
        ("date_year", "연도", 170, "년", 2020, 2035),
        ("date_month", "월", 100, "월", 1, 12),
        ("date_day", "일", 100, "일", 1, 31),
    ]:
        box = (x, y, w, 70)
        form.rect(box)
        form.add_field(fid, label, "number", box, valid=[lo, hi])
        form.text((x + w + 12, y + 35), unit, 32, anchor="lm")
        x += w + 12 + form.text_width(unit, 32) + 30

    # 작업자 / 설비번호
    y = 400
    form.text((LEFT, y + 35), "작업자", 32, bold=True, anchor="lm")
    box = (LABEL_X, y, 420, 70)
    form.rect(box)
    form.add_field("worker_name", "작업자", "text", box)

    form.text((900, y + 35), "설비번호", 32, bold=True, anchor="lm")
    box = (1080, y, RIGHT - 1080, 70)
    form.rect(box)
    form.add_field("equipment_id", "설비번호", "text", box, example="CNC-03")

    # 근무조: 주간 □  야간 □
    y = 510
    form.text((LEFT, y + 35), "근무조", 32, bold=True, anchor="lm")
    x = LABEL_X
    options = {}
    for name in ["주간", "야간"]:
        form.text((x, y + 35), name, 32, anchor="lm")
        x += form.text_width(name, 32) + 16
        box = (x, y + 13, 44, 44)
        form.rect(box, width=3)
        options[name] = list(box)
        x += 44 + 70
    form.add_field("shift", "근무조", "choice", options=options)


def draw_grid(form, top, cols, header_h, row_h, n_rows, headers):
    """표 테두리·칸 선·머리줄을 그리고, 각 행의 위쪽 y 목록을 돌려준다."""
    bottom = top + header_h + row_h * n_rows
    form.draw.rectangle([cols[0], top, cols[-1], top + header_h], fill=230)
    form.rect((cols[0], top, cols[-1] - cols[0], bottom - top), width=3)
    form.hline(top + header_h, cols[0], cols[-1], width=3)
    row_tops = [top + header_h + row_h * i for i in range(n_rows)]
    for ry in row_tops[1:]:
        form.hline(ry, cols[0], cols[-1])
    for cx in cols[1:-1]:
        form.draw.line([cx, top, cx, bottom], fill=0, width=2)
    for (c0, c1), title in zip(zip(cols, cols[1:]), headers):
        form.text(((c0 + c1) // 2, top + header_h // 2), title, 30, bold=True, anchor="mm")
    return row_tops


def draw_measurements(form):
    form.text((LEFT, 640), "1. 측정값", 36, bold=True, anchor="lm")
    cols = [LEFT, 560, 760, 1100, RIGHT]
    row_h = 85
    row_tops = draw_grid(form, 700, cols, 70, row_h, len(MEASUREMENTS), ["항목", "단위", "정상 범위", "측정값"])
    for ry, (fid, name, unit, lo, hi) in zip(row_tops, MEASUREMENTS):
        cy = ry + row_h // 2
        form.text((cols[0] + 24, cy), name, 30, anchor="lm")
        form.text(((cols[1] + cols[2]) // 2, cy), unit, 30, anchor="mm")
        form.text(((cols[2] + cols[3]) // 2, cy), f"{lo} ~ {hi}", 30, anchor="mm")
        # 칸 선이 OCR 에 섞이지 않게 안쪽으로 10px 들인 영역을 입력칸으로 기록
        box = (cols[3] + 10, ry + 10, cols[4] - cols[3] - 20, row_h - 20)
        form.add_field(fid, name, "number", box, unit=unit, normal=[lo, hi])


def draw_checklist(form):
    form.text((LEFT, 1235), "2. 점검 항목", 36, bold=True, anchor="lm")
    cols = [LEFT, 1100, 1302, RIGHT]
    row_h = 80
    row_tops = draw_grid(form, 1295, cols, 70, row_h, len(CHECKLIST), ["점검 항목", "양호", "불량"])
    for i, (ry, (fid, label)) in enumerate(zip(row_tops, CHECKLIST), start=1):
        form.text((cols[0] + 24, ry + row_h // 2), f"{i}) {label}", 30, anchor="lm")
        options = {}
        for name, c0, c1 in [("양호", cols[1], cols[2]), ("불량", cols[2], cols[3])]:
            box = ((c0 + c1) // 2 - 22, ry + (row_h - 44) // 2, 44, 44)
            form.rect(box, width=3)
            options[name] = list(box)
        form.add_field(fid, label, "choice", options=options, normal="양호")


def draw_remarks(form):
    form.text((LEFT, 1805), "3. 특이사항", 36, bold=True, anchor="lm")
    top, h = 1860, 230
    form.rect((LEFT, top, RIGHT - LEFT, h), width=3)
    for k in range(1, 4):  # 글씨 줄 맞추기용 연한 밑줄
        form.hline(top + 57 * k, LEFT + 15, RIGHT - 15, width=1, fill=190)
    form.add_field("remarks", "특이사항", "freetext", (LEFT + 6, top + 6, RIGHT - LEFT - 12, h - 12))


def draw_signatures(form):
    y, h = 2120, 110
    for fid, label, label_x, box_x in [
        ("sign_worker", "작업자 서명", LEFT, LABEL_X),
        ("sign_manager", "관리자 확인", 900, 1080),
    ]:
        form.text((label_x, y + h // 2), label, 32, bold=True, anchor="lm")
        box = (box_x, y, 420 if box_x == LABEL_X else RIGHT - box_x, h)
        form.rect(box)
        form.add_field(fid, label, "signature", box)


def draw_overlay(form, profile, path):
    img = form.img.convert("RGB")
    draw = ImageDraw.Draw(img)
    types = {f["id"]: f["type"] for f in profile["fields"]}
    small = form.font(18, bold=True)
    for fid, option, (x, y, w, h) in iter_boxes(profile):
        color = OVERLAY_COLORS[types[fid]]
        draw.rectangle([x, y, x + w - 1, y + h - 1], outline=color, width=4)
        name = fid if option is None else f"{fid}:{option}"
        draw.text((x + 4, y + 2), name, font=small, fill=color)
    for x, y, w, h in profile["markers"]:
        draw.rectangle([x - 6, y - 6, x + w + 5, y + h + 5], outline=(0, 180, 180), width=4)
    img.save(path, dpi=(DPI, DPI))


def build(font_path=None):
    form = Form(font_path)
    draw_markers(form)
    draw_header(form)
    draw_basic_info(form)
    draw_measurements(form)
    draw_checklist(form)
    draw_remarks(form)
    draw_signatures(form)
    profile = {
        "form_id": FORM_ID,
        "title": "설비 일일 점검표",
        "version": 1,
        "dpi": DPI,
        "size": [W, H],
        "template": f"templates/{FORM_ID}.png",
        "box_format": "[x, y, w, h] px, 템플릿 이미지 기준",
        "markers": form.markers,
        "fields": form.fields,
    }
    return form, profile


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--font", help="한글 .ttf/.ttc 경로 (기본: 맑은 고딕 → Noto CJK 순서로 찾음)")
    args = parser.parse_args()

    form, profile = build(args.font)

    templates = ROOT / "templates"
    form.img.save(templates / f"{FORM_ID}.png", dpi=(DPI, DPI))
    form.img.convert("RGB").save(templates / f"{FORM_ID}.pdf", resolution=DPI)
    draw_overlay(form, profile, templates / f"{FORM_ID}_fields.png")

    with open(ROOT / "profiles" / f"{FORM_ID}.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # 엑셀에서 한글이 안 깨지게 utf-8-sig
    with open(ROOT / "labels" / "answers_template.csv", "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(["sample_id", "writer_id"] + [field["id"] for field in profile["fields"]])

    print(f"양식 {FORM_ID}: 칸 {len(profile['fields'])}개, {W}x{H}px @ {DPI}dpi")
    for field in profile["fields"]:
        print(f"  {field['id']:<18} {field['type']:<10} {field['label']}")


if __name__ == "__main__":
    main()
