import type { ComponentType } from "react"
import { Logomark } from "./Brand"

export interface NavItem<T extends string = string> {
  id: T
  label: string
  icon: ComponentType<{ className?: string }>
}

// 左側 rail：圖示+文字導覽（桌機 w-52；行動裝置收成 w-16 純圖示）。
export function Sidebar<T extends string>(
  { items, active, onSelect, footer }:
  { items: NavItem<T>[]; active: T; onSelect: (id: T) => void; footer?: NavItem<T>[] },
) {
  const renderItem = ({ id, label, icon: Icon }: NavItem<T>) => (
    <button
      key={id}
      onClick={() => onSelect(id)}
      title={label}
      aria-current={active === id ? "page" : undefined}
      className={`flex items-center gap-3 mx-2 my-0.5 px-3 py-2.5 rounded-lg transition
        focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 ${
        active === id ? "bg-brand-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
      }`}
    >
      <Icon className="w-5 h-5 shrink-0" />
      <span className="hidden md:inline text-sm font-medium whitespace-nowrap">{label}</span>
    </button>
  )

  return (
    <aside className="no-print shrink-0 w-16 md:w-52 border-r border-slate-200 bg-white/70 backdrop-blur flex flex-col sticky top-0 h-screen">
      <div className="flex items-center gap-2 px-3 md:px-4 h-16 border-b border-slate-100">
        <Logomark size={28} />
        <div className="hidden md:block font-display font-bold text-base leading-none">
          <span className="text-slate-900">Job</span><span className="text-brand-600">Copilot</span>
        </div>
      </div>
      <nav className="flex-1 py-3 overflow-y-auto">{items.map(renderItem)}</nav>
      {footer && footer.length > 0 && (
        <div className="py-3 border-t border-slate-100">{footer.map(renderItem)}</div>
      )}
    </aside>
  )
}
