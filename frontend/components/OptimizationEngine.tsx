'use client';

import { useState, useEffect } from 'react';
import { api } from '../lib/api';

interface EvidenceData {
  metric?: string;
  avg_cpu_pct?: number;
  max_cpu_pct?: number;
  sample_count?: number;
  observation_window?: string;
  resource_name?: string;
  provider?: string;
  region?: string;
  raw?: string;
}

interface RecommendationItem {
  id: string;
  resource_id: string;
  category: string;
  current_cost: number;
  problem: string;
  action: string;
  recommendation: string;
  monthly_saving: number;
  yearly_saving: number;
  monthly_carbon_saving_kg: number;
  risk: string;
  confidence: number;
  action_status: string;
  priority_score: number;
  evidence: EvidenceData | null;
  assumptions: string;
  trade_offs: string;
}

interface OptimizationSummary {
  total_recommendations: number;
  total_monthly_cost_saving: number;
  total_yearly_cost_saving: number;
  total_monthly_carbon_saving_kg: number;
  total_yearly_carbon_saving_mt: number;
}

interface SimulationRecord {
  id: string;
  name: string;
  scenario_type: string;
  created_at: string;
  pricing_source: string;
  factor_source: string;
  results: {
    baseline_monthly_spend?: number;
    simulated_monthly_spend?: number;
    monthly_cost_saving?: number;
    cost_saving_pct?: number;
    baseline_monthly_carbon_kg?: number;
    simulated_monthly_carbon_kg?: number;
    monthly_carbon_saving_kg?: number;
    carbon_saving_pct?: number;
    payback_period_months?: number;
    risk_level?: string;
    is_read_only_simulation?: boolean;
  };
}

interface SavingsLedgerEntry {
  id: string;
  title: string;
  resource_id: string;
  category: string;
  savings_type: string;
  status: string;
  expected_monthly_cost_saving: number;
  verified_cost_saving: number;
  expected_monthly_carbon_saving_kg: number;
  verified_carbon_saving_kg: number;
  measurement_window_start: string | null;
  measurement_window_end: string | null;
  caveats: string | null;
  notes: string | null;
  created_at: string;
}

interface SavingsSummary {
  total_entries: number;
  total_expected_monthly_cost_saving: number;
  total_verified_monthly_cost_saving: number;
  cost_realization_rate_pct: number;
  total_expected_monthly_carbon_saving_kg: number;
  total_verified_monthly_carbon_saving_kg: number;
  carbon_realization_rate_pct: number;
  entries_with_caveats_count: number;
}

export function OptimizationEngine() {
  const [activeTab, setActiveTab] = useState<'recommendations' | 'simulator' | 'ledger'>('recommendations');
  const [priority, setPriority] = useState<string>('BALANCE');
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [summary, setSummary] = useState<OptimizationSummary | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [formula, setFormula] = useState<string>('');
  const [priorityName, setPriorityName] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [expandedRecId, setExpandedRecId] = useState<string | null>(null);

  // Simulator state
  const [scenarioType, setScenarioType] = useState<string>('RIGHTSIZING');
  const [scenarioName, setScenarioName] = useState<string>('');
  const [downsizePct, setDownsizePct] = useState<number>(40);
  const [offHoursPerWeek, setOffHoursPerWeek] = useState<number>(56);
  const [termYears, setTermYears] = useState<number>(1);
  const [coveragePct, setCoveragePct] = useState<number>(75);
  const [targetRegion, setTargetRegion] = useState<string>('us-west-2');
  const [simResults, setSimResults] = useState<any | null>(null);
  const [simHistory, setSimHistory] = useState<SimulationRecord[]>([]);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simMessage, setSimMessage] = useState<string>('');

  // Ledger state
  const [ledgerEntries, setLedgerEntries] = useState<SavingsLedgerEntry[]>([]);
  const [ledgerSummary, setLedgerSummary] = useState<SavingsSummary | null>(null);
  const [showLedgerModal, setShowLedgerModal] = useState<boolean>(false);
  const [newLedgerTitle, setNewLedgerTitle] = useState<string>('');
  const [newLedgerCategory, setNewLedgerCategory] = useState<string>('RIGHTSIZING');
  const [newLedgerExpected, setNewLedgerExpected] = useState<string>('300.00');
  const [newLedgerVerified, setNewLedgerVerified] = useState<string>('0.00');
  const [newLedgerCaveats, setNewLedgerCaveats] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  const loadData = async (activePriority = priority) => {
    try {
      setLoading(true);
      setError('');

      const optData = await api(`/api/optimization?priority=${activePriority}`);
      if (optData.recommendations) {
        setRecommendations(optData.recommendations);
        setSummary(optData.summary);
        setWeights(optData.scoring_weights || {});
        setFormula(optData.scoring_formula || '');
        setPriorityName(optData.priority_name || '');
      } else if (Array.isArray(optData)) {
        setRecommendations(optData);
      }

      const simList = await api('/api/optimization/simulations');
      setSimHistory(simList || []);

      const ledgerSum = await api('/api/optimization/ledger/summary');
      setLedgerSummary(ledgerSum || null);

      const ledgerList = await api('/api/optimization/ledger');
      setLedgerEntries(ledgerList || []);
    } catch (err: any) {
      console.error('Error loading optimization data:', err);
      setError('Failed to load optimization records from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(priority);
  }, [priority]);

  const handlePriorityChange = (newPriority: string) => {
    setPriority(newPriority);
  };

  const handleRunSimulation = async (presetRecommendationId?: string) => {
    try {
      setSimulating(true);
      setSimMessage('');

      const payload = presetRecommendationId
        ? {
            scenario_type: 'RECOMMENDATION',
            name: `What-If Simulation for Recommendation`,
            recommendation_id: presetRecommendationId,
          }
        : {
            scenario_type: scenarioType,
            name: scenarioName || `${scenarioType} Simulation Model`,
            downsize_percentage: downsizePct,
            off_hours_per_week: offHoursPerWeek,
            term_years: termYears,
            coverage_pct: coveragePct,
            target_region: targetRegion,
          };

      const result = await api('/api/optimization/simulate', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setSimResults(result);
      setSimMessage('Simulation executed successfully. Read-only model recorded with zero infrastructure alterations.');

      // Refresh history
      const updatedSims = await api('/api/optimization/simulations');
      setSimHistory(updatedSims || []);
      setActiveTab('simulator');
    } catch (err: any) {
      console.error('Simulation error:', err);
      setSimMessage('Simulation calculation failed.');
    } finally {
      setSimulating(false);
    }
  };

  const handleCreateLedgerEntry = async () => {
    if (!newLedgerTitle) return;
    try {
      await api('/api/optimization/ledger', {
        method: 'POST',
        body: JSON.stringify({
          title: newLedgerTitle,
          category: newLedgerCategory,
          resource_id: 'res-custom',
          savings_type: Number(newLedgerVerified) > 0 ? 'VERIFIED' : 'EXPECTED',
          status: Number(newLedgerVerified) > 0 ? 'REALIZED' : 'PLANNED',
          expected_monthly_cost_saving: parseFloat(newLedgerExpected) || 0,
          verified_cost_saving: parseFloat(newLedgerVerified) || 0,
          caveats: newLedgerCaveats,
        }),
      });

      setShowLedgerModal(false);
      setNewLedgerTitle('');
      setNewLedgerCaveats('');

      // Refresh ledger
      const sum = await api('/api/optimization/ledger/summary');
      setLedgerSummary(sum);
      const list = await api('/api/optimization/ledger');
      setLedgerEntries(list);
    } catch (err) {
      console.error('Failed to create ledger entry:', err);
    }
  };

  const filteredRecs = recommendations.filter((r) => {
    if (selectedCategory === 'ALL') return true;
    return r.category === selectedCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header & Priority Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>⚡ Optimization & What-If Simulator</span>
          </h1>
          <p className="text-sm muted mt-1">
            Evidence-backed recommendations, read-only what-if simulations, and verified savings ledger.
          </p>
        </div>

        {/* Priority Filter Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-900/80 border border-slate-800 rounded-xl">
          {[
            { id: 'BALANCE', label: '⚖️ Balanced', hint: 'FinOps & GreenOps' },
            { id: 'COST', label: '💰 Cost First', hint: 'Max Dollar Savings' },
            { id: 'EMISSIONS', label: '🌿 Green First', hint: 'Max Decarbonization' },
            { id: 'RISK_AVOIDANT', label: '🛡️ Low Risk', hint: 'High Confidence' },
          ].map((mode) => (
            <button
              key={mode.id}
              onClick={() => handlePriorityChange(mode.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                priority === mode.id
                  ? 'bg-cyan-500 text-slate-950 shadow-sm font-semibold'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>
      </div>

      {/* Priority Scoring Metadata Banner */}
      <div className="panel px-4 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs border border-cyan-500/20 bg-cyan-950/20">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
          <span className="font-semibold text-cyan-200">Active Priority: {priorityName}</span>
          <span className="muted hidden sm:inline">—</span>
          <span className="text-slate-300 font-mono text-[11px]">{formula}</span>
        </div>
        <div className="flex items-center gap-3 text-slate-400">
          <span>Weights:</span>
          {Object.entries(weights).map(([k, v]) => (
            <span key={k} className="bg-slate-900/90 border border-slate-800 px-2 py-0.5 rounded text-[11px]">
              <b className="capitalize text-slate-200">{k}</b>: {(v * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="panel p-4">
          <div className="text-xs uppercase tracking-wider muted font-semibold">Potential Cost Savings</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            ${summary?.total_monthly_cost_saving.toLocaleString() || '0'}/mo
          </div>
          <div className="text-xs muted mt-1">
            ${summary?.total_yearly_cost_saving.toLocaleString() || '0'}/yr run-rate
          </div>
        </div>

        <div className="panel p-4">
          <div className="text-xs uppercase tracking-wider muted font-semibold">Potential Carbon Avoidance</div>
          <div className="text-2xl font-bold text-teal-300 mt-1">
            {summary?.total_monthly_carbon_saving_kg.toFixed(1) || '0.0'} kgCO2e/mo
          </div>
          <div className="text-xs muted mt-1">
            {summary?.total_yearly_carbon_saving_mt.toFixed(2) || '0.00'} MT avoided annually
          </div>
        </div>

        <div className="panel p-4">
          <div className="text-xs uppercase tracking-wider muted font-semibold">Realized Savings Rate</div>
          <div className="text-2xl font-bold text-cyan-300 mt-1">
            {ledgerSummary?.cost_realization_rate_pct.toFixed(1) || '0.0'}%
          </div>
          <div className="text-xs muted mt-1">
            ${ledgerSummary?.total_verified_monthly_cost_saving.toFixed(0) || '0'} verified of ${ledgerSummary?.total_expected_monthly_cost_saving.toFixed(0) || '0'} expected
          </div>
        </div>

        <div className="panel p-4">
          <div className="text-xs uppercase tracking-wider muted font-semibold">Actionable Recommendations</div>
          <div className="text-2xl font-bold text-white mt-1">
            {summary?.total_recommendations || recommendations.length}
          </div>
          <div className="text-xs muted mt-1">
            {ledgerSummary?.entries_with_caveats_count || 0} initiatives with operational caveats
          </div>
        </div>
      </div>

      {/* Main Navigation Tabs */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('recommendations')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'recommendations'
              ? 'border-cyan-400 text-cyan-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Recommendations ({recommendations.length})
        </button>
        <button
          onClick={() => setActiveTab('simulator')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'simulator'
              ? 'border-cyan-400 text-cyan-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          What-If Simulator (Read-Only)
        </button>
        <button
          onClick={() => setActiveTab('ledger')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'ledger'
              ? 'border-cyan-400 text-cyan-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Verified Savings Ledger ({ledgerEntries.length})
        </button>
      </div>

      {/* TAB 1: RECOMMENDATIONS */}
      {activeTab === 'recommendations' && (
        <div className="space-y-4">
          {/* Category Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            {['ALL', 'RIGHTSIZING', 'IDLE_RESOURCE', 'COMMITMENT_PURCHASE'].map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-full text-xs transition-colors border ${
                  selectedCategory === cat
                    ? 'bg-slate-800 border-slate-600 text-white font-medium'
                    : 'bg-transparent border-slate-800/80 text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat.replace('_', ' ')}
              </button>
            ))}
          </div>

          {loading && (
            <div className="panel p-8 text-center muted">Loading evidence-backed recommendations...</div>
          )}

          {error && (
            <div className="panel p-4 text-red-400 border border-red-500/20 bg-red-950/20">{error}</div>
          )}

          {!loading && filteredRecs.length === 0 && (
            <div className="panel p-8 text-center muted">
              No recommendations found for the selected category.
            </div>
          )}

          {!loading &&
            filteredRecs.map((rec) => {
              const isExpanded = expandedRecId === rec.id;
              return (
                <div key={rec.id} className="panel p-5 space-y-4 border border-slate-800/80 hover:border-slate-700 transition-all">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-medium">
                          {rec.category.replace('_', ' ')}
                        </span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                            rec.risk === 'LOW'
                              ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                              : rec.risk === 'MEDIUM'
                              ? 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                              : 'bg-red-950/60 text-red-400 border border-red-800/40'
                          }`}
                        >
                          {rec.risk} RISK
                        </span>
                        <span className="text-xs muted font-mono">
                          Score: <b className="text-cyan-300">{rec.priority_score.toFixed(1)}</b>
                        </span>
                      </div>
                      <h3 className="text-base font-semibold text-white mt-1">{rec.problem}</h3>
                      <p className="text-sm text-slate-300">{rec.action}</p>
                    </div>

                    <div className="text-right sm:min-w-[160px] border-l sm:border-slate-800 sm:pl-4">
                      <div className="text-xl font-bold text-emerald-400">
                        ${rec.monthly_saving.toFixed(0)}
                        <span className="text-xs font-normal text-slate-400">/mo</span>
                      </div>
                      <div className="text-xs text-teal-300 font-medium mt-0.5">
                        -{rec.monthly_carbon_saving_kg.toFixed(1)} kgCO2e/mo
                      </div>
                      <div className="text-[11px] muted mt-1">
                        Current: ${rec.current_cost.toFixed(0)}/mo · {(rec.confidence * 100).toFixed(0)}% conf
                      </div>
                    </div>
                  </div>

                  {/* Expandable Accordion: Evidence & Rationale */}
                  {isExpanded && (
                    <div className="pt-3 border-t border-slate-800/80 space-y-3 text-xs bg-slate-900/40 -mx-5 -mb-5 p-5 rounded-b-xl">
                      {rec.evidence && (
                        <div>
                          <div className="font-semibold text-cyan-300 uppercase tracking-wider text-[11px]">
                            Telemetry Evidence (Actual Monitoring Data)
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-1.5 font-mono text-[11px] bg-slate-950/60 p-2.5 rounded border border-slate-800">
                            <div>Avg CPU: <b className="text-white">{rec.evidence.avg_cpu_pct}%</b></div>
                            <div>Peak CPU: <b className="text-white">{rec.evidence.max_cpu_pct}%</b></div>
                            <div>Samples: <b className="text-white">{rec.evidence.sample_count}</b></div>
                            <div>Region: <b className="text-white">{rec.evidence.region}</b></div>
                          </div>
                        </div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                        <div className="bg-slate-950/40 p-2.5 rounded border border-slate-800/80">
                          <span className="font-semibold text-slate-300 block mb-1">Modeling Assumptions:</span>
                          <p className="muted leading-relaxed">{rec.assumptions}</p>
                        </div>
                        <div className="bg-slate-950/40 p-2.5 rounded border border-slate-800/80">
                          <span className="font-semibold text-slate-300 block mb-1">Operational Trade-offs:</span>
                          <p className="muted leading-relaxed">{rec.trade_offs}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <button
                      onClick={() => setExpandedRecId(isExpanded ? null : rec.id)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 font-medium transition-colors"
                    >
                      {isExpanded ? '▲ Hide Telemetry Evidence' : '▼ Inspect Evidence & Assumptions'}
                    </button>

                    <button
                      onClick={() => handleRunSimulation(rec.id)}
                      disabled={simulating}
                      className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs transition-colors flex items-center gap-1.5"
                    >
                      <span>Simulate What-If</span>
                    </button>
                  </div>
                </div>
              );
            })}
        </div>
      )}

      {/* TAB 2: WHAT-IF SIMULATOR */}
      {activeTab === 'simulator' && (
        <div className="space-y-6">
          <div className="panel p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>🧪 Scenario What-If Modeling</span>
                <span className="text-xs font-normal px-2.5 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/50">
                  Read-Only Guarantee: Zero Cloud Resource Modification
                </span>
              </h2>
              <p className="text-xs muted mt-1">
                Model multi-dimensional cost reductions and grid decarbonization scenarios before taking action.
              </p>
            </div>

            {/* Scenario Builder Form */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">Scenario Archetype</label>
                <select
                  value={scenarioType}
                  onChange={(e) => setScenarioType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                >
                  <option value="RIGHTSIZING">Instance Fleet Rightsizing</option>
                  <option value="SCHEDULED_IDLE">Off-Hours Non-Prod Shutdown</option>
                  <option value="SAVINGS_PLAN">Compute Savings Plan Commitment</option>
                  <option value="REGION_MIGRATION">Low-Carbon Grid Regional Migration</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">Scenario Label</label>
                <input
                  type="text"
                  placeholder="e.g. Q4 Infrastructure Optimization"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                />
              </div>

              {scenarioType === 'RIGHTSIZING' && (
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                    Downsize Ratio ({downsizePct}%)
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="70"
                    step="5"
                    value={downsizePct}
                    onChange={(e) => setDownsizePct(Number(e.target.value))}
                    className="w-full mt-2"
                  />
                </div>
              )}

              {scenarioType === 'SCHEDULED_IDLE' && (
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                    Off-Hours Off ({offHoursPerWeek} hrs/week)
                  </label>
                  <input
                    type="range"
                    min="16"
                    max="80"
                    step="4"
                    value={offHoursPerWeek}
                    onChange={(e) => setOffHoursPerWeek(Number(e.target.value))}
                    className="w-full mt-2"
                  />
                </div>
              )}

              {scenarioType === 'SAVINGS_PLAN' && (
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">Commitment Term</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setTermYears(1)}
                      className={`flex-1 py-1.5 rounded text-xs font-medium border ${
                        termYears === 1
                          ? 'bg-cyan-500 text-slate-950 font-bold border-cyan-400'
                          : 'bg-slate-900 border-slate-700 text-slate-300'
                      }`}
                    >
                      1 Year (36% off)
                    </button>
                    <button
                      type="button"
                      onClick={() => setTermYears(3)}
                      className={`flex-1 py-1.5 rounded text-xs font-medium border ${
                        termYears === 3
                          ? 'bg-cyan-500 text-slate-950 font-bold border-cyan-400'
                          : 'bg-slate-900 border-slate-700 text-slate-300'
                      }`}
                    >
                      3 Years (58% off)
                    </button>
                  </div>
                </div>
              )}

              {scenarioType === 'REGION_MIGRATION' && (
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">Target Clean Grid Region</label>
                  <select
                    value={targetRegion}
                    onChange={(e) => setTargetRegion(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                  >
                    <option value="us-west-2">Oregon us-west-2 (Hydro: 152.4 g/kWh)</option>
                    <option value="eu-north-1">Stockholm eu-north-1 (Clean: 24.1 g/kWh)</option>
                    <option value="ca-central-1">Montreal ca-central-1 (Hydro: 120.0 g/kWh)</option>
                  </select>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => handleRunSimulation()}
                disabled={simulating}
                className="px-5 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-sm transition-all disabled:opacity-50"
              >
                {simulating ? 'Calculating Model...' : 'Execute What-If Model'}
              </button>
            </div>
          </div>

          {/* Simulation Output Card */}
          {simResults && (
            <div className="panel p-6 space-y-4 border border-cyan-500/40 bg-cyan-950/10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-white">{simResults.name}</h3>
                  <div className="text-xs muted">
                    Catalog: {simResults.pricing_source} · Factor Source: {simResults.factor_source}
                  </div>
                </div>
                <div className="text-xs px-2.5 py-1 rounded bg-slate-800 text-cyan-300 font-mono">
                  Scenario ID: {simResults.id.substring(0, 8)}...
                </div>
              </div>

              {simMessage && <p className="text-xs text-emerald-400 font-medium">{simMessage}</p>}

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
                <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
                  <div className="text-xs muted font-semibold">Monthly Spend Impact</div>
                  <div className="text-xl font-bold text-white mt-1">
                    ${simResults.results.simulated_monthly_spend?.toFixed(0)}
                    <span className="text-xs muted font-normal line-through ml-2">
                      ${simResults.results.baseline_monthly_spend?.toFixed(0)}
                    </span>
                  </div>
                  <div className="text-xs text-emerald-400 font-semibold mt-1">
                    -${simResults.results.monthly_cost_saving?.toFixed(0)}/mo (-{simResults.results.cost_saving_pct}%)
                  </div>
                </div>

                <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
                  <div className="text-xs muted font-semibold">Carbon Impact</div>
                  <div className="text-xl font-bold text-white mt-1">
                    {simResults.results.simulated_monthly_carbon_kg?.toFixed(1)} kg
                    <span className="text-xs muted font-normal line-through ml-2">
                      {simResults.results.baseline_monthly_carbon_kg?.toFixed(1)} kg
                    </span>
                  </div>
                  <div className="text-xs text-teal-300 font-semibold mt-1">
                    -{simResults.results.monthly_carbon_saving_kg?.toFixed(1)} kgCO2e (-{simResults.results.carbon_saving_pct}%)
                  </div>
                </div>

                <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
                  <div className="text-xs muted font-semibold">Payback / Breakeven</div>
                  <div className="text-xl font-bold text-cyan-300 mt-1">
                    {simResults.results.payback_period_months === 0 ? 'Immediate' : `${simResults.results.payback_period_months} months`}
                  </div>
                  <div className="text-xs muted mt-1">Operational configuration</div>
                </div>

                <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
                  <div className="text-xs muted font-semibold">Risk Classification</div>
                  <div className="text-xl font-bold text-white mt-1">
                    <span
                      className={`text-sm px-2 py-0.5 rounded font-bold ${
                        simResults.results.risk_level === 'LOW'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : 'bg-amber-950 text-amber-400 border border-amber-800'
                      }`}
                    >
                      {simResults.results.risk_level} RISK
                    </span>
                  </div>
                  <div className="text-xs muted mt-1">Zero downtime expected</div>
                </div>
              </div>
            </div>
          )}

          {/* Past Simulation History */}
          <div className="panel p-6 space-y-4">
            <h3 className="text-base font-bold text-white">Historical Scenario Runs (Audit Log)</h3>
            {simHistory.length === 0 ? (
              <p className="text-xs muted">No simulation runs recorded yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="text-slate-400 uppercase tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-2.5">Scenario Name</th>
                      <th>Type</th>
                      <th>Monthly Saving</th>
                      <th>Carbon Avoidance</th>
                      <th>Pricing Catalog</th>
                      <th>Executed At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {simHistory.map((s) => (
                      <tr key={s.id} className="hover:bg-slate-900/40">
                        <td className="py-2.5 font-sans font-semibold text-white">{s.name}</td>
                        <td>
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {s.scenario_type}
                          </span>
                        </td>
                        <td className="text-emerald-400 font-bold">
                          ${s.results?.monthly_cost_saving?.toFixed(0) || '0'}/mo
                        </td>
                        <td className="text-teal-300">
                          {s.results?.monthly_carbon_saving_kg?.toFixed(1) || '0.0'} kg
                        </td>
                        <td className="text-slate-400 text-[11px] font-sans">{s.pricing_source}</td>
                        <td className="text-slate-500 text-[11px]">
                          {new Date(s.created_at).toLocaleDateString()}
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

      {/* TAB 3: SAVINGS LEDGER */}
      {activeTab === 'ledger' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">Verified FinOps & Carbon Savings Ledger</h2>
              <p className="text-xs muted mt-0.5">
                Authoritative distinction between expected forecast savings and verified post-implementation measurements.
              </p>
            </div>

            <button
              onClick={() => setShowLedgerModal(true)}
              className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition-colors self-start sm:self-auto"
            >
              + Record Savings Initiative
            </button>
          </div>

          {/* Ledger Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="panel p-4">
              <div className="text-xs uppercase tracking-wider muted font-semibold">Expected Monthly Savings</div>
              <div className="text-xl font-bold text-white mt-1">
                ${ledgerSummary?.total_expected_monthly_cost_saving.toLocaleString() || '0'}
              </div>
              <div className="text-xs muted mt-0.5">Committed initiatives</div>
            </div>

            <div className="panel p-4">
              <div className="text-xs uppercase tracking-wider muted font-semibold">Verified Realized Savings</div>
              <div className="text-xl font-bold text-emerald-400 mt-1">
                ${ledgerSummary?.total_verified_monthly_cost_saving.toLocaleString() || '0'}
              </div>
              <div className="text-xs text-emerald-400/80 font-medium mt-0.5">
                {ledgerSummary?.cost_realization_rate_pct.toFixed(1)}% Realization Rate
              </div>
            </div>

            <div className="panel p-4">
              <div className="text-xs uppercase tracking-wider muted font-semibold">Verified Carbon Avoided</div>
              <div className="text-xl font-bold text-teal-300 mt-1">
                {ledgerSummary?.total_verified_monthly_carbon_saving_kg.toFixed(1) || '0.0'} kg
              </div>
              <div className="text-xs text-teal-300/80 mt-0.5">
                {ledgerSummary?.carbon_realization_rate_pct.toFixed(1)}% of planned emissions
              </div>
            </div>

            <div className="panel p-4">
              <div className="text-xs uppercase tracking-wider muted font-semibold">Documented Caveats</div>
              <div className="text-xl font-bold text-amber-300 mt-1">
                {ledgerSummary?.entries_with_caveats_count || 0}
              </div>
              <div className="text-xs muted mt-0.5">Audit adjustments disclosed</div>
            </div>
          </div>

          {/* Ledger Table */}
          <div className="panel p-6 space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-slate-400 uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-2.5">Initiative Title</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Expected ($/mo)</th>
                    <th>Verified ($/mo)</th>
                    <th>Measurement Window</th>
                    <th>Known Caveats & Exclusions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {ledgerEntries.map((e) => (
                    <tr key={e.id} className="hover:bg-slate-900/40">
                      <td className="py-3 font-semibold text-white">
                        {e.title}
                        <div className="text-[11px] muted font-mono font-normal">{e.resource_id}</div>
                      </td>
                      <td>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px]">
                          {e.category}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            e.status === 'REALIZED'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                              : 'bg-cyan-950 text-cyan-400 border border-cyan-800/50'
                          }`}
                        >
                          {e.status}
                        </span>
                      </td>
                      <td className="font-mono text-slate-300">${e.expected_monthly_cost_saving.toFixed(2)}</td>
                      <td className="font-mono font-bold text-emerald-400">
                        ${e.verified_cost_saving.toFixed(2)}
                      </td>
                      <td className="text-slate-400 font-mono text-[11px]">
                        {e.measurement_window_start
                          ? `${new Date(e.measurement_window_start).toLocaleDateString()} → ${
                              e.measurement_window_end
                                ? new Date(e.measurement_window_end).toLocaleDateString()
                                : 'Ongoing'
                            }`
                          : 'TBD'}
                      </td>
                      <td className="text-slate-400 text-xs max-w-xs">
                        {e.caveats ? (
                          <span className="text-amber-200/90 italic">"{e.caveats}"</span>
                        ) : (
                          <span className="muted">None documented</span>
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

      {/* Record Initiative Modal */}
      {showLedgerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="panel max-w-lg w-full p-6 space-y-4 border border-slate-700 bg-slate-950">
            <h3 className="text-lg font-bold text-white">Record Savings Initiative</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-300 block mb-1">Initiative Title</label>
                <input
                  type="text"
                  placeholder="e.g. Q4 Database Downsizing"
                  value={newLedgerTitle}
                  onChange={(e) => setNewLedgerTitle(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-300 block mb-1">Category</label>
                  <select
                    value={newLedgerCategory}
                    onChange={(e) => setNewLedgerCategory(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                  >
                    <option value="RIGHTSIZING">RIGHTSIZING</option>
                    <option value="IDLE_RESOURCE">IDLE_RESOURCE</option>
                    <option value="COMMITMENT_PURCHASE">COMMITMENT_PURCHASE</option>
                    <option value="STORAGE_OPTIMIZATION">STORAGE_OPTIMIZATION</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-300 block mb-1">Expected Monthly Saving ($)</label>
                  <input
                    type="number"
                    value={newLedgerExpected}
                    onChange={(e) => setNewLedgerExpected(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-300 block mb-1">Verified Realized Saving ($) (0 if planned)</label>
                <input
                  type="number"
                  value={newLedgerVerified}
                  onChange={(e) => setNewLedgerVerified(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 block mb-1">Known Caveats or Exclusions</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Seasonal surge in November traffic excluded from baseline"
                  value={newLedgerCaveats}
                  onChange={(e) => setNewLedgerCaveats(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowLedgerModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateLedgerEntry}
                className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold"
              >
                Save Initiative
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
