import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-accent-600 text-white hover:bg-accent-700 focus-visible:outline-accent-600",
  secondary:
    "bg-white text-shelf-900 ring-1 ring-shelf-300 hover:bg-shelf-100 focus-visible:outline-shelf-400",
  ghost: "text-shelf-700 hover:bg-shelf-100 focus-visible:outline-shelf-400",
};

/** Классы кнопки — пригодятся и для ссылок, стилизованных под кнопку. */
export function buttonClass(variant: ButtonVariant = "primary", extra?: string): string {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium",
    "transition-colors focus-visible:outline-2 focus-visible:outline-offset-2",
    "disabled:cursor-not-allowed disabled:opacity-50",
    variants[variant],
    extra,
  );
}
