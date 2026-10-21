'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, downloadFile } from '../lib/api';

interface ReportItem {
  id: string;
  name: string;
  report_type: string;
  format: string;
  period_days: number;
  file_size_bytes: number;
  download_url: string;
  created_at: string;
  status: string;
}

interface ReportJobItem {
  id: string;
  job_type: string;
  status: string;
  delivery_channel: string;
  delivery_status: string;
  report_id: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export function ReportsManager() {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [jobs, setJobs] = useState<ReportJobItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [format, setFormat] = useState<'PDF' | 'CSV'>('PDF');
  const [periodDays, setPeriodDays] = useState<number>(30);
  const [reportType, setReportType] = useState<string>('EXECUTIVE_DIGEST');
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Digest schedule modal state
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleChannel, setScheduleChannel] = useState<'EMAIL_SIMULATED' | 'DOWNLOAD'>('EMAIL_SIMULATED');
  const [schedulePeriod, setSchedulePeriod] = useState<number>(30);
  const [currentUser, setCurrentUser] = useState<{ email: string; name?: string; role: string; organization_name?: string } | null>(null);
  const [currentUtcTime, setCurrentUtcTime] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [repsData, jobsData] = await Promise.all([
        api('/api/reports'),
        api('/api/reports/jobs'),
      ]);
      if (Array.isArray(repsData)) setReports(repsData);
      if (Array.isArray(jobsData)) setJobs(jobsData);
    } catch (err: any) {
      console.error('Failed to load reports and jobs:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    try {
      const stored = localStorage.getItem('user');
      if (stored) setCurrentUser(JSON.parse(stored));
    } catch {}
    api('/api/auth/me')
      .then((u) => {
        if (u) setCurrentUser(u);
      })
      .catch(() => {});

    const updateClock = () => {
      const now = new Date();
      setCurrentUtcTime(now.toUTCString());
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleGenerateReport = async () => {
    setGenerating(true);
    setStatusMsg(null);
    try {
      const result = await api('/api/reports/generate', {
        method: 'POST',
        body: JSON.stringify({
          report_type: format === 'CSV' ? 'COST_BREAKDOWN' : reportType,
          format: format,
          period_days: periodDays,
        }),
      });

      setStatusMsg({
        text: `Report "${result.name}" (${(result.file_size_bytes / 1024).toFixed(1)} KB) generated successfully.`,
        type: 'success',
      });

      // Automatically trigger download
      const filename = `cloudsense-report-${result.id.slice(0, 8)}.${format.toLowerCase()}`;
      await downloadFile(result.download_url, filename);
      await fetchData();
    } catch (err: any) {
      setStatusMsg({
        text: `Report generation failed: ${err.message || 'Server error occurred'}`,
        type: 'error',
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleScheduleDigest = async () => {
    setScheduling(true);
    try {
      const res = await api('/api/reports/digest/schedule', {
        method: 'POST',
        body: JSON.stringify({
          job_type: 'EXECUTIVE_DIGEST',
          delivery_channel: scheduleChannel,
          period_days: schedulePeriod,
        }),
      });

      setShowScheduleModal(false);
      setStatusMsg({
        text: `Digest job scheduled: ${res.delivery_status}`,
        type: 'success',
      });
      await fetchData();
    } catch (err: any) {
      setStatusMsg({
        text: `Digest scheduling failed: ${err.message}`,
        type: 'error',
      });
    } finally {
      setScheduling(false);
    }
  };

  const handleDownloadReport = async (rep: ReportItem) => {
    try {
      const filename = `cloudsense-report-${rep.id.slice(0, 8)}.${rep.format.toLowerCase()}`;
      await downloadFile(rep.download_url, filename);
    } catch (err: any) {
      alert(`Download failed: ${err.message}`);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="space-y-8">
      {/* Executive Digest Generator Header */}
      <div className="panel p-6 bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 border-cyan-500/20">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white tracking-tight">Executive Intelligence & FinOps Reports</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                Phase 8
              </span>
            </div>
            <p className="text-sm text-slate-400 max-w-2xl">
              100% database-reconciled executive artifacts with non-fabrication guarantees. Export publication-ready
              PDF digests or sanitized CSV breakdowns immune to formula injection.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowScheduleModal(true)}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-blue-700 border border-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-cyan-300 dark:border-slate-700 flex items-center gap-2 transition cursor-pointer shadow-sm"
            >
              <svg className="w-4 h-4 text-blue-600 dark:text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Schedule Digest Job
            </button>
          </div>
        </div>
      </div>

      {/* Generation Panel */}
      <div className="panel p-6 bg-slate-900 border-slate-800 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <h3 className="font-semibold text-white text-base flex items-center gap-2">
            <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Generate On-Demand Executive Artifact
          </h3>
          <div className="text-xs text-slate-400">
            Reconciles with authoritative database imports & hardware carbon modeling
          </div>
        </div>

        {/* User Billing & Live Timestamp Provenance Stamp Card */}
        <div className="p-4 rounded-xl border border-cyan-500/30 bg-cyan-950/20 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white flex items-center justify-center font-bold text-sm shadow-md">
              {((currentUser?.name || currentUser?.email || 'U')[0]).toUpperCase()}
            </div>
            <div>
              <div className="text-[10px] text-cyan-400 uppercase tracking-wider font-bold">
                Billed To & Generated By Account Holder
              </div>
              <div className="font-bold text-white text-sm">
                {currentUser?.name || (currentUser?.email ? currentUser.email.split('@')[0].toUpperCase() : 'Enterprise User')}
                <span className="text-slate-400 font-normal text-xs ml-2">
                  ({currentUser?.email || 'user@cloudsense.ai'})
                </span>
              </div>
            </div>
          </div>

          <div className="sm:text-right space-y-0.5">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
              Live Stamped Download Timestamp (UTC)
            </div>
            <div className="font-mono text-emerald-400 font-bold text-xs">
              {currentUtcTime || 'Synchronizing UTC Clock…'}
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Format selection */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Format</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setFormat('PDF')}
                className={`px-4 py-3 rounded-xl text-xs font-semibold border text-center transition flex flex-col items-center gap-1 ${
                  format === 'PDF'
                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 shadow-sm'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold">PDF Digest</span>
                <span className="text-[10px] text-slate-500">Executive layout & charts</span>
              </button>
              <button
                type="button"
                onClick={() => setFormat('CSV')}
                className={`px-4 py-3 rounded-xl text-xs font-semibold border text-center transition flex flex-col items-center gap-1 ${
                  format === 'CSV'
                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 shadow-sm'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold">Sanitized CSV</span>
                <span className="text-[10px] text-slate-500">Formula-injection safe</span>
              </button>
            </div>
          </div>

          {/* Observation window */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Observation Period</label>
            <div className="grid grid-cols-4 gap-2">
              {[7, 14, 30, 90].map((days) => (
                <button
                  key={days}
                  type="button"
                  onClick={() => setPeriodDays(days)}
                  className={`py-3 rounded-xl text-xs font-semibold border text-center transition ${
                    periodDays === days
                      ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  {days}D
                </button>
              ))}
            </div>
          </div>

          {/* Action trigger */}
          <div className="space-y-2 flex flex-col justify-end">
            <button
              onClick={handleGenerateReport}
              disabled={generating}
              className="w-full py-3.5 px-6 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-slate-950 disabled:opacity-50 transition shadow-md shadow-cyan-950/40 flex items-center justify-center gap-2"
            >
              {generating ? (
                <>
                  <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                  <span>Compiling & Reconciling…</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span>Generate & Download {format}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {statusMsg && (
          <div
            className={`p-3 rounded-xl text-xs flex items-center gap-2 ${
              statusMsg.type === 'success'
                ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
            }`}
          >
            {statusMsg.type === 'success' ? '✓' : '⚠'} {statusMsg.text}
          </div>
        )}
      </div>

      {/* Reports Archive */}
      <div className="panel p-6 bg-slate-900 border-slate-800 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-white text-base">Generated Reports Archive</h3>
            <p className="text-xs text-slate-400">Reconciled artifacts available for immediate verified download</p>
          </div>
          <button
            onClick={fetchData}
            className="text-xs text-slate-400 hover:text-cyan-300 flex items-center gap-1 transition"
          >
            ↻ Refresh Archive
          </button>
        </div>

        {reports.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
            No reports generated yet for this workspace. Select options above to compile an executive digest.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Report Name</th>
                  <th className="py-3 px-4">Billed To</th>
                  <th className="py-3 px-4">Format</th>
                  <th className="py-3 px-4">Period</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Generated At</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {reports.map((rep) => (
                  <tr key={rep.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 font-medium text-slate-200">
                      {rep.name}
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">{rep.id.slice(0, 12)}…</div>
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">
                      <span className="text-cyan-400 font-medium">
                        {currentUser?.email ? currentUser.email.split('@')[0] : 'admin'}
                      </span>
                      <span className="text-slate-500 text-[10px] block">
                        {currentUser?.email || 'admin@cloudsense.ai'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          rep.format === 'PDF'
                            ? 'bg-rose-950 text-rose-300 border border-rose-800/40'
                            : 'bg-emerald-950 text-emerald-300 border border-emerald-800/40'
                        }`}
                      >
                        {rep.format}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{rep.period_days} Days</td>
                    <td className="py-3 px-4 text-slate-400 font-mono">{formatBytes(rep.file_size_bytes)}</td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(rep.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDownloadReport(rep)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 hover:border-cyan-500/40 transition inline-flex items-center gap-1.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Background Digest Jobs Tracker */}
      <div className="panel p-6 bg-slate-900 border-slate-800 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-white text-base">Background Digest Execution & Delivery Tracker</h3>
            <p className="text-xs text-slate-400">
              Audit log of digest executions showing real delivery status (Honest Simulated Delivery Disclosure)
            </p>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
            No background digest jobs scheduled yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Job ID</th>
                  <th className="py-3 px-4">Job Type</th>
                  <th className="py-3 px-4">Channel</th>
                  <th className="py-3 px-4">Execution Status</th>
                  <th className="py-3 px-4">Delivery Status (Honest Disclosure)</th>
                  <th className="py-3 px-4">Completed At</th>
                  <th className="py-3 px-4 text-right">Artifact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 font-mono text-slate-400">{j.id.slice(0, 8)}…</td>
                    <td className="py-3 px-4 font-medium text-slate-200">{j.job_type}</td>
                    <td className="py-3 px-4 text-slate-300">{j.delivery_channel}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          j.status === 'SUCCEEDED'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/40'
                            : j.status === 'RUNNING'
                            ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/40'
                            : j.status === 'FAILED'
                            ? 'bg-rose-950 text-rose-300 border border-rose-800/40'
                            : 'bg-amber-950 text-amber-300 border border-amber-800/40'
                        }`}
                      >
                        {j.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-slate-300 text-[11px] font-mono">
                        {j.delivery_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {j.completed_at ? new Date(j.completed_at).toLocaleString() : '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {j.report_id ? (
                        <button
                          onClick={() => downloadFile(`/api/reports/${j.report_id}/download`, `digest-${j.id.slice(0, 8)}.pdf`)}
                          className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold underline underline-offset-2"
                        >
                          Download PDF
                        </button>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Schedule Digest Job Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="panel p-6 max-w-lg w-full bg-slate-900 border-slate-700 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Schedule Executive Digest Job
              </h3>
              <button
                onClick={() => setShowScheduleModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Delivery Channel</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setScheduleChannel('EMAIL_SIMULATED')}
                    className={`p-3 rounded-xl border text-left transition ${
                      scheduleChannel === 'EMAIL_SIMULATED'
                        ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="font-semibold text-xs">Email (Simulated)</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">Discloses simulated delivery without SMTP credentials</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setScheduleChannel('DOWNLOAD')}
                    className={`p-3 rounded-xl border text-left transition ${
                      scheduleChannel === 'DOWNLOAD'
                        ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="font-semibold text-xs">In-App Archive</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">Compiles artifact directly to reports archive</div>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Observation Window</label>
                <select
                  value={schedulePeriod}
                  onChange={(e) => setSchedulePeriod(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs"
                >
                  <option value={7}>Last 7 Days</option>
                  <option value={14}>Last 14 Days</option>
                  <option value={30}>Last 30 Days (Standard Monthly)</option>
                  <option value={90}>Last 90 Days (Quarterly Review)</option>
                </select>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 space-y-1">
                <div className="font-semibold text-slate-300">Digest Artifact Contents:</div>
                <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                  <li>Spend baseline, 30D forecast, and prior period variance</li>
                  <li>Provider breakdown across AWS, Azure, and GCP</li>
                  <li>Scope 1/2/3 greenhouse gas emissions and clean energy ratio</li>
                  <li>Top 4 prioritized rightsizing & optimization actions</li>
                  <li>Non-fabrication statement and methodology citations</li>
                </ul>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-2">
              <button
                onClick={() => setShowScheduleModal(false)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-white dark:border-slate-700 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleScheduleDigest}
                disabled={scheduling}
                className="px-5 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white dark:bg-cyan-400 dark:hover:bg-cyan-300 dark:text-slate-950 transition flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
              >
                {scheduling ? 'Scheduling…' : 'Run Digest Job'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
