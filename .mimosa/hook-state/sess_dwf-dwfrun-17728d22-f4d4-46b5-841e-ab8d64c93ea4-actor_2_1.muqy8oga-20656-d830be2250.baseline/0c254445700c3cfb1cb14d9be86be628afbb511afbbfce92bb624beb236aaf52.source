


def _tokenize(text):
    return text.lower().split()

def compute_tf_idf(query, documents):
    # Lightweight TF-IDF for Loop 2 (Vector Search fallback)
    q_tokens = _tokenize(query)
    scores = []
    for doc in documents:
        d_tokens = _tokenize(doc.get('content', ''))
        common = set(q_tokens) & set(d_tokens)
        score = len(common) # simplified jaccard/TF for zero-dependency
        scores.append((score, doc))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scores if s[0] > 0]
