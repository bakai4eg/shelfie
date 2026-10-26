import { useId, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string;
}

/** Поле формы с подписью, подсказкой и ошибкой — одинаково во всех экранах. */
export default function Field({ label, hint, error, className, id, ...props }: FieldProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={fieldId} className="block text-sm font-medium text-shelf-800">
        {label}
      </label>
      <input
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          "w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900",
          "placeholder:text-shelf-400 focus:border-accent-600 focus:outline-2",
          "focus:outline-offset-2 focus:outline-accent-600",
          error && "border-red-500 focus:border-red-500 focus:outline-red-500",
          className,
        )}
        {...props}
      />
      {error ? (
        <p id={`${fieldId}-error`} className="text-xs text-red-600">
          {error}
        </p>
      ) : hint ? (
        <p id={`${fieldId}-hint`} className="text-xs text-shelf-500">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
