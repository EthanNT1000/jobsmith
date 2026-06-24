"""技能缺口市場分析：彙整搜到職缺的 requirements，比對履歷找出缺口。

無 LLM（便宜、可測）。兩個關鍵設計：
1. 「已具備」比對的對象是整份履歷（技能 + 摘要 + 經歷 + 期望職務），不只 skills 欄位——
   履歷標題寫「AI 工程師」時，職缺要求「AI」就該算具備，不應誤列為缺口。
2. 來源職缺應由呼叫端先篩成「與履歷相關」的（高適配），否則行銷/業務等無關職缺的
   要求（廣告投放、B2B 業務…）會污染缺口清單。
"""
from __future__ import annotations

import re
from collections import Counter

from app.models import Profile, JobPosting, SkillCount, SkillGapReport


def _norm(s: str) -> str:
    """小寫 + 收斂空白。"""
    return " ".join(str(s).lower().split())


def _is_short_ascii(s: str) -> bool:
    """純英數且很短（ai、ml、go、qa…）——子字串比對易誤判，改用字界比對。"""
    return len(s) <= 3 and s.isascii() and s.replace("+", "").replace("#", "").isalnum()


def _profile_blob(profile: Profile) -> str:
    """整份履歷的可比對文字（技能 + 摘要 + 經歷 + 期望職務），正規化成一個字串。"""
    parts: list[str] = list(profile.skills or [])
    if profile.summary:
        parts.append(profile.summary)
    parts += list(profile.preferred_roles or [])
    parts += list(profile.experiences or [])
    return _norm(" \n ".join(parts))


def _covered(req: str, skill_norms: set[str], blob: str) -> bool:
    """這項職缺要求是否已被履歷涵蓋。

    - 某履歷技能是要求的子字串（履歷「python」⊂ 要求「python 後端」）；或
    - 要求出現在履歷任一處文字（要求「ai」出現在摘要「ai 工程師」）。
      短英數要求（ai/ml…）用字界比對，避免「ai」誤中 rail/domain。
    """
    for s in skill_norms:
        if len(s) >= 2 and s in req:
            return True
    if len(req) >= 2:
        if _is_short_ascii(req):
            return bool(re.search(rf"(?<![0-9a-z]){re.escape(req)}(?![0-9a-z])", blob))
        return req in blob
    return False


def analyze_skill_gap(profile: Profile, jobs: list[JobPosting], top_n: int = 15) -> SkillGapReport:
    skill_norms = {_norm(s) for s in (profile.skills or []) if s.strip()}
    blob = _profile_blob(profile)
    counter: Counter[str] = Counter()
    display: dict[str, str] = {}
    for j in jobs:
        for req in (j.requirements or []):
            r = str(req).strip()
            if not r:
                continue
            key = _norm(r)
            if not key:
                continue
            counter[key] += 1
            display.setdefault(key, r)
    ranked = counter.most_common()
    top_demand = [SkillCount(skill=display[k], count=c) for k, c in ranked[:top_n]]
    your_gaps = [SkillCount(skill=display[k], count=c)
                 for k, c in ranked if not _covered(k, skill_norms, blob)][:top_n]
    have = [display[k] for k, _ in ranked if _covered(k, skill_norms, blob)]
    return SkillGapReport(top_demand=top_demand, your_gaps=your_gaps, have=have)
