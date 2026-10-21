'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { api } from '../lib/api';

import {
  Cloud,
  LayoutDashboard,
  WalletCards,
  LineChart,
  TriangleAlert,
  Lightbulb,
  Server,
  ShieldCheck,
  Leaf,
  Settings,
  MessageSquare,
  FileText,
  Activity,
  LogOut,
  Search,
  Sun,
  Moon,
  Menu,
  X,
  Sparkles,
  Command,
} from 'lucide-react';
import { useTheme } from '../lib/theme';
import { useI18n } from '../lib/i18n';
import { useCurrency } from '../lib/currency';
import ThemeToggleSwitch from './ThemeToggleSwitch';
import LanguageSelector from './LanguageSelector';
import CurrencySelector from './CurrencySelector';


let memCachedUser: any = null;
let lastUserFetch = 0;

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggleTheme, mounted } = useTheme();
  const { t } = useI18n();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [rotating, setRotating] = useState(false);

  const navGroups = [
    {
      label: t('nav_overview'),
      items: [
        [t('nav_dashboard'), '/dashboard', LayoutDashboard],
        [t('nav_cloud_accounts'), '/cloud-accounts', Cloud],
        [t('nav_costs'), '/costs', WalletCards],
        [t('nav_budgets'), '/budgets', WalletCards],
        [t('nav_alerts'), '/alerts', TriangleAlert],
      ] as const,
    },
    {
      label: t('nav_intelligence'),
      items: [
        [t('nav_assistant'), '/assistant', MessageSquare],
        [t('nav_optimization'), '/optimization', Lightbulb],
        [t('nav_iac'), '/iac', Server],
        [t('nav_forecast'), '/forecast', LineChart],
        [t('nav_anomalies'), '/anomalies', TriangleAlert],
        [t('nav_rca'), '/rca', Activity],
        [t('nav_scaling'), '/scaling', LineChart],
      ] as const,
    },
    {
      label: t('nav_governance'),
      items: [
        [t('nav_carbon'), '/carbon', Leaf],
        [t('nav_system'), '/system', Activity],
        [t('nav_security'), '/security', ShieldCheck],
        [t('nav_sla'), '/sla', Activity],
        [t('nav_reports'), '/reports', FileText],
        [t('nav_settings'), '/settings', Settings],
      ] as const,
    },
  ];
  const [currentUser, setCurrentUser] = useState<{
    id?: string;
    email: string;
    name?: string;
    role: string;
    organization_name?: string;
    privilege?: {
      title: string;
      above?: string;
      tier: string;
      badge_color?: string;
      badge_class?: string;
      tag?: string;
      description?: string;
      capabilities?: string[];
    };
  } | null>(() => {
    if (memCachedUser) return memCachedUser;
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('user');
        if (stored) {
          memCachedUser = JSON.parse(stored);
          return memCachedUser;
        }
      } catch {}
    }
    return null;
  });

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) {
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        router.push('/login');
      }
      return;
    }

    const now = Date.now();
    // Fast cache: skip redundant network request if user verified within the last 45 seconds
    if (memCachedUser && now - lastUserFetch < 45000) {
      return;
    }

    api('/api/auth/me')
      .then((me) => {
        if (me?.email) {
          memCachedUser = me;
          lastUserFetch = Date.now();
          setCurrentUser(me);
          try {
            localStorage.setItem('user', JSON.stringify(me));
          } catch {}
        }
      })
      .catch(() => {
        if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
          router.push('/login');
        }
      });
  }, [router]);

  const handleLogout = async () => {
    memCachedUser = null;
    lastUserFetch = 0;
    try {
      await api('/api/auth/logout', { method: 'POST' }).catch(() => {});
    } catch {}
    try {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    } catch {}
    router.push('/login');
  };

  const handleThemeToggle = () => {
    setRotating(true);
    toggleTheme();
    setTimeout(() => setRotating(false), 450);
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden animate-fade-in-down"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 flex flex-col border-r transition-all duration-300 ease-out lg:translate-x-0 ${
          mobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
        }`}
        style={{
          background: 'var(--sidebar-bg)',
          borderColor: 'var(--line)',
          backdropFilter: 'blur(20px)',
        }}
      >
        {/* Brand Header */}
        <div className="p-5 border-b flex items-center justify-between" style={{ borderColor: 'var(--line)' }}>
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div
              className="h-10 w-10 rounded-xl flex items-center justify-center transition-all duration-300 group-hover:scale-110 group-hover:rotate-3 shadow-lg"
              style={{
                background: 'linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%)',
                boxShadow: '0 4px 14px rgba(65, 105, 225, 0.5)',
              }}

            >
              <Cloud className="text-white transition-transform group-hover:scale-110" size={22} />
            </div>
            <div>
              <div className="font-bold text-base tracking-tight flex items-center gap-1.5">
                <span>CloudSense</span>
                <span
                  className="text-[11px] px-1.5 py-0.5 rounded-md font-bold badge-shimmer"
                  style={{
                    color: 'var(--accent)',
                    border: '1px solid var(--tag-border)',
                  }}
                >
                  AI
                </span>
              </div>
              <div className="text-[10px] tracking-wider font-semibold muted uppercase">
                Enterprise FinOps
              </div>
            </div>
          </Link>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="lg:hidden p-1.5 rounded-lg muted hover:text-white transition-transform hover:scale-110"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation Items (Categorized with micro-animations) */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navGroups.map((group) => (
            <div key={group.label} className="space-y-1">
              <div className="px-3 text-[11px] font-bold tracking-wider uppercase muted">
                {group.label}
              </div>
              <div className="space-y-0.5 mt-1.5">
                {group.items.map(([name, href, Icon]) => {
                  const isActive = pathname === href;
                  return (
                    <Link
                      key={href}
                      href={href}
                      prefetch={true}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all duration-200 group ${
                        isActive
                          ? 'shadow-md translate-x-1'
                          : 'hover:translate-x-1.5 hover:bg-white/5'
                      }`}
                      style={{
                        background: isActive ? 'var(--tag-bg)' : 'transparent',
                        color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                        border: isActive ? '1px solid var(--tag-border)' : '1px solid transparent',
                        fontWeight: isActive ? 600 : 500,
                      }}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon
                          size={17}
                          className="transition-transform duration-200 group-hover:scale-110"
                          style={{ color: isActive ? 'var(--accent)' : 'var(--muted)' }}
                        />
                        <span>{name}</span>
                      </div>
                      {isActive ? (
                        <div
                          className="w-2 h-2 rounded-full relative"
                          style={{ background: 'var(--accent)', boxShadow: '0 0 10px var(--accent)' }}
                        >
                          <span className="animate-ping absolute inset-0 rounded-full bg-cyan-400 opacity-75" />
                        </div>
                      ) : (
                        <span className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] muted">
                          →
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Sidebar Footer with Clean Authenticated User Identity */}
        <div className="p-3 border-t" style={{ borderColor: 'var(--line)' }}>
          {currentUser ? (
            <div
              className="p-3 rounded-2xl border transition-all duration-200 hover:border-blue-400/50 flex items-center justify-between gap-2 shadow-sm"
              style={{
                background: 'var(--panel-bg)',
                borderColor: 'var(--tag-border)',
              }}
            >
              <div className="flex items-center gap-2.5 overflow-hidden">
                <div
                  className="h-8 w-8 rounded-lg flex items-center justify-center font-bold text-xs shadow text-white shrink-0"
                  style={{
                    background: 'linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%)',
                  }}
                >
                  {(currentUser.name?.[0] || currentUser.email?.[0] || 'U').toUpperCase()}
                </div>
                <div className="overflow-hidden">
                  <div className="text-xs font-bold truncate text-white" title={currentUser.name || currentUser.email}>
                    {currentUser.name || currentUser.email.split('@')[0]}
                  </div>
                  <div className="text-[10px] muted truncate" title={currentUser.email}>
                    {currentUser.email}
                  </div>
                  <div className="text-[9px] font-semibold text-sky-400 uppercase tracking-wider">
                    {currentUser.role || 'MEMBER'}
                  </div>
                </div>
              </div>

              <button
                onClick={handleLogout}
                title={t('sign_out')}
                className="p-1.5 rounded-lg muted hover:text-red-400 hover:scale-110 transition-all shrink-0"
              >
                <LogOut size={15} />
              </button>
            </div>
          ) : (
            <div className="text-center py-1">
              <Link
                href="/login"
                className="text-xs font-semibold text-sky-400 hover:underline"
              >
                {t('sign_in')}
              </Link>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="lg:ml-72 flex-1 flex flex-col min-w-0">
        {/* Top Sticky Header */}
        <header
          className="h-16 border-b flex items-center justify-between px-5 md:px-8 sticky top-0 z-30 transition-colors"
          style={{
            background: 'var(--header-bg)',
            borderColor: 'var(--line)',
            backdropFilter: 'blur(16px)',
          }}
        >
          {/* Left: Mobile trigger & Search */}
          <div className="flex items-center gap-3 flex-1 max-w-md">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 rounded-lg muted hover:text-white transition-transform active:scale-95"
              style={{ background: 'var(--tag-bg)', border: '1px solid var(--line)' }}
            >
              <Menu size={20} />
            </button>

            <div
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl border text-xs w-full max-w-sm transition-all duration-200 focus-within:border-[var(--accent)] focus-within:shadow-md"
              style={{
                background: 'var(--input-bg)',
                borderColor: 'var(--line)',
              }}
            >
              <Search size={15} className="muted" />
              <input
                type="text"
                placeholder={t('search_placeholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent border-none outline-none w-full text-xs"
                style={{ color: 'var(--text)' }}
              />
              <kbd
                className="hidden sm:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono muted border"
                style={{ borderColor: 'var(--line)', background: 'var(--tag-bg)' }}
              >
                ⌘K
              </kbd>
            </div>
          </div>

          {/* Right: Language, Currency, Theme Toggle, Live Status, Identity, Workspace */}
          <div className="flex items-center gap-2.5 text-xs">
            {/* Multi-Language & Country Currency Selectors */}
            <LanguageSelector compact />
            <CurrencySelector compact />

            {/* Real Physical Animated Pill Toggle Switch */}
            <ThemeToggleSwitch />



            {/* Prominent Sign Out Button */}
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all hover:scale-105 active:scale-95 hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400"
              style={{
                background: 'var(--tag-bg)',
                borderColor: 'var(--line)',
                color: 'var(--text)',
              }}
              title={t('sign_out')}
            >
              <LogOut size={14} className="text-red-400" />
              <span>{t('sign_out')}</span>
            </button>
          </div>
        </header>


        {/* Page Content Body with Entrance Animation */}
        <div className="p-5 md:p-8 max-w-[1600px] w-full mx-auto flex-1 animate-fade-in-up">
          {children}
        </div>
      </main>
    </div>
  );
}
