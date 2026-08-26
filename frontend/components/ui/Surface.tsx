import type {ReactNode} from "react";

type SurfaceCardProps = {
  children: ReactNode;
  className?: string;
  heading?: ReactNode;
};

export function SurfaceCard({children, className = "", heading}: SurfaceCardProps) {
  return (
    <section className={["rounded-[var(--radius)] border border-[var(--border)] bg-white p-5 shadow-[var(--shadow)]", className].join(" ")}>
      {heading ? <div className="mb-4 border-b border-[var(--border)] pb-3 text-lg font-bold text-[var(--navy)]">{heading}</div> : null}
      {children}
    </section>
  );
}

type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const statusToneClasses: Record<StatusTone, string> = {
  success: "border-[#97d8bd] bg-[#e5f7ee] text-[#0d6248]",
  warning: "border-[#f0ce86] bg-[#fff5d7] text-[#8a4a00]",
  danger: "border-[#efb5b1] bg-[#fdefee] text-[#9f211a]",
  info: "border-[#abd2f5] bg-[#eaf4ff] text-[#07529d]",
  neutral: "border-[#cdd7e2] bg-[#f4f7fa] text-[#405166]"
};

export function StatusChip({label, tone = "neutral"}: {label: string; tone?: StatusTone}) {
  return <span className={["inline-flex min-h-7 items-center rounded-full border px-3 py-1 text-xs font-bold leading-4", statusToneClasses[tone]].join(" ")}>{label}</span>;
}

type StateTone = "loading" | "error" | "empty" | "success";

const stateToneClasses: Record<StateTone, string> = {
  loading: "border-[#abd2f5] bg-[#f7fbff] text-[#07529d]",
  error: "border-[#efb5b1] bg-[#fef7f6] text-[#9f211a]",
  empty: "border-[var(--border)] bg-[#f9fbfd] text-[var(--muted)]",
  success: "border-[#97d8bd] bg-[#f5fcf8] text-[#0d6248]"
};

export function StatePanel({action, children, title, tone}: {action?: ReactNode; children: ReactNode; title: string; tone: StateTone}) {
  return (
    <section className={["flex flex-col items-start gap-3 rounded-[var(--radius)] border p-5 sm:flex-row sm:items-center sm:justify-between", stateToneClasses[tone]].join(" ")}>
      <div><h2 className="font-bold">{title}</h2><div className="mt-1 text-sm leading-6">{children}</div></div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </section>
  );
}
