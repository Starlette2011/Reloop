"""Reloop API. Run: uvicorn server:app --reload"""
import collections, functools, glob, json, os, time
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.getenv("RELOOP_MODEL", "claude-sonnet-5-5")
MIN_CONF, MAX_B64, RATE = 0.6, 7_000_000, 30  # confidence floor, image cap, requests/min/IP
ACTIONS = {"recycle", "compost", "trash", "dropoff"}

def load_packs():
    packs = {}
    for p in glob.glob(os.path.join(BASE, "rules", "*.json")):
        d = json.load(open(p, encoding="utf-8"))
        packs[d["id"]] = d
    return packs

PACKS = load_packs()
GLOBAL = PACKS["global"]
KEYWORDS = {"bottle": "plastic_bottle", "pizza": "pizza_box", "bag": "plastic_bag", "jar": "glass_jar",
            "glass": "glass_jar", "batter": "battery", "cup": "coffee_cup", "coffee": "coffee_cup",
            "food": "food_scraps", "scrap": "food_scraps", "foam": "styrofoam", "styro": "styrofoam",
            "can": "aluminum_can", "cardboard": "cardboard", "paper": "paper", "phone": "electronics",
            "electronic": "electronics", "charger": "electronics"}
hits = collections.defaultdict(list)
app = FastAPI(title="Reloop")

class Req(BaseModel):
    jurisdiction: str = "global"
    lang: str = "en"
    text: Optional[str] = None
    image: Optional[str] = None  # base64 JPEG, never stored

def ask_claude(content, max_tokens=150):
    import anthropic
    msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=max_tokens,
                                                messages=[{"role": "user", "content": content}])
    return msg.content[0].text.strip().strip("`").removeprefix("json").strip()

def identify(req):
    """Return (key or None, confidence). Claude if configured, else keyword match on text."""
    if os.getenv("ANTHROPIC_API_KEY") and (req.image or req.text):
        keys = list(GLOBAL["items"])
        content = []
        if req.image:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": req.image}})
        content.append({"type": "text", "text": f'Item: {req.text or "(see photo)"}. Pick the closest key from {keys}, '
            'or "unknown". Reply JSON only: {"key": ..., "confidence": 0 to 1}. Be conservative: '
            "low confidence for soiled, mixed, or unclear items."})
        try:
            out = json.loads(ask_claude(content, 80))
            return out.get("key"), float(out.get("confidence", 0))
        except Exception:
            return None, 0.0
    t = (req.text or "").lower()
    for word, key in KEYWORDS.items():
        if word in t:
            return key, 0.9
    return None, 0.0

@functools.lru_cache(maxsize=2048)
def localize(item, tip, lang):
    if lang.lower().startswith("en") or not os.getenv("ANTHROPIC_API_KEY"):
        return item, tip
    try:
        out = json.loads(ask_claude(f'Translate to language code "{lang}". Reply JSON only with keys item and tip: '
                                    + json.dumps({"item": item, "tip": tip}), 300))
        return out["item"], out["tip"]
    except Exception:
        return item, tip

@app.get("/api/jurisdictions")
def jurisdictions():
    rows = [{"id": k, "name": v["name"], "verified": v.get("verified", False)} for k, v in PACKS.items() if k != "global"]
    return sorted(rows, key=lambda r: r["name"]) + [{"id": "global", "name": GLOBAL["name"], "verified": False}]

@app.post("/api/classify")
def classify(req: Req, request: Request):
    ip, now = request.client.host if request.client else "?", time.time()
    hits[ip] = [t for t in hits[ip] if now - t < 60]
    if len(hits[ip]) >= RATE:
        raise HTTPException(429, "Too many requests. Wait a minute and try again.")
    hits[ip].append(now)
    if req.image and len(req.image) > MAX_B64:
        raise HTTPException(413, "Image too large.")
    pack = PACKS.get(req.jurisdiction, GLOBAL)
    key, conf = identify(req)
    entry, scope = pack["items"].get(key), "local"
    if entry is None and key in GLOBAL["items"] and conf >= MIN_CONF:
        entry, scope = GLOBAL["items"][key], "global"
    if entry is None or conf < MIN_CONF:
        item, tip = localize(req.text or "Unclear item",
                             "Not sure. When in doubt, keep it out of recycling and check your local authority.", req.lang)
        return {"item": item, "action": "trash", "tip": tip, "source": "Safe default", "source_url": "",
                "confidence": conf, "safe": True, "scope": "default", "verified": False}
    item, tip = localize(entry[0], entry[2], req.lang)
    return {"item": item, "action": entry[1], "tip": tip, "source": entry[3], "source_url": pack.get("source_url", ""),
            "confidence": conf, "safe": False, "scope": scope, "verified": pack.get("verified", False) and scope == "local"}

app.mount("/", StaticFiles(directory=os.path.join(BASE, "static"), html=True))
