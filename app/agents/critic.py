"""⑥ 品管/反思 Agent：對投遞包評分並給修改指示。"""
from app.llm import get_llm
from app.models import (
    CoverLetter,
    CritiqueReport,
    InterviewKit,
    ParsedJob,
    TailoredResume,
)

CRITIC_SYSTEM = (
    "你是嚴格的投遞包品管審查員。請依『職缺』，對『客製履歷、求職信、面試準備』"
    "三份成品逐項評分（0-100），並判斷整體是否達標（overall_pass）。"
    "評分依據：是否命中 JD 必備條件、ATS 關鍵字覆蓋、台灣在地規範與語氣、"
    "是否具體不空泛、是否有捏造未提供的經歷。"
    "若未達標，請把可執行的具體修改指示放進 per_doc，鍵只能用 "
    "resume / cover_letter / interview，且『只放需要重寫的文件』——已達標的文件不要放，"
    "這樣下一輪只會精準重寫未過的文件、不重跑已過的。"
)


def critique_package(
    job: ParsedJob,
    resume: TailoredResume,
    cover_letter: CoverLetter,
    interview_kit: InterviewKit,
) -> CritiqueReport:
    """評審投遞包（deep 分層）；逐文件回饋放 per_doc，feedback 由程式彙整供顯示。"""
    llm = get_llm("deep").with_structured_output(CritiqueReport)
    human = (
        f"【職缺】\n{job.model_dump_json(indent=2)}\n\n"
        f"【客製履歷】\n{resume.model_dump_json(indent=2)}\n\n"
        f"【求職信】\n{cover_letter.model_dump_json(indent=2)}\n\n"
        f"【面試準備】\n{interview_kit.model_dump_json(indent=2)}"
    )
    report = llm.invoke([("system", CRITIC_SYSTEM), ("human", human)])
    # 由 per_doc 彙整 feedback（前端相容；標註文件別）。
    _DOC_LABEL = {"resume": "履歷", "cover_letter": "求職信", "interview": "面試"}
    report.feedback = [
        f"[{_DOC_LABEL.get(doc, doc)}] {item}"
        for doc, items in (report.per_doc or {}).items() for item in items
    ]
    return report
