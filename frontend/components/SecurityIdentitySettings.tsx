'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

interface WorkspaceProfile {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  created_at: string;
  summary: {
    active_members: number;
    connected_accounts: number;
    active_budgets: number;
  };
}

interface WorkspaceUser {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface AuditLogEntry {
  id: string;
  organization_id: string;
  user_id: string | null;
  user_email: string;
  action: string;
  status: string;
  detail: string | null;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
}

const FINOPS_ROLES = [
  { role: 'ADMIN', label: 'Admin', desc: 'Full workspace authority, user management, and settings.' },
  { role: 'FINOPS_ENGINEER', label: 'FinOps Engineer', desc: 'Budgets, anomaly triage, recommendations, and imports.' },
  { role: 'AUDITOR', label: 'Auditor', desc: 'Read-only compliance access to all costs, carbon, and audit logs.' },
  { role: 'VIEWER', label: 'Viewer', desc: 'Standard read-only access to dashboards, costs, and forecasts.' },
];

export function SecurityIdentitySettings() {
  const [activeTab, setActiveTab] = useState<'profile' | 'team' | 'audit'>('profile');
  const [profile, setProfile] = useState<WorkspaceProfile | null>(null);
  const [users, setUsers] = useState<WorkspaceUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Profile Edit State
  const [editName, setEditName] = useState('');
  const [editCurrency, setEditCurrency] = useState('USD');
  const [editTimezone, setEditTimezone] = useState('UTC');
  const [savingProfile, setSavingProfile] = useState(false);

  // Invite Modal State
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('VIEWER');
  const [inviting, setInviting] = useState(false);

  // Role Edit Modal State
  const [editingUser, setEditingUser] = useState<WorkspaceUser | null>(null);
  const [newRole, setNewRole] = useState('VIEWER');
  const [updatingRole, setUpdatingRole] = useState(false);

  // Audit Filter State
  const [auditActionFilter, setAuditActionFilter] = useState('');
  const [auditStatusFilter, setAuditStatusFilter] = useState('');

  const fetchProfile = useCallback(async () => {
    try {
      const data = await api('/api/workspace');
      setProfile(data);
      setEditName(data.name);
      setEditCurrency(data.currency || 'USD');
      setEditTimezone(data.timezone || 'UTC');
    } catch (err) {
      console.error('Failed to load workspace profile:', err);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      const data = await api('/api/users');
      if (Array.isArray(data)) setUsers(data);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    try {
      let query = '/api/audit/logs?limit=100';
      if (auditActionFilter) query += `&action=${encodeURIComponent(auditActionFilter)}`;
      if (auditStatusFilter) query += `&status=${encodeURIComponent(auditStatusFilter)}`;
      const data = await api(query);
      if (Array.isArray(data)) setAuditLogs(data);
    } catch (err: any) {
      // If user lacks role to view audit logs, suppress noise
      console.warn('Audit logs query notice:', err.message);
    }
  }, [auditActionFilter, auditStatusFilter]);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchProfile(), fetchUsers(), fetchAuditLogs()]).finally(() => setLoading(false));
  }, [fetchProfile, fetchUsers, fetchAuditLogs]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    setMsg(null);
    try {
      const updated = await api('/api/workspace/settings', {
        method: 'PATCH',
        body: JSON.stringify({
          name: editName,
          currency: editCurrency,
          timezone: editTimezone,
        }),
      });
      setProfile(updated);
      setMsg({ text: 'Workspace configuration saved successfully.', type: 'success' });
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to save settings', type: 'error' });
    } finally {
      setSavingProfile(false);
    }
  };

  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviting(true);
    setMsg(null);
    try {
      await api('/api/users/invite', {
        method: 'POST',
        body: JSON.stringify({
          email: inviteEmail.trim(),
          role: inviteRole,
        }),
      });
      setShowInviteModal(false);
      setInviteEmail('');
      setInviteRole('VIEWER');
      setMsg({ text: `Invited ${inviteEmail} as ${inviteRole}.`, type: 'success' });
      await fetchUsers();
      await fetchAuditLogs();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to invite user', type: 'error' });
    } finally {
      setInviting(false);
    }
  };

  const handleUpdateRole = async () => {
    if (!editingUser) return;
    setUpdatingRole(true);
    setMsg(null);
    try {
      await api(`/api/users/${editingUser.id}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole }),
      });
      setEditingUser(null);
      setMsg({ text: `Updated ${editingUser.email} role to ${newRole}.`, type: 'success' });
      await fetchUsers();
      await fetchAuditLogs();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to update role', type: 'error' });
    } finally {
      setUpdatingRole(false);
    }
  };

  const handleDeactivateUser = async (user: WorkspaceUser) => {
    if (!confirm(`Are you sure you want to deactivate account ${user.email}?`)) return;
    setMsg(null);
    try {
      await api(`/api/users/${user.id}`, { method: 'DELETE' });
      setMsg({ text: `User ${user.email} deactivated.`, type: 'success' });
      await fetchUsers();
      await fetchAuditLogs();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to deactivate user', type: 'error' });
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role.toUpperCase()) {
      case 'ADMIN':
        return 'bg-rose-950 text-rose-300 border-rose-800/40';
      case 'FINOPS_ENGINEER':
        return 'bg-cyan-950 text-cyan-300 border-cyan-800/40';
      case 'AUDITOR':
        return 'bg-amber-950 text-amber-300 border-amber-800/40';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="panel p-6 bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 border-cyan-500/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="h-3 w-3 rounded-full bg-emerald-400" />
              <h2 className="text-xl font-bold tracking-tight text-white">Security, Identity & Governance</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                Phase 9
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Enterprise Role-Based Access Control (RBAC), multi-tenant isolation, cryptographic token revocation,
              and immutable audit trails for FinOps workflows.
            </p>
          </div>
          {profile && (
            <div className="text-xs text-slate-400 bg-slate-950/80 px-3 py-2 rounded-xl border border-slate-800">
              <span className="text-slate-500">Workspace:</span> <b className="text-white">{profile.name}</b>
              <div className="text-[10px] text-slate-500 font-mono mt-0.5">Org ID: {profile.id.slice(0, 8)}…</div>
            </div>
          )}
        </div>
      </div>

      {msg && (
        <div
          className={`p-3.5 rounded-xl text-xs flex items-center justify-between ${
            msg.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <span>{msg.type === 'success' ? '✓' : '⚠'}</span>
            <span>{msg.text}</span>
          </div>
          <button onClick={() => setMsg(null)} className="text-slate-400 hover:text-white text-xs">
            ✕
          </button>
        </div>
      )}

      {/* Tabs Bar */}
      <div className="flex border-b border-slate-800 text-sm">
        <button
          onClick={() => setActiveTab('profile')}
          className={`px-5 py-3 font-medium transition border-b-2 flex items-center gap-2 ${
            activeTab === 'profile'
              ? 'border-cyan-400 text-cyan-300 bg-slate-900/40'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          Workspace Profile
        </button>

        <button
          onClick={() => setActiveTab('team')}
          className={`px-5 py-3 font-medium transition border-b-2 flex items-center gap-2 ${
            activeTab === 'team'
              ? 'border-cyan-400 text-cyan-300 bg-slate-900/40'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          Team & Access Control ({users.length})
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`px-5 py-3 font-medium transition border-b-2 flex items-center gap-2 ${
            activeTab === 'audit'
              ? 'border-cyan-400 text-cyan-300 bg-slate-900/40'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Security Audit Trail
        </button>
      </div>

      {/* Tab 1: Workspace Profile */}
      {activeTab === 'profile' && (
        <div className="space-y-6">
          {profile && (
            <div className="grid md:grid-cols-3 gap-4">
              <div className="panel p-5 bg-slate-900 border-slate-800">
                <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Active Members</div>
                <div className="text-2xl font-bold text-white mt-1">{profile.summary.active_members}</div>
                <div className="text-xs text-cyan-400 mt-1">Managed via RBAC</div>
              </div>
              <div className="panel p-5 bg-slate-900 border-slate-800">
                <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Connected Clouds</div>
                <div className="text-2xl font-bold text-white mt-1">{profile.summary.connected_accounts}</div>
                <div className="text-xs text-slate-400 mt-1">AWS, Azure, GCP</div>
              </div>
              <div className="panel p-5 bg-slate-900 border-slate-800">
                <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Active Budgets</div>
                <div className="text-2xl font-bold text-white mt-1">{profile.summary.active_budgets}</div>
                <div className="text-xs text-emerald-400 mt-1">Guarded threshold alerts</div>
              </div>
            </div>
          )}

          <div className="panel p-6 bg-slate-900 border-slate-800 space-y-6 max-w-2xl">
            <h3 className="font-semibold text-white text-base">Workspace Configuration</h3>
            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Workspace Name
                </label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3.5 py-2.5 text-sm text-white"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Reporting Currency
                  </label>
                  <select
                    value={editCurrency}
                    onChange={(e) => setEditCurrency(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3.5 py-2.5 text-sm text-white"
                  >
                    <option value="USD">USD ($) — US Dollar</option>
                    <option value="EUR">EUR (€) — Euro</option>
                    <option value="GBP">GBP (£) — British Pound</option>
                    <option value="JPY">JPY (¥) — Japanese Yen</option>
                    <option value="CAD">CAD ($) — Canadian Dollar</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Reporting Time Zone
                  </label>
                  <select
                    value={editTimezone}
                    onChange={(e) => setEditTimezone(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3.5 py-2.5 text-sm text-white"
                  >
                    <option value="UTC">UTC (Coordinated Universal Time)</option>
                    <option value="America/New_York">America/New_York (EST/EDT)</option>
                    <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
                    <option value="Europe/London">Europe/London (GMT/BST)</option>
                    <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={savingProfile}
                  className="px-5 py-2.5 rounded-xl font-semibold text-xs bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition flex items-center gap-2"
                >
                  {savingProfile ? 'Saving…' : 'Save Workspace Settings'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tab 2: Team & Access Control */}
      {activeTab === 'team' && (
        <div className="space-y-6">
          <div className="panel p-6 bg-slate-900 border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
              <div>
                <h3 className="font-semibold text-white text-base">Team Members & Role Governance</h3>
                <p className="text-xs text-slate-400">
                  Manage organization team members, assign FinOps roles, and enforce least-privilege security.
                </p>
              </div>
              <button
                onClick={() => setShowInviteModal(true)}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Invite Team Member
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Member Email</th>
                    <th className="py-3 px-4">Assigned Role</th>
                    <th className="py-3 px-4">Account Status</th>
                    <th className="py-3 px-4">Joined Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-medium text-slate-200">
                        {u.email}
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">{u.id.slice(0, 10)}…</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2.5 py-0.5 rounded text-[10px] font-semibold border ${getRoleBadgeColor(u.role)}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            u.is_active
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/40'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {u.is_active ? 'ACTIVE' : 'DEACTIVATED'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => {
                            setEditingUser(u);
                            setNewRole(u.role);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 text-[11px] font-medium transition"
                        >
                          Change Role
                        </button>
                        {u.is_active && (
                          <button
                            onClick={() => handleDeactivateUser(u)}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-rose-950/60 text-slate-400 hover:text-rose-300 border border-slate-700 text-[11px] font-medium transition"
                          >
                            Deactivate
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Security & Audit Logs */}
      {activeTab === 'audit' && (
        <div className="space-y-6">
          <div className="panel p-6 bg-slate-900 border-slate-800 space-y-4">
            <div className="flex flex-col md:flex-row justify-between md:items-center gap-3">
              <div>
                <h3 className="font-semibold text-white text-base">Immutable Security & Operations Audit Trail</h3>
                <p className="text-xs text-slate-400">
                  Tamper-evident log of authentication, budget edits, role changes, and data imports.
                </p>
              </div>

              {/* Filters */}
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  placeholder="Filter action (e.g. budget, user)…"
                  value={auditActionFilter}
                  onChange={(e) => setAuditActionFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500"
                />
                <select
                  value={auditStatusFilter}
                  onChange={(e) => setAuditStatusFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
                >
                  <option value="">All Statuses</option>
                  <option value="SUCCESS">Success</option>
                  <option value="FAILED">Failed</option>
                </select>
                <button
                  onClick={fetchAuditLogs}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition"
                >
                  ↻ Refresh
                </button>
              </div>
            </div>

            {auditLogs.length === 0 ? (
              <div className="text-center py-10 text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
                No audit events found matching the selected filter criteria.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Timestamp</th>
                      <th className="py-3 px-4">Actor</th>
                      <th className="py-3 px-4">Action Event</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Event Details</th>
                      <th className="py-3 px-4">Target Resource</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 text-slate-400 font-sans">
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-slate-200 font-sans font-medium">
                          {log.user_email}
                        </td>
                        <td className="py-3 px-4 text-cyan-300">
                          {log.action}
                        </td>
                        <td className="py-3 px-4 font-sans">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              log.status === 'SUCCESS'
                                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/40'
                                : 'bg-rose-950 text-rose-300 border border-rose-800/40'
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300 font-sans max-w-xs truncate" title={log.detail || ''}>
                          {log.detail || '—'}
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {log.resource_type ? `${log.resource_type} (${log.resource_id?.slice(0, 8) || ''})` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="panel p-6 max-w-lg w-full bg-slate-900 border-slate-700 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                Invite Workspace Member
              </h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleInviteUser} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white text-xs focus:border-cyan-400"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">FinOps Role</label>
                <div className="space-y-2">
                  {FINOPS_ROLES.map((r) => (
                    <label
                      key={r.role}
                      className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition ${
                        inviteRole === r.role
                          ? 'bg-cyan-500/10 border-cyan-400 text-cyan-200'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <input
                        type="radio"
                        name="inviteRole"
                        value={r.role}
                        checked={inviteRole === r.role}
                        onChange={(e) => setInviteRole(e.target.value)}
                        className="mt-1"
                      />
                      <div>
                        <div className="font-semibold text-xs text-white">{r.label}</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">{r.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviting}
                  className="px-5 py-2 rounded-lg text-xs font-semibold bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition"
                >
                  {inviting ? 'Inviting…' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Role Update Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="panel p-6 max-w-md w-full bg-slate-900 border-slate-700 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Modify Member Role</h3>
              <button
                onClick={() => setEditingUser(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-sm">
              <div className="text-xs text-slate-400">
                Updating role for <b className="text-white">{editingUser.email}</b>
              </div>

              <div className="space-y-2">
                {FINOPS_ROLES.map((r) => (
                  <label
                    key={r.role}
                    className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition ${
                      newRole === r.role
                        ? 'bg-cyan-500/10 border-cyan-400 text-cyan-200'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <input
                      type="radio"
                      name="newRole"
                      value={r.role}
                      checked={newRole === r.role}
                      onChange={(e) => setNewRole(e.target.value)}
                      className="mt-1"
                    />
                    <div>
                      <div className="font-semibold text-xs text-white">{r.label}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{r.desc}</div>
                    </div>
                  </label>
                ))}
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleUpdateRole}
                  disabled={updatingRole}
                  className="px-5 py-2 rounded-lg text-xs font-semibold bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition"
                >
                  {updatingRole ? 'Updating…' : 'Save Role'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
