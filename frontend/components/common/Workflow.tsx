"use client";

import type {ChangeEventHandler, ReactNode} from "react";

type StepStatus = "completed" | "current" | "upcoming";

export type WorkflowStep = {
  description?: string;
  label: string;
  status: StepStatus;
};

const stepStatusClasses: Record<StepStatus, string> = {
  completed: "border-[var(--success)] bg-[var(--success)] text-white",
  current: "border-[var(--blue)] bg-[var(--blue)] text-white",
  upcoming: "border-[var(--border)] bg-white text-[var(--muted)]"
};

export function StepIndicator({label, steps}: {label: string; steps: WorkflowStep[]}) {
  return (
    <ol aria-label={label} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {steps.map((step, index) => (
        <li className="flex min-w-0 items-start gap-3" key={step.label}>
          <span aria-hidden="true" className={["grid h-8 w-8 shrink-0 place-items-center rounded-full border text-sm font-bold", stepStatusClasses[step.status]].join(" ")}>{index + 1}</span>
          <span className="min-w-0 pt-1"><strong className="block break-words text-sm text-[var(--ink)]">{step.label}</strong>{step.description ? <span className="mt-1 block break-words text-xs leading-5 text-[var(--muted)]">{step.description}</span> : null}</span>
        </li>
      ))}
    </ol>
  );
}

export type SidebarNavItem = {active?: boolean; href: string; label: string};

export function SidebarNav({items, label}: {items: SidebarNavItem[]; label: string}) {
  return (
    <nav aria-label={label} className="border-b border-[var(--border)] bg-white lg:w-60 lg:shrink-0 lg:border-b-0 lg:border-r">
      <ul className="flex overflow-x-auto lg:block">
        {items.map((item) => (
          <li className="shrink-0" key={item.href}>
            <a
              aria-current={item.active ? "page" : undefined}
              className={[
                "block border-b-2 border-transparent px-4 py-3 text-sm font-bold whitespace-nowrap lg:border-b-0 lg:border-l-4",
                item.active ? "border-[var(--blue)] bg-[var(--blue-soft)] text-[var(--blue)]" : "text-[var(--ink)] hover:bg-[#f5f8fb]"
              ].join(" ")}
              href={item.href}
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export type TimelineEvent = {description?: string; label: string; timestamp?: string; tone?: "success" | "warning" | "info" | "neutral"};

const timelineToneClasses = {
  success: "bg-[var(--success)]",
  warning: "bg-[var(--warning)]",
  info: "bg-[var(--blue)]",
  neutral: "bg-[#7a899b]"
};

export function StatusTimeline({events, label}: {events: TimelineEvent[]; label: string}) {
  return (
    <ol aria-label={label} className="space-y-5">
      {events.map((event, index) => (
        <li className="relative flex gap-4" key={event.label + index}>
          {index < events.length - 1 ? <span aria-hidden="true" className="absolute left-[9px] top-5 h-[calc(100%+8px)] w-px bg-[var(--border)]" /> : null}
          <span aria-hidden="true" className={["mt-1 h-5 w-5 shrink-0 rounded-full border-4 border-white shadow-[0_0_0_1px_var(--border)]", timelineToneClasses[event.tone ?? "neutral"]].join(" ")} />
          <div className="min-w-0 pb-1"><strong className="block break-words text-sm text-[var(--ink)]">{event.label}</strong>{event.timestamp ? <time className="mt-1 block text-xs text-[var(--muted)]">{event.timestamp}</time> : null}{event.description ? <p className="mt-1 break-words text-sm leading-6 text-[var(--muted)]">{event.description}</p> : null}</div>
        </li>
      ))}
    </ol>
  );
}

export type ReviewItem = {label: string; value: ReactNode};

export function ReviewSection({action, items, title}: {action?: ReactNode; items: ReviewItem[]; title: string}) {
  return (
    <section className="rounded-[var(--radius)] border border-[var(--border)] bg-white shadow-[var(--shadow)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-5 py-4"><h2 className="text-lg font-bold text-[var(--navy)]">{title}</h2>{action}</div>
      <dl className="divide-y divide-[var(--border)]">{items.map((item) => <div className="grid gap-1 px-5 py-4 sm:grid-cols-[minmax(10rem,1fr)_2fr] sm:gap-6" key={item.label}><dt className="text-sm font-bold text-[var(--muted)]">{item.label}</dt><dd className="break-words text-sm leading-6 text-[var(--ink)]">{item.value}</dd></div>)}</dl>
    </section>
  );
}

export function DeclarationBox({checked, description, id, label, onCheckedChange}: {checked: boolean; description?: string; id: string; label: string; onCheckedChange: ChangeEventHandler<HTMLInputElement>}) {
  return (
    <section className="rounded-[var(--radius)] border border-[#c6dff5] bg-[#f2f8ff] p-4">
      <label className="flex items-start gap-3 text-sm leading-6 text-[var(--ink)]" htmlFor={id}>
        <input checked={checked} className="mt-1 h-4 w-4 shrink-0 accent-[var(--blue)]" id={id} onChange={onCheckedChange} type="checkbox" />
        <span><strong>{label}</strong>{description ? <span className="mt-1 block text-[var(--muted)]">{description}</span> : null}</span>
      </label>
    </section>
  );
}
