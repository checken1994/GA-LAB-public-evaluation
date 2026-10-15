"""[AUDIT-R2 F-01] Token host-binding sentinel cho AttackCrawler.

Regression (commit d80c2464, 2026-08-13): ``AttackCrawler._crawl_github`` đọc
``GITHUB_TOKEN`` với fallback ``HF_TOKEN`` — khi chỉ có HF_TOKEN trong env,
HuggingFace token bị gửi sang ``api.github.com`` qua header ``Authorization``.
Probe audit đã bắt được header đó. Quy tắc: mỗi token chỉ đi với host của
provider nó thuộc về; HF credentials chỉ được dùng trong ``_crawl_huggingface``
qua thư viện ``datasets``, không bao giờ qua HTTP header của host GitHub.

Sentinel fail-closed, không network: ``safe_urlopen`` được thay bằng recorder
ghi lại ``urllib.request.Request`` rồi abort fetch; không byte nào rời máy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import scp.security.attack_crawler as attack_crawler


class _StopFetch(Exception):
    """Abort một fetch đơn lẻ (đã ghi Request) — không network I/O."""


class _RecordingOpener:
    """Context-manager thay safe_urlopen: ghi Request, không kết nối."""

    def __init__(self, requests_out: list, req):
        self._out = requests_out
        self._req = req

    def __enter__(self):
        self._out.append(self._req)
        raise _StopFetch(f"sentinel: fetch attempted for {self._req.full_url!r}")

    def __exit__(self, *exc_info):
        return False


@pytest.fixture()
def recorded_requests(monkeypatch, tmp_path):
    out: list = []
    monkeypatch.setattr(
        attack_crawler, "safe_urlopen",
        lambda req, timeout=0, **kw: _RecordingOpener(out, req),
    )
    return out


def _make_crawler(tmp_path):
    # data_dir riêng trong tmp — không đụng data/ thật, không đọc cache cũ.
    return attack_crawler.AttackCrawler(data_dir=str(tmp_path / "crawler-data"))


def test_f01_hf_token_never_sent_to_github(monkeypatch, tmp_path, recorded_requests):
    """THE sentinel: chỉ có HF_TOKEN (không GITHUB_TOKEN) → mọi request tới
    api.github.com phải KHÔNG CÓ header Authorization. Regression F-01 từng
    gửi HF token qua header này."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("HF_TOKEN", "hf_SENTINEL_never_leak_to_github")

    _make_crawler(tmp_path)._crawl_github()

    assert recorded_requests, "crawl phải thử fetch ít nhất 1 repo github"
    for req in recorded_requests:
        assert req.full_url.startswith("https://api.github.com/"), (
            f"unexpected host in crawl: {req.full_url!r}"
        )
        assert "Authorization" not in req.headers, (
            "F-01 REGRESSION: credential leak — Authorization header gửi sang "
            f"api.github.com khi chỉ có HF_TOKEN: {req.headers.get('Authorization')!r}"
        )


def test_f01_github_token_binds_to_github_host_only(monkeypatch, tmp_path, recorded_requests):
    """GITHUB_TOKEN khi có mặt → Authorization `token <value>` CHỈ trên request
    tới api.github.com (host-binding đúng chiều thuận)."""
    monkeypatch.setenv("GITHUB_TOKEN", "gh_SENTINEL_github_only")
    monkeypatch.delenv("HF_TOKEN", raising=False)

    _make_crawler(tmp_path)._crawl_github()

    assert recorded_requests, "crawl phải thử fetch ít nhất 1 repo github"
    for req in recorded_requests:
        assert req.full_url.startswith("https://api.github.com/")
        assert req.headers.get("Authorization") == "token gh_SENTINEL_github_only"


def test_f01_no_token_no_authorization_header(monkeypatch, tmp_path, recorded_requests):
    """Không token nào → không Authorization (unauthenticated path giữ nguyên)."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)

    _make_crawler(tmp_path)._crawl_github()

    assert recorded_requests
    for req in recorded_requests:
        assert "Authorization" not in req.headers


def test_f01_source_has_no_cross_provider_token_fallback():
    """Static pin (AST-based, comment-immune): _crawl_github không được đọc
    HF_TOKEN từ môi trường. Behavioral sentinels ở trên là bằng chứng chính;
    pin này chặn regression quay lại ở mức source."""
    import ast as _ast

    src = Path(attack_crawler.__file__).read_text(encoding="utf-8")
    tree = _ast.parse(src)
    fn = next(
        n for n in _ast.walk(tree)
        if isinstance(n, _ast.FunctionDef) and n.name == "_crawl_github"
    )
    offenders = [
        _ast.unparse(node)
        for node in _ast.walk(fn)
        if isinstance(node, _ast.Call)
        and _ast.unparse(node.func) in ("os.environ.get", "environ.get")
        and any(
            isinstance(a, _ast.Constant) and a.value == "HF_TOKEN"
            for a in node.args
        )
    ]
    assert not offenders, (
        f"F-01 regression: _crawl_github đọc HF_TOKEN: {offenders}"
    )
