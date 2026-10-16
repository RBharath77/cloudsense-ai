'use client';

import Shell from '../../components/Shell';
import { Page } from '../../components/Page';
import { useEffect, useState } from 'react';
import { api } from '../../lib/api';

interface OptimizationItem {
  id: string;
  problem: string;
  recommendation: string;
  monthly_saving: number;
  risk: string;
  confidence: number;
}

export default function Optimization() {
  const [items, setItems] = useState<OptimizationItem[]>([]);
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState<string | null>(null);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await api('/api/optimization');

      setItems(data);
    } catch (err) {
      console.error('Failed to load optimization recommendations:', err);
      setError('Failed to load optimization recommendations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const simulate = async (id: string) => {
    try {
      setSimulating(id);
      setMsg('');
      setError('');

      const result = await api(`/api/optimization/${id}/simulate`, {
        method: 'POST',
      });

      setMsg(result.message || 'Simulation completed successfully.');

      await load();
    } catch (err) {
      console.error('Simulation failed:', err);
      setError('Unable to run the simulation.');
    } finally {
      setSimulating(null);
    }
  };

  return (
    <Shell>
      <Page
        title="Optimization"
        subtitle="Prioritized savings recommendations with safe simulation."
      >
        <div className="space-y-4">
          {loading && (
            <div className="panel p-5">
              <p className="muted">Loading optimization recommendations...</p>
            </div>
          )}

          {error && (
            <div className="panel p-5">
              <p className="text-red-400">{error}</p>
            </div>
          )}

          {!loading && !error && items.length === 0 && (
            <div className="panel p-5">
              <p className="muted">
                No optimization recommendations are available.
              </p>
            </div>
          )}

          {!loading &&
            items.map((x) => (
              <div className="panel p-5" key={x.id}>
                <div className="flex justify-between gap-4">
                  <div>
                    <b>{x.problem}</b>

                    <p className="muted text-sm mt-1">
                      {x.recommendation}
                    </p>
                  </div>

                  <div className="text-right">
                    <b className="text-emerald-300">
                      ${Number(x.monthly_saving).toFixed(0)}/mo
                    </b>

                    <div className="muted text-xs">
                      {x.risk} risk ·{' '}
                      {(Number(x.confidence) * 100).toFixed(0)}% confidence
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => simulate(x.id)}
                  disabled={simulating === x.id}
                  className="mt-4 border border-slate-700 rounded-lg px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {simulating === x.id
                    ? 'Simulating...'
                    : 'Preview / Simulate'}
                </button>
              </div>
            ))}

          {msg && (
            <div className="mt-4 text-cyan-200">
              {msg}
            </div>
          )}
        </div>
      </Page>
    </Shell>
  );
}
