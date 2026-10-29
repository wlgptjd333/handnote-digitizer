"""양식 프로필(JSON) 읽기와 칸 좌표 꺼내기."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT / "profiles"


def load_profile(name):
    """'worklog_v1' 같은 이름이나 JSON 경로를 받아 dict 로 돌려준다."""
    path = Path(name)
    if path.suffix != ".json":
        path = PROFILES_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def iter_boxes(profile):
    """(field_id, option, [x, y, w, h]) 를 차례로 돌려준다.

    option 은 choice 칸(체크박스 여러 개 중 하나 고르기)에서만 값이 있고, 나머지는 None.
    """
    for field in profile["fields"]:
        if field["type"] == "choice":
            for option, box in field["options"].items():
                yield field["id"], option, box
        else:
            yield field["id"], None, field["box"]
