# Reloop

Know where it goes, wherever you are. Type any city in the world and Reloop finds that place's recycling guidance, cites its source, and tells you how confident it should be. It also gives contamination audits for operators, surplus food routing, and a city view of the mistakes worth fixing.

**Problem (Theme track):** curbside contamination. Add one cited statistic here before submitting.

## Run
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # needed for photos, AI research, and translation
uvicorn server:app --reload    # http://localhost:8000
```
Docker: `docker build -t reloop . && docker run -p 8000:8000 -e ANTHROPIC_API_KEY reloop`
Tests: `pip install -r requirements-dev.txt && python validate_rules.py && pytest`

The API key's organization must have web search enabled in the Anthropic Console. Without a key, typed item names still work against bundled rules and general guidance.

## How an answer is found
Reloop tries these in order and always says which one it used:
1. **Bundled rule pack:** an exact match on a city in `rules/`.
2. **AI-researched:** it searches the web for that place's official waste guidance. An answer is accepted only if it cites a page the search actually retrieved. It is labeled "AI-researched" and links the source.
3. **General guidance:** conservative worldwide defaults from `rules/global.json`, labeled "Local rules may differ."
4. **Safe default:** below 60% confidence, or for unknown items, it says "trash, check your local authority" instead of guessing.

## Worldwide by design
- **Any place:** type any city and country. No pack is required.
- **Any language:** answers are translated into the browser language.
- **Privacy:** photos are downscaled in the browser, sent only for identification, and never stored. Basic per-IP rate limiting is built in.
- **Safety:** model output is stripped of HTML characters and source links are validated before display.

## Add your city
Copy `rules/us-ca-pleasanton.json`, change `id`, `name`, `lang`, and `source_url`, and write each rule from your official guide. Set `"verified": true` only with a real `source_url`. Run `python validate_rules.py`, then open a pull request. A verified pack always beats AI research for that city.

## Honest status
- Bundled packs for Pleasanton, Seattle, and Austin are **unverified sample data**. Check them against official guides before any public use.
- AI-researched answers can still be wrong or outdated. The source link may not say exactly what the model reports, and many small places have no searchable guide. They are labeled unverified.
- Research adds a few seconds and some cost per new place and item. Results are cached for 7 days in memory and reset on restart.
- The interface text is English only. Answer text is translated.
- Food bank matching uses hardcoded sample data. The scan log is stored in the browser, so the City view is per-device. A shared database is the next step for real deployments.
- No accuracy benchmark yet. Build a labeled set and compare against a no-local-rules baseline.

## Next
Benchmark AI-researched answers against verified packs, verified packs for pilot cities, a shared database, interface translations, and a hauler pilot tracking contamination over a quarter.
