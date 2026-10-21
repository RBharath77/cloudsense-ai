'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '../lib/api';

interface ToolProvenance {
  tool: string;
  source_type?: string;
  observation_period_days?: number;
  record_count?: number;
  data_sources?: string[];
  notes?: string;
  data_coverage?: any;
  methodology?: any;
}

interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  tools_invoked?: string[];
  sources?: ToolProvenance[];
  missing_data_acknowledged?: boolean;
  missing_data_details?: string[];
  mode?: string;
  task_executed?: boolean;
  action_performed?: string;
}

interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
  category: string;
}

const AGENTIC_TASKS = [
  { label: '⚡ Run Anomaly Scan', cmd: 'Run anomaly detection scan on our historical cloud billing' },
  { label: '⚡ Generate Executive Report', cmd: 'Generate executive finops report PDF for 30 days' },
  { label: '⚡ Provision Cloud Budget', cmd: 'Create budget for AWS with amount $5000' },
  { label: '⚡ Simulate Rightsizing', cmd: 'Simulate rightsizing savings across active cloud workloads' },
  { label: '⚡ Evaluate Alert Rules', cmd: 'Evaluate active budget thresholds and alert rules' },
  { label: '⚡ Clear All Alerts', cmd: 'Mark all alerts as read' },
  { label: '⚡ Audit Tag Governance', cmd: 'Audit tag governance compliance across cloud resources' },
];

const SUGGESTED_QUERIES = [
  'What is our current monthly cloud spend and trend?',
  'What is our projected cloud spend forecast for next month?',
  'Are there any recent cost spikes or anomalies?',
  'What is our cloud carbon footprint and greenhouse gas emissions?',
  'How can we optimize and save money on idle or over-provisioned instances?',
  'Show active cloud budgets and alert thresholds',
];

export function AIAnalyst() {
  const [messages, setMessages] = useState<ChatMessageItem[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content:
        'Hello! I am your CloudSense AI FinOps & Sustainability Analyst. I provide deterministic, verified insights directly grounded in your cloud billing, ML forecast models, carbon telemetry, and rightsizing engines. I never execute arbitrary code or speculate when data is absent.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      tools_invoked: ['system_readiness_check'],
      mode: 'deterministic_grounded_tool_execution',
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [showToolsDrawer, setShowToolsDrawer] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api('/api/assistant/tools')
      .then((data: ToolDefinition[]) => {
        if (Array.isArray(data)) setTools(data);
      })
      .catch((err) => console.error('Failed to load allowlisted tools:', err));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || loading) return;

    const userMsgId = `user-${Date.now()}`;
    const userMsg: ChatMessageItem = {
      id: userMsgId,
      role: 'user',
      content: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const response = await api('/api/assistant/chat', {
        method: 'POST',
        body: JSON.stringify({ message: textToSend.trim() }),
      });

      const assistantMsgId = `assistant-${Date.now()}`;
      const assistantMsg: ChatMessageItem = {
        id: assistantMsgId,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        tools_invoked: response.tools_invoked || [],
        sources: response.citations || [],
        missing_data_acknowledged: response.missing_data_acknowledged,
        missing_data_details: response.missing_data_details,
        mode: response.mode,
        task_executed: response.task_executed,
        action_performed: response.action_performed,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessageItem = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Error executing query: ${err.message || 'Server error occurred while evaluating allowlisted tools.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        tools_invoked: [],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSourceDrawer = (msgId: string) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Security Disclosure */}
      <div className="panel p-6 bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 border-cyan-500/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="h-3 w-3 rounded-full bg-emerald-400 animate-pulse" />
              <h2 className="text-xl font-bold tracking-tight text-white">Grounded FinOps & GreenOps AI Analyst</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                Phase 8
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Answers are computed deterministically via allowlisted backend tools with multi-tenant data isolation.
              Zero external LLM hallucinations, zero arbitrary SQL, and transparent data provenance citations.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowToolsDrawer(true)}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 flex items-center gap-2 transition"
            >
              <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Allowed Tool Registry ({tools.length})
            </button>
          </div>
        </div>
      </div>

      {/* Actionable Agentic Commands & Suggestions */}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 uppercase tracking-wider">
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
          <span>Execute Workspace Tasks (AI Autonomous Commands):</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {AGENTIC_TASKS.map((task, i) => (
            <button
              key={i}
              onClick={() => handleSendMessage(task.cmd)}
              disabled={loading}
              className="text-xs font-medium bg-cyan-950/40 hover:bg-cyan-900/60 text-cyan-300 hover:text-cyan-200 border border-cyan-500/30 hover:border-cyan-400 rounded-lg px-3 py-1.5 transition text-left shadow-sm flex items-center gap-1"
            >
              <span>{task.label}</span>
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          {SUGGESTED_QUERIES.map((sq, i) => (
            <button
              key={i}
              onClick={() => handleSendMessage(sq)}
              disabled={loading}
              className="text-xs bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/30 rounded-lg px-3 py-1.5 transition text-left"
            >
              💬 {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Conversation Thread */}
      <div className="panel p-5 min-h-[480px] max-h-[620px] overflow-y-auto flex flex-col space-y-4 bg-slate-950/70 border-slate-800">
        {messages.map((m) => {
          const isUser = m.role === 'user';
          return (
            <div
              key={m.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-3xl ${
                isUser ? 'ml-auto' : 'mr-auto'
              } w-full`}
            >
              {/* Message header */}
              <div className="flex items-center gap-2 mb-1 text-xs text-slate-500 px-1">
                <span className="font-medium text-slate-400">{isUser ? 'You' : 'CloudSense Analyst'}</span>
                <span>•</span>
                <span>{m.timestamp}</span>
                {m.mode && (
                  <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">
                    deterministic
                  </span>
                )}
              </div>

              {/* Message Bubble */}
              <div
                className={`p-4 rounded-2xl text-sm leading-relaxed border ${
                  isUser
                    ? 'bg-cyan-600 text-white border-cyan-500/50 rounded-br-none shadow-md shadow-cyan-950/30'
                    : 'bg-slate-900/90 text-slate-200 border-slate-800 rounded-bl-none shadow-sm'
                }`}
              >
                {/* Task Execution Banner */}
                {m.task_executed && (
                  <div className="mb-3 p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping shrink-0" />
                    <span className="font-semibold text-emerald-400 uppercase tracking-wide">✓ Actionable Task Executed:</span>
                    <code className="bg-emerald-950/60 px-2 py-0.5 rounded text-emerald-200 font-mono text-[11px]">
                      {m.action_performed || 'task_complete'}()
                    </code>
                  </div>
                )}

                <div className="whitespace-pre-wrap">{m.content}</div>

                {/* Missing Data Explicit Acknowledgment Banner */}
                {m.missing_data_acknowledged && (
                  <div className="mt-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
                    <svg className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                      <span className="font-semibold">Missing Data Acknowledged:</span> This organization currently has no
                      recorded database entries for the requested domain. The analyst acknowledged the absence rather than synthesizing data.
                    </div>
                  </div>
                )}

                {/* Tools Invoked & Citations Drawer Toggle */}
                {!isUser && m.tools_invoked && m.tools_invoked.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Tools:</span>
                      {m.tools_invoked.map((t, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-950 text-cyan-300 border border-cyan-800/40"
                        >
                          {t}()
                        </span>
                      ))}
                    </div>

                    {m.sources && m.sources.length > 0 && (
                      <button
                        onClick={() => toggleSourceDrawer(m.id)}
                        className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium underline underline-offset-2 transition"
                      >
                        {expandedSources[m.id] ? 'Hide Provenance' : `View Telemetry Sources (${m.sources.length})`}
                      </button>
                    )}
                  </div>
                )}

                {/* Collapsible Provenance & Telemetry Sources */}
                {!isUser && expandedSources[m.id] && m.sources && (
                  <div className="mt-3 p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs space-y-2 animate-fadeIn">
                    <div className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      Verified Data Provenance & Telemetry
                    </div>
                    {m.sources.map((src, sIdx) => (
                      <div key={sIdx} className="p-2 rounded bg-slate-900 border border-slate-800 space-y-1">
                        <div className="flex justify-between items-center text-cyan-300 font-mono text-[11px]">
                          <span>{src.tool}</span>
                          {src.observation_period_days && (
                            <span className="text-slate-400">Window: {src.observation_period_days} Days</span>
                          )}
                        </div>
                        {src.record_count !== undefined && (
                          <div className="text-slate-400">
                            Reconciled Records: <b className="text-slate-200">{src.record_count}</b>
                          </div>
                        )}
                        {src.data_sources && (
                          <div className="text-slate-400">
                            Authoritative Sources: {src.data_sources.join(', ')}
                          </div>
                        )}
                        {src.methodology && (
                          <div className="text-slate-400 text-[11px] italic">
                            Methodology: {src.methodology.standard}
                          </div>
                        )}
                        {src.notes && <div className="text-slate-400 text-[11px]">{src.notes}</div>}
                      </div>
                    ))}
                    <div className="text-[10px] text-slate-500 italic pt-1">
                      Non-fabrication guarantee: Figures originate directly from database aggregations and are never generated from free-form hallucinations.
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-3 text-slate-400 text-xs py-2 px-1">
            <div className="flex space-x-1.5">
              <div className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span>Evaluating allowlisted deterministic tools and compiling provenance citations…</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div className="flex gap-2">
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Ask about monthly cloud spend, forecasts, carbon emissions, optimization recommendations, or budgets…"
          className="flex-1 bg-slate-900 border border-slate-700 focus:border-cyan-400 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none transition shadow-inner"
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={loading || !inputQuery.trim()}
          className="px-6 py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-slate-950 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-md shadow-cyan-950/40 flex items-center gap-2"
        >
          <span>Ask Analyst</span>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </button>
      </div>

      {/* Allowed Tool Registry Modal / Sliding Drawer */}
      {showToolsDrawer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="panel p-6 max-w-2xl w-full max-h-[85vh] overflow-y-auto bg-slate-900 border-slate-700 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Allowlisted Backend Tool Registry
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  The AI Analyst can only query these deterministic, tenant-isolated functions. Zero arbitrary code execution permitted.
                </p>
              </div>
              <button
                onClick={() => setShowToolsDrawer(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              {tools.map((t) => (
                <div key={t.name} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                  <div className="flex justify-between items-center">
                    <span className="font-mono text-xs font-semibold text-cyan-300">{t.name}()</span>
                    <span className="text-[10px] font-medium uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {t.category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300">{t.description}</p>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Parameters: {JSON.stringify(t.parameters)}
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setShowToolsDrawer(false)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition"
              >
                Close Registry
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
