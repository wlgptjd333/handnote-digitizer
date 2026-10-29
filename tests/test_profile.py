"""양식 프로필(worklog_v1)과 생성된 템플릿이 서로 맞는지 확인."""
import csv
from itertools import combinations

from PIL import Image

from src.profile import ROOT, iter_boxes, load_profile

PROFILE = load_profile("worklog_v1")


def overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def test_field_ids_unique():
    ids = [f["id"] for f in PROFILE["fields"]]
    assert len(ids) == len(set(ids))


def test_boxes_inside_page():
    w, h = PROFILE["size"]
    for fid, option, (x, y, bw, bh) in iter_boxes(PROFILE):
        assert 0 <= x and 0 <= y and x + bw <= w and y + bh <= h, (fid, option)


def test_boxes_do_not_overlap():
    boxes = [(f"{fid}:{opt}", box) for fid, opt, box in iter_boxes(PROFILE)]
    boxes += [(f"marker{i}", box) for i, box in enumerate(PROFILE["markers"])]
    for (name_a, a), (name_b, b) in combinations(boxes, 2):
        assert not overlaps(a, b), (name_a, name_b)


def test_template_matches_profile():
    with Image.open(ROOT / PROFILE["template"]) as img:
        assert img.size == tuple(PROFILE["size"])


def test_answer_csv_has_all_fields():
    with open(ROOT / "labels" / "answers_template.csv", encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    assert header == ["sample_id", "writer_id"] + [f["id"] for f in PROFILE["fields"]]
