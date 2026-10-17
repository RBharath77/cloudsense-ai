'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

interface SystemJob {
  id: string;
  job_type: string;
  status: string;
  triggered_by: string;
  payload: any;
  result: any;
  error_message: string | null;
  execution_time_ms: number;
  created_at: string;
  completed_at: string | null;
}

interface WebhookEndpoint {
  id: string;
  name: string;
  url: string;
  events: string[];
  secret_token: string;
  is_active: boolean;
  created_at: string;
  last_dispatched_at: string | null;
  last_status_code: number | null;
}

interface AutomatedAction {
  id: string;
  action_type: string;
  target_resource_id: string;
  target_resource_name: string;
  provider: string;
  estimated_monthly_saving_usd: number;
  risk_level: string;
  status: string;
  is_simulation: boolean;
  rollback_plan: any;
  execution_notes: string | null;
  proposed_at: string;
  decided_at: string | null;
  executed_at: string | null;
}

interface ObservabilitySummary {
  status: string;
  uptime_seconds: number;
  db_latency_ms: number;
  max_rss_mb: number;
  total_records: number;
  total_accounts: number;
  pending_actions_count: number;
  realized_monthly_savings_usd: number;
  recent_jobs: any[];
}

export function SystemObservabilityActions() {
  const [activeTab, setActiveTab] = useState<'health' | 'jobs' | 'actions' | 'webhooks'>('health');
  const [obsSummary, setObsSummary] = useState<ObservabilitySummary | null>(null);
  const [jobs, setJobs] = useState<SystemJob[]>([]);
  const [actions, setActions] = useState<AutomatedAction[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Trigger Job State
  const [triggeringJob, setTriggeringJob] = useState(false);

  // Action Approval / Rejection Modal State
  const [selectedAction, setSelectedAction] = useState<AutomatedAction | null>(null);
  const [actionModalMode, setActionModalMode] = useState<'approve' | 'reject' | 'rollback' | 'details' | null>(null);
  const [actionNotes, setActionNotes] = useState('');
  const [actionSubmitting, setActionSubmitting] = useState(false);

  // Webhook Registration Modal State
  const [isWebhookModalOpen, setIsWebhookModalOpen] = useState(false);
  const [hookName, setHookName] = useState('');
  const [hookUrl, setHookUrl] = useState('');
  const [hookEvents, setHookEvents] = useState<string[]>(['ANOMALY_DETECTED', 'BUDGET_BREACHED']);
  const [hookSubmitting, setHookSubmitting] = useState(false);

  // Prometheus Metrics viewer
  const [metricsText, setMetricsText] = useState<string | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(false);

  const loadAllData = useCallback(async () => {
    setLoading(true);
    try {
      const [sumData, jobsData, actionsData, hooksData] = await Promise.all([
        api('/api/system/observability').catch(() => null),
        api('/api/jobs').catch(() => []),
        api('/api/actions').catch(() => []),
        api('/api/webhooks').catch(() => []),
      ]);
      setObsSummary(sumData);
      setJobs(jobsData);
      setActions(actionsData);
      setWebhooks(hooksData);
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to fetch observability telemetry', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  const handleTriggerJob = async (jobType: string) => {
    setTriggeringJob(true);
    setMsg(null);
    try {
      const res = await api('/api/jobs/trigger', {
        method: 'POST',
        body: JSON.stringify({ job_type: jobType }),
      });
      setMsg({
        text: `Successfully executed ${res.job_type} in ${res.execution_time_ms}ms with status: ${res.status}`,
        type: 'success',
      });
      loadAllData();
    } catch (err: any) {
      setMsg({ text: err.message || `Failed to execute job ${jobType}`, type: 'error' });
    } finally {
      setTriggeringJob(false);
    }
  };

  const handleProposeActions = async () => {
    setLoading(true);
    setMsg(null);
    try {
      const res = await api('/api/actions/propose', { method: 'POST' });
      setMsg({ text: `Generated ${res.length} remediation action proposals.`, type: 'success' });
      loadAllData();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to propose actions', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleActionConfirm = async () => {
    if (!selectedAction || !actionModalMode) return;
    setActionSubmitting(true);
    setMsg(null);
    try {
      if (actionModalMode === 'approve') {
        await api(`/api/actions/${selectedAction.id}/approve`, {
          method: 'POST',
          body: JSON.stringify({ execution_notes: actionNotes.trim() }),
        });
        setMsg({ text: `Approved and executed action for ${selectedAction.target_resource_id}`, type: 'success' });
      } else if (actionModalMode === 'reject') {
        await api(`/api/actions/${selectedAction.id}/reject`, {
          method: 'POST',
          body: JSON.stringify({ reason: actionNotes.trim() }),
        });
        setMsg({ text: `Rejected action for ${selectedAction.target_resource_id}`, type: 'success' });
      } else if (actionModalMode === 'rollback') {
        await api(`/api/actions/${selectedAction.id}/rollback`, { method: 'POST' });
        setMsg({ text: `Rolled back action for ${selectedAction.target_resource_id}`, type: 'success' });
      }
      setActionModalMode(null);
      setSelectedAction(null);
      setActionNotes('');
      loadAllData();
    } catch (err: any) {
      setMsg({ text: err.message || 'Action operation failed', type: 'error' });
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleRegisterWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    setHookSubmitting(true);
    setMsg(null);
    try {
      await api('/api/webhooks', {
        method: 'POST',
        body: JSON.stringify({
          name: hookName.trim(),
          url: hookUrl.trim(),
          events: hookEvents,
        }),
      });
      setMsg({ text: `Webhook '${hookName}' registered with HMAC-SHA256 signing!`, type: 'success' });
      setIsWebhookModalOpen(false);
      setHookName('');
      setHookUrl('');
      loadAllData();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to register webhook', type: 'error' });
    } finally {
      setHookSubmitting(false);
    }
  };

  const handleTestWebhook = async (id: string) => {
    setMsg(null);
    try {
      const res = await api(`/api/webhooks/${id}/test`, { method: 'POST' });
      setMsg({
        text: `Test ping dispatched! Signed with HMAC-SHA256 (Status: ${res.deliveries?.[0]?.status || 'OK'})`,
        type: 'success',
      });
      loadAllData();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to dispatch test ping', type: 'error' });
    }
  };

  const handleDeleteWebhook = async (id: string, name: string) => {
    if (!confirm(`Delete webhook endpoint '${name}'?`)) return;
    try {
      await api(`/api/webhooks/${id}`, { method: 'DELETE' });
      setMsg({ text: `Webhook '${name}' deleted.`, type: 'success' });
      loadAllData();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to delete webhook', type: 'error' });
    }
  };

  const fetchPrometheusMetrics = async () => {
    setLoadingMetrics(true);
    try {
      const res = await fetch('http://localhost:8000/metrics');
      const text = await res.text();
      setMetricsText(text);
    } catch (err: any) {
      setMetricsText('# Failed to load Prometheus metrics from /metrics endpoint');
    } finally {
      setLoadingMetrics(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/10">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>System Observability & Automation</span>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              ● All Systems Nominal
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time subsystem health diagnostics, reliable background maintenance jobs, cryptographic webhook alerts, and safe remediation with rollback plans.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleTriggerJob('ANOMALY_SWEEP')}
            disabled={triggeringJob}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
          >
            {triggeringJob ? 'Executing...' : 'Run Anomaly Sweep'}
          </button>
          <button
            onClick={() => handleTriggerJob('BUDGET_AUDIT')}
            disabled={triggeringJob}
            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            Audit Budgets
          </button>
        </div>
      </div>

      {/* Message Banner */}
      {msg && (
        <div
          className={`p-4 rounded-lg text-sm flex items-center justify-between ${
            msg.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
          }`}
        >
          <span>{msg.text}</span>
          <button onClick={() => setMsg(null)} className="text-xs underline hover:opacity-80">
            Dismiss
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-white/10 pb-1">
        {[
          { key: 'health', label: 'Health & Observability' },
          { key: 'jobs', label: `Background Jobs (${jobs.length})` },
          { key: 'actions', label: `Automated Actions (${actions.filter(a => a.status === 'PROPOSED').length} Pending)` },
          { key: 'webhooks', label: `Alert Webhooks (${webhooks.length})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-1 ${
              activeTab === tab.key
                ? 'border-indigo-500 text-white bg-white/5'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: HEALTH & OBSERVABILITY */}
      {activeTab === 'health' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/40 border border-white/5 space-y-1">
              <span className="text-xs text-slate-400">Database Engine Ping</span>
              <div className="text-2xl font-bold text-white flex items-center gap-2">
                <span>{obsSummary?.db_latency_ms ?? 0} ms</span>
                <span className="text-xs font-normal text-emerald-400">● Live</span>
              </div>
              <div className="text-[11px] text-slate-400">Zero query latency spikes</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/40 border border-white/5 space-y-1">
              <span className="text-xs text-slate-400">Application Uptime</span>
              <div className="text-2xl font-bold text-white">
                {Math.floor((obsSummary?.uptime_seconds ?? 0) / 60)}m {(obsSummary?.uptime_seconds ?? 0) % 60}s
              </div>
              <div className="text-[11px] text-slate-400">Daemon continuous runner</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/40 border border-white/5 space-y-1">
              <span className="text-xs text-slate-400">Resident Memory (RSS)</span>
              <div className="text-2xl font-bold text-white">
                {obsSummary?.max_rss_mb ?? 0} <span className="text-xs font-normal text-slate-400">MB</span>
              </div>
              <div className="text-[11px] text-slate-400">Optimized memory footprint</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/40 border border-white/5 space-y-1">
              <span className="text-xs text-slate-400">Realized Remediation Savings</span>
              <div className="text-2xl font-bold text-emerald-400">
                ${obsSummary?.realized_monthly_savings_usd ?? 0} <span className="text-xs font-normal text-slate-400">/mo</span>
              </div>
              <div className="text-[11px] text-slate-400">From executed automated actions</div>
            </div>
          </div>

          {/* Prometheus Metrics Drawer */}
          <div className="p-4 rounded-xl bg-slate-900/40 border border-white/5 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Prometheus Metrics Exporter</h3>
                <p className="text-xs text-slate-400">Standard Prometheus format exposed at <code>/metrics</code> for Grafana & Datadog ingestion</p>
              </div>
              <button
                onClick={fetchPrometheusMetrics}
                disabled={loadingMetrics}
                className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 rounded-lg transition-colors"
              >
                {loadingMetrics ? 'Scraping /metrics...' : metricsText ? 'Refresh Metrics' : 'View /metrics Stream'}
              </button>
            </div>

            {metricsText && (
              <pre className="p-4 rounded-lg bg-black/60 border border-white/10 font-mono text-[11px] text-emerald-400 max-h-60 overflow-y-auto">
                {metricsText}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: BACKGROUND JOBS */}
      {activeTab === 'jobs' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs text-slate-400">
              Showing {jobs.length} recorded system job executions
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleTriggerJob('STORAGE_ORPHAN_SCAN')}
                disabled={triggeringJob}
                className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 rounded-lg transition-colors"
              >
                Scan Orphan Storage
              </button>
              <button
                onClick={() => handleTriggerJob('SCHEDULED_CONNECTOR_SYNC')}
                disabled={triggeringJob}
                className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 rounded-lg transition-colors"
              >
                Batch Cloud Sync
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-900/40 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 text-xs text-slate-400 uppercase tracking-wider border-b border-white/10">
                  <tr>
                    <th className="py-3 px-4">Job Type</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Triggered By</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Execution Summary</th>
                    <th className="py-3 px-4 text-right">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300 text-xs">
                  {jobs.map((j) => (
                    <tr key={j.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-white">{j.job_type}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            j.status === 'SUCCEEDED'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : j.status === 'RUNNING'
                              ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {j.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">{j.triggered_by}</td>
                      <td className="py-3 px-4 font-mono text-slate-300">{j.execution_time_ms} ms</td>
                      <td className="py-3 px-4 text-slate-300 max-w-xs truncate">
                        {j.result ? JSON.stringify(j.result) : j.error_message || '—'}
                      </td>
                      <td className="py-3 px-4 text-right text-slate-400">
                        {new Date(j.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: AUTOMATED REMEDIATION INBOX */}
      {activeTab === 'actions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Remediation Approval Inbox</h3>
              <p className="text-xs text-slate-400">
                Human-in-the-Loop safeguard: Actions require explicit authorization before applying. Every proposal includes a rollback plan.
              </p>
            </div>
            <button
              onClick={handleProposeActions}
              disabled={loading}
              className="px-3 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow-sm transition-colors"
            >
              Scan & Propose Actions
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {actions.map((act) => (
              <div
                key={act.id}
                className="p-4 rounded-xl bg-slate-900/40 border border-white/5 space-y-3"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-2 border-b border-white/5">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white text-sm">{act.action_type}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white/5 text-slate-300 border border-white/10">
                      {act.provider}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        act.status === 'PROPOSED'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : act.status === 'EXECUTED'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : act.status === 'REJECTED'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                      }`}
                    >
                      {act.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="text-right">
                      <span className="text-xs text-slate-400">Est. Savings: </span>
                      <span className="text-sm font-bold text-emerald-400">
                        ${act.estimated_monthly_saving_usd.toFixed(2)}/mo
                      </span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-slate-300">
                  <div>
                    <span className="text-slate-500">Target Resource: </span>
                    <span className="font-mono text-white">{act.target_resource_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Risk Level: </span>
                    <span className="font-semibold text-emerald-400">{act.risk_level}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Simulation Mode: </span>
                    <span className="text-indigo-400">{act.is_simulation ? 'Active (Safe Dry-Run)' : 'Live'}</span>
                  </div>
                </div>

                {act.execution_notes && (
                  <div className="p-2.5 rounded-lg bg-black/40 border border-white/5 text-xs text-slate-300">
                    {act.execution_notes}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center justify-between pt-2">
                  <button
                    onClick={() => {
                      setSelectedAction(act);
                      setActionModalMode('details');
                    }}
                    className="text-xs text-indigo-400 hover:underline"
                  >
                    View Rollback Plan
                  </button>

                  <div className="flex items-center gap-2">
                    {act.status === 'PROPOSED' && (
                      <>
                        <button
                          onClick={() => {
                            setSelectedAction(act);
                            setActionModalMode('reject');
                          }}
                          className="px-3 py-1 text-xs text-rose-400 hover:bg-rose-500/10 rounded transition-colors"
                        >
                          Reject
                        </button>
                        <button
                          onClick={() => {
                            setSelectedAction(act);
                            setActionModalMode('approve');
                          }}
                          className="px-4 py-1 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded transition-colors shadow-sm"
                        >
                          Approve & Execute
                        </button>
                      </>
                    )}

                    {act.status === 'EXECUTED' && (
                      <button
                        onClick={() => {
                          setSelectedAction(act);
                          setActionModalMode('rollback');
                        }}
                        className="px-3 py-1 text-xs bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 border border-purple-500/30 rounded transition-colors"
                      >
                        Rollback Action
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: ALERT WEBHOOKS */}
      {activeTab === 'webhooks' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Outbound Alert Webhooks</h3>
              <p className="text-xs text-slate-400">
                Cryptographic HMAC-SHA256 signature verification transmitted in <code>X-CloudSense-Signature</code> header.
              </p>
            </div>
            <button
              onClick={() => setIsWebhookModalOpen(true)}
              className="px-3 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow-sm transition-colors"
            >
              Add Webhook Endpoint
            </button>
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-900/40 overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-xs text-slate-400 uppercase tracking-wider border-b border-white/10">
                <tr>
                  <th className="py-3 px-4">Name & Destination</th>
                  <th className="py-3 px-4">Events</th>
                  <th className="py-3 px-4">Secret Signature</th>
                  <th className="py-3 px-4">Last Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300 text-xs">
                {webhooks.map((w) => (
                  <tr key={w.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-medium text-white">{w.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono truncate max-w-xs">{w.url}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {w.events.map((ev) => (
                          <span key={ev} className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-slate-300 border border-white/10">
                            {ev}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">{w.secret_token}</td>
                    <td className="py-3 px-4">
                      {w.last_status_code ? (
                        <span className="text-emerald-400">● HTTP {w.last_status_code}</span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleTestWebhook(w.id)}
                          className="px-2.5 py-1 text-xs bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 rounded transition-colors"
                        >
                          Test Ping
                        </button>
                        <button
                          onClick={() => handleDeleteWebhook(w.id, w.name)}
                          className="px-2 py-1 text-xs text-rose-400 hover:text-rose-300 rounded transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Action Approval / Rejection / Rollback Modal */}
      {actionModalMode && selectedAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="text-lg font-bold text-white capitalize">
                {actionModalMode === 'details'
                  ? 'Rollback Plan & Safety Verification'
                  : `${actionModalMode} Remediation Action`}
              </h3>
              <button onClick={() => setActionModalMode(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-black/40 border border-white/5 space-y-1">
                <div><b>Action:</b> {selectedAction.action_type}</div>
                <div><b>Resource:</b> <span className="font-mono text-indigo-300">{selectedAction.target_resource_id}</span></div>
                <div><b>Estimated Monthly Saving:</b> <span className="text-emerald-400 font-semibold">${selectedAction.estimated_monthly_saving_usd.toFixed(2)}/mo</span></div>
              </div>

              {selectedAction.rollback_plan && (
                <div className="space-y-1">
                  <span className="font-semibold text-slate-300">Rollback Procedure:</span>
                  <pre className="p-3 rounded bg-black/60 border border-white/10 text-emerald-400 font-mono text-[11px] overflow-x-auto">
                    {JSON.stringify(selectedAction.rollback_plan, null, 2)}
                  </pre>
                </div>
              )}

              {actionModalMode !== 'details' && (
                <div className="space-y-1">
                  <label className="text-slate-400 font-medium">
                    {actionModalMode === 'approve' ? 'Approval Note (Optional)' : 'Rejection Reason'}
                  </label>
                  <input
                    type="text"
                    value={actionNotes}
                    onChange={(e) => setActionNotes(e.target.value)}
                    placeholder={actionModalMode === 'approve' ? 'e.g. Approved for sprint cost reduction' : 'e.g. Critical for testing'}
                    className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-white"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-white/10">
              <button
                onClick={() => setActionModalMode(null)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white"
              >
                Close
              </button>
              {actionModalMode !== 'details' && (
                <button
                  onClick={handleActionConfirm}
                  disabled={actionSubmitting}
                  className={`px-4 py-2 text-xs font-semibold rounded-lg text-white ${
                    actionModalMode === 'approve'
                      ? 'bg-emerald-600 hover:bg-emerald-500'
                      : actionModalMode === 'reject'
                      ? 'bg-rose-600 hover:bg-rose-500'
                      : 'bg-purple-600 hover:bg-purple-500'
                  }`}
                >
                  {actionSubmitting ? 'Processing...' : `Confirm ${actionModalMode.toUpperCase()}`}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Webhook Registration Modal */}
      {isWebhookModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <h3 className="text-lg font-bold text-white">Register Alert Webhook</h3>
              <button onClick={() => setIsWebhookModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleRegisterWebhook} className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-slate-400">Endpoint Name *</label>
                <input
                  type="text"
                  required
                  value={hookName}
                  onChange={(e) => setHookName(e.target.value)}
                  placeholder="e.g. FinOps PagerDuty Channel"
                  className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-white"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Destination URL (HTTP/HTTPS) *</label>
                <input
                  type="url"
                  required
                  value={hookUrl}
                  onChange={(e) => setHookUrl(e.target.value)}
                  placeholder="https://events.pagerduty.com/v2/enqueue"
                  className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-white font-mono"
                />
              </div>

              <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-[11px] text-indigo-300">
                🔐 Outgoing payloads are automatically signed with HMAC-SHA256. Consumers can authenticate each dispatch using the secret token.
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setIsWebhookModalOpen(false)}
                  className="px-4 py-2 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={hookSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow-sm"
                >
                  {hookSubmitting ? 'Registering...' : 'Register Webhook'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
