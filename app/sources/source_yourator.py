"""Yourator：v4 jobs JSON API。本環境憑證鏈驗不過，故 verify=False 取公開資料。"""
from __future__ import annotations

from urllib.parse import quote

from app.models import JobPosting, SearchResult
from app.sources.base import http_get

NAME = "yourator"
SEARCHABLE = True
_API = "https://www.yourator.co/api/v4/jobs?term[]={kw}&page=1"


def search(keywords: str, limit: int = 15) -> SearchResult:
    try:
        r = http_get(_API.format(kw=quote(keywords)), verify=False)
        if not r.ok:
            return SearchResult(source=NAME, blocked=True, error=f"HTTP {r.status_code}")
        data = (r.json().get("payload") or {}).get("jobs") or []
    except Exception as e:
        return SearchResult(source=NAME, blocked=True, error=str(e)[:150])

    jobs = []
    for d in data[:limit]:
        comp = d.get("company") or {}
        tags = d.get("tags") or []
        path = d.get("path") or ""
        jobs.append(JobPosting(
            source=NAME,
            title=d.get("name", ""),
            company=comp.get("brand") or comp.get("enName") or "",
            location=d.get("location"),
            salary=d.get("salary"),
            url="https://www.yourator.co" + path if path else "",
            snippet="、".join(tags) if tags else None,
            requirements=tags,
        ))
    return SearchResult(source=NAME, jobs=jobs)
