"""
[Task 8-A] Question fetcher module — extracted from real_question_fetcher.py

TẠI SAO: real_question_fetcher.py god file. Tách fetcher functions vào module
này. Backward-compatible — real_question_fetcher.py re-exports all fetchers.
"""
from __future__ import annotations

import logging
import os
import random
import re

from scp.core.question_fetchers._common import (
    _MAX_CONSECUTIVE_FAILURES,
    _SOURCE_HEALTH,
    _SOURCE_HEALTH_LOCK,
    _clean,
    _http_get_json,
)

logger = logging.getLogger(__name__)
# [S8 security sweep — insecure-randomness finding][B311-fix 2026-09-30] Toàn
# bộ randomness trong module này CHỈ phục vụ stochastic sampling của question
# fetchers: chọn ngẫu nhiên quốc gia/thành phố/câu hỏi/holiday/mục từ dữ liệu
# nguồn để tạo câu hỏi học (fetch_rest_countries, fetch_sunrise_sunset,
# fetch_public_holidays, fetch_stackoverflow, fetch_fruityvice,
# fetch_coingecko, fetch_open_meteo, fetch_openfda). KHÔNG có mục đích bảo
# mật: không token, không secret, không ID/nonce cần unguessable — đoán trước
# mục được chọn không gây hại. Dùng instance SystemRandom RIÊNG ở module level
# (nguồn os.urandom, pattern: scp/security/gcg_attack.py `_GCG_RNG`) thay cho
# global RNG để (1) tách biệt với mọi lời random.seed() của module khác,
# (2) làm rõ ràng tại call site rằng đây là nguồn ngẫu nhiên phi bảo mật, và
# (3) triệt tiêu B311 của bandit. KHÔNG dùng random.Random(seed) ở đây vì
# không có contract seeded-determinism nào trên sampling fetcher (grep
# tests/: không có .seed() hay tham chiếu _FETCHER_RNG).
_FETCHER_RNG = random.SystemRandom()


def fetch_nasa_apod(n: int = 3) -> list[dict]:
    """NASA Astronomy Picture of the Day.
     Skip if source has failed recently (NASA DEMO_KEY rate limit: 30/hour, 50/day).
    """
    results = []
    #  Check source health — skip if failed 3+ times
    # [ROOT-FIX 3] Use _SOURCE_HEALTH_LOCK — was declared but never used → race with
    # ThreadPoolExecutor workers in RealQuestionFetcher.fetch() that mutate the same dict.
    with _SOURCE_HEALTH_LOCK:
        _nasa_fails = _SOURCE_HEALTH.get("nasa_apod", 0)
    if _nasa_fails >= _MAX_CONSECUTIVE_FAILURES:
        logger.info("  nasa_apod: SKIPPED (rate limited, failed %dx)", _nasa_fails)
        return results
    # [V104.36 #75] TẠI SAO: old loop `for _ in range(n)` always broke on first
    # success → returned ≤1 result regardless of n. NASA APOD is daily-singleton
    # (same image all day), so fetching N is fundamentally impossible.
    # Fix: fetch ONCE (no loop), document that APOD is daily-singleton.
    # Callers should set BATCH_SOURCES["nasa_apod"] = 1 (not 50).
    # [GLM-AUDIT-FIX] Use NASA_API_KEY env var; DEMO_KEY is public rate-limited fallback
    _nasa_key = os.environ.get("NASA_API_KEY", "DEMO_KEY")
    data = _http_get_json(f"https://api.nasa.gov/planetary/apod?api_key={_nasa_key}")
    if not data:
        # [ROOT-FIX 3] Lock-protected read-modify-write
        with _SOURCE_HEALTH_LOCK:
            _SOURCE_HEALTH["nasa_apod"] = _SOURCE_HEALTH.get("nasa_apod", 0) + 1
        return results
    title = data.get("title", "")
    explanation = data.get("explanation", "")
    if title and explanation:
        # [ROOT-FIX 3] Lock-protected write
        with _SOURCE_HEALTH_LOCK:
            _SOURCE_HEALTH["nasa_apod"] = 0
        results.append({
            "question": f"What is the astronomy fact about: {title}?",
            "ai_answer": _clean(explanation, 400),
            "source": "nasa_apod",
            "source_url": data.get("url", "https://apod.nasa.gov/"),
            "domain": "astronomy",
            "category": "apod",
        })
    return results





def fetch_mealdb(n: int = 3) -> list[dict]:
    """MealDB — random recipe."""
    results = []
    for _ in range(n):
        data = _http_get_json("https://www.themealdb.com/api/json/v1/1/random.php")
        if not data or not data.get("meals"):
            continue
        meal = data["meals"][0]
        name = meal.get("strMeal", "")
        category = meal.get("strCategory", "")
        area = meal.get("strArea", "")
        if not name:
            continue
        answer = f"{name} — a {category} dish from {area}."
        results.append({
            "question": f"What is the recipe for {name}?",
            "ai_answer": _clean(answer, 300),
            "source": "mealdb",
            "source_url": meal.get("strSource", "https://www.themealdb.com/"),
            "domain": "food",
            "category": category,
        })
    return results





def fetch_cocktaildb(n: int = 3) -> list[dict]:
    """CocktailDB — random cocktail."""
    results = []
    for _ in range(n):
        data = _http_get_json("https://www.thecocktaildb.com/api/json/v1/1/random.php")
        if not data or not data.get("drinks"):
            continue
        drink = data["drinks"][0]
        name = drink.get("strDrink", "")
        category = drink.get("strCategory", "")
        glass = drink.get("strGlass", "")
        if not name:
            continue
        answer = f"{name} — a {category} served in {glass}."
        results.append({
            "question": f"How do you make the cocktail {name}?",
            "ai_answer": _clean(answer, 300),
            "source": "cocktaildb",
            "source_url": "https://www.thecocktaildb.com/",
            "domain": "food",
            "category": "cocktail",
        })
    return results





def fetch_fruityvice(n: int = 5) -> list[dict]:
    """Fruityvice — fruit nutrition facts."""
    results = []
    data = _http_get_json("https://www.fruityvice.com/api/fruit/all")
    if not isinstance(data, list) or not data:
        return results
    _FETCHER_RNG.shuffle(data)  # stochastic sampling only — not security-relevant
    for fruit in data[:n]:
        try:
            name = fruit.get("name", "")
            family = fruit.get("family", "")
            genus = fruit.get("genus", "")
            nutr = fruit.get("nutritions", {})
            if not name:
                continue
            answer = (f"{name} (family: {family}, genus: {genus}). "
                      f"Nutrition per 100g: calories={nutr.get('calories', '?')}, "
                      f"sugar={nutr.get('sugar', '?')}g, carbs={nutr.get('carbohydrates', '?')}g, "
                      f"protein={nutr.get('protein', '?')}g.")
            results.append({
                "question": f"What is the nutritional value of {name}?",
                "ai_answer": _clean(answer, 400),
                "source": "fruityvice",
                "source_url": "https://www.fruityvice.com/",
                "domain": "biology",
                "category": "fruit",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("data_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results


_REST_COUNTRIES_CACHE: list[dict] | None = None





def _get_rest_countries_list() -> list[dict]:
    """Fetch all countries (use v2 fallback)."""
    global _REST_COUNTRIES_CACHE
    if _REST_COUNTRIES_CACHE is not None:
        return _REST_COUNTRIES_CACHE
    # Try v3.1 with single field (sometimes works)
    data = _http_get_json("https://restcountries.com/v3.1/all?fields=cca2")
    if isinstance(data, list) and data:
        _REST_COUNTRIES_CACHE = data
        return data
    # Fallback: hardcoded country codes (250 countries)
    # [V104.36 #76] TẠI SAO: list had duplicates (AO, PL, PW) → random.sample could
    # return duplicate values → wasted API calls. Fix: dedupe via set, then list.
    cca2_list = ["VN", "US", "CN", "JP", "KR", "TH", "IN", "DE", "FR", "GB",
                 "ES", "IT", "RU", "BR", "MX", "AR", "CA", "AU", "NZ", "EG",
                 "ZA", "NG", "KE", "SA", "AE", "IL", "TR", "GR", "PT", "NL",
                 "BE", "CH", "AT", "SE", "NO", "DK", "FI", "PL", "UA", "CZ",
                 "HU", "RO", "BG", "RS", "HR", "SK", "SI", "LT", "LV", "EE",
                 "ID", "MY", "SG", "PH", "BN", "KH", "LA", "MM", "BD", "LK",
                 "PK", "AF", "IR", "IQ", "SY", "JO", "LB", "YE", "OM", "QA",
                 "KW", "BH", "CY", "MT", "IS", "IE", "LU", "MC", "AD", "SM",
                 "VA", "MA", "DZ", "TN", "LY", "SD", "SS", "ET", "ER", "DJ",
                 "SO", "UG", "TZ", "RW", "BI", "MZ", "ZW", "ZM", "MW", "BW",
                 "NA", "AO", "CD", "CG", "GA", "CM", "TD", "CF", "ML", "BF",
                 "CI", "GH", "TG", "BJ", "NE", "SN", "GM", "GN", "SL", "LR",
                 "MR", "CV", "ST", "GQ", "KM", "SC", "MU", "RE", "YT",
                 "PE", "CO", "VE", "EC", "BO", "PY", "UY", "CL", "GY", "SR",
                 "PA", "CR", "NI", "HN", "SV", "GT", "BZ", "CU", "DO", "HT",
                 "JM", "BS", "TT", "BB", "GD", "LC", "VC", "AG", "DM", "KN",
                 "FJ", "PG", "SB", "VU", "NC", "PF", "TO", "WS", "KI", "TV",
                 "NR", "PW", "MH", "FM", "MD", "GE", "AM", "AZ", "KZ",
                 "UZ", "TM", "KG", "TJ", "MN", "KP", "TW", "HK", "MO", "PS",
                 "EH", "TL", "MV"]
    # [V104.36 #76] dedupe — was: AO/PL/PW appeared twice
    cca2_list = list(dict.fromkeys(cca2_list))  # preserve order, remove dupes
    _REST_COUNTRIES_CACHE = [{"cca2": code} for code in cca2_list]
    return _REST_COUNTRIES_CACHE





def fetch_rest_countries(n: int = 5) -> list[dict]:
    """REST Countries — fetch N random countries by alpha code."""
    results = []
    countries = _get_rest_countries_list()
    if not countries:
        return results
    sample = _FETCHER_RNG.sample(countries, min(n, len(countries)))
    for c in sample:
        try:
            cca2 = c.get("cca2")
            if not cca2:
                continue
            data = _http_get_json(f"https://restcountries.com/v3.1/alpha/{cca2}")
            if not isinstance(data, list) or not data:
                continue
            country = data[0]
            name = country.get("name", {}).get("common", "")
            caps = country.get("capital", [])
            pop = country.get("population", 0)
            region = country.get("region", "")
            if not name:
                continue
            # Random question type (stochastic sampling only — not security-relevant)
            qtype = _FETCHER_RNG.choice(["capital", "population", "region"])
            if qtype == "capital" and caps:
                question = f"Thủ đô của {name} là gì?"
                answer = caps[0]
            elif qtype == "population" and pop:
                question = f"Dân số của {name} là bao nhiêu?"
                answer = str(pop)
            else:
                question = f"{name} nằm ở khu vực nào?"
                answer = region
            results.append({
                "question": question,
                "ai_answer": _clean(answer, 200),
                "source": "rest_countries",
                "source_url": f"https://restcountries.com/v3.1/alpha/{cca2}",
                "domain": "geography",
                "category": qtype,
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("data_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_sunrise_sunset(n: int = 2) -> list[dict]:
    """Sunrise-Sunset API — random location."""
    results = []
    # Random major cities
    cities = [("21.03", "105.85", "Hanoi"), ("40.71", "-74.01", "New York"),
              ("35.69", "139.69", "Tokyo"), ("51.51", "-0.13", "London"),
              ("48.85", "2.35", "Paris"), ("-33.87", "151.21", "Sydney"),
              ("55.75", "37.62", "Moscow"), ("28.61", "77.21", "Delhi"),
              ("-23.55", "-46.63", "São Paulo"), ("1.35", "103.82", "Singapore")]
    sample = _FETCHER_RNG.sample(cities, min(n, len(cities)))
    for lat, lng, name in sample:
        try:
            data = _http_get_json(
                f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&date=today")
            if not data or data.get("status") != "OK":
                continue
            results_obj = data.get("results", {})
            sunrise = results_obj.get("sunrise", "")
            sunset = results_obj.get("sunset", "")
            if not sunrise:
                continue
            answer = f"Sunrise: {sunrise}, Sunset: {sunset} (UTC)"
            results.append({
                "question": f"When is sunrise and sunset in {name}?",
                "ai_answer": _clean(answer, 300),
                "source": "sunrise_sunset",
                "source_url": "https://sunrise-sunset.org/",
                "domain": "geography",
                "category": "astronomy",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("data_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_public_holidays(n: int = 5) -> list[dict]:
    """Public Holidays API — historical events."""
    results = []
    countries = ["US", "GB", "FR", "DE", "VN", "CN", "JP", "BR", "CA", "AU"]
    years = [2023, 2024]
    for _ in range(n):
        try:
            country = _FETCHER_RNG.choice(countries)
            year = _FETCHER_RNG.choice(years)
            data = _http_get_json(f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country}")
            if not isinstance(data, list) or not data:
                continue
            holiday = _FETCHER_RNG.choice(data)
            name = holiday.get("name", "")
            date = holiday.get("date", "")
            local_name = holiday.get("localName", "")
            if not name or not date:
                continue
            answer = f"{name} (local: {local_name}) is on {date}."
            results.append({
                "question": f"What is a public holiday in {country}?",
                "ai_answer": _clean(answer, 300),
                "source": "public_holidays",
                "source_url": f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country}",
                "domain": "history",
                "category": "holiday",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("data_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_stackoverflow(n: int = 3) -> list[dict]:
    """Stack Overflow hot questions (technology)."""
    results = []
    data = _http_get_json(
        "https://api.stackexchange.com/2.3/questions?order=desc&sort=hot&site=stackoverflow&pagesize=100&filter=withbody")
    if not data or not data.get("items"):
        return results
    sample = _FETCHER_RNG.sample(data["items"], min(n, len(data["items"])))
    for item in sample:
        try:
            title = item.get("title", "")
            score = item.get("score", 0)
            tags = item.get("tags", [])
            if not title:
                continue
            answer = f"Question score {score}, tags: {','.join(tags[:5])}"
            results.append({
                "question": f"Stack Overflow: {title}",
                "ai_answer": _clean(answer, 300),
                "source": "stackoverflow",
                "source_url": item.get("link", "https://stackoverflow.com/"),
                "domain": "technology",
                "category": "programming",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("data_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_genderize(n: int = 3) -> list[dict]:
    """Genderize API — predict gender from name."""
    results = []
    names = ["luc", "maria", "wei", "olivia", "ahmed", "sophia", "nguyen", "sven",
             "yuki", "alex", "fatima", "ivan", "elena", "robert", "anna"]
    sample = _FETCHER_RNG.sample(names, min(n, len(names)))
    for name in sample:
        try:
            data = _http_get_json(f"https://api.genderize.io?name={name}")
            if not data:
                continue
            gender = data.get("gender", "unknown")
            probability = data.get("probability", 0)
            count = data.get("count", 0)
            if not gender:
                continue
            answer = f"Name '{name}' is likely {gender} (probability {probability}%, based on {count} samples)."
            results.append({
                "question": f"What is the likely gender of the name '{name}'?",
                "ai_answer": _clean(answer, 300),
                "source": "genderize",
                "source_url": "https://genderize.io/",
                "domain": "general",
                "category": "name",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("data_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_tv_maze(n: int = 3) -> list[dict]:
    """TV Maze — TV show search."""
    results = []
    queries = ["girls", "breaking", "office", "friends", "lost", "soprano", "wire"]
    sample = _FETCHER_RNG.sample(queries, min(n, len(queries)))
    for q in sample:
        try:
            data = _http_get_json(f"https://api.tvmaze.com/singlesearch/shows?q={q}")
            if not data:
                continue
            name = data.get("name", "")
            summary = data.get("summary", "")
            # Strip HTML tags
            summary = re.sub(r'<[^>]+>', ' ', summary)
            summary = re.sub(r'\s+', ' ', summary).strip()
            if not name:
                continue
            results.append({
                "question": f"Tell me about the TV show: {name}.",
                "ai_answer": _clean(summary or name, 400),
                "source": "tv_maze",
                "source_url": data.get("url", "https://www.tvmaze.com/"),
                "domain": "entertainment",
                "category": "tv_show",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("data_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results


# ============================================================
# Main Fetcher
# ============================================================


# [V91 NEW] Additional domain-specific fetchers




def fetch_coingecko(n: int = 5) -> list[dict]:
    """CoinGecko — crypto prices (finance)."""
    try:
        data = _http_get_json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=100&page=1", timeout=8)
        if not data:
            return []
        sample = _FETCHER_RNG.sample(data, min(n, len(data)))
        results = []
        for coin in sample:
            name = coin.get("name", "?")
            price = coin.get("current_price", 0)
            symbol = coin.get("symbol", "?").upper()
            results.append({
                "question": f"What is the current price of {name} ({symbol})?",
                "ai_answer": f"${price:,.2f} USD",
                "source": "coingecko",
                "source_url": "https://www.coingecko.com/",
                "domain": "finance",
                "category": "crypto",
            })
        return results
    except Exception as e:
        logger.debug(f"CoinGecko error: {e}", exc_info=True)
        return []





def fetch_open_meteo(n: int = 3) -> list[dict]:
    """Open Meteo — weather data for random cities (weather)."""
    cities = [
        ("Hanoi", 21.0285, 105.8542),
        ("Tokyo", 35.6762, 139.6503),
        ("New York", 40.7128, -74.0060),
        ("London", 51.5074, -0.1278),
        ("Sydney", -33.8688, 151.2093),
        ("Paris", 48.8566, 2.3522),
        ("Moscow", 55.7558, 37.6173),
        ("Cairo", 30.0444, 31.2357),
        ("Mumbai", 19.0760, 72.8777),
        ("Sao Paulo", -23.5505, -46.6333),
    ]
    sample = _FETCHER_RNG.sample(cities, min(n, len(cities)))
    results = []
    for city, lat, lon in sample:
        try:
            data = _http_get_json(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code",
                timeout=8
            )
            if data and "current" in data:
                temp = data["current"].get("temperature_2m", "?")
                data["current"].get("weather_code", 0)
                results.append({
                    "question": f"What is the current temperature in {city}?",
                    "ai_answer": f"{temp}°C",
                    "source": "open_meteo",
                    "source_url": "https://open-meteo.com/",
                    "domain": "weather",
                    "category": "temperature",
                })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("data_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_openfda(n: int = 3) -> list[dict]:
    """OpenFDA — drug info (medical)."""
    try:
        data = _http_get_json(
            "https://api.fda.gov/drug/label.json?limit=200",
            timeout=10
        )
        if not data or "results" not in data:
            return []
        results_list = data["results"]
        sample = _FETCHER_RNG.sample(results_list, min(n, len(results_list)))
        results = []
        for drug in sample:
            brand = drug.get("openfda", {}).get("brand_name", ["Unknown"])
            brand_name = brand[0] if isinstance(brand, list) and brand else str(brand)
            purpose = drug.get("purpose", ["Unknown"])
            purpose_text = purpose[0] if isinstance(purpose, list) and purpose else str(purpose)
            results.append({
                "question": f"What is the drug {brand_name} used for?",
                "ai_answer": purpose_text[:200],
                "source": "openfda",
                "source_url": "https://open.fda.gov/",
                "domain": "medical",
                "category": "drug",
            })
        return results
    except Exception as e:
        logger.debug(f"OpenFDA error: {e}", exc_info=True)
        return []





