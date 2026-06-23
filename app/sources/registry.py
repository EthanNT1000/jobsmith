"""職缺來源註冊表：彙整多站搜尋、LinkedIn 深連結。"""
from __future__ import annotations

from urllib.parse import quote

from app.models import SearchResult
from app.sources import source_104, source_cake, source_yourator

# 可關鍵字搜尋的來源（name -> search 函式）
SEARCHABLE = {
    source_104.NAME: source_104.search,
    source_yourator.NAME: source_yourator.search,
    source_cake.NAME: source_cake.search,
}


def search_all(keywords: str, sources: list[str] | None = None, limit: int = 15) -> list[SearchResult]:
    """對選定來源各跑一次搜尋；單一來源失敗只回該來源 blocked，不影響其他。"""
    names = sources or list(SEARCHABLE)
    results = []
    for n in names:
        fn = SEARCHABLE.get(n)
        if fn is not None:
            results.append(fn(keywords, limit))
    return results


def linkedin_search_url(keywords: str) -> str:
    """LinkedIn 不爬整頁：產生預填關鍵字的台灣職缺搜尋深連結。"""
    return f"https://www.linkedin.com/jobs/search/?keywords={quote(keywords)}&location=Taiwan"
