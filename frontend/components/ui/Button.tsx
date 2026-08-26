"use client";

import type {ButtonHTMLAttributes, ReactNode} from "react";

type ButtonVariant = "primary" | "secondary" | "outline" | "danger";
type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  isLoading?: boolean;
  size?: ButtonSize;
  variant?: ButtonVariant;
};

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: "border border-[var(--blue)] bg-[var(--blue)] text-white hover:bg-[#064e9c]",
  secondary: "border border-[#06366f] bg-[#06366f] text-white hover:bg-[#042a58]",
  outline: "border border-[var(--blue)] bg-white text-[var(--blue)] hover:bg-[var(--blue-soft)]",
  danger: "border border-[var(--danger)] bg-[var(--danger)] text-white hover:bg-[#8f1d14]"
};

const buttonSizeClasses: Record<ButtonSize, string> = {
  sm: "min-h-9 px-3 text-sm",
  md: "min-h-11 px-4 text-sm",
  lg: "min-h-12 px-5 text-base"
};

export function Button({
  children,
  className = "",
  disabled,
  isLoading = false,
  size = "md",
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <button
      className={[
        "inline-flex items-center justify-center gap-2 rounded-[var(--radius)] font-bold transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-60",
        buttonVariantClasses[variant],
        buttonSizeClasses[size],
        className
      ].join(" ")}
      disabled={disabled || isLoading}
      type={type}
      {...props}
    >
      {isLoading ? <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : null}
      {children}
    </button>
  );
}

type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  children: ReactNode;
  label: string;
};

export function IconButton({children, className = "", label, type = "button", ...props}: IconButtonProps) {
  return (
    <button
      aria-label={label}
      className={[
        "group relative inline-grid h-10 w-10 place-items-center rounded-[var(--radius)] border border-[var(--border)] bg-white",
        "text-[var(--navy)] transition-colors hover:bg-[var(--blue-soft)] disabled:cursor-not-allowed disabled:opacity-60",
        className
      ].join(" ")}
      type={type}
      {...props}
    >
      {children}
      <span className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 w-max max-w-48 -translate-x-1/2 rounded-[var(--radius)] bg-[#14243b] px-2 py-1 text-xs font-medium text-white opacity-0 shadow-[var(--shadow)] transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">{label}</span>
    </button>
  );
}
