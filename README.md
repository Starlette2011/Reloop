# Reloop

Know where it goes, wherever you are. Reloop gives local recycling answers for supported cities and clearly labeled general guidance everywhere else. It also runs contamination audits for operators and routes surplus food to food banks.

**Live demo:** https://starlette2011.github.io/Reloop/ (runs entirely in the browser, no API key needed)

**Problem (Theme track):** curbside contamination. Add one cited statistic here before submitting.

**How we'd measure success:** correct-disposal rate in a before-and-after user test, accuracy and harmful-error rate on the benchmark in `eval/`, and, in a pilot, a municipality's contamination rate over a quarter.

## Two versions
- **Hosted demo (GitHub Pages):** `index.html` at the repo root. Typed items only, using the bundled rule packs and general guidance. No server, no key, no cost.
- **Server version:** `server.py` and `static/index.html`. Adds photo recognition, AI web research for any place, and translated answers. Needs an API key.

## Run the server version
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
1. **Bundled rule pack:** an exact match on a city in `rules/`, with its source and the date it was last checked.
2. **AI-researched (server version, needs a key):** it searches the web for that place's official waste guidance and accepts an answer only if it cites a page the search actually retrieved. Labeled "AI-researched" with a source link.
3. **General guidance:** conservative worldwide defaults from `rules/global.json`, labeled "Local rules may differ."
4. **Safe default:** unclear items, or confidence below 60%, return "trash, check your local authority" instead of a guess.

Typed items are matched by whole phrase. Ambiguous or look-alike inputs such as "paper towel" or "cupcake" return the safe default instead of a confident wrong answer.

## Privacy and safety
Photos are downscaled in the browser, sent only for identification, and never stored. Model output is stripped of HTML characters, source links are validated, and basic per-IP rate limiting is built in.

## Add your city
Copy `rules/us-ca-pleasanton.json`, change `id`, `name`, `lang`, and `source_url`, and write each rule from your official guide. Set `"verified": true` only with a real `source_url`, and add `"checked": "YYYY-MM-DD"` with the date you verified it. Add the pack's id to `packs.json` for the hosted demo. Run `python validate_rules.py`, then open a pull request. A verified pack always beats AI research for that city.

## Honest status
- Bundled packs for Pleasanton, Seattle, and Austin are **unverified sample data** until checked against official guides.
- The hosted demo has no photo recognition and no research. Those need the server version and a key.
- AI-researched answers can still be wrong or outdated. They are labeled unverified and link their source.
- Food bank matching uses hardcoded sample data. A shared database would be the next step for real deployments.
- The interface text is English only. Answer text is translated in the server version.

## Next
Benchmark against verified packs, more verified cities, a shared database for audits, interface translations, and a hauler pilot tracking contamination over a quarter.
