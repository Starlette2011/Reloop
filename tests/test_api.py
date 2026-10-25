import os, sys
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
import validate_rules
from server import app
c = TestClient(app)
def post(**kw): return c.post("/api/classify", json=kw).json()
def test_rules_valid(): assert validate_rules.problems() == []
def test_local_beats_global():
    assert post(jurisdiction="us-ca-pleasanton", text="pizza box")["action"] == "compost"
    assert post(jurisdiction="us-tx-austin", text="pizza box")["action"] == "recycle"
def test_unknown_place_uses_global():
    r = post(jurisdiction="nowhere", text="pizza box"); assert r["scope"] == "global" and r["action"] == "trash"
def test_global_fallback_for_missing_key():
    assert post(jurisdiction="us-wa-seattle", text="cardboard")["scope"] == "global"
def test_unknown_item_is_safe():
    r = post(jurisdiction="global", text="mystery thing"); assert r["safe"] and r["action"] == "trash"
def test_jurisdictions_listed(): assert c.get("/api/jurisdictions").json()[-1]["id"] == "global"
