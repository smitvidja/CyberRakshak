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

// A filled button gets a soft shadow in its own colour so it reads as a raised
// control rather than a coloured rectangle; the outline variant gets a warm border
// so it does not glow blue against warm paper.
const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: "border border-[var(--blue)] bg-[var(--blue)] text-white shadow-[0_1px_2px_rgb(7_95_185_/_0.28),0_4px_12px_rgb(7_95_185_/_0.22)] hover:bg-[#064e9c] hover:border-[#064e9c]",
  secondary: "border border-[#06366f] bg-[#06366f] text-white shadow-[0_1px_2px_rgb(8_46_102_/_0.28),0_4px_12px_rgb(8_46_102_/_0.20)] hover:bg-[#042a58]",
  outline: "border border-[var(--border-strong)] bg-white text-[var(--navy)] shadow-[0_1px_2px_rgb(24_33_48_/_0.05)] hover:border-[var(--blue)] hover:bg-[var(--blue-soft)] hover:text-[var(--blue)]",
  danger: "border border-[var(--danger)] bg-[var(--danger)] text-white shadow-[0_1px_2px_rgb(180_35_24_/_0.28),0_4px_12px_rgb(180_35_24_/_0.20)] hover:bg-[#8f1d14]"
};

// Every size clears a 44px touch target at md and above - the portal is used on
// phones by people who are not steady with them.
const buttonSizeClasses: Record<ButtonSize, string> = {
  sm: "min-h-9 px-3.5 text-sm",
  md: "min-h-11 px-5 text-[15px]",
  lg: "min-h-[52px] px-7 text-base"
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
        "inline-flex items-center justify-center gap-2 rounded-[var(--radius-sm)] font-semibold tracking-[-0.005em] transition-colors",
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
