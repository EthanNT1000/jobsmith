"""履歷／求職信的多輪對話修改 agent：使用者與 AI 討論，AI 回覆並（必要時）給出修訂版本。

無狀態：對話歷史由前端帶入 messages，後端每次依「JD + 履歷背景 + 目前文件 + 對話」回應。
"""
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.models import Profile

_RESUME_SYS = (
    "你是資深履歷顧問，正在和求職者一起打磨『客製履歷』。"
    "依對話最新一則訊息回覆（reply，繁體中文、具體可行、簡潔）。"
    "若使用者要求修改履歷，請在 updated_summary / updated_bullets 給出修訂後內容"
    "（updated_bullets 為條列字串陣列）；若只是討論、不需改動，兩者留空（null）。"
    "修訂要貼合職缺 JD 與求職者背景，量化成果、用詞專業，且不可捏造未提供的經歷。"
)
_COVER_SYS = (
    "你是資深求職信顧問，正在和求職者一起打磨『求職信』。"
    "依對話最新一則訊息回覆（reply，繁體中文、具體可行、簡潔）。"
    "若使用者要求修改，請在 updated_subject / updated_body 給出修訂後內容；"
    "若只是討論、不需改動，兩者留空（null）。"
    "修訂要貼合職缺 JD 與求職者背景，且不可捏造未提供的經歷。"
)


class RefineResult(BaseModel):
    reply: str = Field(description="對使用者最新訊息的對話回覆（繁體中文）")
    updated_summary: str | None = Field(default=None, description="修訂後的履歷摘要；不改則 null")
    updated_bullets: list[str] | None = Field(default=None, description="修訂後的履歷重點條列；不改則 null")
    updated_subject: str | None = Field(default=None, description="修訂後的求職信主旨；不改則 null")
    updated_body: str | None = Field(default=None, description="修訂後的求職信內文；不改則 null")


def _brief(p: Profile) -> str:
    return (f"姓名：{p.name}\n定位：{p.summary}\n技能：{'、'.join(p.skills) or '（無）'}\n"
            f"經歷：{'；'.join(p.experiences) or '（無）'}\n年資：{p.years_experience}")


def refine_document(doc_type: str, current: str, messages: list[dict],
                    jd: str, profile: Profile) -> RefineResult:
    """依對話修訂履歷或求職信（standard 分層）。doc_type: 'resume' | 'cover'。"""
    sys = _RESUME_SYS if doc_type == "resume" else _COVER_SYS
    doc_label = "客製履歷" if doc_type == "resume" else "求職信"
    convo = "\n".join(
        f"{'使用者' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')}" for m in messages
    )
    llm = get_llm("standard", max_tokens=2000).with_structured_output(RefineResult)
    human = (f"【職缺 JD】\n{(jd or '')[:3000]}\n\n【求職者背景】\n{_brief(profile)}\n\n"
             f"【目前的{doc_label}】\n{(current or '')[:3000]}\n\n【對話紀錄】\n{convo}")
    return llm.invoke([("system", sys), ("human", human)])
