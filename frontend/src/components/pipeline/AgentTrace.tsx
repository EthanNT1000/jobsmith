const AGENTS: [string, string][] = [
  ["parse", "① 解析 JD"],
  ["match", "② 匹配評分"],
  ["company_research", "⑧ 公司情報"],
  ["resume_tailor", "③ 客製履歷"],
  ["cover_letter", "④ 求職信"],
  ["interview_prep", "⑤ 面試準備"],
  ["critic", "⑥ 品管 / 反思"],
  ["human_gate", "⑦ 人工核可"],
]

export function AgentTrace(
  { done, running, revisions, status }:
  { done: string[]; running: boolean; revisions: number; status: string },
) {
  const seen = new Set(done)
  return (
    <div className="border rounded-xl bg-white p-4 sticky top-4">
      <h2 className="font-semibold mb-3">即時編排追蹤</h2>
      <ul className="space-y-2 text-sm">
        {AGENTS.map(([k, label]) => {
          const ok = seen.has(k)
          return (
            <li key={k} className="flex items-center gap-2">
              <span className={ok ? "text-emerald-600" : "text-slate-300"}>{ok ? "✓" : "○"}</span>
              <span className={ok ? "text-slate-800" : "text-slate-400"}>{label}</span>
            </li>
          )
        })}
      </ul>
      {revisions > 1 && (
        <p className="text-xs text-amber-600 mt-3">🔄 反思迴圈：第 {revisions} 輪評審</p>
      )}
      <p className="text-xs text-slate-500 mt-3">{running ? "⏳ " : ""}{status}</p>
    </div>
  )
}
