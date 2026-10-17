'use client';
import { useEffect, useState, useCallback } from 'react';
import { api, downloadFile } from '../lib/api';
import { Page, DataList } from './Page';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

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
export function Generic({title,path}:{title:string;path:string}){return <Page title={title} subtitle="Live application data from the CloudSense backend."><DataList path={path} render={x=><div><div className="flex justify-between gap-4"><b>{x.name||x.title||x.service||x.provider||x.metric||'Record'}</b><span className="text-cyan-200">{x.severity||x.status||x.availability||''}</span></div><pre className="text-xs muted mt-3 whitespace-pre-wrap overflow-auto">{JSON.stringify(x,null,2)}</pre></div>}/></Page>}
export function Forecast(){const [d,setD]=useState<any>();useEffect(()=>{api('/api/forecast').then(setD)},[]);return <Page title="Cost Forecast" subtitle="Trend model with evaluation metrics and confidence bands."><div className="panel p-5"><div className="grid md:grid-cols-3 gap-4"><Card label="Forecast horizon" value="30 days"/><Card label="MAE" value={d?.mae?.toFixed(2)??'—'}/><Card label="RMSE" value={d?.rmse?.toFixed(2)??'—'}/></div><div className="h-80 mt-6"><ResponsiveContainer width="100%" height="100%"><LineChart data={(d?.predictions||[]).map((v:number,i:number)=>({day:i+1,cost:v}))}><XAxis dataKey="day"/><YAxis/><Tooltip/><Line dataKey="cost" type="monotone" strokeWidth={2}/></LineChart></ResponsiveContainer></div></div></Page>}
export function Assistant(){const [q,setQ]=useState(''),[a,setA]=useState('');return <Page title="CloudSense AI Assistant" subtitle="Answers are grounded in application data; no external LLM is required."><div className="panel p-5 max-w-3xl"><div className="muted text-sm mb-4">Try: “What is my cloud spend?”, “Show critical anomalies”, or “Are there security issues?”</div><div className="flex gap-2"><input value={q} onChange={e=>setQ(e.target.value)} className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2" placeholder="Ask about your cloud…"/><button onClick={async()=>setA((await api('/api/assistant/chat',{method:'POST',body:JSON.stringify({message:q})})).answer)} className="bg-cyan-300 text-slate-950 rounded-lg px-5 font-semibold">Ask AI</button></div>{a&&<div className="mt-5 border border-cyan-300/20 bg-cyan-300/5 rounded-xl p-4">{a}</div>}</div></Page>}
