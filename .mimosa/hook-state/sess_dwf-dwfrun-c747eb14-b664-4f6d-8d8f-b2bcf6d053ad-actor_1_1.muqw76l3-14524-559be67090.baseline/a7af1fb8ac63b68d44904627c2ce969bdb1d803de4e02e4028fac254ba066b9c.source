"""
SCP V104 — Cross-Language Pattern Transfer
============================================
Dịch pattern tiếng Việt → tiếng Anh/Trung/Nhật/Hàn → auto-generate detector patterns.

Ví dụ:
  VI: "bỏ qua hướng dẫn"  →  EN: "ignore instructions"
                           →  ZH: "忽略指令"
                           →  JA: "指示を無視"
                           →  KO: "지시를 무시"

Cách dùng:
    from scp.security.cross_language_learner import CrossLanguageLearner
    learner = CrossLanguageLearner()
    patterns = learner.transfer_all("bo qua huong dan", "injection", "critical")
    # → {"en": "ignore.*instructions", "zh": "忽略.*指令", "ja": "指示.*無視", ...}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("scp.security.cross_language_learner")

# Pre-computed translations (offline, no API needed)
PATTERN_TRANSLATIONS = {
    # Vietnamese → target languages
    "bo qua": {
        "en": "ignore",
        "zh": "忽略",
        "ja": "無視",
        "ko": "무시",
        "fr": "ignorer",
        "de": "ignoriere",
        "es": "ignora",
        "ar": "تجاهل",
    },
    "huong dan": {
        "en": "instructions",
        "zh": "指令",
        "ja": "指示",
        "ko": "지시",
        "fr": "instructions",
        "de": "Anweisungen",
        "es": "instrucciones",
        "ar": "التعليمات",
    },
    "quen di": {
        "en": "forget",
        "zh": "忘记",
        "ja": "忘れて",
        "ko": "잊어버려",
        "fr": "oublie",
        "de": "vergiss",
        "es": "olvida",
        "ar": "انسى",
    },
    "dong vai": {
        "en": "act as|pretend.*are|roleplay",
        "zh": "扮演|假装",
        "ja": "演じて|偽って",
        "ko": "연기해|가장",
        "fr": "agis.*comme|prétend",
        "de": "verhalte.*als|tu.*so",
        "es": "actúa.*como|finge",
        "ar": "تصرف.*كما|تظاهر",
    },
    "khong gioi han": {
        "en": "no.*restrictions?|unrestricted",
        "zh": "无限制|不受限",
        "ja": "制限なし|無制限",
        "ko": "제한.*없|무제한",
        "fr": "sans.*restrict|sans.*limite",
        "de": "ohne.*Einschränk|unbeschränkt",
        "es": "sin.*restric|sin.*límite",
        "ar": "بدون.*قيود|غير.*مقيد",
    },
    "tiet lo": {
        "en": "reveal|show|expose",
        "zh": "揭示|显示|暴露",
        "ja": "明か|示|暴",
        "ko": "공개|보여|노출",
        "fr": "révèle|montre|expose",
        "de": "offenbare|zeige|enthülle",
        "es": "revela|muestra|expone",
        "ar": "كشف|أظهر|اعرض",
    },
    "system prompt": {
        "en": "system.?prompt|initial.?instructions",
        "zh": "系统提示|初始指令",
        "ja": "システムプロンプト|初期指示",
        "ko": "시스템.*프롬프트|초기.*지시",
        "fr": "prompt.*système|instructions.*initiales",
        "de": "System.*Prompt|anfängliche.*Anweisungen",
        "es": "prompt.*sistema|instrucciones.*iniciales",
        "ar": "موجه.*النظام|التعليمات.*الأولية",
    },
    "dan": {
        "en": "dan|do.anything.now",
        "zh": "dan|什么都能做",
        "ja": "dan|何でもできる",
        "ko": "dan|무엇이든.*해",
        "fr": "dan|fais.*tout",
        "de": "dan|tu.*alles",
        "es": "dan|haz.*todo",
        "ar": "dan|افعل.*أي.*شيء",
    },
    "khong can tuan": {
        "en": "no.*need.*follow|don't.*follow",
        "zh": "无需遵守|不必遵守",
        "ja": "従う.*必要.*なし|従わ",
        "ko": "따를.*필요.*없|따르지",
        "fr": "pas.*besoin.*suivre|ne.*suis.*pas",
        "de": "nicht.*folgen|muss.*nicht.*befolgen",
        "es": "no.*necesitas.*seguir|no.*siga",
        "ar": "لا.*تحتاج.*اتباع|لا.*اتبع",
    },
}

SUPPORTED_LANGUAGES = ["en", "zh", "ja", "ko", "fr", "de", "es", "ar"]


@dataclass
class TransferredPattern:
    """1 pattern transfer sang ngôn ngữ khác."""
    source_language: str  # "vi"
    target_language: str  # "en", "zh", ...
    original_pattern: str  # "bỏ qua hướng dẫn"
    transferred_regex: str  # "ignore.*instructions"
    category: str  # "injection", "jailbreak", ...
    severity: str  # "critical", "high", ...


class CrossLanguageLearner:
    """
    Transfer Vietnamese/English patterns → 8 ngôn ngữ khác.
    """

    def __init__(self):
        self._stats = {
            "patterns_transferred": 0,
            "languages": SUPPORTED_LANGUAGES,
            "by_language": {},
        }

    def transfer_pattern(
        self,
        vi_keywords: list[str],
        category: str,
        severity: str,
        target_lang: str = "en",
    ) -> TransferredPattern | None:
        """Transfer 1 Vietnamese pattern sang target language."""
        translated_parts = []
        for kw in vi_keywords:
            kw_norm = kw.lower().strip()
            if kw_norm in PATTERN_TRANSLATIONS:
                translations = PATTERN_TRANSLATIONS[kw_norm]
                if target_lang in translations:
                    translated_parts.append(translations[target_lang])

        if not translated_parts:
            return None

        # Build regex: join with .* for flexibility
        regex = ".*".join(translated_parts)

        self._stats["patterns_transferred"] += 1
        self._stats["by_language"][target_lang] = (
            self._stats["by_language"].get(target_lang, 0) + 1
        )

        return TransferredPattern(
            source_language="vi",
            target_language=target_lang,
            original_pattern=" ".join(vi_keywords),
            transferred_regex=regex,
            category=category,
            severity=severity,
        )

    def transfer_all(
        self,
        vi_keywords: list[str],
        category: str,
        severity: str,
    ) -> dict[str, str]:
        """Transfer 1 pattern sang TẤT CẢ ngôn ngữ → dict {lang: regex}."""
        results = {}
        for lang in SUPPORTED_LANGUAGES:
            transferred = self.transfer_pattern(vi_keywords, category, severity, lang)
            if transferred:
                results[lang] = transferred.transferred_regex
        return results

    def transfer_existing_vietnamese_patterns(self) -> list[dict]:
        """Transfer tất cả Vietnamese patterns hiện có sang 8 ngôn ngữ."""
        # Vietnamese patterns to transfer
        vi_patterns = [
            (["bo qua", "huong dan"], "injection", "critical"),
            (["quen di", "huong dan"], "injection", "critical"),
            (["dong vai", "khong gioi han"], "jailbreak", "critical"),
            (["tiet lo", "system prompt"], "exfiltration", "high"),
            (["khong can tuan"], "injection", "high"),
            (["dan"], "jailbreak", "high"),
        ]

        all_patterns = []
        for keywords, category, severity in vi_patterns:
            for lang in SUPPORTED_LANGUAGES:
                transferred = self.transfer_pattern(keywords, category, severity, lang)
                if transferred:
                    all_patterns.append({
                        "target_lang": transferred.target_language,
                        "regex": transferred.transferred_regex,
                        "category": transferred.category,
                        "severity": transferred.severity,
                        "original": transferred.original_pattern,
                    })

        logger.info(f"CrossLanguage: transferred {len(all_patterns)} patterns to {len(SUPPORTED_LANGUAGES)} languages")
        return all_patterns

    def stats(self) -> dict:
        return self._stats.copy()


if __name__ == "__main__":
    print("=== Cross-Language Learner — Test ===\n")
    learner = CrossLanguageLearner()

    # Test 1: Transfer 1 pattern to all languages
    print("Test 1: Transfer 'bỏ qua hướng dẫn' → all languages")
    results = learner.transfer_all(["bo qua", "huong dan"], "injection", "critical")
    for lang, regex in results.items():
        print(f"  {lang}: {regex}")

    # Test 2: Transfer all existing patterns
    print("\nTest 2: Transfer all existing Vietnamese patterns")
    all_patterns = learner.transfer_existing_vietnamese_patterns()
    print(f"  Total patterns: {len(all_patterns)}")
    for p in all_patterns[:10]:
        print(f"  [{p['target_lang']}] {p['regex'][:50]} ({p['category']}, {p['severity']})")

    print(f"\nStats: {learner.stats()}")
    print("\n✓ Test complete.")
