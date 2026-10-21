'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Cloud,
  Mail,
  Lock,
  KeyRound,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Eye,
  EyeOff,
  AlertCircle,
  Clock,
  RotateCw,
} from 'lucide-react';
import { api } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import ThemeToggleSwitch from '../../components/ThemeToggleSwitch';
import LanguageSelector from '../../components/LanguageSelector';
import CurrencySelector from '../../components/CurrencySelector';
import AnimatedBackground from '../../components/AnimatedBackground';

export default function ForgotPassword() {
  const router = useRouter();
  const { t } = useI18n();

  // USER OTP Wizard state: 1 = Enter Email, 2 = Enter OTP, 3 = New Password, 4 = Success
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [email, setEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [countdown, setCountdown] = useState(60);
  const [canResend, setCanResend] = useState(false);
  const [resending, setResending] = useState(false);

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [infoMsg, setInfoMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Countdown timer for resending OTP
  useEffect(() => {
    let timer: any;
    if (step === 2 && countdown > 0) {
      timer = setInterval(() => {
        setCountdown((c) => {
          if (c <= 1) {
            setCanResend(true);
            return 0;
          }
          return c - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [step, countdown]);

  // Step 1: Send OTP to Email
  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr('');
    setInfoMsg('');
    setLoading(true);
    try {
      const res = await api('/api/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      setStep(2);
      setCountdown(60);
      setCanResend(false);
      setInfoMsg(res.message || `A 6-digit OTP verification code has been dispatched to ${email}.`);
    } catch (e: any) {
      setErr(e.message || 'No registered account found with this email.');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Verify OTP
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr('');
    if (otpCode.trim().length !== 6) {
      setErr('Please enter the 6-digit OTP verification code sent to your email.');
      return;
    }
    setLoading(true);
    try {
      await api('/api/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: otpCode.trim() }),
      });
      setStep(3);
    } catch (e: any) {
      setErr(e.message || 'Invalid or expired OTP code.');
    } finally {
      setLoading(false);
    }
  };

  // Resend OTP
  const handleResendOtp = async () => {
    if (!canResend || resending) return;
    setResending(true);
    setErr('');
    try {
      const res = await api('/api/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      setCountdown(60);
      setCanResend(false);
      setInfoMsg(res.message || `A new 6-digit OTP code was dispatched to ${email}.`);
    } catch (e: any) {
      setErr(e.message || 'Failed to resend code.');
    } finally {
      setResending(false);
    }
  };

  // Step 3: Reset Password with Verified OTP
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr('');
    if (newPassword.length < 6) {
      setErr('Password must be at least 6 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setErr('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await api('/api/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          code: otpCode.trim(),
          new_password: newPassword,
        }),
      });
      setStep(4);
      setSuccessMsg('Your password has been reset successfully! Redirecting to sign in...');
      setTimeout(() => {
        router.push('/login');
      }, 2500);
    } catch (e: any) {
      setErr(e.message || 'Password reset failed.');
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrength = (pass: string) => {
    if (!pass) return { score: 0, label: t('weak'), color: 'bg-slate-600' };
    let score = 0;
    if (pass.length >= 6) score++;
    if (pass.length >= 10) score++;
    if (/[A-Z]/.test(pass)) score++;
    if (/[0-9]/.test(pass)) score++;
    if (/[^A-Za-z0-9]/.test(pass)) score++;

    if (score <= 2) return { score: 25, label: t('weak'), color: 'bg-red-500' };
    if (score <= 3) return { score: 50, label: t('medium'), color: 'bg-amber-500' };
    if (score <= 4) return { score: 75, label: t('strong'), color: 'bg-blue-500' };
    return { score: 100, label: t('enterprise'), color: 'bg-emerald-500' };
  };

  const strength = getPasswordStrength(newPassword);

  return (
    <main className="min-h-screen flex flex-col justify-between p-6 relative overflow-hidden">
      <AnimatedBackground />

      {/* Header Controls: Navbar without "CloudSense AI" text */}
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

      {/* Main Glass Card */}
      <div className="w-full max-w-md mx-auto relative z-10 animate-fade-in-up">
        {/* Navigation Tabs Pill */}
        <div
          className="flex items-center p-1 rounded-2xl border mb-3 backdrop-blur-md"
          style={{ background: 'var(--tag-bg)', borderColor: 'var(--line)' }}
        >
          <Link
            href="/login"
            className="flex-1 py-1.5 px-3 rounded-xl font-medium text-xs text-center muted hover:text-white transition-colors"
          >
            {t('sign_in')}
          </Link>
          <Link
            href="/register"
            className="flex-1 py-1.5 px-3 rounded-xl font-medium text-xs text-center muted hover:text-white transition-colors"
          >
            {t('create_account')}
          </Link>
          <div
            className="flex-1 py-1.5 px-3 rounded-xl font-bold text-xs text-center shadow-sm"
            style={{ background: 'var(--panel-bg)', color: 'var(--accent)' }}
          >
            {t('reset_password')}
          </div>
        </div>

        <div className="panel p-8 space-y-5 shadow-2xl border relative overflow-hidden rounded-2xl">
          {/* Subtle Top Glowing Line */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-sky-400 to-indigo-600" />

          {/* Step Progress Indicators */}
          <div className="flex items-center justify-between px-4 pb-2">
            {[1, 2, 3, 4].map((s) => {
              const isCompleted = step > s;
              const isCurrent = step === s;
              return (
                <React.Fragment key={s}>
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs transition-all duration-300 ${
                        isCompleted
                          ? 'bg-emerald-500 text-white shadow'
                          : isCurrent
                          ? 'bg-blue-600 text-white shadow-lg ring-2 ring-blue-500/30'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {isCompleted ? <CheckCircle2 size={14} /> : s}
                    </div>
                  </div>
                  {s < 4 && (
                    <div
                      className={`flex-1 h-0.5 mx-2 transition-all ${
                        step > s ? 'bg-emerald-500' : 'bg-slate-700/60'
                      }`}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* STEP 1: ENTER EMAIL */}
          {step === 1 && (
            <form onSubmit={handleSendOtp} className="space-y-4">
              <div className="space-y-1">
                <h1 className="text-xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
                  {t('reset_password')}
                </h1>
                <p className="text-xs muted">
                  {t('enter_reg_email_desc')}
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold" style={{ color: 'var(--text)' }}>
                  {t('reg_email_label')}
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
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="e.g. name@company.com or yourgmail@gmail.com"
                    className="bg-transparent border-none outline-none w-full text-xs"
                    style={{ color: 'var(--text)' }}
                  />
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
                <span>{loading ? t('sending_otp') : t('send_verification_otp')}</span>
                <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" />
              </button>
            </form>
          )}

          {/* STEP 2: ENTER OTP */}
          {step === 2 && (
            <form onSubmit={handleVerifyOtp} className="space-y-4 animate-fade-in-up">
              <div className="space-y-1">
                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/30 mb-1">
                  <Mail size={12} />
                  <span>{t('verification_dispatched')}</span>
                </div>
                <h1 className="text-xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
                  {t('enter_verification_code')}
                </h1>
                <p className="text-xs muted">
                  {t('code_sent_notice')} <b className="text-white">{email}</b>.
                </p>
              </div>

              {infoMsg && (
                <div className="p-3 rounded-xl border border-sky-500/30 text-sky-300 bg-sky-950/20 text-xs flex items-center gap-2 animate-fade-in-down">
                  <CheckCircle2 size={15} />
                  <span>{infoMsg}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold" style={{ color: 'var(--text)' }}>
                  {t('six_digit_otp')}
                </label>
                <div
                  className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-xs transition-all focus-within:border-[var(--accent)]"
                  style={{
                    background: 'var(--input-bg)',
                    borderColor: 'var(--line)',
                  }}
                >
                  <KeyRound size={16} className="muted" />
                  <input
                    type="text"
                    maxLength={6}
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    required
                    placeholder="• • • • • •"
                    className="bg-transparent border-none outline-none w-full text-center text-lg font-mono tracking-[0.4em] font-bold"
                    style={{ color: 'var(--text)' }}
                    autoFocus
                  />
                </div>
              </div>

              {/* Resend Countdown */}
              <div className="flex items-center justify-between text-xs pt-1">
                <div className="flex items-center gap-1.5 muted text-[11px]">
                  <Clock size={13} />
                  {countdown > 0 ? (
                    <span>{t('resend_available_in')} {countdown}s</span>
                  ) : (
                    <span className="text-emerald-400 font-medium">{t('ready_to_resend')}</span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={!canResend || resending}
                  className={`text-[11px] font-semibold flex items-center gap-1 transition ${
                    canResend
                      ? 'text-sky-400 hover:text-sky-300 hover:underline'
                      : 'text-slate-500 cursor-not-allowed'
                  }`}
                >
                  <RotateCw size={12} className={resending ? 'animate-spin' : ''} />
                  <span>{resending ? t('sending') : t('resend_code')}</span>
                </button>
              </div>

              {err && (
                <div className="p-3 rounded-xl border border-red-500/30 text-red-400 bg-red-950/20 text-xs flex items-center gap-2 animate-fade-in-down">
                  <AlertCircle size={15} />
                  <span>{err}</span>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setStep(1);
                    setErr('');
                  }}
                  className="p-2.5 rounded-xl border muted hover:text-white transition"
                  style={{ borderColor: 'var(--line)' }}
                >
                  <ArrowLeft size={16} />
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary flex-1 !py-2.5 text-xs font-semibold flex items-center justify-center gap-2 group hover:scale-[1.01] active:scale-95 shadow-lg"
                >
                  <span>{loading ? t('verifying_otp') : t('verify_otp_code')}</span>
                  <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" />
                </button>
              </div>
            </form>
          )}

          {/* STEP 3: ENTER NEW PASSWORD */}
          {step === 3 && (
            <form onSubmit={handleResetPassword} className="space-y-4 animate-fade-in-up">
              <div className="space-y-1">
                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-1">
                  <CheckCircle2 size={12} />
                  <span>{t('identity_verified')}</span>
                </div>
                <h1 className="text-xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
                  {t('set_new_password')}
                </h1>
                <p className="text-xs muted">{t('create_strong_password')} {email}.</p>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold" style={{ color: 'var(--text)' }}>
                  {t('new_password')}
                </label>
                <div
                  className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-xs transition-all focus-within:border-[var(--accent)]"
                  style={{
                    background: 'var(--input-bg)',
                    borderColor: 'var(--line)',
                  }}
                >
                  <Lock size={16} className="muted" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
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

                {newPassword && (
                  <div className="space-y-1 pt-1 animate-fade-in-up">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="muted">{t('password_strength')}:</span>
                      <span className="font-semibold text-sky-400">{strength.label}</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${strength.color}`}
                        style={{ width: `${strength.score}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold" style={{ color: 'var(--text)' }}>
                  {t('confirm_password')}
                </label>
                <div
                  className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-xs transition-all focus-within:border-[var(--accent)]"
                  style={{
                    background: 'var(--input-bg)',
                    borderColor: 'var(--line)',
                  }}
                >
                  <Lock size={16} className="muted" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    placeholder="••••••••••••"
                    className="bg-transparent border-none outline-none w-full text-xs"
                    style={{ color: 'var(--text)' }}
                  />
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
                <span>{loading ? t('updating_password') : t('save_new_password')}</span>
                <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" />
              </button>
            </form>
          )}

          {/* STEP 4: SUCCESS */}
          {step === 4 && (
            <div className="text-center py-6 space-y-4 animate-fade-in-up">
              <div className="w-14 h-14 mx-auto rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center shadow-lg">
                <CheckCircle2 size={32} />
              </div>
              <div className="space-y-1">
                <h2 className="text-xl font-bold text-white">{t('password_updated')}</h2>
                <p className="text-xs muted">{successMsg}</p>
              </div>
              <Link
                href="/login"
                className="btn-primary inline-flex items-center gap-2 !py-2.5 px-6 text-xs font-semibold"
              >
                <span>{t('signin_with_new_password')}</span>
                <ArrowRight size={15} />
              </Link>
            </div>
          )}

          <div
            className="pt-2 border-t text-center text-xs muted flex items-center justify-between"
            style={{ borderColor: 'var(--line-subtle)' }}
          >
            <Link href="/login" className="hover:text-white transition-colors flex items-center gap-1">
              <ArrowLeft size={13} />
              {t('back_to_signin')}
            </Link>
            <Link
              href="/register"
              className="font-semibold underline hover:text-[var(--accent)] transition-colors"
              style={{ color: 'var(--accent)' }}
            >
              {t('create_account')}
            </Link>
          </div>
        </div>
      </div>

      <div className="text-center text-[11px] muted relative z-10">
        Enterprise Identity & Access Governance · Zero-Trust Multi-Tenant Architecture
      </div>
    </main>
  );
}
