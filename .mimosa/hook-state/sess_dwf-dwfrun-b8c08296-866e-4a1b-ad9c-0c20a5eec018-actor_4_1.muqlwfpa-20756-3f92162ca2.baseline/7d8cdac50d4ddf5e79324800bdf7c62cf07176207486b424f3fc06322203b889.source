import datetime
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "benchmark_batches" / "cc047e32d62448678a773738abe08833" / "questions.jsonl"
OUT = ROOT / "data" / "rag_corpus" / "canonical-v4-ddg-20260817" / "corpus_ddg_search.jsonl"
LOG = ROOT / "reports" / "CANONICAL_V4_DDG_SEARCH_STDOUT_2026-08-17.txt"
MAX_RESULTS = 6
REQUEST_TIMEOUT = 25
SLEEP_SECONDS = 0.15
STOPWORDS = {
    "cách", "những", "thông", "tin", "hướng", "dẫn", "liên", "quan", "đến", "mới",
    "nhất", "năm", "nay", "hiện", "quy", "định", "về", "của", "cho", "trong", "theo",
    "điều", "nào", "là", "được", "và", "các", "một", "với", "mã", "hỏi", "tìm", "hiểu",
}
DENY_HOSTS = {"duckduckgo.com", "www.duckduckgo.com", "bing.com", "www.bing.com", "google.com", "www.google.com"}


def load_questions():
    result = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if line.strip():
            result.append(json.loads(line))
    return result


def tokens(text):
    values = re.findall(r"[\wÀ-ỹ]{3,}", str(text).lower())
    return {x for x in values if x not in STOPWORDS and not x.startswith("ch-")}


def normalize_query(question):
    text = re.sub(r"\(Mã\s+CH-\d+\)", "", str(question), flags=re.I)
    text = re.sub(r"\bCH-\d+\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" ?")
    boilerplate = [
        "Hướng dẫn và quy định liên quan đến ",
        "Thông tin và quy định liên quan đến ",
        "Thông tin liên quan đến ",
        "Hướng dẫn về ",
    ]
    for prefix in boilerplate:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):]
            break
    return text.strip()


def unwrap_url(value):
    if not value:
        return None
    if value.startswith("//"):
        value = "https:" + value
    parsed = urlparse(value)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        return unquote(target) if target else None
    return value


def host_ok(value):
    try:
        host = (urlparse(value).hostname or "").lower()
        return bool(host) and not any(host == x or host.endswith("." + x) for x in DENY_HOSTS)
    except Exception:
        return False


def search(session, query):
    response = session.get("https://html.duckduckgo.com/html/", params={"q": query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=REQUEST_TIMEOUT)
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for item in soup.select(".result")[:MAX_RESULTS]:
        anchor = item.select_one(".result__a")
        if not anchor:
            continue
        url = unwrap_url(anchor.get("href"))
        if not host_ok(url):
            continue
        snippet_node = item.select_one(".result__snippet")
        title = anchor.get_text(" ", strip=True)
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        results.append({"title": title, "url": url, "snippet": snippet})
    return results


def score(question, candidate):
    qt = tokens(question)
    ct = tokens(candidate.get("title", "") + " " + candidate.get("snippet", "") + " " + candidate.get("url", ""))
    overlap = len(qt & ct)
    return overlap / max(1, len(qt)), overlap


def canonical_url(soup, fallback):
    link = soup.select_one('link[rel="canonical"]')
    value = link.get("href") if link else None
    if not value:
        return fallback
    if value.startswith("/"):
        parsed = urlparse(fallback)
        return f"{parsed.scheme}://{parsed.netloc}{value}"
    return value


def make_chunks(doc_id, text, size=1800, overlap=250):
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    chunks = []
    start = 0
    index = 0
    while start < len(clean):
        part = clean[start:start + size].strip()
        if len(part) >= 80:
            chunks.append({
                "chunk_id": f"{doc_id}-c{index:04d}",
                "document_id": doc_id,
                "chunk_index": index,
                "text": part,
            })
            index += 1
        if start + size >= len(clean):
            break
        start += size - overlap
    return chunks


def fetch_document(session, candidate):
    response = session.get(candidate["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP_{response.status_code}")
    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else candidate.get("title", "")
    text = soup.get_text(" ", strip=True)
    final_url = canonical_url(soup, response.url)
    return final_url, title, text, response.status_code


def build_one(session, question):
    qid = question.get("id") or question.get("question_id")
    raw_question = question.get("question", "")
    query = normalize_query(raw_question)
    record = {
        "question_id": qid,
        "question": raw_question,
        "search_query": query,
        "source_url": None,
        "source_title": None,
        "fetch_status": "NO_MATCH",
        "final_url": None,
        "document_id": None,
        "chunks": [],
        "search_candidates": [],
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    try:
        candidates = search(session, query)
        ranked = []
        for candidate in candidates:
            ratio, overlap = score(query, candidate)
            candidate = dict(candidate)
            candidate["term_overlap"] = overlap
            candidate["term_overlap_ratio"] = ratio
            ranked.append(candidate)
        ranked.sort(key=lambda x: (x["term_overlap_ratio"], x["term_overlap"]), reverse=True)
        record["search_candidates"] = ranked[:MAX_RESULTS]
        if not ranked or ranked[0]["term_overlap"] < 1:
            return record
        top = ranked[0]
        final_url, title, text, status = fetch_document(session, top)
        doc_id = "doc-" + hashlib.sha256(final_url.encode("utf-8")).hexdigest()[:24]
        chunks = make_chunks(doc_id, text)
        if not chunks:
            record["fetch_status"] = "EMPTY_TEXT"
            return record
        record.update({
            "source_url": final_url,
            "source_title": title,
            "fetch_status": "FETCHED",
            "final_url": final_url,
            "document_id": doc_id,
            "chunks": chunks,
            "source_term_overlap": top["term_overlap"],
            "source_term_overlap_ratio": top["term_overlap_ratio"],
            "http_status": status,
        })
        return record
    except Exception as exc:
        record["fetch_status"] = "FETCH_ERROR"
        record["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
        return record


def main():
    questions = load_questions()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    start = time.time()
    with OUT.open("w", encoding="utf-8") as output, LOG.open("w", encoding="utf-8") as log:
        for index, question in enumerate(questions, 1):
            record = build_one(session, question)
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
            if index % 25 == 0 or index == len(questions):
                fetched = 0
                try:
                    fetched = sum(1 for line in OUT.read_text(encoding="utf-8").splitlines() if '"fetch_status": "FETCHED"' in line)
                except Exception:
                    pass
                msg = {"processed": index, "fetched": fetched, "elapsed_s": round(time.time() - start, 1)}
                print(json.dumps(msg, ensure_ascii=False), flush=True)
                log.write(json.dumps(msg, ensure_ascii=False) + "\n")
                log.flush()
            time.sleep(SLEEP_SECONDS)
    print(json.dumps({"total": len(questions), "output": str(OUT)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
