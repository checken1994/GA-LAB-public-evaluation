"""
SCP - Viet Nam | Self-Correcting Pipeline
 BiologyDataSource - Data source cho Sinh học
"""

import logging
import os
import re
import urllib.parse
from typing import Any

from defusedxml import ElementTree as ET  # nosec B314 — defusedxml hardens XXE

from scp.core.api_utils import fetch_with_retry  # [V5.8-API]
from scp.interfaces.data_source import IDataSource, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger(__name__)

# [AUDIT-20260909 SSRF-S1] taxid từ response NCBI (external data) PHẢI là
# digits — chặn trước khi ghép vào URL efetch.
_NCBI_TAXID_RE = re.compile(r"^\d{1,12}$")


def build_ncbi_efetch_taxonomy_url(taxid: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — taxid PHẢI fullmatch
    ^\\d{1,12}$; input xấu (path traversal, injection) → ValueError TRƯỚC
    KHI fetch. Host cố định eutils.ncbi.nlm.nih.gov."""
    tid = str(taxid or "").strip()
    if not _NCBI_TAXID_RE.fullmatch(tid):
        raise ValueError(f"invalid_taxid:{tid[:32]!r}")
    return (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=taxonomy&id={tid}&retmode=xml"
    )


def _wb_match(key: str, text_lower: str) -> bool:
    """[ROOT-FIX 4] Word-boundary match — prevents 'ATA' matching 'd**ata**',
    'Ala' matching 'b**ala**nce', 'Pro' matching '**pro**cess', etc.
    Uses Unicode-aware lookarounds so Vietnamese diacritics work too.
    """
    if not key or not text_lower:
        return False
    if key == text_lower:
        return True
    pattern = r'(?<![\wÀ-ỹ])' + re.escape(key) + r'(?![\wÀ-ỹ])'
    return bool(re.search(pattern, text_lower))


class BiologyDataSource(IDataSource):
    """
    Data source cho các câu hỏi Sinh học.
    Hỗ trợ: DNA, RNA, tế bào, enzyme, loài.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        # [V5.8-API] NCBI E-utilities API key (taxonomy db)
        self._ncbi_api_key = os.environ.get("NCBI_API_KEY", "").strip() or os.environ.get("PUBMED_API_KEY", "").strip()

        # DNA/RNA info
        self._genetic_code = {
            "TTT": "Phe", "TTC": "Phe", "TTA": "Leu", "TTG": "Leu",
            "CTT": "Leu", "CTC": "Leu", "CTA": "Leu", "CTG": "Leu",
            "ATT": "Ile", "ATC": "Ile", "ATA": "Ile", "ATG": "Met",
            "GTT": "Val", "GTC": "Val", "GTA": "Val", "GTG": "Val",
        }

        # Amino acids
        self._amino_acids = {
            "Ala": "Alanine", "Arg": "Arginine", "Asn": "Asparagine",
            "Asp": "Aspartic acid", "Cys": "Cysteine", "Gln": "Glutamine",
            "Glu": "Glutamic acid", "Gly": "Glycine", "His": "Histidine",
            "Ile": "Isoleucine", "Leu": "Leucine", "Lys": "Lysine",
            "Met": "Methionine", "Phe": "Phenylalanine", "Pro": "Proline",
            "Ser": "Serine", "Thr": "Threonine", "Trp": "Tryptophan",
            "Tyr": "Tyrosine", "Val": "Valine",
        }

        # Cell info
        self._cells = {
            "mitochondria": {"size": "1-10 μm", "function": "ATP production"},
            "ribosome": {"size": "20 nm", "function": "Protein synthesis"},
            "nucleus": {"size": "5-10 μm", "function": "DNA storage"},
            "lysosome": {"size": "0.1-1.2 μm", "function": "Cellular digestion"},
            "chloroplast": {"size": "5-10 μm", "function": "Photosynthesis"},
        }

        # Biological constants
        self._constants = {
            "số base DNA người": 3.2e9,
            "human genome size": 3.2e9,
            "số chromosome người": 46,
            "human chromosomes": 46,
            "kích thước gene trung bình": 2700,  # base pairs
            "average gene size": 2700,
            "tốc độ phiên mã": 30,  # nucleotides/second
            "transcription rate": 30,
            "tốc độ dịch mã": 15,  # amino acids/second
            "translation rate": 15,
        }


    @property
    def name(self) -> str:
        return "BiologyDataSource"

    @property
    def priority(self) -> int:
        return 5

    @property
    def ttl(self) -> int:
        return 86400

    def get_supported_intents(self) -> list[str]:
        return ["lookup", "query", "fact"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        return True

    def fetch(self, intent: str, entity: str, **kwargs):
        result = self.query(entity or intent)
        if result.get("found"):
            return {"value": result.get("answer", ""), "source": "Biology", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[AUDIT-FIX low-4] Fail-closed: ping NCBI E-utilities (einfo — service
        info công khai, không cần key). Trước đây hardcode
        `return True` — fail-open, không có bằng chứng. Bất kỳ HTTP response
        nào chứng minh service sống; exception (egress denied, DNS, timeout)
        → False. Local knowledge base không được OR vào kết quả — degraded
        chỉ báo qua log.

        [V104.32] Kết quả ping đi qua shared negative-result cache
        cross-instance (`shared_health_ping`): trong TTL
        (SCP_HEALTH_NEG_CACHE_TTL, default 60s) các lần gọi sau trả lại quan
        sát gần nhất — kể cả False (đó là reality gần nhất, không fake health)
        — mà KHÔNG re-ping."""
        import time
        healthy = shared_health_ping(type(self).__name__, self._live_ping)
        self._cache['_health_cache'] = healthy
        self._cache['_health_cache_ts'] = time.time()
        return healthy

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật (1 network round-trip) — chỉ gọi qua
        shared_health_ping để được dedupe theo TTL."""
        api_ok = False
        try:
            # [AUDIT-20260909 SSRF-S1] safe_urlopen cho health ping (URL cố định).
            with safe_urlopen("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi", timeout=3):
                api_ok = True
        except Exception as e:
            logger.warning(f"[Biology] health ping failed: {e}", exc_info=True)
        if not api_ok:
            logger.warning(
                "[Biology] health_check: NCBI endpoint unreachable — báo unhealthy "
                "(fail-closed); local knowledge base vẫn trả lời được query (degraded)"
            )
        return api_ok

    def query(self, question: str) -> dict[str, Any]:
        """Query biology data."""
        q = question.lower().strip()

        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        # Check genetic code
        for codon, aa in self._genetic_code.items():
            # [ROOT-FIX 4] Was `codon.lower() in q or aa.lower() in q` — substring
            # match → 'ATA' matched 'data', 'Ala' matched 'balance', 'Pro' matched
            # 'process', 'Met' matched 'method', etc. Now uses word-boundary match.
            if _wb_match(codon.lower(), q) or _wb_match(aa.lower(), q):
                result = {
                    "found": True,
                    "answer": f"Codon {codon} → {aa}",
                    "confidence": 1.0,
                    "source": "Standard Genetic Code"
                }
                break

        # Check amino acids
        for code, name in self._amino_acids.items():
            # [ROOT-FIX 4] Same substring → word-boundary fix.
            if _wb_match(code.lower(), q) or _wb_match(name.lower(), q):
                result = {
                    "found": True,
                    "answer": f"{code} = {name}",
                    "confidence": 1.0,
                    "source": "Amino Acid Database"
                }
                break

        # Check constants
        for name, value in self._constants.items():
            # [ROOT-FIX 4] Same substring → word-boundary fix.
            if _wb_match(name.lower(), q):
                result = {
                    "found": True,
                    "answer": f"{name} = {value}",
                    "confidence": 1.0,
                    "source": "Biological Database"
                }
                break

        # [V5.8-API] Local DB miss → try NCBI taxonomy API for species/genus queries.
        # Skip very short queries (likely codons/amino acids — not species names).
        if not result.get("found") and len(q) >= 4:
            api_result = self._fetch_from_ncbi_taxonomy(question)
            if api_result:
                result = api_result

        self._cache[q] = result
        return result

    # [V5.8-API] NCBI Taxonomy integration
    def _fetch_from_ncbi_taxonomy(self, question: str) -> dict[str, Any] | None:
        """
        [V5.8-API] Fetch taxonomic data from NCBI E-utilities (taxonomy db).
        Step 1: esearch.fcgi (JSON) → taxid list
        Step 2: efetch.fcgi (XML) → parsed TaxName / Rank / Lineage
        Returns dict or None.
        """
        if not question or not question.strip():
            return None
        # Extract a clean search term from the question (strip common stopwords)
        text = question.strip()
        cleaned = re.sub(
            r'\b(what|is|the|a|an|of|for|on|about|species|genus|taxon|taxonomy|là|gì|của|về|tìm|loài|giống)\b',
            ' ', text, flags=re.IGNORECASE,
        ).strip()
        term = re.sub(r'\s+', ' ', cleaned).strip()
        if len(term) < 4:
            return None

        api_key_param = f"&api_key={self._ncbi_api_key}" if self._ncbi_api_key else ""
        esearch_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=taxonomy&term={urllib.parse.quote(term, safe='')}"
            f"&retmode=json&retmax=3{api_key_param}"
        )
        try:
            esearch_data = fetch_with_retry(esearch_url, headers={"User-Agent": "SCP/1.0"}, timeout=5)
            if not esearch_data:
                return None
            id_list = esearch_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return None
        except Exception as e:
            logger.warning(f"[V5.8-API] NCBI taxonomy esearch failed for '{term}': {e}", exc_info=True)
            return None

        # efetch XML parse — use safe_urlopen (fetch_with_retry expects JSON)
        taxid = id_list[0]
        # [AUDIT-20260909 SSRF-S1] taxid (external data) được validate bằng
        # regex trong builder; input xấu → ValueError TRƯỚC KHI fetch.
        efetch_url = build_ncbi_efetch_taxonomy_url(taxid) + api_key_param
        try:
            req = urllib.request.Request(
                efetch_url, headers={"User-Agent": "SCP/1.0"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=8) as resp:
                if getattr(resp, "status", 200) != 200:
                    return None
                body = resp.read().decode("utf-8", errors="replace")
            if not body:
                return None
            root = ET.fromstring(body)
            taxon = root.find('.//Taxon')
            if taxon is None:
                return None
            tax_name = (taxon.findtext('ScientificName') or '').strip()
            rank = (taxon.findtext('Rank') or '').strip()
            lineage = (taxon.findtext('Lineage') or '').strip()
            if not tax_name:
                return None
            answer_parts = [f"Species: {tax_name}"]
            if rank and rank != 'no rank':
                answer_parts.append(f"Rank: {rank}")
            if lineage:
                # Truncate lineage if very long
                lin_str = lineage if len(lineage) <= 400 else lineage[:400] + "..."
                answer_parts.append(f"Lineage: {lin_str}")
            return {
                "found": True,
                "answer": " | ".join(answer_parts),
                "confidence": 0.85,
                "source": "NCBI Taxonomy API",
                "taxid": taxid,
                "scientific_name": tax_name,
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] NCBI taxonomy efetch failed for taxid {taxid}: {e}", exc_info=True)
            return None
