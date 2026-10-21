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
  name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface CurrentUser {
  id: string;
  email: string;
  name: string;
  role: string;
  organization_id?: string;
  organization_name?: string;
  privilege?: Record<string, any>;
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
  { role: 'ADMIN', label: 'Admin', desc: 'Full workspace authority, user management, and direct password/privilege reset without OTP.' },
  { role: 'FINOPS_ENGINEER', label: 'Developer', desc: 'Budgets, anomaly triage, recommendations, and cloud architecture.' },
  { role: 'AUDITOR', label: 'Audit', desc: 'Read-only compliance access to all costs, carbon, and audit logs.' },
  { role: 'VIEWER', label: 'Visitor', desc: 'Standard read-only access to dashboards, costs, and forecasts.' },
];

function getPasswordStrength(p: string): { label: string; score: number; color: string } {
  if (!p) return { label: 'None', score: 0, color: 'bg-slate-700' };
  let score = 0;
  if (p.length >= 6) score += 1;
  if (p.length >= 10) score += 1;
  if (/[A-Z]/.test(p)) score += 1;
  if (/[0-9]/.test(p)) score += 1;
  if (/[^A-Za-z0-9]/.test(p)) score += 1;
  if (score <= 2) return { label: 'Weak', score, color: 'bg-rose-500' };
  if (score <= 4) return { label: 'Moderate', score, color: 'bg-amber-400' };
  return { label: 'Strong', score, color: 'bg-emerald-400' };
}

export function SecurityIdentitySettings() {
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'team' | 'audit'>('profile');
  const [profile, setProfile] = useState<WorkspaceProfile | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [users, setUsers] = useState<WorkspaceUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Profile Edit State
  const [editName, setEditName] = useState('');
  const [editCurrency, setEditCurrency] = useState('USD');
  const [editTimezone, setEditTimezone] = useState('UTC');
  const [savingProfile, setSavingProfile] = useState(false);

  // Member Invite State
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteName, setInviteName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('VIEWER');
  const [inviting, setInviting] = useState(false);
  const [inviteResultModal, setInviteResultModal] = useState<{
    email: string;
    name: string;
    role: string;
    temporary_password: string;
    email_dispatched: boolean;
  } | null>(null);
  const [copiedTempPass, setCopiedTempPass] = useState(false);

  // Teammate Self-Service Password Change via OTP State
  const [otpRequested, setOtpRequested] = useState(false);
  const [otpCountdown, setOtpCountdown] = useState(0);
  const [requestingOtp, setRequestingOtp] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showSelfPass, setShowSelfPass] = useState(false);
  const [changingSelfPassword, setChangingSelfPassword] = useState(false);
  const [selfPassMsg, setSelfPassMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Role Edit Modal State
  const [editingUser, setEditingUser] = useState<WorkspaceUser | null>(null);
  const [newRole, setNewRole] = useState('VIEWER');
  const [updatingRole, setUpdatingRole] = useState(false);

  // Admin Direct Password Reset State (Zero OTP Required)
  const [resettingUser, setResettingUser] = useState<WorkspaceUser | null>(null);
  const [adminNewPassword, setAdminNewPassword] = useState('');
  const [showAdminResetPass, setShowAdminResetPass] = useState(false);
  const [resettingPassword, setResettingPassword] = useState(false);

  // Audit Filter State
  const [auditActionFilter, setAuditActionFilter] = useState('');
  const [auditStatusFilter, setAuditStatusFilter] = useState('');

  // Countdown timer effect
  useEffect(() => {
    if (otpCountdown <= 0) return;
    const timer = setInterval(() => {
      setOtpCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [otpCountdown]);

  const fetchCurrentUser = useCallback(async () => {
    try {
      const data = await api('/api/auth/me');
      setCurrentUser(data);
    } catch (err) {
      console.warn('Failed to fetch current user profile:', err);
    }
  }, []);

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
      console.warn('Audit logs query notice:', err.message);
    }
  }, [auditActionFilter, auditStatusFilter]);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchCurrentUser(), fetchProfile(), fetchUsers(), fetchAuditLogs()]).finally(() =>
      setLoading(false)
    );
  }, [fetchCurrentUser, fetchProfile, fetchUsers, fetchAuditLogs]);

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

  // Admin invites a new member: auto-generates AI password and sends email via Warbytes Gmail
  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviting(true);
    setMsg(null);
    try {
      const res = await api('/api/users/invite', {
        method: 'POST',
        body: JSON.stringify({
          email: inviteEmail.trim(),
          name: inviteName.trim() || undefined,
          role: inviteRole,
        }),
      });
      setShowInviteModal(false);
      setInviteName('');
      setInviteEmail('');
      setInviteRole('VIEWER');
      setInviteResultModal({
        email: res.email,
        name: res.name || res.email.split('@')[0],
        role: res.role,
        temporary_password: res.temporary_password,
        email_dispatched: res.email_dispatched,
      });
      setCopiedTempPass(false);
      setMsg({
        text: `Invitation dispatched to ${res.email}. An AI temporary password was generated and emailed from Warbytes.`,
        type: 'success',
      });
      await fetchUsers();
      await fetchAuditLogs();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to invite user', type: 'error' });
    } finally {
      setInviting(false);
    }
  };

  // Teammate self-service: request password change OTP via Warbytes Gmail
  const handleRequestPasswordChangeOtp = async () => {
    setRequestingOtp(true);
    setSelfPassMsg(null);
    try {
      const res = await api('/api/auth/request-password-change-otp', {
        method: 'POST',
      });
      setOtpRequested(true);
      setOtpCountdown(60);
      setSelfPassMsg({
        text: res.message || `A 6-digit verification code was sent to ${currentUser?.email} from Warbytes.`,
        type: 'success',
      });
    } catch (err: any) {
      setSelfPassMsg({
        text: err.message || 'Failed to send verification OTP. Please try again.',
        type: 'error',
      });
    } finally {
      setRequestingOtp(false);
    }
  };

  // Teammate self-service: submit OTP and new password
  const handleChangePasswordWithOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setSelfPassMsg(null);

    if (newPassword.length < 6) {
      setSelfPassMsg({ text: 'Password must be at least 6 characters long.', type: 'error' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setSelfPassMsg({ text: 'Passwords do not match. Please re-enter.', type: 'error' });
      return;
    }
    if (!otpCode.trim()) {
      setSelfPassMsg({ text: 'Please enter the 6-digit OTP code sent to your email.', type: 'error' });
      return;
    }

    setChangingSelfPassword(true);
    try {
      const res = await api('/api/auth/change-password-with-otp', {
        method: 'POST',
        body: JSON.stringify({
          code: otpCode.trim(),
          new_password: newPassword,
        }),
      });
      setSelfPassMsg({
        text: res.message || 'Your password was updated successfully!',
        type: 'success',
      });
      setOtpCode('');
      setNewPassword('');
      setConfirmPassword('');
      setOtpRequested(false);
      setOtpCountdown(0);
      await fetchAuditLogs();
    } catch (err: any) {
      setSelfPassMsg({
        text: err.message || 'Password update failed. Please check your OTP code and try again.',
        type: 'error',
      });
    } finally {
      setChangingSelfPassword(false);
    }
  };

  // Admin directly updates user role (zero OTP)
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

  // Admin deactivates user
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

  // Admin directly resets user password without OTP
  const handleAdminDirectResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resettingUser) return;
    if (adminNewPassword.length < 6) {
      setMsg({ text: 'Password must be at least 6 characters long.', type: 'error' });
      return;
    }
    setResettingPassword(true);
    setMsg(null);
    try {
      const res = await api(`/api/users/${resettingUser.id}/reset-password`, {
        method: 'POST',
        body: JSON.stringify({ new_password: adminNewPassword }),
      });
      setMsg({
        text: res.message || `Password for ${resettingUser.email} was successfully reset without OTP.`,
        type: 'success',
      });
      setResettingUser(null);
      setAdminNewPassword('');
      await fetchAuditLogs();
    } catch (err: any) {
      setMsg({ text: err.message || 'Direct password reset failed.', type: 'error' });
    } finally {
      setResettingPassword(false);
    }
  };

  const getRoleLabel = (role?: string) => {
    switch (role?.toUpperCase()) {
      case 'ADMIN':
        return 'Admin';
      case 'FINOPS_ENGINEER':
        return 'Developer';
      case 'AUDITOR':
        return 'Audit';
      case 'VIEWER':
        return 'Visitor';
      default:
        return role || 'Visitor';
    }
  };

  const getRoleBadgeColor = (role?: string) => {
    switch (role?.toUpperCase()) {
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

  const strength = getPasswordStrength(newPassword);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="panel p-6 bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 border-cyan-500/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="h-3 w-3 rounded-full bg-emerald-400" />
              <h2 className="text-xl font-bold tracking-tight text-white">Security & Workspace Governance</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                Warbytes Verified
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Role-Based Access Control (Admin, Developer, Audit, Visitor), secure email invitations with AI passwords,
              and authenticated OTP self-service password management.
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
      <div className="flex flex-wrap border-b border-slate-800 text-sm">
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
          onClick={() => setActiveTab('security')}
          className={`px-5 py-3 font-medium transition border-b-2 flex items-center gap-2 ${
            activeTab === 'security'
              ? 'border-cyan-400 text-cyan-300 bg-slate-900/40'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          Account Security & OTP
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

      {/* Tab 2: Account Security & Self-Service OTP Password Change */}
      {activeTab === 'security' && (
        <div className="space-y-6 max-w-2xl">
          {/* User Identity Card */}
          <div className="panel p-5 bg-slate-900 border-slate-800 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 flex items-center justify-center font-bold text-sm">
                {(currentUser?.name || currentUser?.email || 'U')[0].toUpperCase()}
              </div>
              <div>
                <div className="text-white font-semibold text-sm">
                  {currentUser?.name || currentUser?.email?.split('@')[0]}
                </div>
                <div className="text-xs text-slate-400">{currentUser?.email}</div>
              </div>
            </div>
            <div className="text-right">
              <span className={`px-2.5 py-1 rounded text-xs font-semibold border ${getRoleBadgeColor(currentUser?.role)}`}>
                {getRoleLabel(currentUser?.role)}
              </span>
              <div className="text-[10px] text-slate-500 mt-1">Logged In Account</div>
            </div>
          </div>

          {/* OTP Password Change Box */}
          <div className="panel p-6 bg-slate-900 border-slate-800 space-y-5">
            <div className="border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Change Account Password
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                For security, changing your password requires an email OTP verification code sent from{' '}
                <span className="text-cyan-300 font-medium">Warbytes</span> to{' '}
                <b className="text-white">{currentUser?.email}</b>.
              </p>
            </div>

            {selfPassMsg && (
              <div
                className={`p-3.5 rounded-xl text-xs flex items-center justify-between ${
                  selfPassMsg.type === 'success'
                    ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
                }`}
              >
                <span>{selfPassMsg.text}</span>
                <button onClick={() => setSelfPassMsg(null)} className="text-slate-400 hover:text-white text-xs">
                  ✕
                </button>
              </div>
            )}

            {!otpRequested ? (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 space-y-2">
                  <div className="flex items-center gap-2 text-cyan-400 font-semibold">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    Step 1: Request Security Verification Code
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    Click the button below to generate a secure 6-digit OTP code. It will be emailed immediately from{' '}
                    <code className="text-slate-300 bg-slate-900 px-1 py-0.5 rounded">warbytes7@gmail.com</code>.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleRequestPasswordChangeOtp}
                  disabled={requestingOtp}
                  className="w-full py-3 rounded-xl font-semibold text-xs bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/40"
                >
                  {requestingOtp ? (
                    'Sending Verification Code…'
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      Send Verification Code to My Email
                    </>
                  )}
                </button>
              </div>
            ) : (
              <form onSubmit={handleChangePasswordWithOtp} className="space-y-4 text-xs">
                {/* OTP Code Field */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="font-semibold text-slate-300">
                      Enter 6-Digit Email Verification Code
                    </label>
                    <button
                      type="button"
                      disabled={otpCountdown > 0 || requestingOtp}
                      onClick={handleRequestPasswordChangeOtp}
                      className="text-cyan-400 hover:text-cyan-300 disabled:text-slate-600 transition"
                    >
                      {otpCountdown > 0 ? `Resend code in ${otpCountdown}s` : 'Resend Code'}
                    </button>
                  </div>
                  <input
                    type="text"
                    maxLength={6}
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="e.g. 849201"
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-4 py-2.5 text-center text-lg font-mono tracking-widest text-cyan-300 placeholder:text-slate-600"
                    required
                    autoFocus
                  />
                  <div className="text-[10px] text-slate-500 mt-1">
                    Check your Gmail inbox and spam folder for the email sent by Warbytes.
                  </div>
                </div>

                {/* New Password */}
                <div>
                  <label className="block font-semibold text-slate-300 mb-1.5">New Password</label>
                  <div className="relative">
                    <input
                      type={showSelfPass ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="At least 6 characters"
                      className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3.5 py-2.5 text-white pr-12"
                      required
                      minLength={6}
                    />
                    <button
                      type="button"
                      onClick={() => setShowSelfPass(!showSelfPass)}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-white"
                    >
                      {showSelfPass ? 'Hide' : 'Show'}
                    </button>
                  </div>

                  {newPassword && (
                    <div className="mt-2 space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-slate-400">Password strength:</span>
                        <span className="font-semibold text-white">{strength.label}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
                        <div
                          className={`h-full ${strength.color} transition-all duration-300`}
                          style={{ width: `${(strength.score / 5) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Confirm New Password */}
                <div>
                  <label className="block font-semibold text-slate-300 mb-1.5">Confirm New Password</label>
                  <input
                    type={showSelfPass ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter your new password"
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3.5 py-2.5 text-white"
                    required
                    minLength={6}
                  />
                </div>

                <div className="pt-2 flex items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setOtpRequested(false);
                      setSelfPassMsg(null);
                    }}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={changingSelfPassword}
                    className="px-5 py-2.5 rounded-xl font-semibold bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition flex items-center gap-2 shadow-lg shadow-cyan-950/40"
                  >
                    {changingSelfPassword ? 'Verifying OTP & Updating…' : 'Verify OTP & Update Password'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Team & Access Control */}
      {activeTab === 'team' && (
        <div className="space-y-6">
          {/* Admin Direct Override Notice */}
          <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 flex items-start gap-3">
            <span className="text-amber-400 text-base">⚡</span>
            <div className="text-xs text-amber-200/90 leading-relaxed">
              <b className="text-amber-300 font-semibold">Admin Direct Authority:</b> Administrators can change member privileges (Admin, Developer, Audit, Visitor) and directly reset any teammate’s password <b>without OTP verification</b>. Teammates changing their own password from Workspace Settings will be verified via email OTP.
            </div>
          </div>

          <div className="panel p-6 bg-slate-900 border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
              <div>
                <h3 className="font-semibold text-white text-base">Team Members & Privilege Governance</h3>
                <p className="text-xs text-slate-400">
                  Invite teammates with automated AI-generated passwords and manage multi-cloud operational roles.
                </p>
              </div>
              <button
                onClick={() => setShowInviteModal(true)}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition flex items-center gap-2 shadow-lg shadow-cyan-950/40"
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
                    <th className="py-3 px-4">Member</th>
                    <th className="py-3 px-4">Privilege / Role</th>
                    <th className="py-3 px-4">Account Status</th>
                    <th className="py-3 px-4">Joined Date</th>
                    <th className="py-3 px-4 text-right">Admin Direct Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-medium text-slate-200">
                        <div className="font-semibold text-white">{u.name || u.email.split('@')[0]}</div>
                        <div className="text-[11px] text-slate-400">{u.email}</div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">{u.id.slice(0, 10)}…</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2.5 py-1 rounded text-[10px] font-semibold border ${getRoleBadgeColor(u.role)}`}>
                          {getRoleLabel(u.role)} <span className="opacity-70 text-[9px]">({u.role})</span>
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
                          className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-blue-700 border border-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-cyan-300 dark:border-slate-700 text-[11px] font-semibold transition cursor-pointer"
                          title="Direct Privilege Change (No OTP)"
                        >
                          Edit Role
                        </button>
                        <button
                          onClick={() => {
                            setResettingUser(u);
                            setAdminNewPassword('');
                            setShowAdminResetPass(false);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-100 hover:bg-amber-100 text-amber-800 border border-slate-300 dark:bg-slate-800 dark:hover:bg-amber-950/40 dark:text-amber-300 dark:hover:text-amber-200 dark:border-slate-700 text-[11px] font-semibold transition cursor-pointer"
                          title="Direct Admin Password Reset (Zero OTP Required)"
                        >
                          Reset Password
                        </button>
                        {u.is_active && (
                          <button
                            onClick={() => handleDeactivateUser(u)}
                            className="px-2.5 py-1 rounded bg-slate-100 hover:bg-rose-100 text-rose-700 border border-slate-300 dark:bg-slate-800 dark:hover:bg-rose-950/60 dark:text-slate-400 dark:hover:text-rose-300 dark:border-slate-700 text-[11px] font-semibold transition cursor-pointer"
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

      {/* Tab 4: Security & Audit Logs */}
      {activeTab === 'audit' && (
        <div className="space-y-6">
          <div className="panel p-6 bg-slate-900 border-slate-800 space-y-4">
            <div className="flex flex-col md:flex-row justify-between md:items-center gap-3">
              <div>
                <h3 className="font-semibold text-white text-base">Immutable Security & Operations Audit Trail</h3>
                <p className="text-xs text-slate-400">
                  Tamper-evident log of authentication, invitations, OTP verifications, and direct administrator resets.
                </p>
              </div>

              {/* Filters */}
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  placeholder="Filter action (e.g. password, user)…"
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
                        <td className="py-3 px-4 text-cyan-300 font-semibold">{log.action}</td>
                        <td className="py-3 px-4">
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
                        <td className="py-3 px-4 text-slate-500">
                          {log.resource_type ? `${log.resource_type}:${log.resource_id?.slice(0, 8)}…` : '—'}
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

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="panel p-6 max-w-lg w-full bg-slate-900 border-slate-700 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                  Invite Team Member
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Sends credentials and an AI-generated secure password via Warbytes Gmail.
                </p>
              </div>
              <button
                onClick={() => setShowInviteModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleInviteUser} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Teammate Full Name</label>
                <input
                  type="text"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  placeholder="e.g. Alex Morgan"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white text-xs focus:border-cyan-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Gmail / Work Email Address <span className="text-rose-400">*</span>
                </label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="teammate@company.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white text-xs focus:border-cyan-400"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Assign Privilege / Role</label>
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

              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <div className="flex items-center gap-1.5 text-cyan-400 font-semibold">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Automated Credentials Dispatch
                </div>
                <p>
                  A cryptographically secure AI-generated password will be created. The teammate will receive an official invitation email from <span className="text-white font-medium">Warbytes</span> with login instructions. They can change their password anytime via OTP verification in Workspace Settings.
                </p>
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
                  className="px-5 py-2 rounded-lg text-xs font-semibold bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition flex items-center gap-2"
                >
                  {inviting ? 'Generating Password & Sending Mail…' : 'Send Invite & AI Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Invite Result Modal (Shows temporary password & dispatch notice) */}
      {inviteResultModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="panel p-6 max-w-md w-full bg-slate-900 border-cyan-500/40 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                  ✓
                </span>
                <div>
                  <h3 className="text-base font-bold text-white">Invitation Dispatched</h3>
                  <p className="text-[11px] text-emerald-400">Email sent via Warbytes Gmail</p>
                </div>
              </div>
              <button
                onClick={() => setInviteResultModal(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Invited Teammate:</span>
                  <span className="text-white font-semibold">{inviteResultModal.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Email Address:</span>
                  <span className="text-white font-mono">{inviteResultModal.email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Assigned Privilege:</span>
                  <span className="text-cyan-300 font-semibold">{getRoleLabel(inviteResultModal.role)}</span>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                  AI-Generated Temporary Password
                </label>
                <div className="flex items-center gap-2 bg-slate-950 p-2.5 rounded-xl border border-cyan-500/40">
                  <code className="text-cyan-300 font-mono text-sm tracking-wider flex-1 select-all">
                    {inviteResultModal.temporary_password}
                  </code>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(inviteResultModal.temporary_password);
                      setCopiedTempPass(true);
                      setTimeout(() => setCopiedTempPass(false), 2000);
                    }}
                    className="px-3 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 font-semibold text-[11px] transition"
                  >
                    {copiedTempPass ? 'Copied ✓' : 'Copy'}
                  </button>
                </div>
                <p className="text-[10px] text-slate-500 mt-1">
                  The teammate can log in with this temporary password and update it under Workspace Settings using email OTP verification.
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => setInviteResultModal(null)}
                className="px-5 py-2 rounded-lg text-xs font-semibold bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition"
              >
                Close & Return
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Role Update Modal (Admin Direct) */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="panel p-6 max-w-md w-full bg-slate-900 border-slate-700 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Modify Member Privilege</h3>
              <button
                onClick={() => setEditingUser(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-sm">
              <div className="text-xs text-slate-400">
                Updating privilege role for <b className="text-white">{editingUser.email}</b>
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
                  {updatingRole ? 'Updating Privilege…' : 'Save Privilege Directly'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Admin Direct Password Reset Modal (Zero OTP Required) */}
      {resettingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="panel p-6 max-w-md w-full bg-slate-900 border-slate-700 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                  Admin Direct Password Override
                </h3>
                <p className="text-[11px] text-amber-400/90 font-medium mt-0.5">
                  Privileged operation: Zero OTP verification required
                </p>
              </div>
              <button
                onClick={() => setResettingUser(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAdminDirectResetPassword} className="space-y-4 text-sm">
              <div className="text-xs text-slate-400 bg-slate-950 p-3 rounded-xl border border-slate-800">
                Directly assigning a new password for <b className="text-white">{resettingUser.email}</b>. As an Administrator, you can update this user account password immediately without requiring email OTP verification.
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showAdminResetPass ? 'text' : 'password'}
                    value={adminNewPassword}
                    onChange={(e) => setAdminNewPassword(e.target.value)}
                    placeholder="Enter at least 6 characters"
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white text-xs focus:border-amber-400 pr-12"
                    required
                    minLength={6}
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setShowAdminResetPass(!showAdminResetPass)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-white text-xs"
                  >
                    {showAdminResetPass ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setResettingUser(null)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resettingPassword}
                  className="px-5 py-2 rounded-lg text-xs font-semibold bg-amber-400 hover:bg-amber-300 text-slate-950 transition flex items-center gap-1.5"
                >
                  {resettingPassword ? 'Updating Password…' : 'Update Password Directly'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
