"""Mixins for DomainAntibodySystem."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from scp.interfaces.severity import Severity

if TYPE_CHECKING:
    from scp.knowledge.antibody_system import AntibodyResult

class GeneralAntibodyMixin:
    def verify_citation(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check if answer makes factual claims but has no citations
        has_claim = any(kw in answer.lower() for kw in ["theo", "according to", "nghiên cứu", "study"])
        has_citation = any(kw in answer.lower() for kw in ["doi", "http", "nguồn", "source:"])
        if has_claim and not has_citation:
            result.passed = False
            result.severity = "medium"
            result.confidence = 0.7
            result.details = "Answer makes claims without citations"
        else:
            result.details = "Citation check passed: no uncited claims detected"
        return True

    def verify_url(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [FIX-16] Check for suspicious URLs AND bare domains
        urls = re.findall(r"https?://\S+", answer)
        # Also match bare domains like "example.com"
        bare_domains = re.findall(r"\b([a-z0-9-]+\.(com|org|net|edu|gov|io|ai|co|vn|us|uk|invalid|test|foo|bar))\b", answer, re.IGNORECASE)
        all_urls = urls + [d[0] for d in bare_domains]
        for url in all_urls:
            if any(s in url.lower() for s in ["example.com", "example.invalid", "test.com", "foo.", "bar.", "fake."]):
                result.passed = False
                result.severity = "high"
                result.confidence = 0.8
                result.details = f"Suspicious URL: {url[:60]}"
                break
            tld = url.split("//")[-1].split("/")[0].split(".")[-1].lower()
            if tld not in ["com", "org", "net", "edu", "gov", "io", "ai", "co", "vn", "us", "uk"]:
                result.passed = False
                result.severity = "medium"
                result.confidence = 0.6
                result.details = f"Unusual TLD in URL: {url[:60]}"
        if result.passed:
            result.details = f"URL check passed: {len(all_urls)} URL(s) scanned"
        return True

    def verify_date(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check for dates in the future
        future_years = re.findall(r"\b(20[3-9]\d|2[1-9]\d\d)\b", answer)
        if future_years:
            result.passed = False
            result.severity = "medium"
            result.confidence = 0.7
            result.details = f"Future date(s) in answer: {future_years[:3]}"
        else:
            result.details = "Date check passed: no future dates"
        return True

    def verify_fact(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check for extreme percentages
        extreme_pct = re.findall(r"(?:99\.9%|100%)", answer)
        if extreme_pct:
            result.passed = False
            result.severity = "low"
            result.confidence = 0.6
            result.details = f"Extreme percentage claim: {extreme_pct}"
        else:
            result.details = "Fact check passed: no extreme percentages"
        return True

    def verify_general(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check for weasel words (closure words)
        # [DNA-5 FIX Task 9-A] Expanded closure patterns + severity low → high
        # TẠI SAO: Task 8-C benchmark 8/8 closure passed via governance KILL
        # (catch-all). Task 9-A DNA #5 fix removes KILL for missing_evidence,
        # exposing that antibody only had severity="low" → didn't trigger
        # Phase 6 FAIL override (needs high/critical). Fix: severity="high".
        # Also added missing patterns: "well known", "everyone knows",
        # "as everyone can see", "plainly", "needless to say", etc.
        weasel_words = [
            # Vietnamese
            "hiển nhiên", "chắc chắn", "tự nhiên", "rõ ràng",
            "đương nhiên", "tất nhiên", "như đã biết", "như ta đã biết",
            "không cần nói", "quá rõ ràng", "đã rõ",
            # English
            "obviously", "clearly", "as we know", "as is well known",
            "well known", "it goes without saying", "needless to say",
            "of course", "as expected", "naturally", "evidently",
            "everyone knows", "as everyone can see", "plainly",
            "as is well-known", "it is well known",
        ]
        for ww in weasel_words:
            if ww in answer.lower():
                result.passed = False
                result.severity = "high"  # [DNA-5 FIX Task 9-A] was "low" → "high"
                result.confidence = 0.8
                result.details = f"Closure/weasel word detected: '{ww}'"
                break
        if result.passed:
            result.details = "General check passed: no weasel words detected"

        # === [Task 15: NEW] 6 multi-domain antibodies ===
        return True

class MedicalAntibodyMixin:
    def verify_dosage(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check for dosage exceeding known limits
        dosage_match = re.findall(r"(\d+)\s*(mg|ml|g|mcg|µg)", answer, re.IGNORECASE)
        for amount, unit in dosage_match:
            amt = int(amount)
            unit_lower = unit.lower()
            if unit_lower == "mg" and amt > 4000:
                result.passed = False
                result.severity = "high"
                result.confidence = 0.8
                result.details = f"Dosage {amt}{unit} exceeds typical max (4000mg paracetamol)"
            elif unit_lower == "g" and amt > 10:
                result.passed = False
                result.severity = "high"
                result.confidence = 0.7
                result.details = f"Dosage {amt}{unit} seems excessive"
            elif unit_lower == "ml" and amt > 100:
                result.passed = False
                result.severity = "medium"
                result.confidence = 0.6
                result.details = f"Volume {amt}{unit} seems excessive for medication"
        if result.passed:
            result.details = f"Dosage check passed: {len(dosage_match)} dosage(s) scanned"
        return True

    def verify_drug_interaction(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 30-C] Check known drug-drug interactions.
        # Common dangerous pairs: warfarin+aspirin (bleeding),
        # MAOIs+SSRIs (serotonin syndrome), statins+grapefruit, etc.
        KNOWN_INTERACTIONS = [
            ({"warfarin", "aspirin"}, "bleeding risk (additive anticoagulant effect)", "high"),
            ({"warfarin", "nsaids"}, "GI bleeding risk", "high"),
            ({"warfarin", "ibuprofen"}, "GI bleeding risk", "high"),
            ({"ssri", "maoi"}, "serotonin syndrome (potentially fatal)", "critical"),
            ({"fluoxetine", "maoi"}, "serotonin syndrome", "critical"),
            ({"sertraline", "maoi"}, "serotonin syndrome", "critical"),
            ({"simvastatin", "grapefruit"}, "rhabdomyolysis risk (CYP3A4 inhibition)", "medium"),
            ({"atorvastatin", "grapefruit"}, "rhabdomyolysis risk", "medium"),
            ({"metronidazole", "alcohol"}, "disulfiram-like reaction", "high"),
            ({"ciprofloxacin", "theophylline"}, "theophylline toxicity (CYP1A2 inhibition)", "medium"),
            ({"lithium", "nsaids"}, "lithium toxicity (reduced renal clearance)", "high"),
            ({"ace inhibitor", "potassium"}, "hyperkalemia risk", "medium"),
            ({"spironolactone", "potassium"}, "hyperkalemia risk", "medium"),
            ({"tramadol", "maoi"}, "serotonin syndrome + seizure risk", "critical"),
            ({"clarithromycin", "statin"}, "rhabdomyolysis risk", "high"),
        ]
        a_lower = answer.lower()
        # Check which drugs are mentioned in the answer
        found_drugs = set()
        drug_canonical = {
            "warfarin": "warfarin", "aspirin": "aspirin", "asa": "aspirin",
            "nsaids": "nsaids", "nsaid": "nsaids", "ibuprofen": "ibuprofen",
            "ssri": "ssri", "ssris": "ssri", "maoi": "maoi", "maois": "maoi",
            "fluoxetine": "fluoxetine", "prozac": "fluoxetine",
            "sertraline": "sertraline", "zoloft": "sertraline",
            "simvastatin": "simvastatin", "zocor": "simvastatin",
            "atorvastatin": "atorvastatin", "lipitor": "atorvastatin",
            "statin": "statin", "statins": "statin",
            "grapefruit": "grapefruit",
            "metronidazole": "metronidazole", "flagyl": "metronidazole",
            "alcohol": "alcohol", "ethanol": "alcohol",
            "ciprofloxacin": "ciprofloxacin", "cipro": "ciprofloxacin",
            "theophylline": "theophylline",
            "lithium": "lithium",
            "ace inhibitor": "ace inhibitor", "ace inhibitors": "ace inhibitor",
            "potassium": "potassium",
            "spironolactone": "spironolactone", "aldactone": "spironolactone",
            "tramadol": "tramadol", "ultram": "tramadol",
            "clarithromycin": "clarithromycin", "biaxin": "clarithromycin",
        }
        for kw, canonical in drug_canonical.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', a_lower):
                found_drugs.add(canonical)
        # Check for known interactions
        interaction_found = False
        for pair, desc, sev in KNOWN_INTERACTIONS:
            if pair.issubset(found_drugs):
                result.passed = False
                result.severity = sev
                result.confidence = 0.85
                result.details = (
                    f"Known drug-drug interaction: {' + '.join(sorted(pair))} → {desc}. "
                    f"Answer must explicitly warn about this interaction."
                )
                interaction_found = True
                break
        if not interaction_found:
            result.details = (
                f"Drug interaction check passed: {len(found_drugs)} drug(s) detected, "
                f"no known interactions found"
            )
        return True

class FinanceAntibodyMixin:
    def verify_pe_ratio(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check for implausible financial ratios
        # [FIX-15A BUG#2] TẠI SAO: regex cũ P/E\s*(?:ratio\s*)?(?:of\s*)?(\d+...) không match
        # "P/E ratio là 600" (vì "là" xen giữa). Fix: allow any words between P/E và number.
        # Pattern: P/E.*?(\d+(?:\.\d+)?) — non-greedy match any text between P/E và số.
        pe_match = re.findall(r"P/E[^\d]{0,20}(\d+(?:\.\d+)?)", answer, re.IGNORECASE)
        for pe_str in pe_match:
            pe = float(pe_str)
            if pe < 0 or pe > 500:
                result.passed = False
                result.severity = "medium"
                result.confidence = 0.7
                result.details = f"P/E ratio {pe} outside plausible range (0-500)"
        # [FIX-15A] ratio_validator: also check X:Y ratio format (e.g., "100:1", "50:1")
        if ab_name == "ratio_validator":
            ratio_match = re.findall(r"(\d+)\s*:\s*(\d+)", answer)
            for num_str, denom_str in ratio_match:
                num, denom = float(num_str), float(denom_str)
                if denom > 0 and (num / denom > 50 or num / denom < 0.01):
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.7
                    result.details = f"Ratio {num}:{denom} outside plausible range"
        if result.passed:
            result.details = f"Ratio check passed: {len(pe_match)} P/E + ratio(s) scanned"
        return True

    def verify_ratio(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check for implausible financial ratios
        # [FIX-15A BUG#2] TẠI SAO: regex cũ P/E\s*(?:ratio\s*)?(?:of\s*)?(\d+...) không match
        # "P/E ratio là 600" (vì "là" xen giữa). Fix: allow any words between P/E và number.
        # Pattern: P/E.*?(\d+(?:\.\d+)?) — non-greedy match any text between P/E và số.
        pe_match = re.findall(r"P/E[^\d]{0,20}(\d+(?:\.\d+)?)", answer, re.IGNORECASE)
        for pe_str in pe_match:
            pe = float(pe_str)
            if pe < 0 or pe > 500:
                result.passed = False
                result.severity = "medium"
                result.confidence = 0.7
                result.details = f"P/E ratio {pe} outside plausible range (0-500)"
        # [FIX-15A] ratio_validator: also check X:Y ratio format (e.g., "100:1", "50:1")
        if ab_name == "ratio_validator":
            ratio_match = re.findall(r"(\d+)\s*:\s*(\d+)", answer)
            for num_str, denom_str in ratio_match:
                num, denom = float(num_str), float(denom_str)
                if denom > 0 and (num / denom > 50 or num / denom < 0.01):
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.7
                    result.details = f"Ratio {num}:{denom} outside plausible range"
        if result.passed:
            result.details = f"Ratio check passed: {len(pe_match)} P/E + ratio(s) scanned"
        return True

    def verify_interest_rate(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check for implausible interest rates
        rate_match = re.findall(r"(\d+(?:\.\d+)?)\s*%", answer)
        for rate_str in rate_match:
            rate = float(rate_str)
            if rate > 50:
                result.passed = False
                result.severity = "medium"
                result.confidence = 0.6
                result.details = f"Interest rate {rate}% seems implausibly high"
        if result.passed:
            result.details = f"Interest rate check passed: {len(rate_match)} rate(s) scanned"
        return True

class LegalAntibodyMixin:
    def verify_contract(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # Check for excessive penalty clauses
        if "penalty" in answer.lower() or "phạt" in answer.lower():
            penalty_match = re.findall(r"(\d+)\s*%", answer)
            for p_str in penalty_match:
                p = float(p_str)
                if p > 20:
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.6
                    result.details = f"Penalty rate {p}% may be excessive"
        if result.passed:
            result.details = "Contract check passed: no excessive penalties"
        return True

    def verify_statute(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [FIX-16] Check QUESTION for statute keywords, ANSWER for years
        q_lower = question.lower()
        _a_lower = answer.lower()
        if any(kw in q_lower for kw in ["thời hiệu", "statute", "prescription", "hiệu lực"]):
            # Find years in answer
            years = re.findall(r"\b(\d+)\s*năm\b", answer, re.IGNORECASE)
            if not years:
                years = re.findall(r"\b(\d+)\s*years?\b", answer, re.IGNORECASE)
            for y_str in years:
                y = int(y_str)
                if y > 30:
                    result.passed = False
                    result.severity = "low"
                    result.confidence = 0.5
                    result.details = f"Statute of limitations {y} years seems unusually long"
        if result.passed:
            result.details = "Statute check passed: no unusually long statutes"
        return True

class GeographyAntibodyMixin:
    def verify_capital(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 15] Verify capital cities — detect wrong capitals
        KNOWN_CAPITALS = {
            "việt nam": "hà nội", "vietnam": "hà nội", "hanoi": "hà nội",
            "pháp": "paris", "france": "paris", "anh": "london", "uk": "london",
            "mỹ": "washington", "usa": "washington", "nhật": "tokyo", "japan": "tokyo",
            "trung quốc": "bắc kinh", "china": "beijing", "nga": "moscow", "russia": "moscow",
            "đức": "berlin", "germany": "berlin", "ý": "rome", "italy": "rome",
            "tây ban nha": "madrid", "spain": "madrid", "úc": "canberra", "australia": "canberra",
            "hàn quốc": "seoul", "korea": "seoul", "ấn độ": "new delhi", "india": "new delhi",
            "thái lan": "bangkok", "thailand": "bangkok", "cam-pu-chia": "phnom penh",
        }
        a_lower = answer.lower()
        q_lower = question.lower()
        for country, capital in KNOWN_CAPITALS.items():
            if country in q_lower and capital not in a_lower:
                # Question asks about country, answer doesn't contain correct capital
                result.passed = False
                result.severity = "high"
                result.confidence = 0.8
                result.details = f"Question asks about '{country}', capital should be '{capital}' but not in answer"
                break
        if result.passed:
            result.details = "Capital check passed: no contradictions found"
        return True

class ChemistryAntibodyMixin:
    def verify_formula(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 15] Verify chemical formulas — detect wrong formulas
        KNOWN_FORMULAS = {
            "nước": "h2o", "water": "h2o", "muối": "nacl", "salt": "nacl",
            "axit sunfuric": "h2so4", "sulfuric acid": "h2so4",
            "axit clohidric": "hcl", "hydrochloric acid": "hcl",
            "amoniắc": "nh3", "ammonia": "nh3",
            "carbon dioxide": "co2", "khí carbonic": "co2",
            "methane": "ch4", "metan": "ch4",
            "glucose": "c6h12o6", "đường glucose": "c6h12o6",
            "ethanol": "c2h5oh", "rượu": "c2h5oh",
        }
        a_lower = answer.lower()
        q_lower = question.lower()
        for substance, formula in KNOWN_FORMULAS.items():
            if substance in q_lower and formula not in a_lower:
                # Question asks about substance, answer doesn't contain correct formula
                # Check if answer contains a different formula
                import re as _re
                formula_match = _re.findall(r'\b([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+)\b', answer)
                if formula_match:
                    result.passed = False
                    result.severity = "high"
                    result.confidence = 0.8
                    result.details = f"Question asks '{substance}' (formula='{formula}'), but answer has '{formula_match[0]}'"
                    break
        if result.passed:
            result.details = "Formula check passed: no wrong formulas detected"
        return True

class BiologyAntibodyMixin:
    def verify_abbreviation(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [FIX-16] Check QUESTION for abbreviation, ANSWER for wrong expansion
        KNOWN_ABBREVS = {
            "dna": "deoxyribonucleic acid", "rna": "ribonucleic acid",
            "atp": "adenosine triphosphate", "adp": "adenosine diphosphate",
            "rbc": "red blood cell", "wbc": "white blood cell",
            "mrna": "messenger rna", "trna": "transfer rna", "rrna": "ribosomal rna",
            "pcr": "polymerase chain reaction", "nadh": "nicotinamide adenine dinucleotide",
        }
        q_lower = question.lower()
        a_lower = answer.lower()
        for abbr, expansion in KNOWN_ABBREVS.items():
            if abbr in q_lower and expansion not in a_lower:
                # Question asks about abbreviation, answer doesn't contain correct expansion
                result.passed = False
                result.severity = "low"
                result.confidence = 0.6
                result.details = f"Question asks '{abbr.upper()}', correct expansion '{expansion}' not in answer"
                break
        if result.passed:
            result.details = "Abbreviation check passed: no wrong expansions"
        return True

class PhysicsAntibodyMixin:
    def verify_unit(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 15] Verify physics units — detect implausible values
        import re as _re
        # Check velocity claims (m/s, km/h) — also match scientific notation 5e8
        vel_match = _re.findall(r'(\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s*(m/s|km/h|mps|kph)', answer, _re.IGNORECASE)
        for val_str, unit in vel_match:
            val = float(val_str)
            if unit.lower() in ("m/s", "mps") and val > 3e8:
                result.passed = False
                result.severity = "high"
                result.confidence = 0.9
                result.details = f"Velocity {val} m/s exceeds speed of light (3e8 m/s)"
            elif unit.lower() in ("km/h", "kph") and val > 1.08e9:
                result.passed = False
                result.severity = "high"
                result.confidence = 0.9
                result.details = f"Velocity {val} km/h exceeds speed of light"
        # Check temperature claims (°C, K)
        temp_match = _re.findall(r'(\d+(?:\.\d+)?)\s*(°c|°f|k|kelvin|celsius)', answer, _re.IGNORECASE)
        for val_str, unit in temp_match:
            val = float(val_str)
            if unit.lower() in ("°c", "celsius") and (val > 6000 or val < -273.15):
                result.passed = False
                result.severity = "medium"
                result.confidence = 0.8
                result.details = f"Temperature {val}°C outside plausible range (-273.15 to 6000)"
        if result.passed:
            result.details = "Physics unit check passed: no implausible values"
        return True

class HistoryAntibodyMixin:
    def verify_event_date(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [FIX-16] Check QUESTION for event, ANSWER for wrong year
        KNOWN_EVENTS = {
            "thế chiến 2": ("1939", "1945"), "world war 2": ("1939", "1945"), "ww2": ("1939", "1945"),
            "thế chiến 1": ("1914", "1918"), "world war 1": ("1914", "1918"), "ww1": ("1914", "1918"),
            "cách mạng tháng 10": ("1917", "1917"), "october revolution": ("1917", "1917"),
            "cách mạng pháp": ("1789", "1799"), "french revolution": ("1789", "1799"),
            "moon landing": ("1969", "1969"), "apollo": ("1969", "1972"),
            "berlin wall": ("1989", "1989"), "tường berlin": ("1989", "1989"),
            "vietnam war": ("1955", "1975"), "chiến tranh việt": ("1955", "1975"),
        }
        q_lower = question.lower()
        _a_lower = answer.lower()
        for event, (start, end) in KNOWN_EVENTS.items():
            if event in q_lower:
                # Question asks about event, check answer for wrong year
                years = re.findall(r'\b(1[5-9]\d{2}|20[0-2]\d)\b', answer)
                for year in years:
                    if int(year) < int(start) - 5 or int(year) > int(end) + 5:
                        result.passed = False
                        result.severity = "medium"
                        result.confidence = 0.7
                        result.details = f"'{event}' occurred {start}-{end}, but answer mentions {year}"
                        break
                if not result.passed:
                    break
        if result.passed:
            result.details = "Event date check passed: no date contradictions"
        return True

class TechnologyAntibodyMixin:
    def verify_http_status(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [FIX-16] Check QUESTION for status code, ANSWER for wrong description
        KNOWN_STATUS = {
            "200": ("ok", "success", "thành công"),
            "201": ("created", "tạo"),
            "204": ("no content", "không nội dung"),
            "301": ("moved permanently", "chuyển vĩnh viễn"),
            "302": ("found", "redirect", "chuyển hướng"),
            "304": ("not modified", "không thay đổi"),
            "400": ("bad request", "yêu cầu sai"),
            "401": ("unauthorized", "không được ủy quyền"),
            "403": ("forbidden", "cấm"),
            "404": ("not found", "không tìm thấy"),
            "405": ("method not allowed", "phương thức không được phép"),
            "429": ("too many requests", "quá nhiều yêu cầu"),
            "500": ("internal server error", "lỗi server", "lỗi máy chủ"),
            "502": ("bad gateway", "cổng sai"),
            "503": ("service unavailable", "dịch vụ không khả dụng"),
            "504": ("gateway timeout", "hết thời gian chờ"),
        }
        _q_lower = question.lower()
        a_lower = answer.lower()
        # Find status codes in QUESTION
        status_codes = re.findall(r'\b([1-5]\d{2})\b', question)
        for code in status_codes:
            if code in KNOWN_STATUS:
                valid_descs = KNOWN_STATUS[code]
                # Check if answer has wrong description
                if not any(desc in a_lower for desc in valid_descs):
                    result.passed = False
                    result.severity = "high"
                    result.confidence = 0.8
                    result.details = f"HTTP {code} should mean '{valid_descs[0]}', but answer doesn't mention it"
                    break
        if result.passed:
            result.details = f"HTTP status check passed: {len(status_codes)} code(s) scanned"

        # === [Task 29-B: NEW] 6 economics/philosophy/psychology/agriculture/earth_science antibodies ===
        return True

class EconomicsAntibodyMixin:
    def verify_gdp(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 29-B] Verify GDP growth rates — most countries grow 0-10%/yr.
        # >10%/yr sustained is implausible (China peak ~14%, but rare).
        # Pattern: extract % near "GDP", "growth", "tăng trưởng".
        a_lower = answer.lower()
        # Find percentages near GDP/growth keywords (within ~30 chars window)
        # Use a permissive regex: capture all percentages, then check context
        all_pcts = list(re.finditer(r'(\d+(?:\.\d+)?)\s*%', answer))
        for m in all_pcts:
            pct_val = float(m.group(1))
            # Window 30 chars before and after the percentage
            start = max(0, m.start() - 30)
            end = min(len(a_lower), m.end() + 30)
            context = a_lower[start:end]
            if any(kw in context for kw in ["gdp", "growth", "tăng trưởng", "kinh tế"]):
                if pct_val > 10:
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.75
                    result.details = (
                        f"GDP growth rate {pct_val}% is implausibly high "
                        f"(most countries grow 0-10%/yr; only China peaked ~14%)"
                    )
                    break
        if result.passed:
            result.details = f"GDP check passed: {len(all_pcts)} percentage(s) scanned"
        return True

    def verify_inflation(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 29-B] Verify inflation rates — >20% is extreme (except hyperinflation).
        # Hyperinflation (>50%/month) is rare — should be explicit in answer.
        a_lower = answer.lower()
        all_pcts = list(re.finditer(r'(\d+(?:\.\d+)?)\s*%', answer))
        for m in all_pcts:
            pct_val = float(m.group(1))
            start = max(0, m.start() - 30)
            end = min(len(a_lower), m.end() + 30)
            context = a_lower[start:end]
            if any(kw in context for kw in ["inflation", "lạm phát", "cpi", "price index"]):
                if pct_val > 50:
                    # Likely hyperinflation — flag as high severity
                    result.passed = False
                    result.severity = "high"
                    result.confidence = 0.85
                    result.details = (
                        f"Inflation {pct_val}% — hyperinflation territory. "
                        f"Verify if answer explicitly mentions hyperinflation context."
                    )
                    break
                elif pct_val > 20:
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.7
                    result.details = (
                        f"Inflation {pct_val}% is extreme — verify against historical data "
                        f"(most countries stay under 20%, except crises)"
                    )
                    break
        if result.passed:
            result.details = f"Inflation check passed: {len(all_pcts)} percentage(s) scanned"
        return True

class PhilosophyAntibodyMixin:
    def verify_fallacy(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 29-B] Detect logical fallacies in answer.
        # Flag common fallacy patterns by name + Vietnamese equivalent.
        FALLACIES = {
            # English
            "ad hominem": "attacking the person instead of the argument",
            "straw man": "misrepresenting opponent's argument",
            "strawman": "misrepresenting opponent's argument",
            "false dichotomy": "presenting only 2 options when more exist",
            "false dilemma": "presenting only 2 options when more exist",
            "slippery slope": "claiming chain reaction without evidence",
            "circular reasoning": "using conclusion as premise",
            "begging the question": "using conclusion as premise",
            "appeal to authority": "using authority as evidence",
            "appeal to emotion": "using emotion instead of evidence",
            "post hoc": "correlation ≠ causation",
            "red herring": "distracting from the argument",
            "tu quoque": "whataboutism / appeal to hypocrisy",
            # Vietnamese
            "ngụy biện": "fallacy detected (Vietnamese)",
            "ngụy biện cá nhân": "ad hominem (Vietnamese)",
            "ngụy biện rơm rạ": "straw man (Vietnamese)",
            "lập luận vòng lặp": "circular reasoning (Vietnamese)",
        }
        a_lower = answer.lower()
        for fallacy, desc in FALLACIES.items():
            if fallacy in a_lower:
                result.passed = False
                result.severity = "medium"
                result.confidence = 0.7
                result.details = (
                    f"Logical fallacy detected: '{fallacy}' ({desc}) — "
                    f"answer should identify and refute, not commit fallacies"
                )
                break
        if result.passed:
            result.details = "Fallacy check passed: no logical fallacies detected"
        return True

class PsychologyAntibodyMixin:
    def verify_cognitive_bias(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 29-B] Detect cognitive biases in reasoning.
        # Bias acknowledgment is fine; using biased reasoning is not.
        BIASES = {
            "anchoring bias": "over-relying on first piece of information",
            "confirmation bias": "favoring info that confirms existing beliefs",
            "availability heuristic": "overweighting easily-recalled examples",
            "dunning-kruger": "low-ability overestimating competence",
            "survivorship bias": "focusing on survivors, ignoring failures",
            "sunk cost": "continuing because of past investment",
            "hindsight bias": "'I knew it all along' after the fact",
            "framing effect": "drawing different conclusions from same info",
            "bandwagon effect": "believing because others do",
            "halo effect": "one positive trait coloring overall judgment",
            # Vietnamese
            "thiên kiến": "bias (Vietnamese)",
            "thiên kiến xác nhận": "confirmation bias (Vietnamese)",
            "thiên kiến mỏ neo": "anchoring bias (Vietnamese)",
            "thiên lệch": "bias (Vietnamese)",
        }
        a_lower = answer.lower()
        for bias, desc in BIASES.items():
            if bias in a_lower:
                # Check if answer is acknowledging bias (good) vs committing it (bad)
                # Heuristic: if 'avoid', 'recognize', 'aware of', 'bias toward' near → acknowledgment
                bias_pos = a_lower.find(bias)
                window = a_lower[max(0, bias_pos - 40):bias_pos + len(bias) + 40]
                ack_markers = ["avoid", "recognize", "aware of", "fall victim",
                               "overcome", "bias toward", "tránh", "nhận thức",
                               "ý thức được"]
                if not any(ack in window for ack in ack_markers):
                    result.passed = False
                    result.severity = "low"
                    result.confidence = 0.6
                    result.details = (
                        f"Possible cognitive bias in reasoning: '{bias}' ({desc}) — "
                        f"answer uses biased framing without acknowledging it"
                    )
                    break
        if result.passed:
            result.details = "Cognitive bias check passed: no biased reasoning detected"
        return True

class AgricultureAntibodyMixin:
    def verify_crop_yield(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 29-B] Verify crop yield claims — rice 5-10 t/ha normal.
        # >15 t/ha implausible (record is ~12 t/ha for hybrid rice).
        # <1 t/ha suspicious for major crops (would indicate failure).
        # Pattern: extract number near "tấn/ha", "t/ha", "tons/ha".
        a_lower = answer.lower()
        # Match patterns: "X tấn/ha", "X t/ha", "X tons per hectare", "X t/ha"
        yield_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:tấn|t|tons?)\s*(?:/|per)?\s*(?:ha|hectare)',
            r'(\d+(?:\.\d+)?)\s*(?:tạ)\s*(?:/|per)?\s*(?:ha|hectare)',  # 1 tạ = 0.1 t
        ]
        checked = 0
        for pattern in yield_patterns:
            for m in re.finditer(pattern, a_lower):
                val = float(m.group(1))
                # Convert tạ → tấn (1 tấn = 10 tạ)
                if 'tạ' in pattern:
                    val = val / 10.0
                checked += 1
                if val > 15:
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.75
                    result.details = (
                        f"Crop yield {val} t/ha is implausibly high "
                        f"(rice 5-10 t/ha normal; record ~12 t/ha for hybrid rice)"
                    )
                    break
                elif val < 1:
                    result.passed = False
                    result.severity = "low"
                    result.confidence = 0.6
                    result.details = (
                        f"Crop yield {val} t/ha is very low — "
                        f"verify if answer mentions crop failure or specific conditions"
                    )
                    break
            if not result.passed:
                break
        if result.passed:
            result.details = f"Crop yield check passed: {checked} yield(s) scanned"
        return True

class Earth_ScienceAntibodyMixin:
    def verify_earthquake_magnitude(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 29-B] Verify earthquake magnitudes — 0-9 range, >9.5 implausible.
        # Largest recorded: 9.5 (Valdivia, Chile 1960).
        # Negative magnitude is impossible (Richter scale starts at 0).
        a_lower = answer.lower()
        # Find magnitudes near "magnitude", "độ lớn", "richter", "Mw", "Ml".
        # Allow optional words (was|is|of|:|=|scale) between keyword and number
        # to handle natural phrasings like "magnitude was 9.8".
        mag_patterns = [
            r'magnitude\s*(?:of|was|is|:|=|scale)?\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*magnitude',
            r'mw\s*(?:of|was|is|:|=)?\s*(\d+(?:\.\d+)?)',
            r'ml\s*(?:of|was|is|:|=)?\s*(\d+(?:\.\d+)?)',
            r'richter\s*(?:scale)?\s*(?:of|was|is|:|=)?\s*(\d+(?:\.\d+)?)',
            r'độ lớn\s*(?:là|:|=)?\s*(\d+(?:\.\d+)?)',
        ]
        checked = 0
        for pattern in mag_patterns:
            for m in re.finditer(pattern, a_lower):
                val = float(m.group(1))
                checked += 1
                if val > 9.5:
                    result.passed = False
                    result.severity = "high"
                    result.confidence = 0.85
                    result.details = (
                        f"Earthquake magnitude {val} is implausible — "
                        f"largest recorded: 9.5 (Valdivia, Chile 1960)"
                    )
                    break
                elif val < 0:
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.8
                    result.details = (
                        f"Earthquake magnitude {val} is invalid — "
                        f"Richter scale starts at 0 (negative magnitudes impossible)"
                    )
                    break
                elif val > 8:
                    # Great earthquake — flag as low severity for verification
                    result.passed = False
                    result.severity = "low"
                    result.confidence = 0.55
                    result.details = (
                        f"Earthquake magnitude {val} is in 'great earthquake' range (>8.0) — "
                        f"verify against historical records (rare, ~1/year globally)"
                    )
                    break
            if not result.passed:
                break
        if result.passed:
            result.details = f"Earthquake magnitude check passed: {checked} magnitude(s) scanned"
        return True

class EngineeringAntibodyMixin:
    def verify_safety_factor(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 30-C] Safety factor must be >1.0 for structural integrity.
        # <1.0 = failure risk (critical). >10 = over-engineered (suspicious).
        # Pattern: extract number near "safety factor" / "FoS" / "hệ số an toàn".
        a_lower = answer.lower()
        sf_patterns = [
            r'safety\s+factor\s*(?:of|is|=|:|was)?\s*(\d+\.?\d*)',
            r'factor\s+of\s+safety\s*(?:of|is|=|:|was)?\s*(\d+\.?\d*)',
            r'fos\s*(?:of|is|=|:|was)?\s*(\d+\.?\d*)',
            r'hệ\s+số\s+an\s+toàn\s*(?:=|:|là)?\s*(\d+\.?\d*)',
            r'design\s+factor\s*(?:of|is|=|:|was)?\s*(\d+\.?\d*)',
        ]
        checked = 0
        for pattern in sf_patterns:
            for m in re.finditer(pattern, a_lower):
                val = float(m.group(1))
                checked += 1
                if val < 1.0:
                    result.passed = False
                    result.severity = Severity.CRITICAL  # [ROOT-FIX Task 38-A] was: "critical"
                    result.confidence = 0.95
                    result.details = (
                        f"Safety factor {val} < 1.0 — structural failure risk "
                        f"(load exceeds capacity)"
                    )
                    break
                elif val > 10:
                    result.passed = False
                    result.severity = Severity.MEDIUM  # [ROOT-FIX Task 38-A] was: "medium"
                    result.confidence = 0.7
                    result.details = (
                        f"Safety factor {val} > 10 — over-engineered (suspicious); "
                        f"typical FoS = 1.5-3 for most structures"
                    )
                    break
            if not result.passed:
                break
        if result.passed:
            result.details = f"Safety factor check passed: {checked} value(s) scanned"
        return True

    def verify_material_strength(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 30-C] Material strength plausibility.
        # Steel yield: 250-2000 MPa. Aluminum: 70-700 MPa. Concrete compressive: 10-80 MPa.
        # >5000 MPa implausible (no common material exceeds ~5000 MPa).
        # <10 MPa too weak for structural use.
        a_lower = answer.lower()
        # Normalize GPa → MPa (×1000), ksi → MPa (×6.895), psi → MPa (×0.006895)
        strength_patterns = [
            (r'(\d+(?:\.\d+)?)\s*gpa', 1000.0),       # GPa → MPa
            (r'(\d+(?:\.\d+)?)\s*ksi', 6.895),        # ksi → MPa
            (r'(\d+(?:\.\d+)?)\s*psi', 0.006895),     # psi → MPa
            (r'(\d+(?:\.\d+)?)\s*mpa', 1.0),          # MPa
        ]
        checked = 0
        for pattern, mult in strength_patterns:
            for m in re.finditer(pattern, a_lower):
                val_mpa = float(m.group(1)) * mult
                checked += 1
                if val_mpa > 5000:
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.75
                    result.details = (
                        f"Material strength {val_mpa:.1f} MPa is implausibly high "
                        f"(strongest steels ~2000 MPa; carbon nanotube ~63000 MPa is lab-only)"
                    )
                    break
                elif val_mpa < 10:
                    result.passed = False
                    result.severity = "low"
                    result.confidence = 0.6
                    result.details = (
                        f"Material strength {val_mpa:.1f} MPa is very low for structural use "
                        f"(<10 MPa; concrete ~20-40 MPa minimum)"
                    )
                    break
            if not result.passed:
                break
        if result.passed:
            result.details = f"Material strength check passed: {checked} value(s) scanned"
        return True

class ArtAntibodyMixin:
    def verify_art_period(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 30-C] Verify artwork period matches artist's lifetime + style era.
        # Artist lifetimes (subset of canonical Western artists).
        ARTIST_LIFESPAN = {
            "leonardo da vinci": (1452, 1519),
            "da vinci": (1452, 1519),
            "michelangelo": (1475, 1564),
            "raphael": (1483, 1520),
            "rembrandt": (1606, 1669),
            "vermeer": (1632, 1675),
            "vangogh": (1853, 1890), "van gogh": (1853, 1890),
            "monet": (1840, 1926),
            "renoir": (1841, 1919),
            "degas": (1834, 1917),
            "cezanne": (1839, 1906), "cézanne": (1839, 1906),
            "picasso": (1881, 1973),
            "matisse": (1869, 1954),
            "dali": (1904, 1989), "dalí": (1904, 1989),
            "klimt": (1862, 1918),
            "warhol": (1928, 1987),
        }
        # Style eras: (start, end) — flag if year outside era.
        STYLE_ERA = {
            "renaissance": (1400, 1600),
            "baroque": (1600, 1750),
            "rococo": (1700, 1780),
            "neoclassicism": (1760, 1840),
            "romanticism": (1780, 1850),
            "realism": (1840, 1880),
            "impressionism": (1860, 1890),
            "post-impressionism": (1880, 1910),
            "cubism": (1907, 1925),
            "surrealism": (1924, 1966),
            "modernism": (1860, 1970),
            "gothic": (1150, 1500),
        }
        a_lower = answer.lower()
        # Extract year (4-digit)
        years = re.findall(r'\b(1[2-9]\d{2}|20\d{2})\b', answer)
        # Find mentioned artists
        found_artist = None
        for artist, (birth, death) in ARTIST_LIFESPAN.items():
            if artist in a_lower:
                found_artist = (artist, birth, death)
                break
        # Find mentioned style
        found_style = None
        for style, (start, end) in STYLE_ERA.items():
            if style in a_lower:
                found_style = (style, start, end)
                break
        flagged = False
        for year_str in years:
            year = int(year_str)
            # Check against artist lifetime
            if found_artist:
                _, birth, death = found_artist
                if year < birth:
                    result.passed = False
                    result.severity = "high"
                    result.confidence = 0.85
                    result.details = (
                        f"Year {year} is before artist's birth ({birth}) — "
                        f"implausible artwork date"
                    )
                    flagged = True
                    break
                if year > death + 10:
                    result.passed = False
                    result.severity = "high"
                    result.confidence = 0.85
                    result.details = (
                        f"Year {year} is more than 10 years after artist's death ({death}) — "
                        f"implausible artwork date"
                    )
                    flagged = True
                    break
            # Check style era
            if found_style:
                style_name, start, end = found_style
                # [AUTOFIX-T1] mypy [operator]: ensure int (STYLE_ERA values are int
                # but mypy infers str from dict key context). Cast for safety.
                start_i, end_i = int(start), int(end)
                if year < start_i - 5 or year > end_i + 5:
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.7
                    result.details = (
                        f"Year {year} doesn't match {style_name} era "
                        f"(approx. {start}-{end}) — verify attribution"
                    )
                    flagged = True
                    break
        if not flagged:
            result.details = (
                f"Art period check passed: {len(years)} year(s) scanned, "
                f"artist={found_artist[0] if found_artist else 'unknown'}, "
                f"style={found_style[0] if found_style else 'unknown'}"
            )
        return True

class MilitaryAntibodyMixin:
    def verify_weapon_range(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 30-C] Weapon range plausibility by category.
        # Handgun: 50-100m. Rifle: 500-2000m. Artillery/howitzer: 10-40 km.
        # SAM: 50-200 km. ICBM: 5000-15000 km.
        # Flag if range exceeds category typical max.
        a_lower = answer.lower()
        # Detect weapon category
        category = None
        if any(w in a_lower for w in ["handgun", "pistol", "súng ngắn"]):
            category = ("handgun", 1.0, "km")  # 1 km = suspicious
        elif any(w in a_lower for w in ["rifle", "súng trường", "sniper"]):
            category = ("rifle", 3.0, "km")    # 3 km = extreme
        elif any(w in a_lower for w in ["howitzer", "pháo", "artillery", "cannon"]):
            category = ("artillery", 100.0, "km")  # 100 km = extreme
        elif any(w in a_lower for w in ["sam", "surface-to-air", "air defense"]):
            category = ("SAM", 500.0, "km")
        elif any(w in a_lower for w in ["icbm", "intercontinental", "tên lửa liên lục địa"]):
            category = ("ICBM", 20000.0, "km")
        elif any(w in a_lower for w in ["missile", "tên lửa"]):
            category = ("missile", 10000.0, "km")  # generic — wide range
        # Extract ranges (m, km, nautical mile)
        range_patterns = [
            (r'(\d+(?:\.\d+)?)\s*km\b', 1.0, "km"),
            (r'(\d+(?:\.\d+)?)\s*kilometers?\b', 1.0, "km"),
            (r'(\d+(?:\.\d+)?)\s*(?:m|meters?)\b', 0.001, "km"),  # m → km
            (r'(\d+(?:\.\d+)?)\s*(?:nm|nautical\s+miles?)\b', 1.852, "km"),
        ]
        checked = 0
        flagged = False
        for pattern, mult, _unit in range_patterns:
            for m in re.finditer(pattern, a_lower):
                val_km = float(m.group(1)) * mult
                # Only flag if context mentions range keyword within 40 chars
                start = max(0, m.start() - 40)
                end = min(len(a_lower), m.end() + 40)
                context = a_lower[start:end]
                if not any(kw in context for kw in
                           ["range", "tầm", "reach", "distance", "reach", "fired"]):
                    continue
                checked += 1
                if category:
                    cat_name, max_km, _ = category
                    if val_km > max_km:
                        result.passed = False
                        result.severity = "high"
                        result.confidence = 0.8
                        result.details = (
                            f"Weapon range {val_km} km exceeds {cat_name} typical max "
                            f"(~{max_km} km) — verify specification"
                        )
                        flagged = True
                        break
            if flagged:
                break
        if not flagged:
            result.details = (
                f"Weapon range check passed: {checked} range(s) scanned"
                + (f", category={category[0]}" if category else "")
            )
        return True

class EnvironmentalAntibodyMixin:
    def verify_carbon_emission(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 30-C] Carbon emission plausibility.
        # Global total: ~37000 Mt CO2/yr (2023). Country: 1-10000 Mt.
        # Per capita: 1-50 tons/yr (Qatar highest ~37). >100 tons/person = implausible.
        a_lower = answer.lower()
        # Detect "per capita" context
        is_per_capita = any(kw in a_lower for kw in
                            ["per capita", "per person", "người", "mỗi người"])
        # Detect emission unit
        unit_patterns = [
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:mt|megaton)', "Mt"),
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:gt|gigaton)', "Gt"),
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:kt|kiloton)', "kt"),
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*tons?\s*(?:co2|carbon)', "tons"),
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:tấn)\s*(?:co2|carbon)', "tons"),
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*kg\s*(?:co2|carbon)', "kg"),
        ]
        checked = 0
        flagged = False
        for pattern, unit in unit_patterns:
            for m in re.finditer(pattern, a_lower, re.IGNORECASE):
                raw = m.group(1).replace(",", "")
                val = float(raw)
                checked += 1
                # Normalize to Mt CO2
                if unit == "Gt":
                    val_mt = val * 1000
                elif unit == "kt":
                    val_mt = val / 1000
                elif unit == "tons":
                    # If per capita, val is tons/person; else assume country total in tons
                    if is_per_capita:
                        # Per capita threshold
                        if val > 100:
                            result.passed = False
                            result.severity = "high"
                            result.confidence = 0.85
                            result.details = (
                                f"Per capita CO2 emission {val} tons/yr is implausible "
                                f"(global highest: Qatar ~37 tons/yr)"
                            )
                            flagged = True
                            break
                        continue
                    else:
                        val_mt = val / 1_000_000  # tons → Mt
                elif unit == "kg":
                    if is_per_capita:
                        val_tons = val / 1000
                        if val_tons > 100:
                            result.passed = False
                            result.severity = "high"
                            result.confidence = 0.85
                            result.details = (
                                f"Per capita CO2 emission {val_tons:.1f} tons/yr is implausible "
                                f"(global highest: Qatar ~37 tons/yr)"
                            )
                            flagged = True
                            break
                    continue
                else:
                    val_mt = val
                # Country-level Mt threshold (skip per capita)
                if not is_per_capita and val_mt > 50000:
                    result.passed = False
                    result.severity = "high"
                    result.confidence = 0.85
                    result.details = (
                        f"CO2 emission {val_mt:.0f} Mt is implausible — "
                        f"global total ~37000 Mt/yr; verify unit/context"
                    )
                    flagged = True
                    break
            if flagged:
                break
        if not flagged:
            result.details = (
                f"Carbon emission check passed: {checked} value(s) scanned"
                + (", per capita context" if is_per_capita else "")
            )
        return True

class EducationAntibodyMixin:
    def verify_pedagogy(self, result: AntibodyResult, question: str, answer: str, ab_name: str) -> bool:
        _check_ran = True
        # [Task 30-C] Verify pedagogical theory claims.
        # Piaget: 4 stages — sensorimotor (0-2), preoperational (2-7),
        #   concrete operational (7-11), formal operational (11+).
        # Bloom: 6 levels — remember, understand, apply, analyze,
        #   evaluate, create (revised; original had 'knowledge' at bottom).
        # Vygotsky: ZPD = gap between solo and assisted performance.
        a_lower = answer.lower()
        flagged = False
        # Piaget stage age verification
        PIAGET_STAGES = {
            "sensorimotor": (0, 2),
            "preoperational": (2, 7),
            "concrete operational": (7, 11),
            "formal operational": (11, 100),
        }
        if "piaget" in a_lower:
            for stage, (lo, hi) in PIAGET_STAGES.items():
                if stage in a_lower:
                    # Find age mention near the stage
                    stage_pos = a_lower.find(stage)
                    window = a_lower[max(0, stage_pos - 60):stage_pos + len(stage) + 60]
                    ages = re.findall(r'(\d+)\s*(?:-|\s+to\s+)\s*(\d+)', window)
                    for age_lo, age_hi in ages:
                        age_lo, age_hi = int(age_lo), int(age_hi)
                        if age_lo != lo or age_hi != hi:
                            result.passed = False
                            result.severity = "medium"
                            result.confidence = 0.8
                            result.details = (
                                f"Piaget '{stage}' stage is ages {lo}-{hi}, "
                                f"but answer claims {age_lo}-{age_hi}"
                            )
                            flagged = True
                            break
                    if flagged:
                        break
            # Check if answer claims wrong stage count
            if not flagged:
                stage_count_claim = re.search(
                    r'(\d+)\s*(?:stages?|giai đoạn)', a_lower)
                if stage_count_claim:
                    claimed = int(stage_count_claim.group(1))
                    if "piaget" in a_lower and claimed != 4:
                        result.passed = False
                        result.severity = "medium"
                        result.confidence = 0.8
                        result.details = (
                            f"Piaget has 4 stages, but answer claims {claimed}"
                        )
                        flagged = True
        # Bloom taxonomy level count
        if not flagged and "bloom" in a_lower:
            BLOOM_LEVELS = {"remember", "understand", "apply", "analyze",
                            "evaluate", "create"}
            [lvl for lvl in BLOOM_LEVELS if lvl in a_lower]
            count_claim = re.search(r'(\d+)\s*(?:levels?|cấp độ|tầng)', a_lower)
            if count_claim:
                claimed = int(count_claim.group(1))
                if claimed != 6:
                    result.passed = False
                    result.severity = "medium"
                    result.confidence = 0.8
                    result.details = (
                        f"Bloom's revised taxonomy has 6 levels, "
                        f"but answer claims {claimed}"
                    )
                    flagged = True
        # Vygotsky ZPD verification
        if not flagged and "vygotsky" in a_lower:
            if "zpd" in a_lower or "zone of proximal development" in a_lower:
                # ZPD = gap between solo and assisted ability
                # Flag if answer claims ZPD is a fixed ability (misattribution)
                zpd_pos = max(a_lower.find("zpd"),
                              a_lower.find("zone of proximal development"))
                if zpd_pos >= 0:
                    window = a_lower[max(0, zpd_pos - 60):zpd_pos + 100]
                    if any(wrong in window for wrong in
                           ["fixed ability", "innate ability",
                            " IQ ", "intelligence quotient"]):
                        result.passed = False
                        result.severity = "medium"
                        result.confidence = 0.75
                        result.details = (
                            "Vygotsky ZPD is the gap between what a learner can do "
                            "alone vs with guidance — not a fixed ability or IQ measure"
                        )
                        flagged = True
        if not flagged:
            result.details = "Pedagogy check passed: no misattributed theory claims"
        return True

