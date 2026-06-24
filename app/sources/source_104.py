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


# 104 薪資型態碼（欄位 s10）。salaryDesc 已不再回傳，真值在 salaryLow/salaryHigh。
_SALARY_TYPE = {10: "面議", 30: "時薪", 40: "日薪", 50: "月薪", 60: "年薪"}


def _format_salary(d: dict) -> str | None:
    """由 salaryLow/salaryHigh + 型態碼 s10 組出可讀薪資字串。"""
    try:
        low = int(d.get("salaryLow") or 0)
        high = int(d.get("salaryHigh") or 0)
    except (TypeError, ValueError):
        low = high = 0
    try:
        code = int(d.get("s10") or 0)
    except (TypeError, ValueError):
        code = 0
    if code == 10 or (low == 0 and high == 0):
        return "面議"
    label = _SALARY_TYPE.get(code, "")
    if low and high and low != high:
        amount = f"NT${low:,}–{high:,}"
    elif high:
        amount = f"NT${high:,}"
    elif low:
        amount = f"NT${low:,} 以上"
    else:
        return "面議"
    return f"{label} {amount}".strip()


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
            salary=_format_salary(d),
            url=link.get("job", "") or "",
            snippet=clean(d.get("descSnippet") or d.get("description") or ""),
        ))
    return SearchResult(source=NAME, jobs=jobs)
