'use client';

import { useState } from 'react';
import { Calendar } from 'lucide-react';

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
  presets?: boolean;
}

const presetRanges = [
  { label: 'Last 24 hours', hours: 24 },
  { label: 'Last 7 days', hours: 7 * 24 },
  { label: 'Last 30 days', hours: 30 * 24 },
  { label: 'Last 90 days', hours: 90 * 24 },
];

export function DateRangePicker({
  startDate,
  endDate,
  onChange,
  presets = true,
}: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false);

  const applyPreset = (hours: number) => {
    const end = new Date();
    const start = new Date(end.getTime() - hours * 60 * 60 * 1000);
    onChange(start.toISOString(), end.toISOString());
    setIsOpen(false);
  };

  const formatDateDisplay = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50"
      >
        <Calendar className="h-4 w-4 text-gray-500" />
        <span>
          {formatDateDisplay(startDate)} - {formatDateDisplay(endDate)}
        </span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border z-20">
          {presets && (
            <div className="p-2 border-b">
              <p className="text-xs font-medium text-gray-500 mb-2 px-2">
                Quick Select
              </p>
              <div className="grid grid-cols-2 gap-1">
                {presetRanges.map((preset) => (
                  <button
                    key={preset.hours}
                    onClick={() => applyPreset(preset.hours)}
                    className="px-3 py-1.5 text-sm text-left rounded hover:bg-gray-100"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="p-3">
            <p className="text-xs font-medium text-gray-500 mb-2">Custom Range</p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Start</label>
                <input
                  type="datetime-local"
                  value={startDate.slice(0, 16)}
                  onChange={(e) =>
                    onChange(new Date(e.target.value).toISOString(), endDate)
                  }
                  className="w-full px-2 py-1 text-sm border rounded"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">End</label>
                <input
                  type="datetime-local"
                  value={endDate.slice(0, 16)}
                  onChange={(e) =>
                    onChange(startDate, new Date(e.target.value).toISOString())
                  }
                  className="w-full px-2 py-1 text-sm border rounded"
                />
              </div>
            </div>
          </div>

          <div className="p-2 border-t flex justify-end gap-2">
            <button
              onClick={() => setIsOpen(false)}
              className="px-3 py-1.5 text-sm rounded hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
