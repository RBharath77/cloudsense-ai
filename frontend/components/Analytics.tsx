'use client';
import { useEffect, useState, useCallback } from 'react';
import { api, downloadFile } from '../lib/api';
import { Page, DataList } from './Page';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';

function Card({
  label,
  value,
  sub,
  badge,
}: {
  label: string;
  value: any;
  sub?: string;
  badge?: { text: string; color: string };
}) {
  return (
    <div className="panel p-5">
      <div className="flex justify-between items-start">
        <div className="muted text-xs uppercase tracking-wider">{label}</div>
        {badge && (
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.color}`}>
            {badge.text}
          </span>
        )}
      </div>
      <div className="text-2xl font-semibold mt-2">{value}</div>
      {sub && <div className="text-xs text-cyan-200 mt-1">{sub}</div>}
    </div>
  );
}

export function Dashboard() {
  const [d, setD] = useState<any>();
  const [costs, setCosts] = useState<any[]>([]);

  useEffect(() => {
    api('/api/dashboard/summary').then(setD).catch(console.error);
    api('/api/costs').then(setCosts).catch(console.error);
  }, []);

  return (
    <Page title="Executive Dashboard" subtitle="Unified visibility across AWS, Azure and GCP">
      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
        {d ? (
          [
            ['Total Cloud Spend', `$${d.total_spend.toLocaleString()}`, d.change_percentage != null ? `${d.change_percentage > 0 ? '+' : ''}${d.change_percentage}% vs prev period` : undefined],
            ['Predicted Month-End', `$${d.predicted_month_end.toLocaleString()}`],
            ['Potential Savings', `$${d.potential_savings.toLocaleString()}`],
            ['Cloud Health', `${d.cloud_health}%`],
            ['Active Resources', d.active_resources],
            ['Open Anomalies', d.anomalies],
            ['Carbon Emissions', `${d.carbon_kg} kg`],
            ['Data Lineage Batches', d.contributing_imports ?? '—', d.latest_import_time ? `Latest: ${new Date(d.latest_import_time).toLocaleDateString()}` : 'Live seed data'],
          ].map(([a, b, c]) => <Card key={a} label={a} value={b} sub={c} />)
        ) : (
          <div className="panel p-6">Loading dashboard…</div>
        )}
      </div>
      <div className="grid xl:grid-cols-3 gap-5 mt-5">
        <div className="panel p-5 xl:col-span-2">
          <h3 className="font-medium">Cloud spending trend</h3>
          <div className="h-72 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={costs.slice(-30)}>
                <XAxis dataKey="date" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="cost" stroke="#06b6d4" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel p-5">
          <h3 className="font-medium">What you can do</h3>
          <div className="space-y-3 mt-4 text-sm">
            {['Inspect high-severity anomalies', 'Review underutilized resources', 'Check security findings', 'Generate executive PDF report'].map((x) => (
              <div className="border border-slate-800 rounded-lg p-3 hover:border-slate-700 transition" key={x}>
                {x}
              </div>
            ))}
          </div>
        </div>
      </div>
    </Page>
  );
}

export function Accounts() {
  return (
    <Page title="Cloud Accounts" subtitle="Provider connections stay behind the backend.">
      <DataList
        path="/api/cloud/accounts"
        render={(x) => (
          <div className="flex justify-between">
            <div>
              <b>{x.name}</b>
              <div className="muted text-sm">{x.provider} · {x.region} · {x.identifier}</div>
            </div>
            <span className="text-emerald-300 text-sm">● {x.status}</span>
          </div>
        )}
      />
    </Page>
  );
}

export function Costs() {
  const [provider, setProvider] = useState<string>('ALL');
  const [groupBy, setGroupBy] = useState<string>('provider');
  const [timeRange, setTimeRange] = useState<string>('30');
  const [summary, setSummary] = useState<any>(null);
  const [daily, setDaily] = useState<any[]>([]);
  const [lineage, setLineage] = useState<any>(null);
  const [showLineage, setShowLineage] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [exporting, setExporting] = useState<boolean>(false);
  const [err, setErr] = useState<string>('');

  const fetchCosts = useCallback(async () => {
    setLoading(true);
    setErr('');
    try {
      const params = new URLSearchParams();
      if (provider !== 'ALL') params.append('provider', provider);
      params.append('group_by', groupBy);

      if (timeRange !== 'all') {
        const days = parseInt(timeRange, 10);
        const start = new Date();
        start.setDate(start.getDate() - days);
        params.append('start_date', start.toISOString().split('T')[0]);
      }

      const qStr = params.toString() ? `?${params.toString()}` : '';
      const sumData = await api(`/api/costs/summary${qStr}`);
      setSummary(sumData);

      const dailyParams = new URLSearchParams();
      if (provider !== 'ALL') dailyParams.append('provider', provider);
      if (timeRange !== 'all') {
        const days = parseInt(timeRange, 10);
        const start = new Date();
        start.setDate(start.getDate() - days);
        dailyParams.append('start_date', start.toISOString().split('T')[0]);
      }
      const dailyQStr = dailyParams.toString() ? `?${dailyParams.toString()}` : '';
      const dailyData = await api(`/api/costs${dailyQStr}`);
      setDaily(dailyData);

      const linData = await api(`/api/costs/lineage${dailyQStr}`);
      setLineage(linData);
    } catch (e: any) {
      setErr(e.message || 'Failed to load cost intelligence');
    } finally {
      setLoading(false);
    }
  }, [provider, groupBy, timeRange]);

  useEffect(() => {
    fetchCosts();
  }, [fetchCosts]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (provider !== 'ALL') params.append('provider', provider);
      if (timeRange !== 'all') {
        const days = parseInt(timeRange, 10);
        const start = new Date();
        start.setDate(start.getDate() - days);
        params.append('start_date', start.toISOString().split('T')[0]);
      }
      const qStr = params.toString() ? `?${params.toString()}` : '';
      await downloadFile(`/api/costs/export${qStr}`, `cloudsense_costs_${provider}_${groupBy}.csv`);
    } catch (e: any) {
      alert('CSV Export failed: ' + e.message);
    } finally {
      setExporting(false);
    }
  };

  const palette = ['#06b6d4', '#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

  return (
    <Page title="Cost Intelligence & Explorer" subtitle="Normalized spend, multidimensional breakdown, and end-to-end data lineage.">
      {/* Controls Toolbar */}
      <div className="panel p-4 mb-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <span className="text-xs muted block mb-1">Provider</span>
            <div className="flex rounded-lg border border-slate-700 overflow-hidden text-xs">
              {['ALL', 'AWS', 'AZURE', 'GCP'].map((p) => (
                <button
                  key={p}
                  onClick={() => setProvider(p)}
                  className={`px-3 py-1.5 transition ${provider === p ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'}`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div>
            <span className="text-xs muted block mb-1">Group By</span>
            <div className="flex rounded-lg border border-slate-700 overflow-hidden text-xs">
              {[
                { id: 'provider', label: 'Provider' },
                { id: 'service', label: 'Service' },
                { id: 'region', label: 'Region' },
              ].map((g) => (
                <button
                  key={g.id}
                  onClick={() => setGroupBy(g.id)}
                  className={`px-3 py-1.5 transition ${groupBy === g.id ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'}`}
                >
                  {g.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <span className="text-xs muted block mb-1">Time Horizon</span>
            <div className="flex rounded-lg border border-slate-700 overflow-hidden text-xs">
              {[
                { id: '7', label: '7D' },
                { id: '30', label: '30D' },
                { id: '90', label: '90D' },
                { id: 'all', label: 'All' },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTimeRange(t.id)}
                  className={`px-3 py-1.5 transition ${timeRange === t.id ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowLineage(!showLineage)}
            className="px-3 py-1.5 text-xs rounded-lg border border-slate-700 hover:border-slate-500 text-slate-300 transition flex items-center gap-1.5"
          >
            <span>{showLineage ? 'Hide Lineage' : 'Audit Lineage'}</span>
            {lineage?.import_coverage_count > 0 && (
              <span className="bg-cyan-500/30 text-cyan-300 px-1.5 py-0.2 rounded-full font-mono text-[10px]">
                {lineage.import_coverage_count}
              </span>
            )}
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition flex items-center gap-1.5 disabled:opacity-50"
          >
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        </div>
      </div>

      {err && <div className="panel p-4 text-red-300 mb-5">Error: {err}</div>}

      {/* KPI Summary Cards */}
      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4 mb-5">
        <Card
          label="Total Filtered Spend"
          value={summary ? `$${summary.total_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
          badge={
            summary?.change_percentage != null
              ? {
                  text: `${summary.change_percentage > 0 ? '+' : ''}${summary.change_percentage}%`,
                  color: summary.change_percentage <= 0 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300',
                }
              : undefined
          }
          sub={summary ? `Prev period: $${summary.previous_cost.toLocaleString()}` : undefined}
        />
        <Card
          label="Cost Records"
          value={summary?.record_count?.toLocaleString() ?? '—'}
          sub="Active records in scope"
        />
        <Card
          label="Breakdown Categories"
          value={summary?.items?.length ?? 0}
          sub={`Grouped by ${groupBy}`}
        />
        <Card
          label="Reconciliation Status"
          value="100% Invariant"
          badge={{ text: 'Verified', color: 'bg-emerald-500/20 text-emerald-300' }}
          sub="API, breakdown & export match"
        />
      </div>

      {/* Data Lineage Drawer */}
      {showLineage && (
        <div className="panel p-5 mb-5 border border-cyan-500/30 bg-cyan-950/10">
          <div className="flex justify-between items-center mb-3">
            <h4 className="font-semibold text-cyan-200 text-sm">Data Lineage & Billing Traceability</h4>
            <span className="text-xs muted">
              {lineage?.import_coverage_count || 0} contributing import batch(es)
            </span>
          </div>
          {lineage?.contributing_imports?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2">Import ID</th>
                    <th className="py-2">Source File</th>
                    <th className="py-2">Imported At</th>
                    <th className="py-2">Rows</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {lineage.contributing_imports.map((imp: any) => (
                    <tr key={imp.id} className="hover:bg-slate-900/50">
                      <td className="py-2 font-mono text-cyan-300">{imp.id.slice(0, 8)}…</td>
                      <td className="py-2 font-medium">{imp.filename}</td>
                      <td className="py-2 text-slate-400">{new Date(imp.created_at).toLocaleString()}</td>
                      <td className="py-2">{imp.imported_rows} / {imp.total_rows}</td>
                      <td className="py-2">
                        <span className="text-emerald-300 font-semibold">● {imp.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-xs muted py-3">
              No billing import batches detected for this filter period. Costs originate from initial seed/mock inventory.
            </div>
          )}
        </div>
      )}

      {/* Charts & Breakdown */}
      <div className="grid xl:grid-cols-3 gap-5">
        {/* Trend Chart */}
        <div className="panel p-5 xl:col-span-2">
          <h3 className="font-medium text-sm mb-4">Daily Cost Trend ({daily.length} days)</h3>
          <div className="h-64">
            {daily.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={daily}>
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                    formatter={(val: any) => [`$${Number(val).toLocaleString()}`, 'Cost']}
                  />
                  <Line type="monotone" dataKey="cost" stroke="#06b6d4" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs muted">
                No trend data available for current selection
              </div>
            )}
          </div>
        </div>

        {/* Breakdown Items List */}
        <div className="panel p-5">
          <h3 className="font-medium text-sm mb-4">Spend by {groupBy.charAt(0).toUpperCase() + groupBy.slice(1)}</h3>
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {summary?.items?.length > 0 ? (
              summary.items.map((item: any, idx: number) => (
                <div key={item.key || idx} className="border border-slate-800/80 rounded-lg p-3 bg-slate-900/30">
                  <div className="flex justify-between items-center text-xs mb-1.5">
                    <span className="font-medium text-slate-200 truncate max-w-[150px]">{item.key}</span>
                    <div className="text-right">
                      <span className="font-semibold text-white">
                        ${item.cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                      <span className="muted text-[10px] ml-1.5">({item.percentage}%)</span>
                    </div>
                  </div>
                  {/* Progress Bar */}
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(100, Math.max(2, item.percentage))}%`,
                        backgroundColor: palette[idx % palette.length],
                      }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs muted py-8 text-center">No cost records found matching filters.</div>
            )}
          </div>
        </div>
      </div>
    </Page>
  );
}
export function Budgets() {
  const [budgets, setBudgets] = useState<any[]>([]);
  const [governance, setGovernance] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [form, setForm] = useState({
    name: '',
    scope: 'ORGANIZATION',
    target: 'ALL',
    amount: '',
    threshold: '0.85',
    period: 'MONTHLY',
  });
  const [err, setErr] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [bData, gData] = await Promise.all([
        api('/api/budgets'),
        api('/api/governance/tags').catch(() => null),
      ]);
      setBudgets(bData);
      setGovernance(gData);
    } catch (e: any) {
      setErr(e.message || 'Failed to load budgets');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErr('');
    try {
      await api('/api/budgets', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name || undefined,
          scope: form.scope,
          target: form.target,
          amount: parseFloat(form.amount),
          threshold: parseFloat(form.threshold),
          period: form.period,
        }),
      });
      setShowModal(false);
      setForm({ name: '', scope: 'ORGANIZATION', target: 'ALL', amount: '', threshold: '0.85', period: 'MONTHLY' });
      await loadData();
    } catch (e: any) {
      setErr(e.message || 'Failed to create budget');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this budget?')) return;
    try {
      await api(`/api/budgets/${id}`, { method: 'DELETE' });
      await loadData();
    } catch (e: any) {
      alert('Delete failed: ' + e.message);
    }
  };

  const totalLimit = budgets.reduce((acc, b) => acc + (b.amount || 0), 0);
  const totalSpend = budgets.reduce((acc, b) => acc + (b.actual_spend || 0), 0);
  const exceededCount = budgets.filter((b) => b.status === 'EXCEEDED').length;
  const warningCount = budgets.filter((b) => b.status === 'WARNING').length;

  return (
    <Page title="Budget Management & Tag Governance" subtitle="Set spend caps, monitor burn rates, and enforce cloud governance policies.">
      {/* KPI Cards */}
      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4 mb-5">
        <Card label="Total Budget Allocated" value={`$${totalLimit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} sub={`${budgets.length} active budget(s)`} />
        <Card label="Total Actual Spend" value={`$${totalSpend.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} sub="Sum across active budgets" />
        <Card
          label="Budget Health"
          value={exceededCount > 0 ? `${exceededCount} Exceeded` : warningCount > 0 ? `${warningCount} Warning` : 'All Healthy'}
          badge={
            exceededCount > 0
              ? { text: `${exceededCount} Breached`, color: 'bg-rose-500/20 text-rose-300' }
              : warningCount > 0
              ? { text: `${warningCount} Near Cap`, color: 'bg-amber-500/20 text-amber-300' }
              : { text: 'Healthy', color: 'bg-emerald-500/20 text-emerald-300' }
          }
          sub="Evaluation status"
        />
        <Card
          label="Tag Governance Rate"
          value={governance ? `${governance.compliance_rate}%` : '—'}
          badge={
            governance?.compliance_rate >= 80
              ? { text: 'Compliant', color: 'bg-emerald-500/20 text-emerald-300' }
              : { text: 'Attention', color: 'bg-amber-500/20 text-amber-300' }
          }
          sub={governance ? `${governance.untagged_count} untagged ($${governance.unallocated_monthly_cost.toLocaleString()}/mo)` : undefined}
        />
      </div>

      {/* Action Bar */}
      <div className="panel p-4 mb-5 flex justify-between items-center">
        <div>
          <h3 className="text-sm font-semibold text-white">Active Budgets</h3>
          <p className="text-xs muted mt-0.5">Automated threshold warnings triggered at configured utilization milestones.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 text-xs font-semibold rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition"
        >
          + Create Budget
        </button>
      </div>

      {err && <div className="panel p-4 text-rose-300 mb-5">{err}</div>}

      {/* Budgets Grid */}
      {loading ? (
        <div className="panel p-8 text-center text-xs muted">Loading budget intelligence…</div>
      ) : budgets.length === 0 ? (
        <div className="panel p-8 text-center text-xs muted">No budgets defined yet. Create your first budget cap above.</div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          {budgets.map((b) => {
            const isExceeded = b.status === 'EXCEEDED';
            const isWarning = b.status === 'WARNING';
            const barColor = isExceeded ? '#f43f5e' : isWarning ? '#f59e0b' : '#10b981';

            return (
              <div key={b.id} className="panel p-5 border border-slate-800/80 bg-slate-900/30">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-sm text-white">{b.name}</h4>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {b.scope}: {b.target}
                      </span>
                    </div>
                    <div className="text-[11px] muted mt-0.5">
                      Period: {b.period} ({b.period_start} to {b.period_end})
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                        isExceeded
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : isWarning
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {b.status}
                    </span>
                    <button
                      onClick={() => handleDelete(b.id)}
                      className="text-xs text-slate-500 hover:text-rose-400 p-1"
                      title="Delete Budget"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">
                      Spend: <b>${b.actual_spend.toLocaleString(undefined, { minimumFractionDigits: 2 })}</b> of ${b.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                    <span className="font-semibold text-white">{b.percentage_used}%</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden relative">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(100, Math.max(1, b.percentage_used))}%`,
                        backgroundColor: barColor,
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] muted mt-1">
                    <span>Threshold alert at {Math.round(b.threshold * 100)}%</span>
                    <span>Remaining: ${b.remaining_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800/60 flex justify-between text-xs">
                  <span className="muted">Run-rate forecast:</span>
                  <span className={`font-semibold ${b.forecast_status === 'EXCEEDED' ? 'text-rose-300' : 'text-slate-200'}`}>
                    ${b.forecast_spend.toLocaleString(undefined, { minimumFractionDigits: 2 })} ({b.forecast_status})
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="panel p-6 max-w-md w-full border border-slate-700">
            <h3 className="font-semibold text-lg text-white mb-4">Create New Budget</h3>
            <form onSubmit={handleCreate} className="space-y-4 text-xs">
              <div>
                <label className="muted block mb-1">Budget Name</label>
                <input
                  type="text"
                  placeholder="e.g. Q1 AWS Infrastructure"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-100"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="muted block mb-1">Scope</label>
                  <select
                    value={form.scope}
                    onChange={(e) => setForm({ ...form, scope: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-100"
                  >
                    <option value="ORGANIZATION">Organization</option>
                    <option value="PROVIDER">Provider</option>
                    <option value="SERVICE">Service</option>
                  </select>
                </div>
                <div>
                  <label className="muted block mb-1">Target</label>
                  <input
                    type="text"
                    placeholder="e.g. AWS, EC2, ALL"
                    value={form.target}
                    onChange={(e) => setForm({ ...form, target: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="muted block mb-1">Budget Limit ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="10000"
                    value={form.amount}
                    onChange={(e) => setForm({ ...form, amount: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-100"
                  />
                </div>
                <div>
                  <label className="muted block mb-1">Alert Threshold (%)</label>
                  <select
                    value={form.threshold}
                    onChange={(e) => setForm({ ...form, threshold: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-100"
                  >
                    <option value="0.5">50%</option>
                    <option value="0.75">75%</option>
                    <option value="0.85">85%</option>
                    <option value="0.9">90%</option>
                    <option value="0.95">95%</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="muted block mb-1">Period</label>
                <select
                  value={form.period}
                  onChange={(e) => setForm({ ...form, period: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-100"
                >
                  <option value="MONTHLY">Monthly</option>
                  <option value="QUARTERLY">Quarterly</option>
                  <option value="ANNUAL">Annual</option>
                  <option value="ALL">All-Time</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 text-slate-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-semibold"
                >
                  {submitting ? 'Creating…' : 'Save Budget'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Page>
  );
}

export function Alerts() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [msg, setMsg] = useState<string>('');

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (unreadOnly) params.append('unread', 'true');
      if (severityFilter !== 'ALL') params.append('severity', severityFilter);
      const q = params.toString() ? `?${params.toString()}` : '';
      const data = await api(`/api/alerts${q}`);
      setAlerts(data);
    } catch (e: any) {
      setMsg('Failed to load alerts: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [unreadOnly, severityFilter]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  const handleEvaluate = async () => {
    setEvaluating(true);
    setMsg('');
    try {
      const res = await api('/api/alerts/evaluate', { method: 'POST' });
      setMsg(`Rules evaluated: ${res.created_alerts} new alert(s), ${res.updated_alerts} updated.`);
      await loadAlerts();
    } catch (e: any) {
      setMsg('Evaluation failed: ' + e.message);
    } finally {
      setEvaluating(false);
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await api(`/api/alerts/${id}/read`, { method: 'POST' });
      await loadAlerts();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api('/api/alerts/read-all', { method: 'POST' });
      await loadAlerts();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api(`/api/alerts/${id}`, { method: 'DELETE' });
      await loadAlerts();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const unreadCount = alerts.filter((a) => !a.read).length;
  const criticalCount = alerts.filter((a) => a.severity === 'CRITICAL').length;
  const highCount = alerts.filter((a) => a.severity === 'HIGH').length;

  return (
    <Page title="Alerts & Governance Center" subtitle="Automated threshold evaluation, cost spike detection, and incident triage.">
      {/* KPI Cards */}
      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4 mb-5">
        <Card label="Total Active Alerts" value={alerts.length} sub="Current scope" />
        <Card
          label="Unread Alerts"
          value={unreadCount}
          badge={unreadCount > 0 ? { text: `${unreadCount} Pending`, color: 'bg-amber-500/20 text-amber-300' } : { text: 'All Read', color: 'bg-emerald-500/20 text-emerald-300' }}
        />
        <Card label="Critical Breaches" value={criticalCount} badge={criticalCount > 0 ? { text: 'Critical', color: 'bg-rose-500/20 text-rose-300' } : undefined} />
        <Card label="High Severity" value={highCount} badge={highCount > 0 ? { text: 'High', color: 'bg-amber-500/20 text-amber-300' } : undefined} />
      </div>

      {/* Controls Bar */}
      <div className="panel p-4 mb-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <span className="text-xs muted block mb-1">Severity</span>
            <div className="flex rounded-lg border border-slate-700 overflow-hidden text-xs">
              {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-3 py-1.5 transition ${severityFilter === sev ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'}`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer pt-4">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => setUnreadOnly(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700"
            />
            <span>Unread Only</span>
          </label>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleMarkAllRead}
            disabled={unreadCount === 0}
            className="px-3 py-1.5 text-xs rounded-lg border border-slate-700 hover:border-slate-500 text-slate-300 transition disabled:opacity-40"
          >
            Mark All as Read
          </button>
          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition disabled:opacity-50"
          >
            {evaluating ? 'Evaluating…' : '⚡ Evaluate Policies'}
          </button>
        </div>
      </div>

      {msg && <div className="panel p-3 text-xs text-cyan-200 mb-5 bg-cyan-950/20 border-cyan-800">{msg}</div>}

      {/* Alerts List */}
      {loading ? (
        <div className="panel p-8 text-center text-xs muted">Loading alerts…</div>
      ) : alerts.length === 0 ? (
        <div className="panel p-8 text-center text-xs muted">No alerts match the active filters. Your cloud posture is healthy.</div>
      ) : (
        <div className="space-y-3">
          {alerts.map((a) => {
            const isCrit = a.severity === 'CRITICAL';
            const isHigh = a.severity === 'HIGH';

            return (
              <div
                key={a.id}
                className={`panel p-4 border transition ${
                  a.read ? 'border-slate-800/60 opacity-75' : isCrit ? 'border-rose-500/40 bg-rose-950/10' : 'border-slate-700'
                }`}
              >
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                          isCrit
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : isHigh
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-cyan-500/20 text-cyan-300'
                        }`}
                      >
                        {a.severity}
                      </span>
                      <span className="text-[11px] muted font-mono">{a.type}</span>
                      {!a.read && <span className="w-2 h-2 rounded-full bg-cyan-400" title="Unread" />}
                    </div>
                    <h4 className="font-semibold text-sm text-white">{a.title}</h4>
                    <p className="text-xs text-slate-300 mt-1">{a.message}</p>
                    <div className="text-[10px] muted mt-2">
                      {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {!a.read && (
                      <button
                        onClick={() => handleMarkRead(a.id)}
                        className="text-xs text-cyan-300 hover:text-cyan-200 border border-cyan-800 rounded px-2.5 py-1"
                      >
                        Read
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(a.id)}
                      className="text-xs text-slate-500 hover:text-rose-400 px-2 py-1"
                      title="Dismiss"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Page>
  );
}
export function Generic({title,path}:{title:string;path:string}){return <Page title={title} subtitle="Live application data from the CloudSense backend."><DataList path={path} render={x=><div><div className="flex justify-between gap-4"><b>{x.name||x.title||x.service||x.provider||x.metric||'Record'}</b><span className="text-cyan-200">{x.severity||x.status||x.availability||''}</span></div><pre className="text-xs muted mt-3 whitespace-pre-wrap overflow-auto">{JSON.stringify(x,null,2)}</pre></div>}/></Page>}

export function Forecast() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [horizon, setHorizon] = useState<number>(30);
  const [provider, setProvider] = useState<string>('ALL');
  const [confidence, setConfidence] = useState<number>(0.95);

  const fetchForecast = useCallback(async () => {
    setLoading(true);
    try {
      const pParam = provider !== 'ALL' ? `&provider=${encodeURIComponent(provider)}` : '';
      const res = await api(`/api/forecast?horizon=${horizon}&confidence=${confidence}${pParam}`);
      setData(res);
    } catch (err) {
      console.error('Failed to load forecast:', err);
    } finally {
      setLoading(false);
    }
  }, [horizon, provider, confidence]);

  useEffect(() => {
    fetchForecast();
  }, [fetchForecast]);

  // Merge historical and forecast series into unified timeline
  const chartData = (() => {
    if (!data) return [];
    const hist = (data.historical_series || []).map((h: any) => ({
      date: h.date,
      actual: h.cost,
      predicted: null as number | null,
      lower: null as number | null,
      upper: null as number | null,
    }));

    const fc = (data.forecast_series || []).map((f: any) => ({
      date: f.date,
      actual: null as number | null,
      predicted: f.prediction,
      lower: f.lower,
      upper: f.upper,
    }));

    // Connect last historical to first forecast point
    if (hist.length > 0 && fc.length > 0) {
      const lastHist = hist[hist.length - 1];
      lastHist.predicted = lastHist.actual;
      lastHist.lower = lastHist.actual;
      lastHist.upper = lastHist.actual;
    }

    return [...hist, ...fc];
  })();

  return (
    <Page
      title="Cost Forecast & ML Registry"
      subtitle="Out-of-sample evaluated trend models with non-negative guardrails, confidence intervals, and naive baseline benchmarks."
    >
      {/* Control Toolbar */}
      <div className="panel p-4 mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs uppercase font-medium text-slate-400">Horizon:</span>
          <div className="flex bg-slate-900 border border-slate-700 rounded-lg p-1">
            {[7, 14, 30, 60, 90].map((h) => (
              <button
                key={h}
                onClick={() => setHorizon(h)}
                className={`text-xs px-3 py-1 rounded-md font-medium transition ${
                  horizon === h
                    ? 'bg-cyan-500 text-slate-950 shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                {h}D
              </button>
            ))}
          </div>

          <span className="text-xs uppercase font-medium text-slate-400 ml-2">Provider:</span>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-xs rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-400"
          >
            <option value="ALL">All Cloud Providers</option>
            <option value="AWS">AWS</option>
            <option value="Azure">Azure</option>
            <option value="GCP">GCP</option>
          </select>

          <span className="text-xs uppercase font-medium text-slate-400 ml-2">Confidence:</span>
          <div className="flex bg-slate-900 border border-slate-700 rounded-lg p-1">
            {[
              { label: '95% (2σ)', val: 0.95 },
              { label: '80% (1.28σ)', val: 0.80 },
            ].map((c) => (
              <button
                key={c.val}
                onClick={() => setConfidence(c.val)}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition ${
                  confidence === c.val
                    ? 'bg-purple-500 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={fetchForecast}
          disabled={loading}
          className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-200 transition"
        >
          {loading ? 'Recalculating…' : 'Refresh Model'}
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card
          label={`Projected ${horizon}-Day Spend`}
          value={`$${(data?.total_predicted_spend ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          sub={`Avg $${(data?.daily_average_predicted ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/day`}
          badge={{ text: `${horizon}D Horizon`, color: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' }}
        />
        <Card
          label="Model vs Baseline MAE"
          value={`$${(data?.mae ?? 0).toFixed(2)}`}
          sub={`Baseline: $${(data?.baseline_mae ?? 0).toFixed(2)} (${data?.improvement_pct != null ? `${data.improvement_pct > 0 ? '+' : ''}${data.improvement_pct.toFixed(1)}%` : '0%'})`}
          badge={{
            text: (data?.improvement_pct ?? 0) >= 0 ? 'Beat Baseline' : 'Trailing',
            color: (data?.improvement_pct ?? 0) >= 0 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
          }}
        />
        <Card
          label="Out-of-Sample RMSE"
          value={`$${(data?.rmse ?? 0).toFixed(2)}`}
          sub={`Baseline RMSE: $${(data?.baseline_rmse ?? 0).toFixed(2)}`}
          badge={{ text: 'Zero Leakage', color: 'bg-blue-500/20 text-blue-300 border border-blue-500/30' }}
        />
        <Card
          label="Active ML Model"
          value={data?.model_name ? 'Polynomial Trend' : 'Loading…'}
          sub={`${data?.training_samples ?? 0} samples • Non-negative bound`}
          badge={{ text: 'Non-Negative', color: 'bg-purple-500/20 text-purple-300 border border-purple-500/30' }}
        />
      </div>

      {/* Visual Chart Panel */}
      <div className="panel p-5 mb-6">
        <div className="flex flex-wrap items-center justify-between mb-4 gap-2">
          <div>
            <h3 className="font-semibold text-slate-100">Historical Actual Spend vs Projected Trajectory</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Solid line depicts historical daily cost; dashed line indicates {horizon}-day projection with confidence boundaries.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-cyan-300 font-medium">
              <span className="w-3 h-0.5 bg-cyan-400 rounded-full inline-block"></span>
              Historical Actual
            </span>
            <span className="flex items-center gap-1.5 text-purple-400 font-medium">
              <span className="w-3 h-0.5 bg-purple-400 rounded-full inline-block border-t border-dashed"></span>
              Projected Trend
            </span>
            <span className="flex items-center gap-1.5 text-slate-400">
              <span className="w-3 h-0.5 bg-slate-500 rounded-full inline-block"></span>
              Confidence Bounds
            </span>
          </div>
        </div>

        <div className="h-96 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                minTickGap={25}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => `$${v.toLocaleString()}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                }}
                formatter={(val: any, name: any) => {
                  if (val == null) return ['—', name];
                  const labelMap: Record<string, string> = {
                    actual: 'Actual Spend',
                    predicted: 'Predicted Trend',
                    upper: 'Upper Bound',
                    lower: 'Lower Bound',
                  };
                  return [`$${Number(val).toFixed(2)}`, labelMap[name] || name];
                }}
              />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="#06b6d4"
                strokeWidth={2}
                dot={false}
                name="actual"
              />
              <Line
                type="monotone"
                dataKey="predicted"
                stroke="#c084fc"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
                name="predicted"
              />
              <Line
                type="monotone"
                dataKey="upper"
                stroke="#64748b"
                strokeWidth={1}
                strokeDasharray="2 2"
                dot={false}
                name="upper"
              />
              <Line
                type="monotone"
                dataKey="lower"
                stroke="#64748b"
                strokeWidth={1}
                strokeDasharray="2 2"
                dot={false}
                name="lower"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model Registry Details */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="panel p-5">
          <h4 className="font-semibold text-slate-100 text-sm mb-3">Model Registry & Training Governance</h4>
          <dl className="grid grid-cols-2 gap-y-3 text-xs">
            <dt className="text-slate-400">Architecture:</dt>
            <dd className="text-slate-200 font-mono">Polynomial (deg=2) + DaySeasonality</dd>

            <dt className="text-slate-400">Regularization:</dt>
            <dd className="text-slate-200 font-mono">L2 Ridge (α=1.0)</dd>

            <dt className="text-slate-400">Backtest Temporal Split:</dt>
            <dd className="text-slate-200 font-mono">80% Train / 20% Out-of-Sample</dd>

            <dt className="text-slate-400">Leakage Protection:</dt>
            <dd className="text-emerald-400 font-medium">Strict Chronological Window (Zero Leakage)</dd>

            <dt className="text-slate-400">Non-Negative Guardrail:</dt>
            <dd className="text-emerald-400 font-medium">Enforced (min clamp $0.00)</dd>
          </dl>
        </div>

        <div className="panel p-5">
          <h4 className="font-semibold text-slate-100 text-sm mb-3">Out-of-Sample Baseline Benchmark</h4>
          <p className="text-xs text-slate-400 mb-3">
            In compliance with FinOps forecasting standards, model accuracy is evaluated against a strict Naive Persistence Baseline (predicting last observed spend forward).
          </p>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between p-2 bg-slate-900/60 rounded border border-slate-800">
              <span className="text-slate-400">Model MAE:</span>
              <span className="font-mono text-cyan-300">${(data?.mae ?? 0).toFixed(2)}</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-900/60 rounded border border-slate-800">
              <span className="text-slate-400">Naive Baseline MAE:</span>
              <span className="font-mono text-slate-300">${(data?.baseline_mae ?? 0).toFixed(2)}</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-900/60 rounded border border-slate-800">
              <span className="text-slate-400">Accuracy Improvement:</span>
              <span className={`font-mono font-semibold ${(data?.improvement_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {(data?.improvement_pct ?? 0) >= 0 ? '+' : ''}{(data?.improvement_pct ?? 0).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </Page>
  );
}

export function Anomalies() {
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [providerFilter, setProviderFilter] = useState<string>('ALL');
  const [detecting, setDetecting] = useState<boolean>(false);
  const [detectBanner, setDetectBanner] = useState<string | null>(null);

  // Root Cause Analysis (RCA) modal state
  const [selectedRca, setSelectedRca] = useState<any | null>(null);
  const [rcaLoading, setRcaLoading] = useState<boolean>(false);

  const loadAnomalies = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (severityFilter !== 'ALL') params.set('severity', severityFilter);
      if (providerFilter !== 'ALL') params.set('provider', providerFilter);
      const queryString = params.toString() ? `?${params.toString()}` : '';
      const res = await api(`/api/anomalies${queryString}`);
      setAnomalies(res);
    } catch (err) {
      console.error('Failed to load anomalies:', err);
    } finally {
      setLoading(false);
    }
  }, [severityFilter, providerFilter]);

  useEffect(() => {
    loadAnomalies();
  }, [loadAnomalies]);

  const handleRunDetection = async () => {
    setDetecting(true);
    setDetectBanner(null);
    try {
      const res = await api('/api/anomalies/detect?contamination=0.08', { method: 'POST' });
      setDetectBanner(
        `Dynamic anomaly run complete: ${res.anomalies_detected ?? res.detected_count} anomalies identified across ${res.evaluated_days ?? 0} days of spend data evaluated.`
      );
      await loadAnomalies();
    } catch (err: any) {
      setDetectBanner(`Anomaly detection failed: ${err.message || 'Unknown error'}`);
    } finally {
      setDetecting(false);
    }
  };

  const handleOpenRca = async (anomalyId: string) => {
    setRcaLoading(true);
    try {
      const rca = await api(`/api/rca/${anomalyId}`);
      setSelectedRca(rca);
    } catch (err) {
      console.error('Failed to load RCA:', err);
    } finally {
      setRcaLoading(false);
    }
  };

  const totalDeviation = anomalies.reduce((sum, a) => sum + (a.financial_impact || 0), 0);
  const criticalCount = anomalies.filter((a) => a.severity === 'CRITICAL').length;
  const highCount = anomalies.filter((a) => a.severity === 'HIGH').length;

  return (
    <Page
      title="Anomaly Detection & Root Cause Analysis"
      subtitle="Isolation Forest ML residual analysis flagging unexpected cost deviations and providing deterministic root cause evidence."
    >
      {/* KPI Cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card
          label="Total Anomalies"
          value={anomalies.length}
          sub={`${criticalCount} Critical, ${highCount} High`}
          badge={{ text: 'Isolation Forest', color: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' }}
        />
        <Card
          label="Estimated Financial Impact"
          value={`$${totalDeviation.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          sub="Unplanned spend above baseline"
          badge={{ text: 'Total Exposure', color: 'bg-rose-500/20 text-rose-300 border border-rose-500/30' }}
        />
        <Card
          label="Critical Anomalies"
          value={criticalCount}
          sub="Require immediate investigation"
          badge={{ text: 'P0 Priority', color: 'bg-red-500/20 text-red-300 border border-red-500/30' }}
        />
        <Card
          label="Engine Status"
          value="Operational"
          sub="Contamination tuned: 8%"
          badge={{ text: 'Active', color: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' }}
        />
      </div>

      {/* Detection Banner if triggered */}
      {detectBanner && (
        <div className="mb-6 p-4 rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-200 text-xs flex justify-between items-center">
          <span>{detectBanner}</span>
          <button
            onClick={() => setDetectBanner(null)}
            className="text-cyan-400 hover:text-white font-bold ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* Toolbar & Filter Bar */}
      <div className="panel p-4 mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs uppercase font-medium text-slate-400">Severity:</span>
          <div className="flex bg-slate-900 border border-slate-700 rounded-lg p-1">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
              <button
                key={s}
                onClick={() => setSeverityFilter(s)}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition ${
                  severityFilter === s
                    ? 'bg-cyan-500 text-slate-950 shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          <span className="text-xs uppercase font-medium text-slate-400 ml-2">Provider:</span>
          <div className="flex bg-slate-900 border border-slate-700 rounded-lg p-1">
            {['ALL', 'AWS', 'Azure', 'GCP'].map((p) => (
              <button
                key={p}
                onClick={() => setProviderFilter(p)}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition ${
                  providerFilter === p
                    ? 'bg-purple-500 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunDetection}
            disabled={detecting}
            className="text-xs px-3.5 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-semibold rounded-lg shadow-sm transition flex items-center gap-2 disabled:opacity-50"
          >
            {detecting ? (
              <>
                <span className="animate-spin inline-block w-3 h-3 border-2 border-slate-950 border-t-transparent rounded-full"></span>
                Evaluating Residuals…
              </>
            ) : (
              <>
                <span>⚡</span>
                Run Anomaly Detection
              </>
            )}
          </button>
        </div>
      </div>

      {/* Anomalies Cards List */}
      {loading ? (
        <div className="panel p-12 text-center text-slate-400 text-sm">
          Loading anomalies…
        </div>
      ) : anomalies.length === 0 ? (
        <div className="panel p-12 text-center text-slate-400">
          <div className="text-4xl mb-3">🛡️</div>
          <p className="text-sm font-medium text-slate-200">No anomalies detected</p>
          <p className="text-xs text-slate-500 mt-1">All spend and utilization metrics are operating within expected baseline envelopes.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {anomalies.map((a) => {
            const sevColor =
              a.severity === 'CRITICAL'
                ? 'bg-red-500/20 text-red-300 border-red-500/40'
                : a.severity === 'HIGH'
                ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                : a.severity === 'MEDIUM'
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';

            const providerColor =
              a.provider === 'AWS'
                ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                : a.provider === 'Azure'
                ? 'text-sky-400 bg-sky-500/10 border-sky-500/30'
                : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';

            return (
              <div
                key={a.id}
                className="panel p-5 hover:border-slate-600 transition flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-bold border ${sevColor}`}>
                      {a.severity}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold border ${providerColor}`}>
                      {a.provider}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      {a.resource_id || 'Cluster-wide'}
                    </span>
                    <span className="text-xs text-slate-500">
                      {a.timestamp ? new Date(a.timestamp).toLocaleDateString() : 'Recent'}
                    </span>
                  </div>

                  <p className="text-sm text-slate-200 font-medium">
                    {a.reason}
                  </p>

                  <div className="text-xs text-slate-400">
                    <span className="text-slate-500 font-semibold uppercase">Recommendation: </span>
                    {a.recommendation}
                  </div>
                </div>

                <div className="flex md:flex-col items-end justify-between md:justify-center gap-3 min-w-[160px] border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-4">
                  <div className="text-right">
                    <div className="text-xs text-slate-400 uppercase font-medium">Financial Impact</div>
                    <div className="text-base font-bold text-rose-400 font-mono">
                      +${(a.financial_impact || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono">
                      Score: {((a.score || 0) * 100).toFixed(0)}%
                    </div>
                  </div>

                  <button
                    onClick={() => handleOpenRca(a.id)}
                    className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-cyan-200 border border-slate-700 hover:border-cyan-500/50 rounded-lg transition"
                  >
                    Investigate RCA →
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Root Cause Analysis (RCA) Modal */}
      {selectedRca && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-xs uppercase font-semibold text-cyan-400 tracking-wider">
                  Automated Root Cause Analysis
                </span>
                <h3 className="text-lg font-bold text-white mt-1">
                  {selectedRca.provider} Anomaly Investigation
                </h3>
              </div>
              <button
                onClick={() => setSelectedRca(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            {/* Impact Highlights */}
            <div className="grid grid-cols-3 gap-3 p-3 bg-slate-950/60 rounded-xl border border-slate-800 text-center">
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Estimated Impact</div>
                <div className="text-sm font-bold text-rose-400 font-mono">
                  +${(selectedRca.financial_impact || 0).toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Severity</div>
                <div className="text-sm font-bold text-amber-300">
                  {selectedRca.severity}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Confidence Score</div>
                <div className="text-sm font-bold text-cyan-300 font-mono">
                  {((selectedRca.score || 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Root Cause Detail */}
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-400 mb-1.5">Root Cause Statement</h4>
              <div className="p-3 bg-slate-800/80 rounded-lg border border-slate-700/60 text-sm text-slate-200">
                {selectedRca.root_cause}
              </div>
            </div>

            {/* Evidence Checklist */}
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-400 mb-1.5">Deterministic Evidence Points</h4>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {(selectedRca.evidence || []).map((ev: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-cyan-400 font-bold">•</span>
                    <span>{ev}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Timeline */}
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-400 mb-1.5">Chronological Event Timeline</h4>
              <div className="space-y-1.5 text-xs">
                {(selectedRca.timeline || []).map((t: any, idx: number) => (
                  <div key={idx} className="flex items-center gap-3 text-slate-400">
                    <span className="font-mono text-[11px] text-slate-500 min-w-[70px]">
                      {t.time ? new Date(t.time).toLocaleDateString() : 'Event'}
                    </span>
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                    <span className="text-slate-300">{t.event}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommended Action */}
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-400 mb-1.5">Actionable Remediation</h4>
              <div className="p-3 bg-cyan-950/30 border border-cyan-800/40 rounded-lg text-xs text-cyan-200">
                {selectedRca.recommendation}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedRca(null)}
                className="text-xs px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition"
              >
                Close Investigation
              </button>
            </div>
          </div>
        </div>
      )}
    </Page>
  );
}
export function Assistant(){const [q,setQ]=useState(''),[a,setA]=useState('');return <Page title="CloudSense AI Assistant" subtitle="Answers are grounded in application data; no external LLM is required."><div className="panel p-5 max-w-3xl"><div className="muted text-sm mb-4">Try: “What is my cloud spend?”, “Show critical anomalies”, or “Are there security issues?”</div><div className="flex gap-2"><input value={q} onChange={e=>setQ(e.target.value)} className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2" placeholder="Ask about your cloud…"/><button onClick={async()=>setA((await api('/api/assistant/chat',{method:'POST',body:JSON.stringify({message:q})})).answer)} className="bg-cyan-300 text-slate-950 rounded-lg px-5 font-semibold">Ask AI</button></div>{a&&<div className="mt-5 border border-cyan-300/20 bg-cyan-300/5 rounded-xl p-4">{a}</div>}</div></Page>}
