"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize);
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  const canGoPrev = page > 1;
  const canGoNext = page < totalPages;

  if (total === 0) return null;

  return (
    <div className="flex flex-col gap-3 border-t border-slate-200/70 bg-white/60 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm text-slate-500">
        Showing <span className="font-medium">{start}</span> to{" "}
        <span className="font-medium">{end}</span> of{" "}
        <span className="font-medium">{total}</span> results
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={!canGoPrev}
          className={`
            rounded-2xl border p-2 transition-colors
            ${
              canGoPrev
                ? "border-white/70 bg-white/80 text-slate-700 hover:bg-cyan-50 hover:text-cyan-700"
                : "cursor-not-allowed border-slate-200 text-slate-300"
            }
          `}
        >
          <ChevronLeft className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
            let pageNum: number;
            if (totalPages <= 5) {
              pageNum = i + 1;
            } else if (page <= 3) {
              pageNum = i + 1;
            } else if (page >= totalPages - 2) {
              pageNum = totalPages - 4 + i;
            } else {
              pageNum = page - 2 + i;
            }

            return (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                className={`
                  rounded-2xl px-3 py-1.5 text-sm font-semibold transition-colors
                  ${
                    pageNum === page
                      ? "bg-slate-950 text-white shadow-lg shadow-slate-900/15"
                      : "text-slate-700 hover:bg-white"
                  }
                `}
              >
                {pageNum}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={!canGoNext}
          className={`
            rounded-2xl border p-2 transition-colors
            ${
              canGoNext
                ? "border-white/70 bg-white/80 text-slate-700 hover:bg-cyan-50 hover:text-cyan-700"
                : "cursor-not-allowed border-slate-200 text-slate-300"
            }
          `}
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
