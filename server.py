"""Reloop API. Run: uvicorn server:app --reload"""
import collections, functools, glob, json, os, re, time
from typing import Optional
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.getenv("RELOOP_MODEL", "claude-sonnet-5-5")
MIN_CONF, MAX_B64, RATE, TTL = 0.6, 7_000_000, 30, 7 * 86400
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
_cache = {}
app = FastAPI(title="Reloop")

class Req(BaseModel):
    place: str = ""            # free text: "Pune, India", "Lyon", "Nairobi, Kenya"
    lang: str = "en"
    text: Optional[str] = None
    image: Optional[str] = None  # base64 JPEG, never stored

def clean(s, n=300):  # strip characters that could break out of HTML
    return re.sub(r'[<>"\'&]', "", str(s))[:n]

def safe_url(u):
    p = urlparse(str(u))
    ok = p.scheme in ("http", "https") and p.netloc and not re.search(r'[\s"\'<>]', str(u))
    return str(u) if ok else ""

def has_key():
    return bool(os.getenv("ANTHROPIC_API_KEY"))

def ask_claude(content, max_tokens=150, **kw):
    import anthropic
    return anthropic.Anthropic().messages.create(
        model=MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": content}], **kw)

def text_of(msg):
    return "".join(b.text for b in msg.content if b.type == "text").strip()

def parse_json(s):
    return json.loads(s[s.index("{"): s.rindex("}") + 1])

def match_pack(place):
    p = place.lower().strip()
    for k, v in PACKS.items():
        if k != "global" and (p == k or v["name"].lower() in p):  # full "City, ST" match only
            return v
    return None

def identify(req):
    """Return (key or None, label, confidence)."""
    if has_key() and (req.image or req.text):
        content = []
        if req.image:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": req.image}})
        content.append({"type": "text", "text": f'Item: {req.text or "(see photo)"}. Reply JSON only: '
            f'{{"key": closest of {list(GLOBAL["items"])} or "other", "label": "short English name of the item", '
            '"confidence": 0 to 1}. Be conservative: low confidence for soiled, mixed, or unclear items.'})
        try:
            o = parse_json(text_of(ask_claude(content, 120)))
            return o.get("key"), clean(o.get("label", ""), 60), float(o.get("confidence", 0))
        except Exception:
            return None, "", 0.0
    t = (req.text or "").lower()
    for word, key in KEYWORDS.items():
        if word in t:
            return key, clean(req.text, 60), 0.9
    return None, clean(req.text or "", 60), 0.0

def research(place, label):
    """Search the web for official local guidance. Accepts only answers citing a page it retrieved."""
    k = (place.lower().strip(), label.lower().strip())
    if k in _cache and time.time() - _cache[k][0] < TTL:
        return _cache[k][1]
    try:
        prompt = (f'Find the official household recycling or waste guidance for "{place}" (city, county, or national '
            f'waste authority) for this item: "{label}". Use only official government or waste-authority pages. '
            'Reply JSON only: {"action": "recycle" or "compost" or "trash" or "dropoff" or "unknown", '
            '"tip": "one short sentence in your own words on how to prepare it or where to take it", '
            '"source_url": "exact URL of the page you relied on", "source_name": "name of the authority", '
            '"confidence": 0 to 1}. If you cannot find an official source covering this item, use action "unknown".')
        msg = ask_claude(prompt, 1200, tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}])
        urls = set()
        for b in msg.content:
            if b.type == "web_search_tool_result" and isinstance(b.content, list):
                urls.update(getattr(r, "url", "") for r in b.content)
        o = parse_json(text_of(msg))
        url = safe_url(o.get("source_url", ""))
        if o.get("action") in ACTIONS and url and url in urls and float(o.get("confidence", 0)) >= MIN_CONF:
            res = {"action": o["action"], "tip": clean(o.get("tip", "")), "source": clean(o.get("source_name", "Official site"), 80), "url": url}
            _cache[k] = (time.time(), res)
            return res
    except Exception:
        pass
    return None

@functools.lru_cache(maxsize=2048)
def localize(item, tip, lang):
    if lang.lower().startswith("en") or not has_key():
        return item, tip
    try:
        o = parse_json(text_of(ask_claude(f'Translate to language code "{lang}". Reply JSON only with keys item and tip: '
                                          + json.dumps({"item": item, "tip": tip}), 300)))
        return clean(o["item"], 60), clean(o["tip"])
    except Exception:
        return item, tip

def out(item, action, tip, source, url, conf, scope, lang, verified=False):
    item, tip = localize(clean(item, 60), clean(tip), lang)
    return {"item": item, "action": action, "tip": tip, "source": clean(source, 80), "source_url": safe_url(url),
            "confidence": conf, "safe": scope == "default", "scope": scope, "verified": verified}

@app.get("/api/jurisdictions")
def jurisdictions():
    rows = [{"id": k, "name": v["name"]} for k, v in PACKS.items() if k != "global"]
    return sorted(rows, key=lambda r: r["name"]) + [{"id": "global", "name": GLOBAL["name"]}]

@app.post("/api/classify")
def classify(req: Req, request: Request):
    ip, now = request.client.host if request.client else "?", time.time()
    hits[ip] = [t for t in hits[ip] if now - t < 60]
    if len(hits[ip]) >= RATE:
        raise HTTPException(429, "Too many requests. Wait a minute and try again.")
    hits[ip].append(now)
    if req.image and len(req.image) > MAX_B64:
        raise HTTPException(413, "Image too large.")
    place = clean(req.place, 100).strip()
    key, label, conf = identify(req)
    safe_tip = "Not sure. When in doubt, keep it out of recycling and check your local authority."
    if conf < MIN_CONF or not (key or label):
        return out(req.text or label or "Unclear item", "trash", safe_tip, "Safe default", "", conf, "default", req.lang)
    pack = match_pack(place)
    if pack and key in pack["items"]:                      # 1. bundled local pack
        e = pack["items"][key]
        return out(e[0], e[1], e[2], e[3], pack.get("source_url", ""), conf, "local", req.lang, pack.get("verified", False))
    if place and has_key():                                # 2. AI web research for this exact place
        r = research(place, label)
        if r:
            return out(label, r["action"], r["tip"], r["source"], r["url"], conf, "researched", req.lang)
    if key in GLOBAL["items"]:                             # 3. general guidance
        e = GLOBAL["items"][key]
        return out(e[0], e[1], e[2], e[3], "", conf, "global", req.lang)
    return out(label, "trash", safe_tip, "Safe default", "", conf, "default", req.lang)  # 4. safe default

app.mount("/", StaticFiles(directory=os.path.join(BASE, "static"), html=True))
