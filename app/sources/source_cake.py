"""Cake（cake.me）：盡力解析搜尋頁的 __NEXT_DATA__。結構較脆弱，失敗即降級。"""
from __future__ import annotations

import json
import re
from urllib.parse import quote

from app.models import JobPosting, SearchResult
from app.sources.base import http_get

NAME = "cake"
SEARCHABLE = True
_PAGE = "https://www.cake.me/jobs?q={kw}"
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL)


def _collect_jobs(node, out: list, depth: int = 0):
    """遞迴在 __NEXT_DATA__ 找看起來像職缺的物件（含 title/path 且 path 指向 /jobs/）。"""
    if depth > 8 or len(out) >= 40:
        return
    if isinstance(node, dict):
        path = node.get("path") or node.get("link") or ""
        title = node.get("title") or node.get("name")
        if isinstance(path, str) and "/jobs/" in path and title:
            out.append(node)
        for v in node.values():
            _collect_jobs(v, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _collect_jobs(v, out, depth + 1)


def search(keywords: str, limit: int = 15) -> SearchResult:
    try:
        r = http_get(_PAGE.format(kw=quote(keywords)), verify=False)
        if not r.ok:
            return SearchResult(source=NAME, blocked=True, error=f"HTTP {r.status_code}")
        m = _NEXT.search(r.text)
        if not m:
            return SearchResult(source=NAME, blocked=True, error="找不到 __NEXT_DATA__")
        data = json.loads(m.group(1))
    except Exception as e:
        return SearchResult(source=NAME, blocked=True, error=str(e)[:150])

    found: list = []
    _collect_jobs(data, found)
    seen, jobs = set(), []
    for d in found:
        path = d.get("path") or d.get("link") or ""
        if path in seen:
            continue
        seen.add(path)
        comp = d.get("company") or {}
        company = comp.get("name") if isinstance(comp, dict) else (d.get("company_name") or "")
        url = path if str(path).startswith("http") else "https://www.cake.me" + str(path)
        jobs.append(JobPosting(
            source=NAME,
            title=d.get("title") or d.get("name") or "",
            company=company or "",
            location=d.get("location") or None,
            salary=d.get("salary") or None,
            url=url,
            snippet=(d.get("description") or "")[:200] or None,
        ))
        if len(jobs) >= limit:
            break
    if not jobs:
        return SearchResult(source=NAME, blocked=True, error="解析不到職缺")
    return SearchResult(source=NAME, jobs=jobs)
