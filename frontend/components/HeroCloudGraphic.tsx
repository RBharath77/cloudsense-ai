'use client';

import React, { useEffect, useState } from 'react';
import {
  Cloud,
  Brain,
  ShieldCheck,
  Zap,
  TrendingDown,
  Activity,
  Server,
  Leaf,
  Sparkles,
  ArrowUpRight,
  Database,
  Cpu,
} from 'lucide-react';

export default function HeroCloudGraphic() {
  const [tickerSpend, setTickerSpend] = useState(30170);
  const [savingsTicker, setSavingsTicker] = useState(8420);
  const [photonPos, setPhotonPos] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setTickerSpend((prev) => prev + (Math.floor(Math.random() * 5) - 2));
      setSavingsTicker((prev) => prev + (Math.random() > 0.6 ? 1 : 0));
    }, 1800);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative w-full max-w-5xl mx-auto my-8 select-none">
      {/* Outer Glow Halo in Royal Blue */}
      <div
        className="absolute inset-0 rounded-3xl blur-[90px] opacity-45 pointer-events-none animate-pulse-glow"
        style={{
          background: 'radial-gradient(circle, #4169E1 0%, #1E3A8A 60%, transparent 80%)',
        }}
      />

      {/* Cybernetic Stage Container in Royal Midnight */}
      <div
        className="relative w-full h-[520px] rounded-3xl border overflow-hidden backdrop-blur-2xl transition-all duration-300"
        style={{
          background: 'radial-gradient(ellipse at 50% 50%, rgba(30, 58, 138, 0.45) 0%, rgba(8, 16, 38, 0.95) 75%)',
          borderColor: 'rgba(65, 105, 225, 0.45)',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.7), inset 0 0 40px rgba(65, 105, 225, 0.15)',
        }}
      >

        {/* Animated Cyber Grid Floor */}
        <div
          className="absolute inset-x-0 bottom-0 h-44 opacity-25 pointer-events-none"
          style={{
            backgroundImage: `linear-gradient(to right, rgba(90, 169, 230, 0.2) 1px, transparent 1px),
                              linear-gradient(to bottom, rgba(90, 169, 230, 0.2) 1px, transparent 1px)`,
            backgroundSize: '36px 36px',
            transform: 'perspective(400px) rotateX(60deg)',
            transformOrigin: 'bottom',
          }}
        />

        {/* Ambient Floating Dust Particles */}
        <div className="absolute top-12 left-1/4 w-2 h-2 rounded-full bg-cyan-300 animate-ping opacity-60" />
        <div className="absolute top-28 right-1/3 w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping opacity-50 delay-300" />
        <div className="absolute bottom-20 left-1/3 w-2 h-2 rounded-full bg-emerald-400 animate-ping opacity-40 delay-500" />

        {/* SVG Fiber Beams and Data Circuits */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="beamGradientAWS" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FF9900" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#5AA9E6" stopOpacity="0.2" />
            </linearGradient>
            <linearGradient id="beamGradientAzure" x1="100%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#0078D4" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#5AA9E6" stopOpacity="0.2" />
            </linearGradient>
            <linearGradient id="beamGradientGCP" x1="0%" y1="100%" x2="50%" y2="50%">
              <stop offset="0%" stopColor="#34A853" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#5AA9E6" stopOpacity="0.2" />
            </linearGradient>
            <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Circuit Lines to Center (Center is roughly at 50% 50% => 500, 260) */}
          <path
            d="M 200 130 C 320 130, 400 220, 500 260"
            fill="none"
            stroke="url(#beamGradientAWS)"
            strokeWidth="2.5"
            strokeDasharray="6 8"
            className="animate-pulse"
          />
          <path
            d="M 800 130 C 680 130, 600 220, 500 260"
            fill="none"
            stroke="url(#beamGradientAzure)"
            strokeWidth="2.5"
            strokeDasharray="6 8"
            className="animate-pulse"
          />
          <path
            d="M 280 400 C 380 400, 440 320, 500 260"
            fill="none"
            stroke="url(#beamGradientGCP)"
            strokeWidth="2.5"
            strokeDasharray="6 8"
            className="animate-pulse"
          />
        </svg>

        {/* -------------------------------------------------------------
            CENTRAL AI NEURAL CORE
           ------------------------------------------------------------- */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center justify-center">
          {/* Outermost Radar Expanding Ring */}
          <div className="absolute w-72 h-72 rounded-full border border-cyan-400/25 animate-ping opacity-25" />
          <div className="absolute w-60 h-60 rounded-full border border-cyan-300/30 animate-pulse-glow" />

          {/* Counter-Rotating Dashed Cyber Rings */}
          <div
            className="absolute w-48 h-48 rounded-full border-2 border-dashed border-cyan-400/40 animate-spin-slow"
            style={{ animationDuration: '28s' }}
          />
          <div
            className="absolute w-40 h-40 rounded-full border border-dashed border-blue-300/50 animate-spin-slow"
            style={{ animationDirection: 'reverse', animationDuration: '18s' }}
          />

          {/* Central Glowing Core Orb in Royal Blue & White */}
          <div
            className="relative z-10 w-24 h-24 rounded-2xl flex flex-col items-center justify-center shadow-2xl cursor-pointer group transition-all duration-300 hover:scale-110"
            style={{
              background: 'linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%)',
              boxShadow: '0 0 40px rgba(65, 105, 225, 0.85), inset 0 0 15px rgba(255, 255, 255, 0.5)',
            }}
          >
            <Brain size={38} className="text-white animate-pulse" />
            <span className="text-[9px] font-extrabold tracking-wider text-white uppercase mt-1">
              AI CORE
            </span>
          </div>

          {/* Core Info Chip in Royal Blue & Pure White */}
          <div
            className="relative z-10 mt-4 px-3 py-1 rounded-full border backdrop-blur-md text-[11px] font-semibold flex items-center gap-2 shadow-lg"
            style={{
              background: 'rgba(30, 58, 138, 0.85)',
              borderColor: 'rgba(65, 105, 225, 0.6)',
              color: '#FFFFFF',
            }}
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
        </div>


        {/* -------------------------------------------------------------
            ORBITING PROVIDER NODE 1: AWS (Top Left)
           ------------------------------------------------------------- */}
        <div
          className="absolute top-12 left-8 sm:left-14 p-3.5 rounded-2xl border backdrop-blur-xl flex items-center gap-3 shadow-xl transition-all duration-300 hover:scale-105 animate-float"
          style={{
            background: 'rgba(26, 34, 48, 0.88)',
            borderColor: 'rgba(255, 153, 0, 0.4)',
            boxShadow: '0 10px 25px rgba(255, 153, 0, 0.15)',
          }}
        >
          <div
            className="h-10 w-10 rounded-xl flex items-center justify-center font-bold text-xs"
            style={{
              background: 'linear-gradient(135deg, #FF9900 0%, #FFB84D 100%)',
              color: '#111827',
            }}
          >
            <Cloud size={20} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-white">AWS Production</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-mono">
                us-east-1
              </span>
            </div>
            <div className="text-[11px] font-semibold text-emerald-400 flex items-center gap-1 mt-0.5">
              <span>$14,820/mo</span>
              <span className="text-slate-400 font-normal">· CUR Syncing</span>
            </div>
          </div>
        </div>

        {/* -------------------------------------------------------------
            ORBITING PROVIDER NODE 2: Azure (Top Right)
           ------------------------------------------------------------- */}
        <div
          className="absolute top-12 right-8 sm:right-14 p-3.5 rounded-2xl border backdrop-blur-xl flex items-center gap-3 shadow-xl transition-all duration-300 hover:scale-105 animate-float delay-1"
          style={{
            background: 'rgba(26, 34, 48, 0.88)',
            borderColor: 'rgba(0, 120, 212, 0.45)',
            boxShadow: '0 10px 25px rgba(0, 120, 212, 0.2)',
          }}
        >
          <div
            className="h-10 w-10 rounded-xl flex items-center justify-center font-bold text-xs"
            style={{
              background: 'linear-gradient(135deg, #0078D4 0%, #50E6FF 100%)',
              color: '#FFFFFF',
            }}
          >
            <Database size={20} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-white">Azure Enterprise</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-300 font-mono">
                East US 2
              </span>
            </div>
            <div className="text-[11px] font-semibold text-cyan-300 flex items-center gap-1 mt-0.5">
              <span>$9,240/mo</span>
              <span className="text-slate-400 font-normal">· OAuth Active</span>
            </div>
          </div>
        </div>

        {/* -------------------------------------------------------------
            ORBITING PROVIDER NODE 3: GCP Kubernetes (Bottom Left)
           ------------------------------------------------------------- */}
        <div
          className="absolute bottom-12 left-10 sm:left-16 p-3.5 rounded-2xl border backdrop-blur-xl flex items-center gap-3 shadow-xl transition-all duration-300 hover:scale-105 animate-float delay-2"
          style={{
            background: 'rgba(26, 34, 48, 0.88)',
            borderColor: 'rgba(52, 168, 83, 0.45)',
            boxShadow: '0 10px 25px rgba(52, 168, 83, 0.15)',
          }}
        >
          <div
            className="h-10 w-10 rounded-xl flex items-center justify-center font-bold text-xs"
            style={{
              background: 'linear-gradient(135deg, #34A853 0%, #4285F4 100%)',
              color: '#FFFFFF',
            }}
          >
            <Server size={20} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-white">GCP Kubernetes</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                us-central1
              </span>
            </div>
            <div className="text-[11px] font-semibold text-emerald-400 flex items-center gap-1 mt-0.5">
              <span>$6,110/mo</span>
              <span className="text-slate-400 font-normal">· GKE & Pods</span>
            </div>
          </div>
        </div>

        {/* -------------------------------------------------------------
            HOLOGRAPHIC FINOPS BADGE 1: Shift-Left IaC Gate (Bottom Right)
           ------------------------------------------------------------- */}
        <div
          className="absolute bottom-12 right-10 sm:right-16 p-3.5 rounded-2xl border backdrop-blur-xl flex items-center gap-3 shadow-xl transition-all duration-300 hover:scale-105 animate-float delay-3"
          style={{
            background: 'rgba(26, 34, 48, 0.88)',
            borderColor: 'rgba(90, 169, 230, 0.45)',
            boxShadow: '0 10px 25px rgba(90, 169, 230, 0.2)',
          }}
        >
          <div
            className="h-10 w-10 rounded-xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #1F3A5F 0%, #5AA9E6 100%)',
              color: '#FFFFFF',
            }}
          >
            <ShieldCheck size={20} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-white">Shift-Left PR Gate</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                PASSED
              </span>
            </div>
            <div className="text-[11px] font-semibold text-cyan-300 mt-0.5">
              <span>Δ -$410/mo · 0 Security Flags</span>
            </div>
          </div>
        </div>

        {/* -------------------------------------------------------------
            TOP CENTER LIVE FINOPS TICKER BAR
           ------------------------------------------------------------- */}
        <div
          className="absolute top-4 inset-x-0 mx-auto w-fit px-4 py-1.5 rounded-full border backdrop-blur-xl flex items-center gap-4 text-xs font-medium shadow-md transition-all hover:scale-105"
          style={{
            background: 'rgba(20, 26, 36, 0.85)',
            borderColor: 'rgba(90, 169, 230, 0.3)',
            color: '#EAF4F4',
          }}
        >
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase font-bold text-slate-400">Total Spend:</span>
            <span className="font-mono font-bold text-cyan-300">
              ${tickerSpend.toLocaleString()}
            </span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase font-bold text-slate-400">Realized Savings:</span>
            <span className="font-mono font-bold text-emerald-400">
              +${savingsTicker.toLocaleString()}/mo
            </span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5">
            <Leaf size={13} className="text-emerald-400" />
            <span className="font-mono text-emerald-300 font-bold">-38% CO₂e</span>
          </div>
        </div>
      </div>
    </div>
  );
}
