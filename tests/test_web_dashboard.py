from pathlib import Path
ROOT = Path(__file__).parents[1]
def test_dashboard_assets_exist():
    assert (ROOT / "apps/web/index.html").exists()
    assert (ROOT / "apps/web/styles.css").exists()
    assert (ROOT / "apps/web/app.js").exists()
def test_dashboard_uses_api_contract():
    js=(ROOT / "apps/web/app.js").read_text()
    assert "/health" in js
    assert "/v1/business/snapshot" in js
