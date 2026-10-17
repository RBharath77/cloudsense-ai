'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

interface PlanChange {
  address: string;
  type: string;
  actions: string[];
  provider: string;
  region: string;
  cost_before: number;
  cost_after: number;
  cost_delta: number;
  emissions_before: number;
  emissions_after: number;
  emissions_delta: number;
  before: any;
  after: any;
}

interface PolicyViolation {
  rule: string;
  severity: string;
  message: string;
  target: string;
}

interface TerraformAnalysis {
  id: string;
  plan_name: string;
  provider: string;
  resources_created: number;
  resources_updated: number;
  resources_deleted: number;
  monthly_cost_before_usd: number;
  monthly_cost_after_usd: number;
  monthly_cost_delta_usd: number;
  monthly_emissions_delta_kgco2e: number;
  policy_status: string;
  violations: PolicyViolation[];
  summary?: any;
  created_at: string;
}

interface KubernetesAllocation {
  id: string;
  cluster_name: string;
  namespace: string;
  workload_name: string;
  workload_type: string;
  cpu_allocated_cores: number;
  cpu_usage_cores: number;
  memory_allocated_bytes: number;
  memory_usage_bytes: number;
  efficiency_score: number;
  monthly_allocated_cost_usd: number;
  monthly_idle_cost_usd: number;
  active_cost_usd: number;
  is_simulated: boolean;
  recorded_date: string;
  created_at: string;
}

interface KubernetesSummary {
  total_allocated_cost_usd: number;
  total_idle_waste_cost_usd: number;
  total_active_cost_usd: number;
  overall_efficiency_pct: number;
  cluster_count: number;
  namespace_count: number;
  workload_count: number;
  namespace_breakdown: Array<{
    namespace: string;
    allocated_cost_usd: number;
    idle_cost_usd: number;
    active_cost_usd: number;
    efficiency_pct: number;
    workload_count: number;
  }>;
  workload_type_breakdown: Record<string, number>;
  is_simulated_benchmark: boolean;
}

const PRESET_PLANS = {
  WEB_EXPANSION: {
    name: 'Web Fleet Scale-Up (3x t3.large + 2x 200GB gp3)',
    json: {
      format_version: '1.0',
      terraform_version: '1.8.2',
      resource_changes: [
        {
          address: 'aws_instance.api_gateway[0]',
          type: 'aws_instance',
          provider_name: 'aws',
          change: {
            actions: ['create'],
            after: {
              instance_type: 't3.large',
              region: 'us-east-1',
              tags: { Environment: 'Production', Owner: 'DevOps', Project: 'CloudSense' },
            },
          },
        },
        {
          address: 'aws_instance.api_gateway[1]',
          type: 'aws_instance',
          provider_name: 'aws',
          change: {
            actions: ['create'],
            after: {
              instance_type: 't3.large',
              region: 'us-east-1',
              tags: { Environment: 'Production', Owner: 'DevOps', Project: 'CloudSense' },
            },
          },
        },
        {
          address: 'aws_instance.api_gateway[2]',
          type: 'aws_instance',
          provider_name: 'aws',
          change: {
            actions: ['create'],
            after: {
              instance_type: 't3.large',
              region: 'us-east-1',
              tags: { Environment: 'Production', Owner: 'DevOps', Project: 'CloudSense' },
            },
          },
        },
        {
          address: 'aws_ebs_volume.storage_a',
          type: 'aws_ebs_volume',
          provider_name: 'aws',
          change: {
            actions: ['create'],
            after: {
              size: 200,
              type: 'gp3',
              region: 'us-east-1',
              tags: { Environment: 'Production', Owner: 'DevOps', Project: 'CloudSense' },
            },
          },
        },
        {
          address: 'aws_ebs_volume.storage_b',
          type: 'aws_ebs_volume',
          provider_name: 'aws',
          change: {
            actions: ['create'],
            after: {
              size: 200,
              type: 'gp3',
              region: 'us-east-1',
              tags: { Environment: 'Production', Owner: 'DevOps', Project: 'CloudSense' },
            },
          },
        },
      ],
    },
  },
  BLOCKED_GPU: {
    name: 'Unapproved AI Training Node (p4d.24xlarge $23k/mo)',
    json: {
      resource_changes: [
        {
          address: 'aws_instance.deep_learning_gpu',
          type: 'aws_instance',
          change: {
            actions: ['create'],
            after: {
              instance_type: 'p4d.24xlarge',
              region: 'us-east-1',
              tags: { Environment: 'Research', Owner: 'ML-Team' },
            },
          },
        },
      ],
    },
  },
  UNTAGGED_DEV: {
    name: 'Shadow Cloud VM (Missing Mandatory Cost Tags)',
    json: {
      resource_changes: [
        {
          address: 'aws_instance.unmanaged_service',
          type: 'aws_instance',
          change: {
            actions: ['create'],
            after: {
              instance_type: 'm5.large',
              region: 'us-east-1',
              tags: {},
            },
          },
        },
      ],
    },
  },
  TEARDOWN_SAVINGS: {
    name: 'Staging Fleet Teardown (Negative Delta / Net Savings)',
    json: {
      resource_changes: [
        {
          address: 'aws_instance.legacy_test_runner',
          type: 'aws_instance',
          change: {
            actions: ['delete'],
            before: {
              instance_type: 'c5.2xlarge',
              region: 'us-east-1',
            },
          },
        },
        {
          address: 'aws_ebs_volume.legacy_snapshot',
          type: 'aws_ebs_volume',
          change: {
            actions: ['delete'],
            before: {
              size: 500,
              type: 'gp2',
              region: 'us-east-1',
            },
          },
        },
      ],
    },
  },
};

export function IaCKubernetesFinOps() {
  const [activeTab, setActiveTab] = useState<'iac' | 'k8s'>('iac');

  // Terraform state
  const [planName, setPlanName] = useState('Web Fleet Scale-Up');
  const [planJsonInput, setPlanJsonInput] = useState(
    JSON.stringify(PRESET_PLANS.WEB_EXPANSION.json, null, 2)
  );
  const [analyzing, setAnalyzing] = useState(false);
  const [latestAnalysis, setLatestAnalysis] = useState<TerraformAnalysis | null>(null);
  const [historyAnalyses, setHistoryAnalyses] = useState<TerraformAnalysis[]>([]);
  const [iacError, setIacError] = useState<string | null>(null);

  // Kubernetes state
  const [k8sSummary, setK8sSummary] = useState<KubernetesSummary | null>(null);
  const [k8sAllocations, setK8sAllocations] = useState<KubernetesAllocation[]>([]);
  const [selectedNamespace, setSelectedNamespace] = useState<string>('all');
  const [k8sLoading, setK8sLoading] = useState(false);
  const [k8sError, setK8sError] = useState<string | null>(null);

  // Ingestion Modal
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);
  const [ingestSubmitting, setIngestSubmitting] = useState(false);
  const [ingestCluster, setIngestCluster] = useState('production-eks-cluster');
  const [ingestNamespace, setIngestNamespace] = useState('analytics');
  const [ingestWorkload, setIngestWorkload] = useState('flink-event-consumer');
  const [ingestWorkloadType, setIngestWorkloadType] = useState('StatefulSet');
  const [ingestCpuAlloc, setIngestCpuAlloc] = useState('6.0');
  const [ingestCpuUse, setIngestCpuUse] = useState('2.1');
  const [ingestMemAlloc, setIngestMemAlloc] = useState('16');
  const [ingestMemUse, setIngestMemUse] = useState('8');
  const [ingestCost, setIngestCost] = useState('280.0');

  const fetchHistory = useCallback(async () => {
    try {
      const data = await api('/api/iac/terraform/analyses');
      if (Array.isArray(data)) {
        setHistoryAnalyses(data);
        if (data.length > 0 && !latestAnalysis) {
          // Fetch detailed first one
          api(`/api/iac/terraform/analyses/${data[0].id}`).then((d) => setLatestAnalysis(d));
        }
      }
    } catch (err: any) {
      console.error(err);
    }
  }, [latestAnalysis]);

  const fetchKubernetesData = useCallback(async () => {
    setK8sLoading(true);
    setK8sError(null);
    try {
      const [sum, allocs] = await Promise.all([
        api('/api/containers/kubernetes/summary'),
        api('/api/containers/kubernetes/allocations'),
      ]);
      setK8sSummary(sum);
      setK8sAllocations(Array.isArray(allocs) ? allocs : []);
    } catch (err: any) {
      setK8sError(err.message || 'Failed to load container data');
    } finally {
      setK8sLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
    fetchKubernetesData();
  }, [fetchHistory, fetchKubernetesData]);

  const handleAnalyzePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setAnalyzing(true);
    setIacError(null);
    try {
      let parsedPlan;
      try {
        parsedPlan = JSON.parse(planJsonInput);
      } catch (jsonErr: any) {
        throw new Error(`Invalid JSON: ${jsonErr.message}`);
      }

      const result = await api('/api/iac/terraform/analyze', {
        method: 'POST',
        body: JSON.stringify({
          plan_name: planName,
          plan_data: parsedPlan,
        }),
      });

      setLatestAnalysis(result);
      fetchHistory();
    } catch (err: any) {
      setIacError(err.message || 'Terraform analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSelectPreset = (key: keyof typeof PRESET_PLANS) => {
    const p = PRESET_PLANS[key];
    setPlanName(p.name);
    setPlanJsonInput(JSON.stringify(p.json, null, 2));
    setIacError(null);
  };

  const handleIngestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIngestSubmitting(true);
    try {
      const cpuAlloc = parseFloat(ingestCpuAlloc) || 1.0;
      const cpuUse = parseFloat(ingestCpuUse) || 0.5;
      const memAllocBytes = (parseFloat(ingestMemAlloc) || 4.0) * 1024 * 1024 * 1024;
      const memUseBytes = (parseFloat(ingestMemUse) || 2.0) * 1024 * 1024 * 1024;
      const cost = parseFloat(ingestCost) || 100.0;

      await api('/api/containers/kubernetes/ingest', {
        method: 'POST',
        body: JSON.stringify({
          cluster_name: ingestCluster,
          allocations: [
            {
              namespace: ingestNamespace,
              workload_name: ingestWorkload,
              workload_type: ingestWorkloadType,
              cpu_allocated_cores: cpuAlloc,
              cpu_usage_cores: cpuUse,
              memory_allocated_bytes: memAllocBytes,
              memory_usage_bytes: memUseBytes,
              monthly_allocated_cost_usd: cost,
              is_simulated: false,
            },
          ],
        }),
      });

      setIsIngestModalOpen(false);
      fetchKubernetesData();
    } catch (err: any) {
      alert(`Ingest failed: ${err.message}`);
    } finally {
      setIngestSubmitting(false);
    }
  };

  const filteredAllocations = k8sAllocations.filter(
    (a) => selectedNamespace === 'all' || a.namespace === selectedNamespace
  );

  return (
    <div className="space-y-8">
      {/* Tab Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab('iac')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === 'iac'
              ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <span>Shift-Left Terraform Estimator</span>
          {latestAnalysis && (
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                latestAnalysis.policy_status === 'PASSED'
                  ? 'bg-emerald-950 text-emerald-300'
                  : latestAnalysis.policy_status === 'BLOCKED'
                  ? 'bg-red-950 text-red-300'
                  : 'bg-amber-950 text-amber-300'
              }`}
            >
              {latestAnalysis.policy_status}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('k8s')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === 'k8s'
              ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <span>Kubernetes & Container FinOps</span>
          {k8sSummary && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300">
              {k8sSummary.overall_efficiency_pct}% eff
            </span>
          )}
        </button>
      </div>

      {/* ========================================================= */}
      {/* TAB 1: TERRAFORM COST & CARBON DIFF ESTIMATOR            */}
      {/* ========================================================= */}
      {activeTab === 'iac' && (
        <div className="space-y-8">
          {/* Header Description & Presets */}
          <div className="panel p-6 border-cyan-500/20 bg-slate-950/80">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="text-xl font-semibold tracking-tight text-white flex items-center gap-2">
                  <span className="text-cyan-400">⚡</span> Shift-Left Terraform Plan Analyzer
                </h2>
                <p className="text-sm muted mt-1">
                  Evaluate infrastructure-as-code cost and carbon deltas pre-deployment before code is merged into main.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="text-slate-400 font-medium">Demo Templates:</span>
                <button
                  type="button"
                  onClick={() => handleSelectPreset('WEB_EXPANSION')}
                  className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-cyan-300 hover:bg-slate-700"
                >
                  Fleet Scale-Up
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectPreset('BLOCKED_GPU')}
                  className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-red-300 hover:bg-slate-700"
                >
                  Blocked GPU ($23k)
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectPreset('UNTAGGED_DEV')}
                  className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-amber-300 hover:bg-slate-700"
                >
                  Untagged Shadow VM
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectPreset('TEARDOWN_SAVINGS')}
                  className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-emerald-300 hover:bg-slate-700"
                >
                  Teardown Savings
                </button>
              </div>
            </div>

            {/* Input Form */}
            <form onSubmit={handleAnalyzePlan} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Plan Description / Pull Request Title
                </label>
                <input
                  type="text"
                  value={planName}
                  onChange={(e) => setPlanName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">
                    Terraform Plan JSON (<code className="text-cyan-300">terraform show -json tfplan.binary</code>)
                  </label>
                  <span className="text-[11px] text-slate-500">
                    Extracts <code className="text-slate-400">resource_changes</code> diffs
                  </span>
                </div>
                <textarea
                  rows={9}
                  value={planJsonInput}
                  onChange={(e) => setPlanJsonInput(e.target.value)}
                  className="w-full font-mono text-xs bg-slate-900/90 border border-slate-700 rounded-lg p-3 text-cyan-200 focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              {iacError && (
                <div className="p-3 bg-red-950/80 border border-red-500/40 rounded-lg text-sm text-red-200">
                  {iacError}
                </div>
              )}

              <div className="flex items-center justify-between">
                <div className="text-xs muted flex items-center gap-2">
                  <span>Policy threshold:</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">+$500/mo max</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">Tags: Environment, Owner</span>
                </div>
                <button
                  type="submit"
                  disabled={analyzing}
                  className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg text-sm shadow-lg shadow-cyan-600/20 transition-all flex items-center gap-2"
                >
                  {analyzing ? 'Analyzing Plan...' : 'Evaluate Plan Diff & Policies'}
                </button>
              </div>
            </form>
          </div>

          {/* Latest Analysis Results */}
          {latestAnalysis && (
            <div className="space-y-6">
              {/* Diff Cards Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Cost Delta */}
                <div className="panel p-5 border-slate-800">
                  <span className="text-xs font-medium muted block mb-1">Projected Monthly Cost Delta</span>
                  <div className="flex items-baseline gap-2">
                    <span
                      className={`text-2xl font-bold font-mono ${
                        latestAnalysis.monthly_cost_delta_usd > 0
                          ? 'text-amber-300'
                          : latestAnalysis.monthly_cost_delta_usd < 0
                          ? 'text-emerald-300'
                          : 'text-slate-300'
                      }`}
                    >
                      {latestAnalysis.monthly_cost_delta_usd >= 0 ? '+' : ''}$
                      {latestAnalysis.monthly_cost_delta_usd.toFixed(2)}
                    </span>
                    <span className="text-xs muted">/month</span>
                  </div>
                  <div className="text-[11px] muted mt-2 flex items-center justify-between">
                    <span>Baseline: ${latestAnalysis.monthly_cost_before_usd.toFixed(2)}</span>
                    <span>Proposed: ${latestAnalysis.monthly_cost_after_usd.toFixed(2)}</span>
                  </div>
                </div>

                {/* Carbon Delta */}
                <div className="panel p-5 border-slate-800">
                  <span className="text-xs font-medium muted block mb-1">Pre-Deployment Carbon Delta</span>
                  <div className="flex items-baseline gap-2">
                    <span
                      className={`text-2xl font-bold font-mono ${
                        latestAnalysis.monthly_emissions_delta_kgco2e > 0
                          ? 'text-amber-300'
                          : latestAnalysis.monthly_emissions_delta_kgco2e < 0
                          ? 'text-emerald-300'
                          : 'text-slate-300'
                      }`}
                    >
                      {latestAnalysis.monthly_emissions_delta_kgco2e >= 0 ? '+' : ''}
                      {latestAnalysis.monthly_emissions_delta_kgco2e.toFixed(1)}
                    </span>
                    <span className="text-xs muted">kgCO₂e/mo</span>
                  </div>
                  <div className="text-[11px] muted mt-2">
                    EPA eGRID 2024 / EEA 2023 Factor Grid
                  </div>
                </div>

                {/* Policy Guardrails Status */}
                <div className="panel p-5 border-slate-800">
                  <span className="text-xs font-medium muted block mb-1">CI/CD Policy Guardrail Status</span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xl font-bold font-mono px-2.5 py-1 rounded-md ${
                        latestAnalysis.policy_status === 'PASSED'
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/30'
                          : latestAnalysis.policy_status === 'BLOCKED'
                          ? 'bg-red-950/80 text-red-300 border border-red-500/30'
                          : 'bg-amber-950/80 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {latestAnalysis.policy_status}
                    </span>
                  </div>
                  <div className="text-[11px] muted mt-2">
                    {latestAnalysis.violations.length === 0
                      ? 'All budget & tag gates satisfied'
                      : `${latestAnalysis.violations.length} policy exception(s) detected`}
                  </div>
                </div>

                {/* Resource Change Counters */}
                <div className="panel p-5 border-slate-800">
                  <span className="text-xs font-medium muted block mb-1">Resource Modifications</span>
                  <div className="flex items-center gap-3 mt-1 font-mono text-sm">
                    <span className="text-emerald-400 font-semibold">
                      +{latestAnalysis.resources_created} create
                    </span>
                    <span className="text-amber-400 font-semibold">
                      ~{latestAnalysis.resources_updated} update
                    </span>
                    <span className="text-red-400 font-semibold">
                      -{latestAnalysis.resources_deleted} delete
                    </span>
                  </div>
                  <div className="text-[11px] muted mt-2">
                    Provider: <span className="uppercase text-slate-300">{latestAnalysis.provider}</span>
                  </div>
                </div>
              </div>

              {/* Policy Violations Callout if any */}
              {latestAnalysis.violations.length > 0 && (
                <div className="panel p-5 border-amber-500/30 bg-amber-950/20">
                  <h3 className="text-sm font-semibold text-amber-300 mb-3 flex items-center gap-2">
                    <span>⚠️</span> CI/CD Policy Violations & Guardrail Warnings
                  </h3>
                  <div className="space-y-2">
                    {latestAnalysis.violations.map((v, i) => (
                      <div
                        key={i}
                        className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs gap-2"
                      >
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`px-1.5 py-0.5 rounded font-mono font-bold text-[10px] ${
                                v.severity === 'BLOCKING'
                                  ? 'bg-red-900/80 text-red-200'
                                  : 'bg-amber-900/80 text-amber-200'
                              }`}
                            >
                              {v.severity}
                            </span>
                            <span className="font-mono text-slate-300 font-semibold">{v.rule}</span>
                            <span className="text-slate-500">on {v.target}</span>
                          </div>
                          <p className="text-slate-300">{v.message}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Resource Changes Diff Breakdown */}
              {latestAnalysis.summary?.changes && (
                <div className="panel p-6 border-slate-800">
                  <h3 className="text-base font-semibold text-white mb-4">
                    Resource Line-Item Cost & Carbon Diff
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/90 text-slate-400 font-medium border-b border-slate-800">
                        <tr>
                          <th className="p-3">Action</th>
                          <th className="p-3">Resource Address</th>
                          <th className="p-3">Type</th>
                          <th className="p-3">Region</th>
                          <th className="p-3 text-right">Old Cost</th>
                          <th className="p-3 text-right">New Cost</th>
                          <th className="p-3 text-right">Cost Delta</th>
                          <th className="p-3 text-right">Carbon Delta</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {latestAnalysis.summary.changes.map((c: PlanChange, idx: number) => {
                          const action = c.actions.includes('create')
                            ? 'create'
                            : c.actions.includes('delete')
                            ? 'delete'
                            : 'update';
                          return (
                            <tr key={idx} className="hover:bg-slate-900/50">
                              <td className="p-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    action === 'create'
                                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/30'
                                      : action === 'delete'
                                      ? 'bg-red-950 text-red-300 border border-red-500/30'
                                      : 'bg-amber-950 text-amber-300 border border-amber-500/30'
                                  }`}
                                >
                                  {action === 'create' ? '+ create' : action === 'delete' ? '- delete' : '~ update'}
                                </span>
                              </td>
                              <td className="p-3 text-slate-200 font-sans font-medium">{c.address}</td>
                              <td className="p-3 text-slate-400">{c.type}</td>
                              <td className="p-3 text-slate-400">{c.region}</td>
                              <td className="p-3 text-right text-slate-400">${c.cost_before.toFixed(2)}</td>
                              <td className="p-3 text-right text-slate-200">${c.cost_after.toFixed(2)}</td>
                              <td
                                className={`p-3 text-right font-semibold ${
                                  c.cost_delta > 0
                                    ? 'text-amber-300'
                                    : c.cost_delta < 0
                                    ? 'text-emerald-300'
                                    : 'text-slate-400'
                                }`}
                              >
                                {c.cost_delta >= 0 ? '+' : ''}${c.cost_delta.toFixed(2)}
                              </td>
                              <td
                                className={`p-3 text-right ${
                                  c.emissions_delta > 0
                                    ? 'text-amber-300'
                                    : c.emissions_delta < 0
                                    ? 'text-emerald-300'
                                    : 'text-slate-400'
                                }`}
                              >
                                {c.emissions_delta >= 0 ? '+' : ''}{c.emissions_delta.toFixed(1)} kg
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Historical Plan Analyses */}
          {historyAnalyses.length > 0 && (
            <div className="panel p-6 border-slate-800">
              <h3 className="text-base font-semibold text-white mb-4">Past Plan Evaluations</h3>
              <div className="space-y-2">
                {historyAnalyses.map((h) => (
                  <div
                    key={h.id}
                    onClick={() => api(`/api/iac/terraform/analyses/${h.id}`).then((d) => setLatestAnalysis(d))}
                    className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 hover:border-cyan-500/40 hover:bg-slate-900 cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-3 transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-slate-200">{h.plan_name}</span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${
                            h.policy_status === 'PASSED'
                              ? 'bg-emerald-950 text-emerald-300'
                              : h.policy_status === 'BLOCKED'
                              ? 'bg-red-950 text-red-300'
                              : 'bg-amber-950 text-amber-300'
                          }`}
                        >
                          {h.policy_status}
                        </span>
                      </div>
                      <div className="muted text-[11px]">
                        +{h.resources_created} / ~{h.resources_updated} / -{h.resources_deleted} resources •{' '}
                        {new Date(h.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 font-mono">
                      <div className="text-right">
                        <span
                          className={`font-semibold ${
                            h.monthly_cost_delta_usd >= 0 ? 'text-amber-300' : 'text-emerald-300'
                          }`}
                        >
                          {h.monthly_cost_delta_usd >= 0 ? '+' : ''}${h.monthly_cost_delta_usd.toFixed(2)}/mo
                        </span>
                        <div className="text-[10px] muted">
                          {h.monthly_emissions_delta_kgco2e >= 0 ? '+' : ''}
                          {h.monthly_emissions_delta_kgco2e.toFixed(1)} kgCO₂e
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: KUBERNETES & CONTAINER FINOPS                      */}
      {/* ========================================================= */}
      {activeTab === 'k8s' && (
        <div className="space-y-8">
          {/* Header & Ingest Action */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-white flex items-center gap-2">
                <span className="text-indigo-400">☸️</span> Kubernetes & Container Cost Allocation
              </h2>
              <p className="text-sm muted mt-1">
                Measure utilized application spend vs. idle overprovisioned waste across clusters, namespaces, and workloads.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setIsIngestModalOpen(true)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg text-sm shadow-md transition-all flex items-center gap-2"
              >
                <span>+ Ingest Telemetry</span>
              </button>
            </div>
          </div>

          {k8sError && (
            <div className="p-4 bg-red-950/80 border border-red-500/40 rounded-lg text-sm text-red-200">
              {k8sError}
            </div>
          )}

          {k8sSummary && (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="panel p-5 border-slate-800">
                  <span className="text-xs font-medium muted block mb-1">Total Cluster Monthly Cost</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold font-mono text-white">
                      ${k8sSummary.total_allocated_cost_usd.toFixed(2)}
                    </span>
                    <span className="text-xs muted">/mo</span>
                  </div>
                  <div className="text-[11px] muted mt-2">
                    {k8sSummary.cluster_count} Cluster(s) • {k8sSummary.namespace_count} Namespaces
                  </div>
                </div>

                <div className="panel p-5 border-slate-800">
                  <span className="text-xs font-medium muted block mb-1">Actively Utilized Spend</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold font-mono text-emerald-400">
                      ${k8sSummary.total_active_cost_usd.toFixed(2)}
                    </span>
                    <span className="text-xs muted">/mo</span>
                  </div>
                  <div className="text-[11px] text-emerald-300/80 mt-2">
                    Productive application CPU & memory
                  </div>
                </div>

                <div className="panel p-5 border-slate-800">
                  <span className="text-xs font-medium muted block mb-1">Idle / Overprovisioned Waste</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold font-mono text-amber-400">
                      ${k8sSummary.total_idle_waste_cost_usd.toFixed(2)}
                    </span>
                    <span className="text-xs muted">/mo</span>
                  </div>
                  <div className="text-[11px] text-amber-300/80 mt-2">
                    Requests exceeding utilization
                  </div>
                </div>

                <div className="panel p-5 border-slate-800">
                  <span className="text-xs font-medium muted block mb-1">Overall Cluster Efficiency</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold font-mono text-cyan-300">
                      {k8sSummary.overall_efficiency_pct}%
                    </span>
                  </div>
                  {/* Visual gauge */}
                  <div className="w-full bg-slate-800 h-2 rounded-full mt-2 overflow-hidden">
                    <div
                      className="bg-cyan-400 h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, k8sSummary.overall_efficiency_pct))}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Namespace Breakdown Cards */}
              <div className="panel p-6 border-slate-800">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-semibold text-white">Namespace Cost & Efficiency Distribution</h3>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="muted">Filter namespace:</span>
                    <select
                      value={selectedNamespace}
                      onChange={(e) => setSelectedNamespace(e.target.value)}
                      className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-slate-200"
                    >
                      <option value="all">All Namespaces ({k8sAllocations.length})</option>
                      {k8sSummary.namespace_breakdown.map((n) => (
                        <option key={n.namespace} value={n.namespace}>
                          {n.namespace} (${n.allocated_cost_usd.toFixed(0)})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {k8sSummary.namespace_breakdown.map((ns) => (
                    <div
                      key={ns.namespace}
                      className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white font-mono text-sm">{ns.namespace}</span>
                        <span
                          className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                            ns.efficiency_pct >= 70
                              ? 'bg-emerald-950 text-emerald-300'
                              : ns.efficiency_pct >= 40
                              ? 'bg-cyan-950 text-cyan-300'
                              : 'bg-amber-950 text-amber-300'
                          }`}
                        >
                          {ns.efficiency_pct}% eff
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-xs muted font-mono">
                        <span>Total: ${ns.allocated_cost_usd.toFixed(2)}/mo</span>
                        <span>{ns.workload_count} workloads</span>
                      </div>

                      {/* Stacked Bar: Active vs Idle */}
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden flex">
                        <div
                          className="bg-emerald-400 h-full"
                          style={{ width: `${ns.efficiency_pct}%` }}
                          title={`Active: $${ns.active_cost_usd.toFixed(2)}`}
                        />
                        <div
                          className="bg-amber-400 h-full"
                          style={{ width: `${100 - ns.efficiency_pct}%` }}
                          title={`Idle: $${ns.idle_cost_usd.toFixed(2)}`}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <span className="text-emerald-400">Active: ${ns.active_cost_usd.toFixed(2)}</span>
                        <span className="text-amber-400">Idle: ${ns.idle_cost_usd.toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Workload Allocation Table */}
              <div className="panel p-6 border-slate-800">
                <h3 className="text-base font-semibold text-white mb-4">Workload Allocation & Waste Inventory</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/90 text-slate-400 font-medium border-b border-slate-800">
                      <tr>
                        <th className="p-3">Namespace</th>
                        <th className="p-3">Workload</th>
                        <th className="p-3">Type</th>
                        <th className="p-3">CPU (Alloc / Use)</th>
                        <th className="p-3">Memory (Alloc / Use)</th>
                        <th className="p-3">Efficiency</th>
                        <th className="p-3 text-right">Allocated Cost</th>
                        <th className="p-3 text-right">Idle Waste</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {filteredAllocations.map((alloc) => (
                        <tr key={alloc.id} className="hover:bg-slate-900/50">
                          <td className="p-3 text-cyan-300">{alloc.namespace}</td>
                          <td className="p-3 font-sans font-medium text-slate-200">{alloc.workload_name}</td>
                          <td className="p-3 text-slate-400">{alloc.workload_type}</td>
                          <td className="p-3 text-slate-300">
                            {alloc.cpu_allocated_cores.toFixed(1)} / {alloc.cpu_usage_cores.toFixed(1)} cores
                          </td>
                          <td className="p-3 text-slate-300">
                            {(alloc.memory_allocated_bytes / (1024 * 1024 * 1024)).toFixed(1)} /{' '}
                            {(alloc.memory_usage_bytes / (1024 * 1024 * 1024)).toFixed(1)} GiB
                          </td>
                          <td className="p-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                alloc.efficiency_score >= 70
                                  ? 'bg-emerald-950 text-emerald-300'
                                  : alloc.efficiency_score >= 40
                                  ? 'bg-cyan-950 text-cyan-300'
                                  : 'bg-amber-950 text-amber-300'
                              }`}
                            >
                              {alloc.efficiency_score}%
                            </span>
                          </td>
                          <td className="p-3 text-right text-slate-200 font-semibold">
                            ${alloc.monthly_allocated_cost_usd.toFixed(2)}
                          </td>
                          <td className="p-3 text-right text-amber-400 font-semibold">
                            ${alloc.monthly_idle_cost_usd.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Ingest Container Metrics Modal */}
      {isIngestModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="panel w-full max-w-lg p-6 border-indigo-500/30 bg-slate-950 shadow-2xl space-y-4">
            <h3 className="text-lg font-semibold text-white">Ingest Kubernetes Workload Telemetry</h3>
            <p className="text-xs muted">
              Simulate container usage metrics from Kubecost, Prometheus, or cAdvisor.
            </p>

            <form onSubmit={handleIngestSubmit} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block muted mb-1">Cluster Name</label>
                  <input
                    type="text"
                    value={ingestCluster}
                    onChange={(e) => setIngestCluster(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                    required
                  />
                </div>
                <div>
                  <label className="block muted mb-1">Namespace</label>
                  <input
                    type="text"
                    value={ingestNamespace}
                    onChange={(e) => setIngestNamespace(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block muted mb-1">Workload Name</label>
                  <input
                    type="text"
                    value={ingestWorkload}
                    onChange={(e) => setIngestWorkload(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                    required
                  />
                </div>
                <div>
                  <label className="block muted mb-1">Workload Type</label>
                  <select
                    value={ingestWorkloadType}
                    onChange={(e) => setIngestWorkloadType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                  >
                    <option value="Deployment">Deployment</option>
                    <option value="StatefulSet">StatefulSet</option>
                    <option value="DaemonSet">DaemonSet</option>
                    <option value="Job">Job</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block muted mb-1">CPU Allocated / Used (Cores)</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      step="0.1"
                      value={ingestCpuAlloc}
                      onChange={(e) => setIngestCpuAlloc(e.target.value)}
                      placeholder="Alloc"
                      className="w-1/2 bg-slate-900 border border-slate-700 rounded p-2 text-white"
                    />
                    <input
                      type="number"
                      step="0.1"
                      value={ingestCpuUse}
                      onChange={(e) => setIngestCpuUse(e.target.value)}
                      placeholder="Used"
                      className="w-1/2 bg-slate-900 border border-slate-700 rounded p-2 text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block muted mb-1">RAM Allocated / Used (GiB)</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      step="0.5"
                      value={ingestMemAlloc}
                      onChange={(e) => setIngestMemAlloc(e.target.value)}
                      placeholder="Alloc"
                      className="w-1/2 bg-slate-900 border border-slate-700 rounded p-2 text-white"
                    />
                    <input
                      type="number"
                      step="0.5"
                      value={ingestMemUse}
                      onChange={(e) => setIngestMemUse(e.target.value)}
                      placeholder="Used"
                      className="w-1/2 bg-slate-900 border border-slate-700 rounded p-2 text-white"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block muted mb-1">Monthly Allocated Cost ($ USD)</label>
                <input
                  type="number"
                  step="0.01"
                  value={ingestCost}
                  onChange={(e) => setIngestCost(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsIngestModalOpen(false)}
                  className="px-4 py-2 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={ingestSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg"
                >
                  {ingestSubmitting ? 'Ingesting...' : 'Save Telemetry Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default IaCKubernetesFinOps;
