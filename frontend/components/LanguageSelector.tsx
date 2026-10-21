'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Globe, ChevronDown, Check } from 'lucide-react';
import { useI18n, LANGUAGES, LanguageCode } from '../lib/i18n';

export default function LanguageSelector({ compact = false }: { compact?: boolean }) {
  const { language, setLanguage } = useI18n();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const current = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-xs font-semibold transition-all hover:scale-105 active:scale-95 shadow-sm"
        style={{
          background: 'var(--tag-bg)',
          borderColor: open ? 'var(--accent)' : 'var(--line)',
          color: 'var(--text)',
        }}
        title="Change Language (English, தமிழ், ಕನ್ನಡ, हिन्दी, Español, etc.)"
      >
        <span className="text-sm leading-none">{current.flag}</span>
        {!compact && <span className="font-medium">{current.nativeName}</span>}
        <ChevronDown size={13} className={`muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          className="absolute right-0 mt-2 w-48 rounded-2xl shadow-2xl border py-1.5 z-50 animate-fade-in-down backdrop-blur-xl"
          style={{
            background: 'var(--panel-bg)',
            borderColor: 'var(--line)',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
          }}
        >
          <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider muted border-b mb-1" style={{ borderColor: 'var(--line-subtle)' }}>
            Select Language
          </div>
          <div className="max-h-64 overflow-y-auto space-y-0.5 px-1">
            {LANGUAGES.map((lang) => {
              const active = lang.code === language;
              return (
                <button
                  key={lang.code}
                  onClick={() => {
                    setLanguage(lang.code);
                    setOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs transition-all ${
                    active ? 'font-bold' : 'hover:bg-blue-500/10'
                  }`}
                  style={{
                    color: active ? 'var(--accent)' : 'var(--text)',
                    background: active ? 'var(--tag-bg)' : 'transparent',
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm leading-none">{lang.flag}</span>
                    <span>{lang.nativeName}</span>
                    <span className="text-[10px] muted">({lang.name})</span>
                  </div>
                  {active && <Check size={14} className="text-blue-400" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
