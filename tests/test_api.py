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
    assert post(place="Pleasanton, CA", text="pizza box")["action"] == "compost"
    assert post(place="Austin, TX, USA", text="pizza box")["action"] == "recycle"
def test_similar_name_does_not_match():
    assert post(place="Austin, Minnesota", text="pizza box")["scope"] == "global"
def test_unknown_place_uses_global():
    r = post(place="Nairobi, Kenya", text="pizza box"); assert r["scope"] == "global"
def test_unknown_item_is_safe():
    r = post(place="", text="mystery thing"); assert r["safe"] and r["action"] == "trash"
def test_output_is_html_safe():
    assert "<" not in post(place="x", text="<script>pizza")["item"]
