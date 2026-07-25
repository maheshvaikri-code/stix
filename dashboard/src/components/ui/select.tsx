"use client";

import { type SelectHTMLAttributes, forwardRef } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, placeholder, className = "", ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="mb-1 block text-sm font-semibold text-slate-700">
            {label}
          </label>
        )}
        <select
          ref={ref}
          className={`
            block w-full rounded-2xl border bg-white/80 px-3.5 py-2.5 text-sm text-slate-900 shadow-sm shadow-slate-200/60 backdrop-blur
            focus:outline-none focus:ring-2 focus:ring-offset-0
            ${
              error
                ? "border-rose-300 focus:border-rose-500 focus:ring-rose-500/30"
                : "border-white/70 focus:border-cyan-400 focus:ring-cyan-400/30"
            }
            disabled:bg-slate-50 disabled:text-slate-500
            ${className}
          `}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && <p className="mt-1 text-sm text-rose-600">{error}</p>}
      </div>
    );
  },
);

Select.displayName = "Select";
