'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Cloud,
  Brain,
  ShieldCheck,
  Leaf,
  ArrowRight,
  Server,
  Zap,
  TrendingDown,
  Sparkles,
  Lock,
  LogIn,
  LogOut,
} from 'lucide-react';

import { useRouter } from 'next/navigation';
import ThemeToggleSwitch from '../components/ThemeToggleSwitch';
import LanguageSelector from '../components/LanguageSelector';
import CurrencySelector from '../components/CurrencySelector';
import HeroCloudGraphic from '../components/HeroCloudGraphic';
import { useI18n } from '../lib/i18n';

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const router = useRouter();
  const { t } = useI18n();

  useEffect(() => {
    try {
      setIsLoggedIn(Boolean(localStorage.getItem('token')));
    } catch {}
    router.prefetch('/dashboard');
    router.prefetch('/login');
  }, [router]);

  const handleSignOut = () => {
    try {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    } catch {}
    setIsLoggedIn(false);
  };
  return (
    <main className="min-h-screen flex flex-col justify-between selection:bg-[#5AA9E6]/30 overflow-hidden">
      {/* Top Navbar */}
      <nav
        className="sticky top-0 z-50 border-b backdrop-blur-md px-6 py-4 transition-all duration-300 animate-fade-in-down"
        style={{
          background: 'var(--header-bg)',
          borderColor: 'var(--line)',
        }}
      >
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Link href="/" className="flex items-center gap-3 group cursor-pointer" title="Home">
            <div
              className="h-10 w-10 rounded-xl flex items-center justify-center shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-6"
              style={{
                background: 'linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%)',
                boxShadow: '0 4px 14px rgba(65, 105, 225, 0.5)',
              }}
            >
              <Cloud className="text-white" size={22} />
            </div>
          </Link>

          <div className="flex items-center gap-3 text-sm">
            <LanguageSelector compact />
            <CurrencySelector compact />
            {/* Real Sliding Pill Theme Toggle Switch */}
            <ThemeToggleSwitch />

            {isLoggedIn ? (
              <>
                <Link
                  href="/dashboard"
                  className="btn-primary text-xs !py-2 !px-4 hover:scale-105 active:scale-95 shadow-md flex items-center gap-1.5"
                >
                  <span>Console</span>
                  <ArrowRight size={14} />
                </Link>
                <button
                  onClick={handleSignOut}
                  className="px-3.5 py-2 rounded-xl border font-semibold text-xs transition-all hover:scale-105 active:scale-95 flex items-center gap-1.5 shadow-sm hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400"
                  style={{
                    background: 'var(--panel-bg)',
                    borderColor: 'var(--line)',
                    color: 'var(--text)',
                  }}
                  title={t('sign_out')}
                >
                  <LogOut size={14} className="text-red-400" />
                  <span>{t('sign_out')}</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="px-4 py-2 rounded-xl border font-semibold text-xs transition-all hover:border-[var(--accent)] hover:scale-105 active:scale-95 flex items-center gap-1.5 shadow-sm"
                  style={{
                    background: 'var(--panel-bg)',
                    borderColor: 'var(--line)',
                    color: 'var(--text)',
                  }}
                >
                  <LogIn size={14} style={{ color: 'var(--accent)' }} />
                  <span>{t('sign_in')}</span>
                </Link>

                <Link href="/login" className="btn-primary text-xs !py-2 !px-4 hover:scale-105 active:scale-95 shadow-md">
                  {t('explore_demo')} <ArrowRight size={14} />
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 pt-12 pb-20 w-full flex-1 flex flex-col justify-center">
        <div className="text-center max-w-4xl mx-auto space-y-6">
          {/* Pill Badge */}
          <div
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-semibold tracking-wide badge-shimmer animate-fade-in-down"
            style={{
              borderColor: 'var(--tag-border)',
              color: 'var(--accent)',
            }}
          >
            <Sparkles size={14} className="animate-spin-slow" />
            <span>{t('hero_badge')}</span>
          </div>

          {/* Animated Headline */}
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight leading-[1.1] animate-fade-in-up">
            <span>{t('hero_line1')}</span>
            <br />
            <span>{t('hero_line2')}</span>
            <br />
            <span className="text-flow">
              {t('hero_line3')}
            </span>
          </h1>

          <p
            className="text-base sm:text-xl max-w-2xl mx-auto leading-relaxed animate-fade-in-up delay-1"
            style={{ color: 'var(--muted)' }}
          >
            {t('hero_desc')}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-2 animate-fade-in-up delay-2">
            <Link href="/login" className="btn-primary text-sm !px-6 !py-3 group shadow-xl hover:scale-105">
              {t('launch_workspace')}
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
            <Link href="/register" className="btn-secondary text-sm !px-6 !py-3 hover:scale-105">
              {t('create_enterprise_account')}
            </Link>
          </div>

          {/* Quick Demo Credentials Banner */}
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs border max-w-md mx-auto animate-fade-in-up delay-3 transition-transform hover:scale-105 cursor-pointer shadow-sm"
            style={{
              background: 'var(--panel-bg)',
              borderColor: 'var(--line)',
            }}
          >
            <Lock size={13} style={{ color: 'var(--accent)' }} />
            <span className="muted font-mono">{t('demo_banner')}</span>
          </div>
        </div>

        {/* -------------------------------------------------------------
            HUGE ANIMATED GRAPHIC STAGE
           ------------------------------------------------------------- */}
        <div className="animate-fade-in-up delay-3">
          <HeroCloudGraphic />
        </div>

        {/* Live Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 max-w-5xl mx-auto w-full">
          {[
            ['$2.4M+', t('metric_spend'), TrendingDown],
            ['34.2%', t('metric_savings'), Zap],
            ['100%', t('metric_telemetry'), ShieldCheck],
            ['13/13', t('metric_phases'), Cloud],
          ].map(([val, label, Icon]: any, i: number) => (
            <div
              key={label}
              className={`panel panel-hover p-5 text-center space-y-1 animate-fade-in-up delay-${i + 1}`}
            >
              <div
                className="text-2xl sm:text-3xl font-extrabold tracking-tight transition-transform hover:scale-105"
                style={{ color: 'var(--accent)' }}
              >
                {val}
              </div>
              <div className="text-xs font-medium muted">{label}</div>
            </div>
          ))}
        </div>

        {/* Feature Cards Grid with Floating Icons */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-10 max-w-6xl mx-auto w-full">
          {[
            {
              icon: Cloud,
              title: t('feature_connectors'),
              desc: t('feature_connectors_desc'),
            },
            {
              icon: Brain,
              title: t('feature_analyst'),
              desc: t('feature_analyst_desc'),
            },
            {
              icon: Leaf,
              title: t('feature_carbon'),
              desc: t('feature_carbon_desc'),
            },
            {
              icon: Server,
              title: t('feature_iac'),
              desc: t('feature_iac_desc'),
            },
          ].map((item, i: number) => (
            <div
              key={item.title}
              className={`panel panel-hover p-6 flex flex-col justify-between space-y-4 group animate-fade-in-up delay-${i + 2}`}
            >
              <div>
                <div
                  className="h-12 w-12 rounded-xl flex items-center justify-center mb-4 transition-all duration-300 group-hover:scale-110 shadow"
                  style={{
                    background: 'var(--tag-bg)',
                    border: '1px solid var(--tag-border)',
                  }}
                >
                  <item.icon size={22} className="animate-float" style={{ color: 'var(--accent)' }} />
                </div>
                <h3 className="font-bold text-base tracking-tight" style={{ color: 'var(--text)' }}>
                  {item.title}
                </h3>
                <p className="text-xs leading-relaxed mt-2" style={{ color: 'var(--muted)' }}>
                  {item.desc}
                </p>
              </div>
              <div
                className="text-[11px] font-semibold flex items-center gap-1.5 transition-transform group-hover:translate-x-1"
                style={{ color: 'var(--accent)' }}
              >
                <span>{t('verified_working')}</span>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer
        className="border-t py-6 px-6 text-center text-xs transition-colors"
        style={{
          borderColor: 'var(--line)',
          background: 'var(--header-bg)',
          color: 'var(--muted)',
        }}
      >
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            © 2026 <b>CloudSense AI</b>. Enterprise Cloud Cost Intelligence & Carbon Provenance.
          </div>
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="hover:underline hover:text-[var(--accent)] transition-colors">Dashboard</Link>
            <Link href="/iac" className="hover:underline hover:text-[var(--accent)] transition-colors">IaC Estimator</Link>
            <Link href="/assistant" className="hover:underline hover:text-[var(--accent)] transition-colors">AI Analyst</Link>
            <Link href="/settings" className="hover:underline hover:text-[var(--accent)] transition-colors">Security</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
