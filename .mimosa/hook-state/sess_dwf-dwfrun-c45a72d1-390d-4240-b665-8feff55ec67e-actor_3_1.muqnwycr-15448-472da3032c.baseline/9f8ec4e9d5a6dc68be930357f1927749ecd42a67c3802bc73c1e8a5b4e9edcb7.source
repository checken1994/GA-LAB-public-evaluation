import json
import requests
from bs4 import BeautifulSoup

query = "Cách phân biệt Deepfake và video thật mới nhất năm nay"
response = requests.get("https://html.duckduckgo.com/html/", params={"q": query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
soup = BeautifulSoup(response.text, "html.parser")
print(json.dumps({
    "status": response.status_code,
    "bytes": len(response.content),
    "title": soup.title.get_text(" ", strip=True) if soup.title else None,
    "result_count": len(soup.select(".result")),
    "result_a_count": len(soup.select(".result a.result__a")),
    "classes": sorted({c for tag in soup.find_all(True) for c in (tag.get("class") or [])})[:80],
    "body": soup.get_text(" ", strip=True)[:800],
}, ensure_ascii=False))
