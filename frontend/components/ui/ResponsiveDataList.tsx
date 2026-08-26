import type {ReactNode} from "react";

export type DataListColumn = {key: string; label: string};
export type DataListRow = {id: string; values: Record<string, ReactNode>};

type ResponsiveDataListProps = {
  caption: string;
  columns: DataListColumn[];
  emptyMessage: string;
  rows: DataListRow[];
};

export function ResponsiveDataList({caption, columns, emptyMessage, rows}: ResponsiveDataListProps) {
  if (rows.length === 0) {
    return <p className="rounded-[var(--radius)] border border-dashed border-[var(--border)] bg-[#f9fbfd] p-5 text-sm text-[var(--muted)]">{emptyMessage}</p>;
  }

  return (
    <>
      <div className="hidden overflow-x-auto rounded-[var(--radius)] border border-[var(--border)] md:block">
        <table className="min-w-full border-collapse text-left text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-[#eef5fb] text-[var(--navy)]">
            <tr>{columns.map((column) => <th className="px-4 py-3 font-bold" key={column.key} scope="col">{column.label}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)] bg-white">
            {rows.map((row) => <tr key={row.id}>{columns.map((column) => <td className="px-4 py-3 align-top leading-6 text-[var(--ink)]" key={column.key}>{row.values[column.key]}</td>)}</tr>)}
          </tbody>
        </table>
      </div>
      <div className="space-y-3 md:hidden">
        {rows.map((row) => (
          <article className="rounded-[var(--radius)] border border-[var(--border)] bg-white p-4 shadow-[var(--shadow)]" key={row.id}>
            <dl className="space-y-3">
              {columns.map((column) => <div key={column.key}><dt className="text-xs font-bold uppercase text-[var(--muted)]">{column.label}</dt><dd className="mt-1 break-words text-sm leading-6 text-[var(--ink)]">{row.values[column.key]}</dd></div>)}
            </dl>
          </article>
        ))}
      </div>
    </>
  );
}
