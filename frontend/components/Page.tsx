'use client';

import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';

export function Page({
  title,
  subtitle,
  children,
  action,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="space-y-6 animate-fade-in-up">
      <div
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b transition-colors"
        style={{ borderColor: 'var(--line-subtle)' }}
      >
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm mt-1.5 leading-relaxed" style={{ color: 'var(--muted)' }}>
              {subtitle}
            </p>
          )}
        </div>
        {action && <div className="flex items-center gap-3 transition-transform hover:scale-105">{action}</div>}
      </div>
      <div className="space-y-6">{children}</div>
    </div>
  );
}

export function DataList({
  path,
  render,
}: {
  path: string;
  render: (x: any) => React.ReactNode;
}) {
  const [data, setData] = useState<any[] | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    api(path)
      .then((x) => setData(Array.isArray(x) ? x : x.providers || []))
      .catch((e) => setErr(e.message));
  }, [path]);

  if (err) {
    return (
      <div className="panel p-6 border-red-500/30 text-red-400 bg-red-950/20 text-sm animate-fade-in-down">
        Unable to load data: {err}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="panel p-10 text-center text-sm muted flex flex-col items-center justify-center gap-3 animate-pulse-glow">
        <div
          className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
          style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}
        />
        <span className="font-medium">Streaming cloud intelligence…</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {data.map((x, i) => (
        <div
          className={`panel panel-hover p-4.5 animate-fade-in-up delay-${Math.min(i + 1, 5)}`}
          key={x.id || i}
        >
          {render(x)}
        </div>
      ))}
    </div>
  );
}
