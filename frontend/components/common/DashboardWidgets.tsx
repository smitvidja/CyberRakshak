import type {ReactNode} from "react";

export function MetricCard({description, label, value}: {description?: string; label: string; value: ReactNode}) {
  return (
    <article className="min-w-0 rounded-[var(--radius)] border border-[var(--border)] bg-white p-5 shadow-[var(--shadow)]">
      <p className="text-sm font-bold text-[var(--muted)]">{label}</p>
      <p className="mt-2 break-words text-3xl font-bold text-[var(--navy)]">{value}</p>
      {description ? <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{description}</p> : null}
    </article>
  );
}

export type QuickAction = {description?: string; href: string; label: string};

export function QuickActionList({actions, title}: {actions: QuickAction[]; title: string}) {
  return (
    <section className="rounded-[var(--radius)] border border-[var(--border)] bg-white shadow-[var(--shadow)]">
      <h2 className="border-b border-[var(--border)] px-5 py-4 text-lg font-bold text-[var(--navy)]">{title}</h2>
      <ul className="divide-y divide-[var(--border)]">
        {actions.map((action) => (
          <li key={action.href}>
            <a className="block px-5 py-4 transition-colors hover:bg-[#f5f8fb]" href={action.href}>
              <strong className="block break-words text-sm text-[var(--blue)]">{action.label}</strong>
              {action.description ? <span className="mt-1 block break-words text-sm leading-6 text-[var(--muted)]">{action.description}</span> : null}
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
