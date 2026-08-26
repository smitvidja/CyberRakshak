"use client";

import type {ChangeEvent} from "react";

type UploadDropzoneProps = {
  accept?: string;
  browseLabel: string;
  description: string;
  disabled?: boolean;
  error?: string;
  id: string;
  maxSizeLabel?: string;
  multiple?: boolean;
  onFilesSelected?: (files: File[]) => void;
  title: string;
};

export function UploadDropzone({
  accept,
  browseLabel,
  description,
  disabled = false,
  error,
  id,
  maxSizeLabel,
  multiple = false,
  onFilesSelected,
  title
}: UploadDropzoneProps) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    onFilesSelected?.(Array.from(event.target.files ?? []));
  }

  return (
    <section className="rounded-[var(--radius)] border border-dashed border-[var(--blue)] bg-[#f7fbff] p-5 text-center">
      <h2 className="text-base font-bold text-[var(--navy)]">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">{description}</p>
      {maxSizeLabel ? <p className="mt-2 text-xs font-medium text-[var(--muted)]">{maxSizeLabel}</p> : null}
      <label
        aria-disabled={disabled}
        className={[
          "mt-4 inline-flex min-h-11 items-center justify-center rounded-[var(--radius)] border border-[var(--blue)] bg-white px-4 py-2 text-sm font-bold text-[var(--blue)]",
          disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:bg-[var(--blue-soft)]"
        ].join(" ")}
        htmlFor={id}
      >
        {browseLabel}
      </label>
      <input accept={accept} className="sr-only" disabled={disabled} id={id} multiple={multiple} onChange={handleChange} type="file" />
      {error ? <p className="mt-3 text-sm font-medium text-[var(--danger)]" role="alert">{error}</p> : null}
    </section>
  );
}
