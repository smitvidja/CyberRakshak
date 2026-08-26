"use client";

import type {ChangeEventHandler, InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes} from "react";

type FieldBaseProps = {
  description?: string;
  error?: string;
  id: string;
  label: string;
  required?: boolean;
};

function FieldMessages({description, error, id}: Pick<FieldBaseProps, "description" | "error" | "id">) {
  return (
    <>
      {description ? <p className="mt-1 text-sm leading-5 text-[var(--muted)]" id={id + "-description"}>{description}</p> : null}
      {error ? <p className="mt-1 text-sm font-medium leading-5 text-[var(--danger)]" id={id + "-error"} role="alert">{error}</p> : null}
    </>
  );
}

function describedBy({description, error, id}: Pick<FieldBaseProps, "description" | "error" | "id">) {
  return [description ? id + "-description" : "", error ? id + "-error" : ""].filter(Boolean).join(" ") || undefined;
}

const fieldClassName = [
  "mt-1 block min-h-11 w-full rounded-[var(--radius)] border bg-white px-3 py-2 text-[var(--ink)]",
  "placeholder:text-[#7a899b] focus:border-[var(--blue)]",
  "disabled:cursor-not-allowed disabled:bg-[#eef3f8] disabled:text-[var(--muted)]"
].join(" ");

export type TextInputProps = FieldBaseProps & Omit<InputHTMLAttributes<HTMLInputElement>, "id">;

export function TextInput({description, error, id, label, required, ...inputProps}: TextInputProps) {
  return (
    <label className="block text-sm font-bold text-[var(--ink)]" htmlFor={id}>
      {label}{required ? <span aria-hidden="true" className="ml-1 text-[var(--danger)]">*</span> : null}
      <input
        aria-describedby={describedBy({description, error, id})}
        aria-invalid={Boolean(error)}
        className={[fieldClassName, error ? "border-[var(--danger)]" : "border-[var(--border)]"].join(" ")}
        id={id}
        required={required}
        {...inputProps}
      />
      <FieldMessages description={description} error={error} id={id} />
    </label>
  );
}

export type SelectOption = {disabled?: boolean; label: string; value: string};
export type SelectFieldProps = FieldBaseProps & Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> & {options: SelectOption[]};

export function SelectField({description, error, id, label, options, required, ...selectProps}: SelectFieldProps) {
  return (
    <label className="block text-sm font-bold text-[var(--ink)]" htmlFor={id}>
      {label}{required ? <span aria-hidden="true" className="ml-1 text-[var(--danger)]">*</span> : null}
      <select
        aria-describedby={describedBy({description, error, id})}
        aria-invalid={Boolean(error)}
        className={[fieldClassName, error ? "border-[var(--danger)]" : "border-[var(--border)]"].join(" ")}
        id={id}
        required={required}
        {...selectProps}
      >
        {options.map((option) => <option disabled={option.disabled} key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      <FieldMessages description={description} error={error} id={id} />
    </label>
  );
}

export type TextAreaProps = FieldBaseProps & Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id">;

export function TextArea({className = "", description, error, id, label, required, ...textareaProps}: TextAreaProps) {
  return (
    <label className="block text-sm font-bold text-[var(--ink)]" htmlFor={id}>
      {label}{required ? <span aria-hidden="true" className="ml-1 text-[var(--danger)]">*</span> : null}
      <textarea
        aria-describedby={describedBy({description, error, id})}
        aria-invalid={Boolean(error)}
        className={[fieldClassName, "min-h-28 resize-y", error ? "border-[var(--danger)]" : "border-[var(--border)]", className].join(" ")}
        id={id}
        required={required}
        {...textareaProps}
      />
      <FieldMessages description={description} error={error} id={id} />
    </label>
  );
}

export type CheckboxFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "type"> & FieldBaseProps & {
  onCheckedChange?: ChangeEventHandler<HTMLInputElement>;
};

export function CheckboxField({description, error, id, label, onCheckedChange, required, ...inputProps}: CheckboxFieldProps) {
  return (
    <div>
      <label className="flex items-start gap-3 text-sm leading-5 text-[var(--ink)]" htmlFor={id}>
        <input
          aria-describedby={describedBy({description, error, id})}
          aria-invalid={Boolean(error)}
          className="mt-1 h-4 w-4 shrink-0 accent-[var(--blue)]"
          id={id}
          onChange={onCheckedChange}
          required={required}
          type="checkbox"
          {...inputProps}
        />
        <span><strong>{label}</strong>{required ? <span aria-hidden="true" className="ml-1 text-[var(--danger)]">*</span> : null}</span>
      </label>
      <div className="ml-7"><FieldMessages description={description} error={error} id={id} /></div>
    </div>
  );
}
