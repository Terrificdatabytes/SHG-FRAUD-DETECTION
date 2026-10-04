from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")

PAGES = [
    "Executive Overview",
    "New Loan Application",
    "Review Queue",
    "SHG / Member Detail",
    "Topology Evidence",
    "Village Risk",
    "Explanation & Audit Report",
    "Model Performance",
    "System & Compliance",
    "How It Works",
]


def test_every_manual_page_renders():
    app = AppTest.from_file(APP_PATH, default_timeout=180).run()
    assert not app.exception
    for page in PAGES:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, page
