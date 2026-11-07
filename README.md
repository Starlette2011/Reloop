# Reloop

Know where it goes, wherever you are. Reloop gives local recycling answers for supported cities and clearly labeled general guidance everywhere else. It also runs contamination audits for operators and routes surplus food to food banks.

**Live demo:** https://starlette2011.github.io/Reloop/ (runs entirely in the browser, no API key needed)

**Problem (Theme track):** curbside contamination. Add one cited statistic here before submitting.

**How we'd measure success:** correct-disposal rate in a before-and-after user test, accuracy and harmful-error rate on the benchmark in `eval/`, and, in a pilot, a municipality's contamination rate over a quarter.

## Two versions
- **Hosted demo (GitHub Pages):** `index.html` at the repo root. Typed items and on-device photo analysis, using the bundled rule packs and general guidance. No server, no key, no cost. Photos never leave the device.
- **Server version:** `server.py` and `static/index.html`. Adds photo recognition with a larger AI model, AI web research for any place, and translated answers. Needs an API key. It does not include the follow-up questions, CSV export, or offline mode.

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
4. **Safe default:** unclear items, unclear photos, or confidence below the threshold return "trash, check your local authority" instead of a guess.

Typed items are matched by whole phrase. Ambiguous or look-alike inputs such as "paper towel" or "cupcake" return the safe default instead of a confident wrong answer.

## Follow-up questions
Some answers depend on something a photo can't show. For example, a pizza box in a place without its own rule asks "Is the box greasy or food-soiled?" and gives a different answer for each reply. Questions live in an `asks` block in a rule pack and can be added per city; a city's own rule overrides the general one.

## Photo analysis
- **Hosted demo:** a small open-source image model (CLIP, via Transformers.js) runs in the browser. It compares the photo against descriptions of 12 supported items plus "none of these" options, and answers only when the top match is confident and clearly ahead of the runner-up.
- **Server version:** with an API key, photos are identified by Claude.
- Neither can see grease, food residue, or whether a container is empty, which is why the follow-up questions exist.

## Bin audits
List or photograph items from a bin or load. Reloop reports the contamination rate (the share of items that do not belong in recycling), the top three mistakes for bin-tag messaging, and a downloadable CSV with the date, place, and per-item results.

## Offline use
After the first visit, the page and rule packs are cached so typed items work without a connection. The photo model's offline behavior is untested.

## Privacy and safety
In the hosted demo, photos are analyzed on the device and never uploaded; only the model files download from a CDN on first use. In the server version, photos are downscaled in the browser, sent only for identification, and never stored. Model output is stripped of HTML characters, source links are validated, and basic per-IP rate limiting is built in. CSV cells are protected against spreadsheet formula injection.

## Benchmark
`eval/cases.csv` holds labeled test cases (place, item, expected answer, source URL), filled in by hand from official city guides. `python eval/run_eval.py eval/cases.csv` compares a no-local-rules baseline against the local rule packs and reports the share correct, the share that fell back to the safe default, and the harmful rate: items wrongly sent to recycling, which is what contaminates a load.

## Honest status
- Bundled packs for Pleasanton, Seattle, and Austin are **unverified sample data** until checked against official guides.
- The hosted demo's photo analysis is unbenchmarked, downloads a model on first use, needs an internet connection the first time, and can be slow on older phones. AI web research needs the server version and a key.
- AI-researched answers can still be wrong or outdated. They are labeled unverified and link their source.
- Follow-up questions exist only for pizza boxes so far, and only on single-item checks.
- Food bank matching uses hardcoded sample data. A shared database would be the next step for real deployments.
- The interface text is English only. Answer text is translated in the server version.

## Next
Benchmark photo analysis on real items, more verified cities and follow-up questions, a printable audit report, a shared database for audits, interface translations, and a hauler pilot tracking contamination over a quarter.
