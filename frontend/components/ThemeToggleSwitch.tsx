'use client';

import React from 'react';
import { Sun, Moon, Sparkles } from 'lucide-react';
import { useTheme } from '../lib/theme';

export default function ThemeToggleSwitch({ className = '' }: { className?: string }) {
  const { theme, toggleTheme, mounted } = useTheme();
  const isDark = mounted ? theme === 'dark' : true;

  return (
    <button
      onClick={toggleTheme}
      type="button"
      role="switch"
      aria-checked={!isDark}
      title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      className={`group relative inline-flex h-8 w-16 flex-shrink-0 cursor-pointer items-center rounded-full p-1 transition-all duration-300 ease-in-out focus:outline-none shadow-inner border ${className}`}
      style={{
        background: isDark
          ? 'linear-gradient(135deg, #1E3A8A 0%, #0A142F 100%)'
          : 'linear-gradient(135deg, #5AA9E6 0%, #BEE3F8 100%)',
        borderColor: isDark ? 'rgba(65, 105, 225, 0.6)' : 'rgba(31, 58, 95, 0.3)',
        boxShadow: isDark
          ? 'inset 0 2px 4px rgba(0,0,0,0.6), 0 0 14px rgba(65,105,225,0.4)'
          : 'inset 0 2px 4px rgba(31,58,95,0.15), 0 0 14px rgba(90,169,230,0.35)',
      }}
    >
      {/* Track Icons Background */}
      <span className="absolute inset-0 flex items-center justify-between px-2 text-[10px] pointer-events-none select-none">
        <Moon
          size={13}
          className={`transition-all duration-300 ${
            isDark ? 'text-white opacity-95 scale-100' : 'text-slate-400 opacity-20 scale-75'
          }`}
        />
        <Sun
          size={13}
          className={`transition-all duration-300 ${
            !isDark ? 'text-amber-500 opacity-100 scale-100' : 'text-slate-500 opacity-20 scale-75'
          }`}
        />
      </span>

      {/* Sliding Knob with Icons */}
      <span
        className={`pointer-events-none relative inline-flex h-6 w-6 transform items-center justify-center rounded-full shadow-lg transition-all duration-300 ease-out ${
          isDark ? 'translate-x-0' : 'translate-x-8'
        }`}
        style={{
          background: isDark
            ? 'linear-gradient(135deg, #FFFFFF 0%, #E0E7FF 100%)'
            : 'linear-gradient(135deg, #FFFFFF 0%, #FFFBEB 100%)',
          boxShadow: isDark
            ? '0 0 12px rgba(65, 105, 225, 0.8), 0 2px 4px rgba(0,0,0,0.5)'
            : '0 0 10px rgba(245, 158, 11, 0.4), 0 2px 4px rgba(0,0,0,0.15)',
        }}
      >
        {isDark ? (
          <Moon size={13} className="text-[#4169E1] transform transition-transform duration-300 -rotate-12" />
        ) : (
          <Sun size={13} className="text-amber-500 transform transition-transform duration-300 rotate-90" />
        )}
      </span>

    </button>
  );
}
