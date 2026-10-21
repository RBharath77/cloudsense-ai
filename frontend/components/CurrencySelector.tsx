'use client';

import React, { useState, useRef, useEffect } from 'react';
import { DollarSign, ChevronDown, Check, Sparkles } from 'lucide-react';
import { useCurrency, CURRENCIES, CurrencyCode } from '../lib/currency';

export default function CurrencySelector({ compact = false }: { compact?: boolean }) {
  const { currency, setCurrency, detectedCurrency } = useCurrency();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const current = CURRENCIES[currency] || CURRENCIES.USD;

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
        title={`Global Currency Conversion: ${current.name} (${current.code})`}
      >
        <span className="text-sm leading-none">{current.flag}</span>
        <span className="font-bold text-sky-400">{current.symbol}</span>
        {!compact && <span className="font-semibold">{current.code}</span>}
        <ChevronDown size={13} className={`muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          className="absolute right-0 mt-2 w-56 rounded-2xl shadow-2xl border py-1.5 z-50 animate-fade-in-down backdrop-blur-xl"
          style={{
            background: 'var(--panel-bg)',
            borderColor: 'var(--line)',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
          }}
        >
          <div className="px-3 py-1.5 border-b mb-1 flex items-center justify-between" style={{ borderColor: 'var(--line-subtle)' }}>
            <span className="text-[10px] font-bold uppercase tracking-wider muted">Select Currency</span>
            <div className="flex items-center gap-1 text-[9px] text-emerald-400 font-semibold">
              <Sparkles size={9} />
              <span>Location Aware</span>
            </div>
          </div>
          <div className="max-h-64 overflow-y-auto space-y-0.5 px-1">
            {Object.values(CURRENCIES).map((item) => {
              const active = item.code === currency;
              const isPredicted = item.code === detectedCurrency;
              return (
                <button
                  key={item.code}
                  onClick={() => {
                    setCurrency(item.code as CurrencyCode);
                    setOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-xs transition-all ${
                    active ? 'font-bold' : 'hover:bg-blue-500/10'
                  }`}
                  style={{
                    color: active ? 'var(--accent)' : 'var(--text)',
                    background: active ? 'var(--tag-bg)' : 'transparent',
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm leading-none">{item.flag}</span>
                    <span className="font-bold text-sky-400 w-5 text-left">{item.symbol}</span>
                    <span>{item.code}</span>
                    {isPredicted && (
                      <span className="text-[9px] px-1.5 py-0.2 rounded-md font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        IP Match
                      </span>
                    )}
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
