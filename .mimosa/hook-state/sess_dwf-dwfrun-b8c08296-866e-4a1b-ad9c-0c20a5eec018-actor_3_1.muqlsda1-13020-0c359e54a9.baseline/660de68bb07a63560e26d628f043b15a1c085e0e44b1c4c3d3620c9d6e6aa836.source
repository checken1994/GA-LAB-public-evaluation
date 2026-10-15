"""
Question Normalizer — Shared util cho tất cả SLM.

[Z.ai-ROOT-FIX #9] TẠI SAO: SLM hiện tại dùng `if keyword in q_lower` (exact substring)
→ không xử lý biến thể câu hỏi thực tế ("số xương" vs "bao nhiêu xương" vs "số lượng xương").
Benchmark ISO cho thấy 3/6 câu cùng ý nhưng SLM chỉ match 1-2 câu.

Fix từ gốc: Question Normalizer với 3 lớp:
1. Stopword removal — bỏ từ không mang ý nghĩa ("có", "là", "bao nhiêu", "của", "trong")
2. Synonym replacement — map biến thể về canonical form ("bao nhiêu xương" → "số xương")
3. Token-based matching — Jaccard overlap thay vì exact substring

Synonym dictionary cho 10 domain (biology, chemistry, physics, medical, math, etc.)
được định nghĩa ở đây (single source of truth) thay vì rải rác trong từng SLM.

Usage:
    from scp.core.question_normalizer import normalize_question, match_question

    canonical_q = normalize_question("Cơ thể người có bao nhiêu xương?")
    # → "số xương cơ thể người"

    is_match = match_question("bao nhiêu xương trong người", "số xương cơ thể người")
    # → True (Jaccard ≥ 0.5)
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable

logger = logging.getLogger(__name__)


# ============================================================
# STOPWORDS — từ không mang ý nghĩa, bỏ trước khi match
# ============================================================

_STOPWORDS_VI = {
    # Question words
    "bao nhiêu", "bao nhieu", "là gì", "la gi", "gì", "gi",
    "như thế nào", "nhu the nao", "thế nào", "the nao",
    "có bao nhiêu", "co bao nhieu",
    "cho biết", "cho biet", "hãy cho", "hay cho",
    "tại sao", "tai sao", "vì sao", "vi sao",
    "như nào", "nhu nao",
    # Prepositions/articles
    "của", "cua", "trong", "có", "co", "là", "la", "và", "va",
    "các", "cac", "những", "nhung", "một", "mot", "cái", "cai",
    "được", "duoc", "bị", "bi", "về", "ve", "với", "voi",
    "để", "de", "từ", "tu", "vào", "vao", "ra", "lên", "len", "xuống", "xuong",
    "này", "nay", "kia", "đó", "do", "đây", "day",
    "người", "nguoi",  # thường không cần thiết
    # English equivalents
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "what", "how", "why", "when", "where", "who", "which",
    "of", "in", "on", "at", "to", "for", "with", "by",
    "does", "did", "can", "could", "would", "should",
    "tell", "me", "about", "explain", "describe",
    "many", "much", "long", "old", "far",
}

# Punctuation to strip
_PUNCT_RE = re.compile(r"[!?.,;:()\[\]{}\"'`/\\@#$%^&*+=<>|~]")
# Multi-space collapse
_MULTISPACE_RE = re.compile(r"\s+")


# ============================================================
# SYNONYM DICTIONARY — canonical form → variants
# ============================================================
# Key = canonical form (what SLM KB uses)
# Value = set of variant phrases that should map to canonical

_SYNONYMS = {
    # ============================================================
    # BIOLOGY
    # ============================================================
    "số xương": {
        "bao nhiêu xương", "số lượng xương", "tổng số xương",
        "số cai xương", "số chiếc xương", "có bao nhiêu xương",
        "bao nhiêu cái xương", "bao nhiêu chiếc xương",
        "how many bones", "number of bones",
    },
    # [G5-RUFF] merged with duplicate at line 291 (TRANSLITERATION)
    # [G5-RUFF] merged with duplicate at line 159 (MEDICAL)
    "dna": {"deoxyribonucleic acid", "phân tử dna", "chuỗi dna"},
    "rna": {"ribonucleic acid", "phân tử rna"},
    "atp": {"adenosine triphosphate"},
    # [G5-RUFF] merged with duplicate at line 289 (TRANSLITERATION)
    # [G5-RUFF] merged with duplicate at line 290 (TRANSLITERATION)
    "nucleus": {"nhân tế bào", "nhân"},
    "ribosome": {"thể hạt nhỏ", "ribosome"},
    "quang hợp": {"photosynthesis", "tổng hợp ánh sáng"},
    "nhóm máu": {"hệ máu", "blood type", "blood group"},
    # [G5-RUFF] merged with duplicate at line 157 (MEDICAL) — kept both synonym sets

    # ============================================================
    # CHEMISTRY
    # ============================================================
    "công thức hóa học": {
        "công thức", "formula", "chemical formula",
        "công thức phân tử", "molecular formula",
    },
    "nguyên tử số": {"atomic number", "số nguyên tử"},
    "số nguyên tử": {"number of atoms", "atom count", "số lượng nguyên tử"},
    "số proton": {"number of protons", "proton count"},
    "số electron": {"number of electrons", "electron count"},
    "số neutron": {"number of neutrons", "neutron count"},
    "khối lượng mol": {"molar mass", "phân tử lượng", "khối lượng phân tử", "molecular weight"},
    "hóa trị": {"valence", "valency"},
    "kim loại": {"metal", "kim loại nhẹ", "kim loại nặng"},
    "phi kim": {"nonmetal", "non-metal"},

    # ============================================================
    # PHYSICS
    # ============================================================
    "tốc độ ánh sáng": {"speed of light", "vận tốc ánh sáng", "light speed"},
    "nhiệt độ sôi của nước": {
        "boiling point of water", "điểm sôi của nước", "nhiệt độ hóa hơi của nước",
        "boiling point", "nhiệt độ sôi", "điểm sôi",  # shorter forms
    },
    "nhiệt độ đóng băng của nước": {
        "freezing point of water", "điểm đóng băng của nước", "nhiệt độ đông đặc của nước",
        "freezing point", "nhiệt độ đóng băng", "điểm đóng băng",
    },
    "gia tốc trọng trường": {"gravity", "trọng lực", "gia tốc rơi tự do", "gravitational acceleration"},
    "số avogadro": {"avogadro number", "avogadro's number", "hằng số avogadro"},
    "hằng số planck": {"planck constant", "planck's constant"},
    "điện tích electron": {"electron charge", "electron electric charge"},
    "điện tích nguyên tố": {"elementary charge", "electron charge"},
    "quarks": {"quark", "hạt quark"},
    "khối lượng trái đất": {"mass of earth", "trọng lượng trái đất", "khối lượng đất"},
    "bán kính trái đất": {"radius of earth", "bán kính đất"},
    "hằng số hấp dẫn": {"gravitational constant", "hằng số vạn vật hấp dẫn"},
    "khối lượng electron": {"mass of electron", "electron mass"},
    "khối lượng proton": {"mass of proton", "proton mass"},
    "khối lượng neutron": {"mass of neutron", "neutron mass"},
    "áp suất khí quyển": {"atmospheric pressure", "atm pressure"},
    "tốc độ âm thanh": {"speed of sound", "vận tốc âm thanh"},

    # ============================================================
    # MATH
    # ============================================================
    # [G5-RUFF] merged with duplicate at line 259 (MATH extended)
    # [G5-RUFF] merged with duplicate at line 260 (MATH extended)
    # [G5-RUFF] merged with duplicate at line 261 (MATH extended)
    # [G5-RUFF] merged with duplicate at line 262 (MATH extended)
    # [G5-RUFF] merged with duplicate at line 263 (MATH extended)
    # [G5-RUFF] merged with duplicate at line 264 (MATH extended)

    # ============================================================
    # MEDICAL
    # ============================================================
    # [G5-RUFF] merged with duplicate at line 247 (MEDICAL extended)
    # [G5-RUFF] merged with duplicate at line 248 (MEDICAL extended)
    "huyết áp": {"blood pressure", "bp"},
    "nhịp tim": {"heart rate", "tần suất tim", "số nhịp tim", "hr", "pulse"},
    "bmi": {"body mass index", "chỉ số khối cơ thể"},
    "insulin": {"insulin", "insullin", "hormone insulin"},
    # [G5-RUFF] merged with duplicate at line 250 (MEDICAL extended)

    # ============================================================
    # GEOGRAPHY
    # ============================================================
    "thủ đô": {"capital", "capital city", "kinh đô"},
    # [G5-RUFF] merged with duplicate at line 232 (FINANCE/GEO)
    "dân số": {"population", "số dân", "số người"},
    "lục địa": {"continent", "châu lục"},

    # ============================================================
    # HISTORY
    # ============================================================
    "chiến tranh": {"war", "cuộc chiến", "civil war"},
    "cách mạng": {"revolution", "cuộc cách mạng"},
    "đế chế": {"empire", "đế quốc"},
    "chiến tranh thế giới": {"world war", "wwii", "ww2", "wwi", "ww1"},
    "độc lập": {"independence", "tuyên ngôn độc lập"},
    "sụp đổ": {"fell", "collapse", "kết thúc"},

    # ============================================================
    # TECHNOLOGY
    # ============================================================
    "status code": {"http status", "mã trạng thái", "http code", "status"},
    "viết tắt": {"stands for", "abbreviation", "viết tắc", "viêt tắt"},
    "ram": {"random access memory", "bộ nhớ truy cập ngẫu nhiên"},
    "cpu": {"central processing unit", "bộ xử lý trung tâm"},
    "gpu": {"graphics processing unit", "bộ xử lý đồ họa"},
    "dns": {"domain name system", "hệ thống tên miền"},
    "json": {"javascript object notation"},
    "api": {"application programming interface", "giao diện lập trình"},
    "sql": {"structured query language", "ngôn ngữ truy vấn có cấu trúc"},
    "docker": {"container", "containerization"},
    "kubernetes": {"k8s", "orchestration"},
    "cloud": {"đám mây", "computing cloud", "cloud computing"},
    "machine learning": {"ml", "học máy"},
    "deep learning": {"dl", "học sâu"},
    "neural network": {"mạng nơ-ron", "mạng neural"},
    # [G5-RUFF] merged with duplicate at line 294 (TRANSLITERATION)
    "database": {"cơ sở dữ liệu", "db", "database"},

    # ============================================================
    # ASTRONOMY
    # ============================================================
    "hành tinh": {"planet", "các hành tinh"},
    "sao thủy": {"mercury", "thủy tinh"},
    "sao kim": {"venus", "sao hôm", "hôm tinh"},
    "sao hỏa": {"mars", "hỏa tinh"},
    "sao mộc": {"jupiter", "mộc tinh"},
    "sao thổ": {"saturn", "thổ tinh"},
    "sao thiên vương": {"uranus", "thiên vương tinh"},
    "sao hải vương": {"neptune", "hải vương tinh"},
    "mặt trăng": {"moon", "lunar", "nguyệt"},
    "mặt trời": {"sun", "solar", "thái dương"},
    "galaxy": {"ngân hà", "thiên hà", "milky way"},
    "vũ trụ": {"universe", "cosmos", "space"},
    # [G5-RUFF] merged with duplicate at line 293 (TRANSLITERATION)
    "orbit": {"quỹ đạo", "orbital"},

    # ============================================================
    # FINANCE
    # ============================================================
    "tiền tệ": {"currency", "đơn vị tiền", "money"},
    "bitcoin": {"btc", "satoshi"},
    "ethereum": {"eth", "ether"},
    "blockchain": {"chuỗi khối", "distributed ledger"},
    "vnd": {"vietnamese dong", "đồng việt nam", "vnđ"},
    "usd": {"us dollar", "đô la mỹ", "dollar"},
    "eur": {"euro", "đồng euro"},
    "tỉ giá": {"exchange rate", "tỷ giá", "exchange"},
    "chứng khoán": {"stock", "share", "equity"},
    "inflation": {"lạm phát", "price inflation"},
    "diện tích": {"area", "kích thước", "size", "square"},
    "quốc gia": {"country", "nation", "state"},
    "thành phố": {"city", "urban", "municipality"},
    "sông": {"river", "stream"},
    "núi": {"mountain", "peak", "summit"},
    "biển": {"sea", "ocean", "marine"},
    "hồ": {"lake", "pond"},
    "sa mạc": {"desert"},
    "everest": {"đỉnh everest", "mount everest", "núi everest"},
    "nile": {"sông nile", "sông nil"},
    "sahara": {"sa mạc sahara"},

    # ============================================================
    # MEDICAL (extended)
    # ============================================================
    "paracetamol": {"acetaminophen", "panadol", "paracetamon", "tylenol"},
    "aspirin": {"acetylsalicylic acid", "asa", "bufferin"},
    "ibuprofen": {"advil", "motrin", "brufen"},
    "vaccine": {"vắc xin", "vắc-xin", "tiêm chủng", "immunization"},
    "antibiotic": {"kháng sinh", "antibiotics"},
    "covid": {"covid-19", "coronavirus", "sars-cov-2"},
    "bệnh viện": {"hospital", "medical center"},
    "bác sĩ": {"doctor", "physician", "medical doctor"},

    # ============================================================
    # MATH (extended)
    # ============================================================
    "giai thừa": {"factorial", "tính giai thừa", "factorial of"},
    "fibonacci": {"fib", "dãy fibonacci", "số fibonacci", "fibonacci sequence", "fibonacci of"},
    "gcd": {"ưcln", "ước số chung lớn nhất", "greatest common divisor", "gcd of"},
    "lcm": {"bcnn", "bội số chung nhỏ nhất", "least common multiple", "lcm of"},
    "căn bậc": {"square root", "sqrt", "căn", "căn bậc hai"},
    "lũy thừa": {"mũ", "power", "exponent", "exponential", "to the power"},
    "logarithm": {"log", "logarit"},
    "phương trình": {"equation", "solve equation"},
    "axit": {"acid", "acidic"},
    "bazơ": {"base", "basic", "alkaline"},
    "muối": {"salt", "ionic compound"},
    "glucose": {"đường gluco", "c6h12o6", "blood sugar"},
    "nước": {"water", "h2o", "liquid water"},

    # ============================================================
    # MIX VI+EN (very common in Vietnamese tech/medical context)
    # ============================================================
    "capital của": {"thủ đô của", "capital of"},
    "population của": {"dân số của", "population of"},
    "area của": {"diện tích của", "area of"},

    # ============================================================
    # TRANSLITERATION (foreign names → Vietnamese phonetic)
    # ============================================================
    "tokyo": {"đông kinh", "đông kinh đô"},
    "paris": {"pa-ri", "pari"},
    "london": {"luân đôn", "luan don"},
    "washington": {"oa-shinh-tơn", "oashington"},
    "newton": {"niuton", "niutơn"},
    "einstein": {"anh-stanh", "ein-stein"},
    "mitochondria": {"mai-tô-côn-tri-a", "ti thể", "thể hạt"},
    "chloroplast": {"clo-ro-plast", "lục lạp", "lạp lục"},
    "hemoglobin": {"hê-mô-glô-bin", "huyết sắc tố", "hb", "hemoglobin", "hemo"},
    "photosynthesis": {"quang hợp", "pho-tô-sin-thẹ-sis"},
    "satellite": {"sa-tên-lai", "vệ tinh", "artificial satellite"},
    "algorithm": {"al-gô-rithm", "thuật toán", "algo"},
}


# Build reverse lookup: variant → canonical
_VARIANT_TO_CANONICAL: dict[str, str] = {}
for _canonical, _variants in _SYNONYMS.items():
    _VARIANT_TO_CANONICAL[_canonical.lower()] = _canonical.lower()
    for _v in _variants:
        _VARIANT_TO_CANONICAL[_v.lower()] = _canonical.lower()


# ============================================================
# NORMALIZE — main entry point
# ============================================================

def normalize_question(question: str) -> str:
    """Normalize question for matching.

    Steps:
    1. Lowercase + strip punctuation
    2. Replace synonyms (variants → canonical)
    3. Remove stopwords
    4. Collapse whitespace

    Args:
        question: Raw question string

    Returns:
        Normalized question (canonical form, ready for KB/SLM lookup)
    """
    if not question:
        return ""

    # 1. Lowercase + strip punctuation
    q = question.lower().strip()
    q = _PUNCT_RE.sub(" ", q)

    # 2. Replace synonyms (longest match first to avoid partial overlap)
    # Sort variants by length descending so "bao nhiêu xương" matches before "xương"
    for variant in sorted(_VARIANT_TO_CANONICAL.keys(), key=len, reverse=True):
        if variant in q:
            canonical = _VARIANT_TO_CANONICAL[variant]
            q = q.replace(variant, canonical)

    # 3. Remove stopwords (multi-word stopwords first)
    for sw in sorted(_STOPWORDS_VI, key=len, reverse=True):
        # Use word boundary to avoid partial matches
        q = re.sub(r"\b" + re.escape(sw) + r"\b", " ", q, flags=re.IGNORECASE)

    # 4. Collapse whitespace + strip
    q = _MULTISPACE_RE.sub(" ", q).strip()

    return q


def match_question(query: str, stored_question: str, min_overlap: float = 0.5) -> bool:
    """Check if two questions match (token-based Jaccard overlap).

    Args:
        query: User's question (raw)
        stored_question: Question stored in KB/SLM KB
        min_overlap: Minimum Jaccard similarity (default 0.5)

    Returns:
        True if questions are considered equivalent
    """
    if not query or not stored_question:
        return False

    # Normalize both
    q1 = normalize_question(query)
    q2 = normalize_question(stored_question)

    # Exact match after normalization
    if q1 == q2:
        return True

    # Token-based Jaccard
    tokens1 = {w for w in q1.split() if len(w) > 1}
    tokens2 = {w for w in q2.split() if len(w) > 1}

    if not tokens1 or not tokens2:
        return False

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    jaccard = len(intersection) / len(union)

    return jaccard >= min_overlap


def keyword_match(question: str, keywords: Iterable[str], min_overlap: float = 0.5) -> bool:
    """Check if question contains any of the keywords (with synonym matching).

    Replaces SLM's `if keyword in q_lower` with synonym-aware matching.

    Args:
        question: User's question
        keywords: Iterable of keywords to match against
        min_overlap: For token-based fallback match

    Returns:
        True if any keyword matches (exact or synonym)
    """
    if not question or not keywords:
        return False

    q_normalized = normalize_question(question)
    q_lower = question.lower()

    for kw in keywords:
        if not kw:
            continue
        kw_lower = kw.lower().strip()
        # 1. Direct substring match (after normalization)
        if kw_lower in q_normalized:
            return True
        # 2. Synonym match — check if any variant of this keyword appears
        if kw_lower in _SYNONYMS:
            for variant in _SYNONYMS[kw_lower]:
                if variant.lower() in q_lower or variant.lower() in q_normalized:
                    return True
        # 3. Reverse: keyword might be a variant → check canonical
        canonical = _VARIANT_TO_CANONICAL.get(kw_lower)
        if canonical and canonical in q_normalized:
            return True

    return False


__all__ = ["normalize_question", "match_question", "keyword_match"]
