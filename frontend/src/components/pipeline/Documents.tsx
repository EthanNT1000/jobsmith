import type { ReactNode } from "react"
import type {
  MatchReport, CompanyBrief, TailoredResume, CoverLetter, InterviewKit, CritiqueReport,
} from "../../types"
import { ScoreRing } from "../ScoreRing"

function Chips({ items, color }: { items: string[]; color: string }) {
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((t, i) => (
        <span key={i} className={`text-xs px-2 py-0.5 rounded-full ${color}`}>{t}</span>
      ))}
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border rounded-xl bg-white p-5">
      <h3 className="font-bold mb-3">{title}</h3>
      {children}
    </section>
  )
}

export function MatchCard({ m }: { m: MatchReport }) {
  return (
    <Section title="② 匹配評分">
      <div className="flex items-center gap-5 mb-3">
        <ScoreRing score={m.score} />
        <div>
          <p className="text-sm">{m.recommend_proceed ? "✅ 建議續做" : "⚠️ 建議再評估"}</p>
          <p className="text-sm text-slate-600 mt-1">{m.reason}</p>
        </div>
      </div>
      {m.matched.length > 0 && (
        <><p className="text-sm font-medium mt-2 mb-1">符合項</p>
          <Chips items={m.matched} color="bg-emerald-100 text-emerald-700" /></>
      )}
      {m.gaps.length > 0 && (
        <><p className="text-sm font-medium mt-3 mb-1">落差項</p>
          <Chips items={m.gaps} color="bg-rose-100 text-rose-700" /></>
      )}
      {m.suggestions.length > 0 && (
        <ul className="list-disc pl-5 text-sm mt-3 space-y-1">
          {m.suggestions.map((s, i) => <li key={i}>{s}</li>)}
        </ul>
      )}
    </Section>
  )
}

export function CompanyCard({ c }: { c: CompanyBrief }) {
  return (
    <Section title={`⑧ 公司情報：${c.company}`}>
      {c.data_limited && <p className="text-xs text-amber-600 mb-2">（公開資料有限，建議自行補查）</p>}
      <dl className="grid grid-cols-2 gap-2 text-sm">
        {c.industry && <><dt className="text-slate-500">產業</dt><dd>{c.industry}</dd></>}
        {c.size && <><dt className="text-slate-500">規模</dt><dd>{c.size}</dd></>}
        {c.salary_range && <><dt className="text-slate-500">薪資範圍</dt><dd>{c.salary_range}</dd></>}
        {c.funding && <><dt className="text-slate-500">資金</dt><dd>{c.funding}</dd></>}
      </dl>
      {c.culture_summary && <p className="text-sm mt-3">{c.culture_summary}</p>}
      {c.benefits.length > 0 && (
        <><p className="text-sm font-medium mt-3 mb-1">福利</p>
          <Chips items={c.benefits} color="bg-indigo-100 text-indigo-700" /></>
      )}
      {c.red_flags.length > 0 && (
        <><p className="text-sm font-medium mt-3 mb-1">避雷紅旗</p>
          <Chips items={c.red_flags} color="bg-rose-100 text-rose-700" /></>
      )}
      {c.recent_news.length > 0 && (
        <ul className="list-disc pl-5 text-sm mt-3 space-y-1">
          {c.recent_news.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
      )}
    </Section>
  )
}

export function ResumeDoc({ r }: { r: TailoredResume }) {
  return (
    <Section title="③ 客製履歷">
      <p className="text-sm font-medium mb-2">{r.summary}</p>
      <ul className="list-disc pl-5 text-sm space-y-1">
        {r.bullets.map((b, i) => <li key={i}>{b}</li>)}
      </ul>
      {r.ats_keywords_hit.length > 0 && (
        <><p className="text-sm font-medium mt-3 mb-1">ATS 命中</p>
          <Chips items={r.ats_keywords_hit} color="bg-emerald-100 text-emerald-700" /></>
      )}
      {r.ats_keywords_missing.length > 0 && (
        <><p className="text-sm font-medium mt-3 mb-1">ATS 尚缺</p>
          <Chips items={r.ats_keywords_missing} color="bg-amber-100 text-amber-700" /></>
      )}
      {r.notes && <p className="text-xs text-slate-500 mt-3">{r.notes}</p>}
    </Section>
  )
}

export function CoverLetterDoc({ c }: { c: CoverLetter }) {
  return (
    <Section title="④ 求職信">
      {c.subject && <p className="text-sm font-medium mb-2">主旨：{c.subject}</p>}
      <div className="text-sm whitespace-pre-wrap leading-relaxed">{c.body}</div>
    </Section>
  )
}

function QList({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null
  return (
    <div className="mt-3">
      <p className="text-sm font-medium mb-1">{title}</p>
      <ul className="list-disc pl-5 text-sm space-y-1">
        {items.map((q, i) => <li key={i}>{q}</li>)}
      </ul>
    </div>
  )
}

export function InterviewKitDoc({ k }: { k: InterviewKit }) {
  return (
    <Section title="⑤ 面試準備">
      <QList title="技術題" items={k.technical_questions} />
      <QList title="行為題" items={k.behavioral_questions} />
      <QList title="台灣特有題" items={k.taiwan_specific_questions} />
      <QList title="STAR 擬答" items={k.sample_answers} />
      <QList title="反向提問" items={k.reverse_questions} />
      <QList title="避雷提醒" items={k.cautions} />
    </Section>
  )
}

export function CritiqueCard({ q }: { q: CritiqueReport }) {
  const rows: [string, number][] = [
    ["履歷", q.resume_score], ["求職信", q.cover_letter_score], ["面試", q.interview_score],
  ]
  return (
    <Section title="⑥ 品管評審">
      <p className="text-sm mb-2">{q.overall_pass ? "✅ 整體達標" : "⚠️ 未達標（已觸發重寫）"}</p>
      <div className="grid grid-cols-3 gap-3">
        {rows.map(([label, score]) => (
          <div key={label} className="text-center">
            <div className="text-2xl font-bold">{score}</div>
            <div className="text-xs text-slate-500">{label}</div>
          </div>
        ))}
      </div>
      {q.feedback.length > 0 && (
        <ul className="list-disc pl-5 text-sm mt-3 space-y-1">
          {q.feedback.map((f, i) => <li key={i}>{f}</li>)}
        </ul>
      )}
    </Section>
  )
}
