'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Cloud,
  Lock,
  Mail,
  ArrowRight,
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { api } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import ThemeToggleSwitch from '../../components/ThemeToggleSwitch';
import LanguageSelector from '../../components/LanguageSelector';
import CurrencySelector from '../../components/CurrencySelector';
import AnimatedBackground from '../../components/AnimatedBackground';

export default function Login() {
  const [email, setEmail] = useState('admin@cloudsense.ai');
  const [password, setPassword] = useState('CloudSense@123');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { t } = useI18n();

  React.useEffect(() => {
    router.prefetch('/dashboard');
    router.prefetch('/register');
  }, [router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr('');
    setLoading(true);
    try {
      const res = await api('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem('token', res.access_token);
      localStorage.setItem(
        'user',
        JSON.stringify({
          email: res.email || email,
          name: res.name,
          role: res.role,
          privilege: res.privilege,
        })
      );
      router.push('/dashboard');
    } catch (e: any) {
      setErr(e.message || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col justify-between p-6 relative overflow-hidden">
      <AnimatedBackground />

      {/* Top Header Controls */}
      <div className="max-w-xl w-full mx-auto flex items-center justify-between pb-4 relative z-10 animate-fade-in-down">
        <Link href="/" className="flex items-center gap-2 group" title="Home">
          <div
            className="h-9 w-9 rounded-xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-105"
            style={{
              background: 'linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%)',
            }}
          >
            <Cloud className="text-white" size={19} />
          </div>
        </Link>

        <div className="flex items-center gap-2">
          <LanguageSelector compact />
          <CurrencySelector compact />
          <ThemeToggleSwitch />
        </div>
      </div>

      {/* Main Login Card */}
      <div className="w-full max-w-md mx-auto relative z-10 animate-fade-in-up">
        {/* Navigation Tabs Pill */}
        <div
          className="flex items-center p-1 rounded-2xl border mb-3 backdrop-blur-md"
          style={{ background: 'var(--tag-bg)', borderColor: 'var(--line)' }}
        >
          <div
            className="flex-1 py-1.5 px-3 rounded-xl font-bold text-xs text-center shadow-sm"
            style={{ background: 'var(--panel-bg)', color: 'var(--accent)' }}
          >
            {t('sign_in')}
          </div>
          <Link
            href="/register"
            className="flex-1 py-1.5 px-3 rounded-xl font-medium text-xs text-center muted hover:text-white transition-colors"
          >
            {t('create_account')}
          </Link>
          <Link
            href="/forgot-password"
            className="flex-1 py-1.5 px-3 rounded-xl font-medium text-xs text-center muted hover:text-white transition-colors"
          >
            {t('reset_password')}
          </Link>
        </div>

        <div className="panel p-8 space-y-6 shadow-2xl border relative overflow-hidden rounded-2xl">
          {/* Subtle Top Glowing Line */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-sky-400 to-indigo-600" />

          <div className="space-y-1.5">
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
              {t('sign_in')}
            </h1>
            <p className="text-xs muted">
              Sign in to access your enterprise FinOps workspace and multi-cloud analytics.
            </p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold" style={{ color: 'var(--text)' }}>
                {t('email_address')}
              </label>
              <div
                className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-xs transition-all duration-200 focus-within:border-[var(--accent)]"
                style={{
                  background: 'var(--input-bg)',
                  borderColor: 'var(--line)',
                }}
              >
                <Mail size={16} className="muted" />
                <input
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="admin@cloudsense.ai or username"
                  className="bg-transparent border-none outline-none w-full text-xs"
                  style={{ color: 'var(--text)' }}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold" style={{ color: 'var(--text)' }}>
                  {t('password')}
                </label>
                <Link
                  href="/forgot-password"
                  className="text-[11px] font-medium text-sky-400 hover:underline transition-colors"
                >
                  {t('forgot_password')}
                </Link>
              </div>
              <div
                className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-xs transition-all duration-200 focus-within:border-[var(--accent)]"
                style={{
                  background: 'var(--input-bg)',
                  borderColor: 'var(--line)',
                }}
              >
                <Lock size={16} className="muted" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  className="bg-transparent border-none outline-none w-full text-xs"
                  style={{ color: 'var(--text)' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="muted hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Remember Me Option */}
            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded accent-blue-600 cursor-pointer"
                />
                <span className="text-xs muted">{t('remember_browser')}</span>
              </label>
              <div className="flex items-center gap-1 text-[11px] text-emerald-400">
                <ShieldCheck size={13} />
                <span>{t('encrypted_256')}</span>
              </div>
            </div>

            {err && (
              <div className="p-3 rounded-xl border border-red-500/30 text-red-400 bg-red-950/20 text-xs flex items-center gap-2 animate-fade-in-down">
                <AlertCircle size={15} />
                <span>{err}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full !py-2.5 text-xs font-semibold flex items-center justify-center gap-2 group hover:scale-[1.01] active:scale-95 shadow-lg"
            >
              <span>{loading ? t('authenticating') : t('sign_in')}</span>
              <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" />
            </button>
          </form>

          <div
            className="pt-3 border-t text-center text-xs muted flex items-center justify-between"
            style={{ borderColor: 'var(--line-subtle)' }}
          >
            <span>{t('need_workspace')}</span>
            <Link
              href="/register"
              className="font-semibold underline hover:text-[var(--accent)] transition-colors"
              style={{ color: 'var(--accent)' }}
            >
              {t('create_account')}
            </Link>
          </div>
        </div>

        {/* Subtle quick test credentials reminder */}
        <div className="mt-3 text-center">
          <button
            type="button"
            onClick={() => {
              setEmail('admin@cloudsense.ai');
              setPassword('CloudSense@123');
            }}
            className="text-[11px] muted hover:text-sky-300 transition-colors"
          >
            Demo access: <span className="font-mono text-sky-400">admin@cloudsense.ai</span> (click to fill)
          </button>
        </div>
      </div>

      <div className="text-center text-[11px] muted relative z-10">
        CloudSense AI FinOps Intelligence · Enterprise IAM Protocol
      </div>
    </main>
  );
}
