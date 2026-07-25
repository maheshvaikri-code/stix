"use client";

import { type InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = "", ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="mb-1 block text-sm font-semibold text-slate-700">
            {label}
          </label>
        )}
        <input
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
        />
        {error && <p className="mt-1 text-sm text-rose-600">{error}</p>}
        {helperText && !error && (
          <p className="mt-1 text-sm text-slate-500">{helperText}</p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";

// Textarea variant
interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = "", ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="mb-1 block text-sm font-semibold text-slate-700">
            {label}
          </label>
        )}
        <textarea
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
        />
        {error && <p className="mt-1 text-sm text-rose-600">{error}</p>}
      </div>
    );
  },
);

Textarea.displayName = "Textarea";
