"""104 人力銀行：前端搜尋 JSON API（需帶 Referer）。個人使用、低頻、被擋即降級。"""
from __future__ import annotations

from urllib.parse import quote

from app.models import JobPosting, SearchResult
from app.sources.base import clean, http_get

NAME = "104"
SEARCHABLE = True
_REFERER = "https://www.104.com.tw/jobs/search/"
_API = ("https://www.104.com.tw/jobs/search/api/jobs?ro=0&kwop=7&keyword={kw}"
        "&order=15&asc=0&page=1&mode=s&jobsource=2018indexpoc")


def search(keywords: str, limit: int = 15) -> SearchResult:
    try:
        r = http_get(_API.format(kw=quote(keywords)), referer=_REFERER)
        if not r.ok:
            return SearchResult(source=NAME, blocked=True, error=f"HTTP {r.status_code}")
        data = r.json().get("data") or []
    except Exception as e:  # 連線/解析錯誤 → 降級
        return SearchResult(source=NAME, blocked=True, error=str(e)[:150])

    jobs = []
    for d in data[:limit]:
        link = d.get("link") or {}
        jobs.append(JobPosting(
            source=NAME,
            title=clean(d.get("jobName", "")),
            company=clean(d.get("custName", "")),
            location=d.get("jobAddrNoDesc") or d.get("jobAddress"),
            salary=d.get("salaryDesc"),
            url=link.get("job", "") or "",
            snippet=clean(d.get("descSnippet") or d.get("description") or ""),
        ))
    return SearchResult(source=NAME, jobs=jobs)
