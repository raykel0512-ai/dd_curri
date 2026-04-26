"""
storage.py — 수기 편집 데이터 저장/불러오기
로컬: data/edits.json
"""
import json
from pathlib import Path

EDITS_PATH = Path(__file__).parent / "data" / "edits.json"


def load_edits() -> dict:
    """저장된 편집 데이터 불러오기"""
    try:
        if EDITS_PATH.exists():
            with open(EDITS_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_edits(edits: dict) -> bool:
    """편집 데이터 저장"""
    try:
        EDITS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EDITS_PATH, "w", encoding="utf-8") as f:
            json.dump(edits, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"저장 오류: {e}")
        return False
