# Reloop

Know where it goes, wherever you are. Reloop gives local recycling answers for households, contamination audits for operators, surplus food routing, and a city view of the mistakes worth fixing. One scan log feeds all four.

**Problem (Theme track):** curbside contamination. Add one cited statistic here before submitting.

## Run
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # optional: photo recognition, any item, translated answers
uvicorn server:app --reload    # http://localhost:8000
```
Docker: `docker build -t reloop . && docker run -p 8000:8000 -e ANTHROPIC_API_KEY reloop`
Tests: `pip install -r requirements-dev.txt && python validate_rules.py && pytest`

## Worldwide by design
- **Any place:** each place is a rule pack in `rules/`. If a place has no pack, or a pack lacks an item, Reloop falls back to `rules/global.json` and says so ("General guidance. Local rules may differ"). It never presents general advice as local fact.
- **Any language:** with an API key, answers are translated to the browser language.
- **Safe by default:** below 60% confidence, or for unknown items, it answers "trash, check your local authority" instead of guessing.
- **Privacy:** photos are downscaled in the browser, sent only for identification, and never stored. Basic per-IP rate limiting is built in.

## Add your city
Copy `rules/us-ca-pleasanton.json`, change `id`, `name`, `lang`, and `source_url`, and write each rule from your official guide. Set `"verified": true` only with a real `source_url`. Run `python validate_rules.py`, then open a pull request.

## Honest status
- Bundled packs for Pleasanton, Seattle, and Austin are **unverified sample data**. Check them against official guides before any public use.
- Coverage worldwide depends on contributed packs. The interface text is English only; result text is translated.
- Food bank matching uses hardcoded sample data. The scan log is stored in the browser, so the City view is per-device. A shared database is the next step for real deployments.
- No accuracy benchmark yet. Build a labeled set and compare against a no-local-rules baseline.

## Next
Benchmark, verified packs for pilot cities, a shared database, interface translations, and a hauler pilot tracking contamination over a quarter.
