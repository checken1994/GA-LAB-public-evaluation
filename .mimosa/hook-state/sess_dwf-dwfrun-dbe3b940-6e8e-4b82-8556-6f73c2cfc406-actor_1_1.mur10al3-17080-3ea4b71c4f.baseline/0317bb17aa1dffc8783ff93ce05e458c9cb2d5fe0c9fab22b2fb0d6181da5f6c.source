"""
[Task 7-A] WHY engine source handlers — extracted from meta/why_engine.py

TẠI SAO: why_engine.py 1,551 LOC god file. Tách source handlers (Wikipedia,
PubChem, crypto, ...) vào package này. Backward-compatible — WhyEngine._query_*
methods become thin wrappers calling these modules.

Modules:
  wikipedia.py  — Wikipedia API handler (~70 LOC)
  pubchem.py    — PubChem molecular weight handler (~25 LOC)
  wikidata.py   — Wikidata SPARQL handler (~25 LOC)
  rest_countries.py — REST Countries API handler (~35 LOC)
  open_meteo.py — Open-Meteo weather handler (~30 LOC)
  crypto.py     — CoinGecko crypto price handler (~25 LOC)
  frankfurter.py — Frankfurter exchange rate handler (~30 LOC)
  nasa.py       — NASA APOD handler (~20 LOC)

Total: ~260 LOC extracted (was inline in why_engine.py).
"""
