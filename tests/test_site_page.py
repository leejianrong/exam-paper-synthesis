"""The landing page and the SPA shell (EXA-170): the product name is "Exam papers", never the
repo name, and every link into this repo on GitHub points at a file that exists."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
SPA = (ROOT / "web" / "index.html").read_text(encoding="utf-8")


def test_repo_links_on_the_landing_page_point_at_files_that_exist():
    paths = re.findall(r"github\.com/leejianrong/exam-paper-synthesis/blob/main/([^\"#?]+)", SITE)
    assert paths, "the landing page links to the product spec"
    for path in paths:
        assert (ROOT / path).is_file(), path


def test_the_product_name_is_exam_papers_not_the_repo_name():
    for page in (SITE, SPA):
        assert "Exam Paper Synthesis" not in page
        assert re.search(r"<title>Exam papers\b", page)
