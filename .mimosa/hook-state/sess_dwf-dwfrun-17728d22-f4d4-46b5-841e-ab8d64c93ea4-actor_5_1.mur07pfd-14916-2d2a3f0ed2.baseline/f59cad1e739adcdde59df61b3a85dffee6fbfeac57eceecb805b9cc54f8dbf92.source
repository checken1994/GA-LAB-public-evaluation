"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
 DomainClassifier — phân loại câu hỏi vào 1 trong 45+ domains.

Sử dụng keyword matching + scoring để chọn domain phù hợp nhất.
Fallback: nếu không match → 'general' (LiveKnowledgeFetcher xử lý).
"""
import logging
import re

from scp.data_sources.domain_registry import search_domains_by_keyword

logger = logging.getLogger("scp.domain_classifier")


# Manual routing rules for common patterns (priority over keyword search)
ROUTING_RULES = [
    # [V88 FIX] Stack Overflow → technology (MUST be first, before conversion "to" match)
    (r'stack\s+overflow', 'technology'),
    # Math patterns
    (r'^\s*Tính\s+\d', 'math'),
    (r'^\s*Calculate\s+\d', 'math'),
    (r'^\s*\d+\s*[+\-*/]\s*\d+', 'math'),
    (r'^\s*sqrt\s*\(', 'math'),
    (r'^\s*gcd\s*\(', 'math'),
    (r'^\s*\d+\s*!', 'math'),
    (r'^\s*\d+\s*[<>=!]+\s*\d+', 'logic'),
    # Conversion patterns
    (r'chuyển\s+đổi\s+\d', 'conversion'),
    (r'convert\s+\d', 'conversion'),
    (r'\d+\s*(?:km|m|cm|mm|kg|g|lb|hour|minute)\s*(?:sang|to|=)', 'conversion'),
    # Capital patterns
    (r'thủ\s+đô\s+của', 'geography'),
    (r'capital\s+of', 'geography'),
    # Weather patterns
    (r'nhiệt\s+độ\s+(?:hiện\s+tại\s+)?(?:tại|ở|của)', 'weather'),
    (r'temperature\s+(?:at|in)', 'weather'),
    # History patterns
    (r'năm\s+\d{3,4}\s+(?:xảy\s+ra|có|diễn\s+ra)', 'history'),
    (r'sự\s+kiện\s+năm\s+\d{3,4}', 'history'),
    # Chemistry patterns
    (r'khối\s+lượng\s+phân\s+tử', 'chemistry'),
    (r'molar\s+mass\s+of', 'chemistry'),
    (r'molecular\s+weight\s+of', 'chemistry'),
    # Crypto patterns
    (r'giá\s+\w+\s+hiện\s+tại', 'finance'),
    (r'price\s+of\s+\w+', 'finance'),
    (r'chuyển\s+đổi\s+\d+\s+\w{3}\s+sang', 'conversion'),
    # Physics constants
    (r'hằng\s+số\s+\w', 'physics'),
    (r'gia\s+tốc\s+trọng\s+trường', 'physics'),
    (r'tốc\s+độ\s+ánh\s+sáng', 'physics'),
    # Astronomy patterns
    (r'khối\s+lượng\s+của\s+\w+\s*(?:sao|hành\s+tinh|planet)', 'astronomy'),
    (r'\w+\s+(?:có\s+)?bao\s+nhieu\s+vệ\s+tinh', 'astronomy'),
    # Medical patterns
    (r'(?:bệnh|thuốc|triệu\s+chứng|điều\s+trị|vaccine)', 'medical'),
    (r'(?:disease|medicine|symptom|treatment|vaccine)', 'medical'),
    # Sports patterns
    (r'(?:olympic|world\s+cup|fifa|bóng\s+đá|bóng\s+rổ|tennis)', 'sports'),
    # Legal patterns
    (r'(?:luật|hiến\s+pháp|pháp\s+luật|hợp\s+đồng|quyền)', 'legal'),
    (r'(?:law|constitution|contract|rights|legal)', 'legal'),
    # Tech patterns
    (r'(?:python|javascript|java|c\+\+|rust|go\s+language|AI|machine\s+learning|deep\s+learning|neural\s+network|LLM|GPT|BERT)', 'technology'),
    (r'(?:programming|software|hardware|CPU|GPU|RAM|HTTP|TCP|UDP)', 'technology'),
    # Arts patterns
    (r'(?:họa\s+sĩ|bức\s+tranh|phim|điện\s+ảnh|nhạc\s+sĩ|UX|UI)', 'arts'),
    (r'(?:painter|painting|film|cinema|composer)', 'arts'),
    # [V88 FIX] Entertainment patterns — books, TV shows, movies, Star Wars, etc.
    (r'tell\s+me\s+about\s+the\s+book', 'arts'),
    (r'tell\s+me\s+about\s+the\s+tv\s+show', 'entertainment'),
    (r'tell\s+me\s+about\s+the\s+movie', 'entertainment'),
    (r'tell\s+me\s+about\s+the\s+star\s+wars', 'entertainment'),
    (r'star\s+wars\s+(?:planet|specie|people|character|ship|vehicle|film|movie)', 'entertainment'),
    (r'tell\s+me\s+about\s+the\s+film', 'entertainment'),
    (r'tell\s+me\s+about\s+the\s+anime', 'entertainment'),
    (r'tell\s+me\s+about\s+the\s+manga', 'entertainment'),
    (r'tell\s+me\s+about\s+the\s+video\s+game', 'entertainment'),
    (r'tell\s+me\s+about\s+the\s+pokemon', 'entertainment'),
    (r'tell\s+me\s+about\s+the\s+tv\s+show', 'entertainment'),
    # [V88 FIX] Food patterns — cocktails, recipes, nutrition
    (r'how\s+do\s+you\s+make\s+the\s+cocktail', 'food'),
    (r'how\s+do\s+you\s+make\s+the\s+(?:dish|recipe|food|drink|salad|soup|stew|curry|cake|dessert)', 'food'),
    (r'what\s+is\s+the\s+nutritional\s+value', 'food'),
    (r'what\s+is\s+a\s+public\s+holiday', 'holiday'),
    # [V88 FIX] Vietnamese "là loại gì" pattern → general (but don't route to wrong domain)
    (r'là\s+loại\s+gì', 'general'),
    (r'là\s+ai', 'general'),
    (r'là\s+đâu', 'geography'),
    # [V88 FIX] Bible patterns
    (r'what\s+does\s+the\s+bible\s+say', 'religion'),
    (r'who\s+is\s+the\s+author\s+of', 'arts'),
    # [V88 FIX] Gender name → general
    (r'what\s+is\s+the\s+likely\s+gender\s+of\s+the\s+name', 'general'),
    # [V88 FIX] Short description → general
    (r'what\s+is\s+a\s+short\s+description\s+of', 'universal'),
    # [V90 EN] Wikipedia entity patterns → universal (not sports/arts/etc)
    (r'what\s+type\s+of\s+thing\s+is', 'universal'),
    (r'what\s+is\s+a\s+short\s+description', 'universal'),
    (r'tell\s+me\s+about\s+the\s+star\s+wars', 'entertainment'),
    # [V93.8 FIX] "what studio animated X" was false-matching "studio" keyword
    # in the audiovideo (audio engineering) domain instead of entertainment/anime.
    (r'what\s+studio\s+animated', 'entertainment'),
    (r'(?:anime|manga)', 'entertainment'),
    (r'which\s+bond\s+film', 'entertainment'),
    (r'which\s+quote.*(?:film|movie)', 'entertainment'),
]


def classify_question(question: str, top_k: int = 3) -> list[tuple[str, float]]:
    """
    Classify câu hỏi vào domains.

    Args:
        question: Câu hỏi
        top_k: Trả về top K domains với score

    Returns:
        List of (domain_id, score) tuples, sorted by score descending
    """
    if not question or not question.strip():
        return [("general", 1.0)]

    q_lower = question.lower().strip()
    scores: dict[str, float] = {}

    # 1. Apply routing rules (high confidence)
    # [V58-V59 FIX] Use word-boundary matching for ALL routing rules
    # to prevent "AI" matching "r**AI**ndom", "UX" matching "bu**UX**", etc.
    for pattern, domain in ROUTING_RULES:
        #  Always wrap with word boundaries — extract alternatives from (?:...) patterns
        if pattern.startswith('(?:') or pattern.startswith('('):
            # Complex pattern — extract alternatives and wrap each with \b
            # VD: "(?:python|javascript|AI|GPT)" → r"\b(?:python|javascript|AI|GPT)\b"
            wrapped = r'\b' + pattern + r'\b'
        elif '\\b' in pattern:
            wrapped = pattern  # Already has word boundaries
        elif '|' in pattern:
            alts = pattern.split('|')
            wrapped = '|'.join(r'\b' + a + r'\b' if not a.startswith('\\') and not a.startswith('(') else a for a in alts)
        else:
            wrapped = r'\b' + pattern + r'\b'

        try:
            if re.search(wrapped, q_lower, re.IGNORECASE):
                scores[domain] = scores.get(domain, 0) + 10.0
        except re.error:
            # If wrapped pattern fails, fall back to original
            logger.debug('classify_question: re.error ignored', exc_info=True)
            if re.search(pattern, q_lower, re.IGNORECASE):
                scores[domain] = scores.get(domain, 0) + 10.0

    # 2. Keyword matching
    matched_domains = search_domains_by_keyword(question)
    for i, domain_id in enumerate(matched_domains):
        # Earlier match = higher score
        score = 5.0 - (i * 0.5)
        scores[domain_id] = scores.get(domain_id, 0) + max(score, 1.0)

    # 3. Specific keyword boosts
    boost_keywords = {
        'medical': ['bệnh', 'disease', 'thuốc', 'medicine', 'y tế', 'sức khỏe', 'health',
                    'triệu chứng', 'symptom', 'vaccine', 'paracetamol', 'insulin'],
        'technology': ['AI', 'GPT', 'machine learning', 'python', 'javascript', 'programming',
                       'phần mềm', 'software', 'CPU', 'GPU', 'HTTP'],
        'sports': ['olympic', 'fifa', 'world cup', 'messi', 'ronaldo', 'bóng đá', 'football',
                   'bóng rổ', 'basketball', 'tennis'],
        'legal': ['luật', 'law', 'hiến pháp', 'constitution', 'hợp đồng', 'contract',
                  'quyền', 'rights', 'pháp luật'],
        'arts': ['họa sĩ', 'painter', 'tranh', 'painting', 'phim', 'film', 'nhạc sĩ',
                 'composer', 'UX', 'UI', 'thiết kế', 'design'],
        'finance': ['giá', 'price', 'cổ phiếu', 'stock', 'tỷ giá', 'exchange rate',
                    'cryptocurrency', 'bitcoin', 'ethereum'],
        'environment': ['môi trường', 'environment', 'biến đổi khí hậu', 'climate change',
                        'carbon', 'phát thải'],
        'agriculture': ['nông nghiệp', 'agriculture', 'trồng trọt', 'chăn nuôi',
                        'lâm nghiệp', 'thủy sản'],
        'tourism': ['du lịch', 'tourism', 'khách sạn', 'hotel', 'nhà hàng', 'restaurant'],
        'education': ['giáo dục', 'education', 'trường', 'school', 'đại học', 'university',
                      'học sinh', 'giáo viên'],
        'psychology': ['tâm lý', 'psychology', 'cognitive', 'nhận thức', 'hành vi'],
        'religion': ['tôn giáo', 'religion', 'Phật', 'Buddha', 'Thiên Chúa', 'God', 'đạo'],
        'military': ['quân đội', 'military', 'quốc phòng', 'an ninh', 'vũ khí', 'weapon'],
        'cybersecurity': ['an ninh mạng', 'cybersecurity', 'mật mã', 'cryptography',
                          'malware', 'hacker'],
        'blockchain': ['blockchain', 'NFT', 'web3', 'DeFi', 'smart contract'],
        'genai': ['genAI', 'ChatGPT', 'GPT', 'LLM', 'transformer', 'DALL-E', 'Midjourney'],
        'aerospace': ['hàng không', 'aerospace', 'tên lửa', 'rocket', 'NASA', 'SpaceX',
                      'phi hành gia', 'astronaut'],
        'energy': ['năng lượng', 'energy', 'dầu khí', 'petroleum', 'mỏ', 'mining',
                   'than', 'coal', 'mặt trời', 'solar'],
        'transport': ['vận tải', 'transport', 'logistics', 'chuỗi cung ứng', 'supply chain'],
        'foodtech': ['thực phẩm', 'food', 'chế biến', 'processing', 'bảo quản'],
        'heritage': ['di sản', 'heritage', 'bảo tàng', 'museum', 'cổ vật', 'UNESCO'],
        'oceanography': ['hải dương', 'oceanography', 'biển', 'đại dương', 'marine'],
        'geology': ['địa chất', 'geology', 'khoáng sản', 'mineral', 'động đất', 'earthquake'],
    }
    vn_ai_patterns = [r'\bbạn là ai\b', r'\bai là\b', r'\bai đó\b', r'\bvới ai\b', r'\bcho ai\b', r'\blà ai\b']
    for domain, keywords in boost_keywords.items():
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower == 'ai' and any(re.search(p, q_lower) for p in vn_ai_patterns):
                continue
            # [V54 FIX] Use word-boundary matching for short keywords (<=4 chars)
            # Trước V54: "AI" matched "r**AI**ndom" → false positive
            if len(kw_lower) <= 4:
                pattern = r'\b' + re.escape(kw_lower) + r'\b'
                if re.search(pattern, q_lower):
                    scores[domain] = scores.get(domain, 0) + 3.0
            else:
                if kw_lower in q_lower:
                    scores[domain] = scores.get(domain, 0) + 3.0

    # [V88 FIX] Override: "Star Wars" → entertainment, NOT astronomy
    # "star" and "planet" in astronomy keywords falsely match Star Wars questions
    if 'star wars' in q_lower:
        scores.pop('astronomy', None)
        scores['entertainment'] = scores.get('entertainment', 0) + 10.0

    # [V88 FIX] Override: "cocktail" → food, NOT general
    if 'cocktail' in q_lower:
        scores['food'] = scores.get('food', 0) + 10.0

    if not scores:
        return [("general", 1.0)]

    #  Require minimum absolute score to avoid false routing
    # Trước V53: "random question with no clear domain" → "domain" matches technology keyword
    #           → routed to technology → wrong SLM answer
    # V53: require score >= 3.0 (at least 1 keyword match with boost) to route to specific domain
    min_routing_score = 3.0
    filtered = [(d, s) for d, s in scores.items() if s >= min_routing_score]
    if not filtered:
        return [("general", 1.0)]

    # Sort by score, normalize
    sorted_scores = sorted(filtered, key=lambda x: -x[1])
    max_score = sorted_scores[0][1]
    normalized = [(d, s / max_score) for d, s in sorted_scores[:top_k]]

    return normalized


def classify_top1(question: str) -> str:
    """Return top 1 domain id."""
    results = classify_question(question, top_k=1)
    return results[0][0] if results else "general"


def main():
    """Test the classifier."""
    test_questions = [
        "Tính 2 + 3",
        "Thủ đô của Pháp là gì?",
        "Khối lượng phân tử nước bằng bao nhiêu?",
        "Nhiệt độ tại Hà Nội",
        "Giá bitcoin hiện tại",
        "Bệnh cảm lạnh triệu chứng gì?",
        "Olympic 2024 ở đâu?",
        "Luật đất đai 2024 có bao nhiêu điều?",
        "Python là ngôn ngữ gì?",
        "Ai là Leonardo da Vinci?",
        "Biến đổi khí hậu ảnh hưởng gì?",
        "Phân biệt blockchain và bitcoin",
        "SpaceX phóng tên lửa gì?",
        "Khối lượng của Sao Mộc",
        "Hằng số pi bằng bao nhiêu?",
        "chuyển đổi 1 USD sang VND",
        "Ai là Beethoven?",
        "Vaccine COVID-19 hiệu quả bao nhiêu?",
    ]
    print("\n=== Domain Classifier Test ===")
    for q in test_questions:
        results = classify_question(q, top_k=3)
        top = results[0]
        print(f"  Q: {q[:55]:55s} → {top[0]:15s} (score={top[1]:.2f})")


if __name__ == "__main__":
    main()
