"""P8a — the paper templates (engine content), for the template buttons and the generate
dialog. Public: they are product content, not anyone's data."""

from __future__ import annotations

from exam_engine import paper
from fastapi import APIRouter

router = APIRouter()


@router.get("/papers")
def list_paper_templates() -> dict:
    return {
        "templates": [
            {
                "code": t["code"],
                "label": t["label"],
                "title": t["title"],
                "time_min": t["time_min"],
                "sections": [
                    {
                        "title": s["title"],
                        "mode": s["mode"],
                        "marks_target": s["marks_target"],
                        "questions": sum(x["count"] for x in s["slots"]),
                    }
                    for s in t["sections"]
                ],
            }
            for t in paper.paper_templates()
        ],
        "levels": list(paper.LEVELS),
    }
