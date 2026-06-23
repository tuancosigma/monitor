"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  fetchChannels,
  createChannel,
  updateChannel,
  deleteChannel,
  testChannel,
  fetchRoutingRules,
  createRoutingRule,
  updateRoutingRule,
  deleteRoutingRule,
  fetchSilences,
  createSilence,
  updateSilence,
  deleteSilence,
  type Channel,
  type RoutingRule,
  type Silence,
} from "@/lib/api";

type Tab = "channels" | "routing" | "silences";

export default function ChannelsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("channels");
  
  // Data lists
  const [channels, setChannels] = useState<Channel[]>([]);
  const [routingRules, setRoutingRules] = useState<RoutingRule[]>([]);
  const [silences, setSilences] = useState<Silence[]>([]);
  
  // Status flags
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{ id: number; success: boolean; msg: string } | null>(null);

  // Forms states
  const [showChannelForm, setShowChannelForm] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [channelForm, setChannelForm] = useState({
    name: "",
    type: "slack",
    config: {} as Record<string, any>,
    is_active: true,
  });

  const [showRuleForm, setShowRuleForm] = useState(false);
  const [editingRule, setEditingRule] = useState<RoutingRule | null>(null);
  const [ruleForm, setRuleForm] = useState({
    name: "",
    channel_id: 0,
    criteria: {
      severities: [] as string[],
      rule_ids: [] as string[],
      tags: [] as string[],
    },
    is_active: true,
    escalation_delay_min: "" as string | number,
  });

  const [showSilenceForm, setShowSilenceForm] = useState(false);
  const [editingSilence, setEditingSilence] = useState<Silence | null>(null);
  const [silenceForm, setSilenceForm] = useState({
    name: "",
    filters: {
      severity: "",
      rule_id: "",
      entity_value: "",
    },
    start_time: "",
    end_time: "",
    is_active: true,
  });

  // Load all configurations
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [chData, ruleData, silData] = await Promise.all([
        fetchChannels(),
        fetchRoutingRules(),
        fetchSilences(),
      ]);
      setChannels(chData);
      setRoutingRules(ruleData);
      setSilences(silData);
      
      // Auto-set default channel in rule form if channels exist
      if (chData.length > 0 && !ruleForm.channel_id) {
        setRuleForm((prev) => ({ ...prev, channel_id: chData[0]?.id ?? 0 }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings data");
    } finally {
      setLoading(false);
    }
  }, [ruleForm.channel_id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Initialize config fields when channel type changes
  useEffect(() => {
    if (editingChannel) return; // Keep existing values if editing
    
    let defaultConf: Record<string, any> = {};
    if (channelForm.type === "slack" || channelForm.type === "discord") {
      defaultConf = { webhook_url: "" };
    } else if (channelForm.type === "telegram") {
      defaultConf = { bot_token: "", chat_id: "" };
    } else if (channelForm.type === "smtp") {
      defaultConf = {
        host: "",
        port: 587,
        username: "",
        password: "",
        use_tls: false,
        use_starttls: true,
        from_email: "sentinel@example.com",
        to_email: "",
      };
    } else if (channelForm.type === "webhook") {
      defaultConf = { webhook_url: "", method: "POST", headers: {} };
    }
    setChannelForm((prev) => ({ ...prev, config: defaultConf }));
  }, [channelForm.type, editingChannel]);

  // ============================================================================
  // Channels Actions
  // ============================================================================
  
  const handleOpenCreateChannel = () => {
    setEditingChannel(null);
    setChannelForm({
      name: "",
      type: "slack",
      config: { webhook_url: "" },
      is_active: true,
    });
    setShowChannelForm(true);
  };

  const handleOpenEditChannel = (ch: Channel) => {
    setEditingChannel(ch);
    setChannelForm({
      name: ch.name,
      type: ch.type,
      config: { ...ch.config },
      is_active: ch.is_active,
    });
    setShowChannelForm(true);
  };

  const handleSaveChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingChannel) {
        const updated = await updateChannel(editingChannel.id, channelForm);
        setChannels((prev) => prev.map((c) => (c.id === editingChannel.id ? updated : c)));
      } else {
        const created = await createChannel(channelForm);
        setChannels((prev) => [...prev, created]);
      }
      setShowChannelForm(false);
      setEditingChannel(null);
    } catch (err) {
      alert("Failed to save channel: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleDeleteChannel = async (id: number) => {
    if (!confirm("Are you sure you want to delete this notification channel?")) return;
    try {
      await deleteChannel(id);
      setChannels((prev) => prev.filter((c) => c.id !== id));
      setRoutingRules((prev) => prev.filter((r) => r.channel_id !== id));
    } catch (err) {
      alert("Failed to delete channel: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleTestChannel = async (id: number) => {
    setTestingId(id);
    setTestResult(null);
    try {
      const res = await testChannel(id);
      setTestResult({ id, success: true, msg: res.message });
    } catch (err) {
      setTestResult({ id, success: false, msg: err instanceof Error ? err.message : "Test failed" });
    } finally {
      setTestingId(null);
    }
  };

  // ============================================================================
  // Routing Rules Actions
  // ============================================================================

  const handleOpenCreateRule = () => {
    setEditingRule(null);
    setRuleForm({
      name: "",
      channel_id: channels[0]?.id || 0,
      criteria: {
        severities: [],
        rule_ids: [],
        tags: [],
      },
      is_active: true,
      escalation_delay_min: "",
    });
    setShowRuleForm(true);
  };

  const handleOpenEditRule = (rule: RoutingRule) => {
    setEditingRule(rule);
    setRuleForm({
      name: rule.name,
      channel_id: rule.channel_id,
      criteria: {
        severities: rule.criteria.severities || [],
        rule_ids: rule.criteria.rule_ids || [],
        tags: rule.criteria.tags || [],
      },
      is_active: rule.is_active,
      escalation_delay_min: rule.escalation_delay_min !== null ? rule.escalation_delay_min : "",
    });
    setShowRuleForm(true);
  };

  const handleSaveRule = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: ruleForm.name,
      channel_id: ruleForm.channel_id,
      is_active: ruleForm.is_active,
      escalation_delay_min: ruleForm.escalation_delay_min === "" ? null : Number(ruleForm.escalation_delay_min),
      criteria: {
        severities: ruleForm.criteria.severities.filter(Boolean),
        rule_ids: ruleForm.criteria.rule_ids.filter(Boolean),
        tags: ruleForm.criteria.tags.filter(Boolean),
      },
    };

    try {
      if (editingRule) {
        const updated = await updateRoutingRule(editingRule.id, payload);
        setRoutingRules((prev) => prev.map((r) => (r.id === editingRule.id ? updated : r)));
      } else {
        const created = await createRoutingRule(payload);
        setRoutingRules((prev) => [...prev, created]);
      }
      setShowRuleForm(false);
      setEditingRule(null);
    } catch (err) {
      alert("Failed to save routing rule: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleDeleteRule = async (id: number) => {
    if (!confirm("Are you sure you want to delete this routing rule?")) return;
    try {
      await deleteRoutingRule(id);
      setRoutingRules((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      alert("Failed to delete routing rule: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  // ============================================================================
  // Silences Actions
  // ============================================================================

  const handleOpenCreateSilence = () => {
    setEditingSilence(null);
    // Default to start now, end in 1 hour
    const now = new Date();
    const oneHourLater = new Date(now.getTime() + 60 * 60 * 1000);
    
    setSilenceForm({
      name: "",
      filters: {
        severity: "",
        rule_id: "",
        entity_value: "",
      },
      start_time: now.toISOString().slice(0, 16),
      end_time: oneHourLater.toISOString().slice(0, 16),
      is_active: true,
    });
    setShowSilenceForm(true);
  };

  const handleOpenEditSilence = (sil: Silence) => {
    setEditingSilence(sil);
    setSilenceForm({
      name: sil.name || "",
      filters: {
        severity: sil.filters.severity || "",
        rule_id: sil.filters.rule_id || "",
        entity_value: sil.filters.entity_value || "",
      },
      start_time: new Date(sil.start_time).toISOString().slice(0, 16),
      end_time: new Date(sil.end_time).toISOString().slice(0, 16),
      is_active: sil.is_active,
    });
    setShowSilenceForm(true);
  };

  const handleSaveSilence = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Construct filter cleaning empty values
    const cleanFilters: Record<string, any> = {};
    if (silenceForm.filters.severity) cleanFilters.severity = silenceForm.filters.severity;
    if (silenceForm.filters.rule_id) cleanFilters.rule_id = silenceForm.filters.rule_id;
    if (silenceForm.filters.entity_value) cleanFilters.entity_value = silenceForm.filters.entity_value;

    const payload = {
      name: silenceForm.name || null,
      start_time: new Date(silenceForm.start_time).toISOString(),
      end_time: new Date(silenceForm.end_time).toISOString(),
      is_active: silenceForm.is_active,
      filters: cleanFilters,
    };

    try {
      if (editingSilence) {
        const updated = await updateSilence(editingSilence.id, payload);
        setSilences((prev) => prev.map((s) => (s.id === editingSilence.id ? updated : s)));
      } else {
        const created = await createSilence(payload);
        setSilences((prev) => [...prev, created]);
      }
      setShowSilenceForm(false);
      setEditingSilence(null);
    } catch (err) {
      alert("Failed to save silence rule: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleDeleteSilence = async (id: number) => {
    if (!confirm("Are you sure you want to delete this silence rule?")) return;
    try {
      await deleteSilence(id);
      setSilences((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      alert("Failed to delete silence rule: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleToggleSilence = async (sil: Silence) => {
    try {
      const updated = await updateSilence(sil.id, { is_active: !sil.is_active });
      setSilences((prev) => prev.map((s) => (s.id === sil.id ? updated : s)));
    } catch (err) {
      alert("Failed to update silence rule status: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-8">
      {/* Header */}
      <header className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Link href="/" className="hover:text-slate-200">Home</Link>
          <span>/</span>
          <span className="text-slate-200">Alerting Settings</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white mt-1">Alerting & Routing Settings</h1>
        <p className="text-slate-400">Configure notification integrations, severity routing matrices, and active silences.</p>
      </header>

      {/* Navigation Tabs */}
      <div className="flex gap-4 border-b border-slate-800 pb-3">
        <Link href="/alerts" className="text-sm font-semibold text-slate-400 hover:text-slate-200 pb-3 px-1">
          Alerts List
        </Link>
        <Link href="/incidents" className="text-sm font-semibold text-slate-400 hover:text-slate-200 pb-3 px-1">
          Incidents Board
        </Link>
        <button
          onClick={() => setActiveTab("channels")}
          className={`text-sm font-semibold pb-3 px-1 outline-none ${
            activeTab === "channels" ? "border-b-2 border-sky-500 text-sky-400" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Notification Channels
        </button>
        <button
          onClick={() => setActiveTab("routing")}
          className={`text-sm font-semibold pb-3 px-1 outline-none ${
            activeTab === "routing" ? "border-b-2 border-sky-500 text-sky-400" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Routing Rules
        </button>
        <button
          onClick={() => setActiveTab("silences")}
          className={`text-sm font-semibold pb-3 px-1 outline-none ${
            activeTab === "silences" ? "border-b-2 border-sky-500 text-sky-400" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Muting Silences
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500" />
        </div>
      ) : (
        <>
          {/* TAB 1: Channels */}
          {activeTab === "channels" && (
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold text-white">Notification Channels</h2>
                  <p className="text-sm text-slate-400">Integrate Slack, Telegram, Discord, SMTP, or secure custom webhooks.</p>
                </div>
                <button
                  onClick={handleOpenCreateChannel}
                  className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 transition"
                >
                  Add Channel
                </button>
              </div>

              {/* Channels Grid */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {channels.map((ch) => (
                  <div key={ch.id} className="rounded-xl border border-slate-800 bg-slate-900/30 p-5 flex flex-col gap-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-slate-100">{ch.name}</h3>
                        <span className="inline-block rounded bg-slate-800 border border-slate-700/50 px-1.5 py-0.5 text-2xs font-mono text-slate-400 mt-1 uppercase">
                          {ch.type}
                        </span>
                      </div>
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${
                          ch.is_active ? "bg-emerald-500" : "bg-slate-600"
                        }`}
                        title={ch.is_active ? "Active" : "Inactive"}
                      />
                    </div>

                    <div className="text-xs text-slate-400 font-mono divide-y divide-slate-800/40 bg-slate-950/40 p-3 rounded-lg border border-slate-800/60">
                      {ch.type === "slack" && <div>Webhook: {ch.config.webhook_url ? "Configured" : "Not Set"}</div>}
                      {ch.type === "discord" && <div>Webhook: {ch.config.webhook_url ? "Configured" : "Not Set"}</div>}
                      {ch.type === "telegram" && (
                        <>
                          <div className="pb-1">Chat ID: {ch.config.chat_id || "—"}</div>
                          <div className="pt-1">Token: {ch.config.bot_token ? "••••••••" : "—"}</div>
                        </>
                      )}
                      {ch.type === "smtp" && (
                        <>
                          <div className="pb-1">Server: {ch.config.host}:{ch.config.port}</div>
                          <div className="py-1">To: {ch.config.to_email || "—"}</div>
                          <div className="pt-1">From: {ch.config.from_email || "—"}</div>
                        </>
                      )}
                      {ch.type === "webhook" && (
                        <>
                          <div className="pb-1">Target: {ch.config.webhook_url || "—"}</div>
                          <div className="pt-1">Method: {ch.config.method || "POST"}</div>
                        </>
                      )}
                    </div>

                    {testResult && testResult.id === ch.id && (
                      <div
                        className={`text-xs p-2 rounded border ${
                          testResult.success
                            ? "bg-emerald-950/30 text-emerald-400 border-emerald-900/30"
                            : "bg-red-950/30 text-red-400 border-red-900/30"
                        }`}
                      >
                        {testResult.msg}
                      </div>
                    )}

                    <div className="flex gap-2 mt-auto pt-2 border-t border-slate-800/50">
                      <button
                        onClick={() => handleTestChannel(ch.id)}
                        disabled={testingId !== null}
                        className="text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-900 px-3 py-1.5 rounded transition mr-auto border border-slate-700/50"
                      >
                        {testingId === ch.id ? "Testing..." : "Test Send"}
                      </button>
                      <button
                        onClick={() => handleOpenEditChannel(ch)}
                        className="text-xs font-semibold text-sky-400 hover:text-sky-300"
                      >
                        Edit
                      </button>
                      <span className="text-slate-700">|</span>
                      <button
                        onClick={() => handleDeleteChannel(ch.id)}
                        className="text-xs font-semibold text-red-400 hover:text-red-300"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
                
                {channels.length === 0 && (
                  <div className="col-span-full text-center py-12 border border-dashed border-slate-800 rounded-xl bg-slate-900/5 text-slate-500">
                    No channels configured. Click &quot;Add Channel&quot; to create one.
                  </div>
                )}
              </div>

              {/* Channel Form Modal */}
              {showChannelForm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                  <div className="w-full max-w-lg rounded-xl border border-slate-800 bg-slate-900 p-6 flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
                    <header className="flex justify-between items-center border-b border-slate-800 pb-3">
                      <h3 className="text-lg font-bold text-white">
                        {editingChannel ? "Edit Channel" : "New Notification Channel"}
                      </h3>
                      <button
                        onClick={() => setShowChannelForm(false)}
                        className="text-slate-400 hover:text-white"
                      >
                        ✕
                      </button>
                    </header>

                    <form onSubmit={handleSaveChannel} className="flex flex-col gap-4">
                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Channel Name</label>
                        <input
                          type="text"
                          required
                          value={channelForm.name}
                          onChange={(e) => setChannelForm((prev) => ({ ...prev, name: e.target.value }))}
                          placeholder="e.g. SOC Team Slack"
                          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                        />
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Channel Type</label>
                        <select
                          value={channelForm.type}
                          disabled={editingChannel !== null}
                          onChange={(e) => setChannelForm((prev) => ({ ...prev, type: e.target.value }))}
                          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none disabled:opacity-50"
                        >
                          <option value="slack">Slack Webhook</option>
                          <option value="discord">Discord Webhook</option>
                          <option value="telegram">Telegram Bot</option>
                          <option value="smtp">SMTP Email</option>
                          <option value="webhook">Generic Webhook (SSRF Guarded)</option>
                        </select>
                      </div>

                      {/* Config fields depending on type */}
                      <fieldset className="border border-slate-800 p-4 rounded-lg flex flex-col gap-3">
                        <legend className="text-xs font-bold text-slate-500 px-2 uppercase tracking-wide">Connection Parameters</legend>
                        
                        {(channelForm.type === "slack" || channelForm.type === "discord") && (
                          <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-slate-400 uppercase">Webhook URL</label>
                            <input
                              type="text"
                              required
                              value={channelForm.config.webhook_url || ""}
                              onChange={(e) =>
                                setChannelForm((prev) => ({
                                  ...prev,
                                  config: { ...prev.config, webhook_url: e.target.value },
                                }))
                              }
                              placeholder="e.g. ${SLACK_WEBHOOK_URL} or https://hooks.slack.com/services/..."
                              className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none font-mono"
                            />
                            <p className="text-2xs text-slate-500 italic mt-0.5">
                              {"Tip: Reference environment secrets like ${SLACK_WEBHOOK_URL}."}
                            </p>
                          </div>
                        )}

                        {channelForm.type === "telegram" && (
                          <>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">Bot Token</label>
                              <input
                                type="text"
                                required
                                value={channelForm.config.bot_token || ""}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, bot_token: e.target.value },
                                  }))
                                }
                                placeholder="e.g. ${TELEGRAM_BOT_TOKEN} or 123456:ABC-DEF"
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none font-mono"
                              />
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">Chat ID</label>
                              <input
                                type="text"
                                required
                                value={channelForm.config.chat_id || ""}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, chat_id: e.target.value },
                                  }))
                                }
                                placeholder="e.g. -100123456789"
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none font-mono"
                              />
                            </div>
                          </>
                        )}

                        {channelForm.type === "smtp" && (
                          <div className="grid grid-cols-2 gap-3">
                            <div className="flex flex-col gap-1.5 col-span-2">
                              <label className="text-xs font-semibold text-slate-400 uppercase">SMTP Server Host</label>
                              <input
                                type="text"
                                required
                                value={channelForm.config.host || ""}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, host: e.target.value },
                                  }))
                                }
                                placeholder="smtp.mailgun.org"
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                              />
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">Port</label>
                              <input
                                type="number"
                                required
                                value={channelForm.config.port || 587}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, port: Number(e.target.value) },
                                  }))
                                }
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                              />
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">Use STARTTLS</label>
                              <select
                                value={String(channelForm.config.use_starttls ?? true)}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, use_starttls: e.target.value === "true" },
                                  }))
                                }
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                              >
                                <option value="true">True (Port 587)</option>
                                <option value="false">False</option>
                              </select>
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">SMTP User</label>
                              <input
                                type="text"
                                value={channelForm.config.username || ""}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, username: e.target.value },
                                  }))
                                }
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                              />
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">SMTP Password</label>
                              <input
                                type="password"
                                value={channelForm.config.password || ""}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, password: e.target.value },
                                  }))
                                }
                                placeholder="••••••••"
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                              />
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">Recipient Email</label>
                              <input
                                type="email"
                                required
                                value={channelForm.config.to_email || ""}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, to_email: e.target.value },
                                  }))
                                }
                                placeholder="soc@example.com"
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                              />
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">Sender Email</label>
                              <input
                                type="email"
                                required
                                value={channelForm.config.from_email || ""}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, from_email: e.target.value },
                                  }))
                                }
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                              />
                            </div>
                          </div>
                        )}

                        {channelForm.type === "webhook" && (
                          <>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">Target Endpoint URL</label>
                              <input
                                type="text"
                                required
                                value={channelForm.config.webhook_url || ""}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, webhook_url: e.target.value },
                                  }))
                                }
                                placeholder="https://api.internal.com/notify"
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none font-mono"
                              />
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold text-slate-400 uppercase">HTTP Method</label>
                              <select
                                value={channelForm.config.method || "POST"}
                                onChange={(e) =>
                                  setChannelForm((prev) => ({
                                    ...prev,
                                    config: { ...prev.config, method: e.target.value },
                                  }))
                                }
                                className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                              >
                                <option value="POST">POST</option>
                                <option value="PUT">PUT</option>
                              </select>
                            </div>
                          </>
                        )}
                      </fieldset>

                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          id="ch_active"
                          checked={channelForm.is_active}
                          onChange={(e) => setChannelForm((prev) => ({ ...prev, is_active: e.target.checked }))}
                          className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-sky-600 focus:ring-sky-500"
                        />
                        <label htmlFor="ch_active" className="text-sm text-slate-300 font-semibold select-none">
                          Channel is Active
                        </label>
                      </div>

                      <div className="flex justify-end gap-2 border-t border-slate-800 pt-4 mt-2">
                        <button
                          type="button"
                          onClick={() => setShowChannelForm(false)}
                          className="rounded bg-slate-800 border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 transition"
                        >
                          Save Channel
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: Routing Rules */}
          {activeTab === "routing" && (
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold text-white">Routing Rules</h2>
                  <p className="text-sm text-slate-400">Map security severities, tags, or specific rules to target notification channels.</p>
                </div>
                <button
                  onClick={handleOpenCreateRule}
                  disabled={channels.length === 0}
                  className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50 transition"
                >
                  Create Rule
                </button>
              </div>

              {/* Rules Table */}
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/10">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                      <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">Rule Name</th>
                      <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">Matching Criteria</th>
                      <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">Target Channel</th>
                      <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">Escalation Delay</th>
                      <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850">
                    {routingRules.map((rule) => (
                      <tr key={rule.id} className="hover:bg-slate-900/25 transition">
                        <td className="px-4 py-4">
                          <div className="font-semibold text-slate-200">{rule.name}</div>
                          <span
                            className={`inline-block rounded-full px-1.5 py-0.5 text-3xs font-semibold border mt-1.5 ${
                              rule.is_active
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : "bg-slate-800 text-slate-500 border-slate-700"
                            }`}
                          >
                            {rule.is_active ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex flex-col gap-1.5 max-w-[400px]">
                            {rule.criteria.severities && rule.criteria.severities.length > 0 && (
                              <div className="flex items-center gap-1.5">
                                <span className="text-2xs font-semibold text-slate-500 w-16">Severities:</span>
                                <div className="flex flex-wrap gap-1">
                                  {rule.criteria.severities.map((s: string) => (
                                    <span key={s} className="rounded bg-sky-950/40 border border-sky-900/30 text-sky-400 text-3xs font-semibold px-1.5 py-0.2">
                                      {s.toUpperCase()}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {rule.criteria.rule_ids && rule.criteria.rule_ids.length > 0 && (
                              <div className="flex items-center gap-1.5">
                                <span className="text-2xs font-semibold text-slate-500 w-16">Rules:</span>
                                <div className="flex flex-wrap gap-1">
                                  {rule.criteria.rule_ids.map((r: string) => (
                                    <span key={r} className="rounded bg-slate-800 border border-slate-700/50 text-slate-300 font-mono text-3xs px-1.5 py-0.2">
                                      {r.slice(0, 12)}...
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {rule.criteria.tags && rule.criteria.tags.length > 0 && (
                              <div className="flex items-center gap-1.5">
                                <span className="text-2xs font-semibold text-slate-500 w-16">MITRE Tags:</span>
                                <div className="flex flex-wrap gap-1">
                                  {rule.criteria.tags.map((t: string) => (
                                    <span key={t} className="rounded bg-red-950/40 border border-red-900/30 text-red-400 text-3xs font-semibold px-1.5 py-0.2">
                                      {t}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {!rule.criteria.severities?.length && !rule.criteria.rule_ids?.length && !rule.criteria.tags?.length && (
                              <span className="text-slate-500 italic text-2xs">Match All Alerts/Incidents</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          {rule.channel ? (
                            <div>
                              <div className="font-semibold text-slate-200">{rule.channel.name}</div>
                              <div className="text-3xs text-slate-500 font-mono uppercase">{rule.channel.type}</div>
                            </div>
                          ) : (
                            <span className="text-red-400 italic">No channel mapped</span>
                          )}
                        </td>
                        <td className="px-4 py-4 text-slate-300 font-mono">
                          {rule.escalation_delay_min !== null ? (
                            <span className="text-amber-400 font-semibold">{rule.escalation_delay_min} mins</span>
                          ) : (
                            <span className="text-slate-500">— (Immediate)</span>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-3">
                            <button
                              onClick={() => handleOpenEditRule(rule)}
                              className="text-xs font-semibold text-sky-400 hover:text-sky-300"
                            >
                              Edit
                            </button>
                            <span className="text-slate-700">|</span>
                            <button
                              onClick={() => handleDeleteRule(rule.id)}
                              className="text-xs font-semibold text-red-400 hover:text-red-300"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {routingRules.length === 0 && (
                      <tr>
                        <td colSpan={5} className="text-center py-12 text-slate-500">
                          No routing rules configured. Create one to enable alert forwards.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Rule Form Modal */}
              {showRuleForm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                  <div className="w-full max-w-lg rounded-xl border border-slate-800 bg-slate-900 p-6 flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
                    <header className="flex justify-between items-center border-b border-slate-800 pb-3">
                      <h3 className="text-lg font-bold text-white">
                        {editingRule ? "Edit Routing Rule" : "New Routing Rule"}
                      </h3>
                      <button
                        onClick={() => setShowRuleForm(false)}
                        className="text-slate-400 hover:text-white"
                      >
                        ✕
                      </button>
                    </header>

                    <form onSubmit={handleSaveRule} className="flex flex-col gap-4">
                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Rule Name</label>
                        <input
                          type="text"
                          required
                          value={ruleForm.name}
                          onChange={(e) => setRuleForm((prev) => ({ ...prev, name: e.target.value }))}
                          placeholder="e.g. Route Criticals to Slack"
                          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                        />
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Target Channel</label>
                        <select
                          value={ruleForm.channel_id}
                          onChange={(e) => setRuleForm((prev) => ({ ...prev, channel_id: Number(e.target.value) }))}
                          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                        >
                          {channels.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name} ({c.type.toUpperCase()})
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Criteria Selectors */}
                      <fieldset className="border border-slate-800 p-4 rounded-lg flex flex-col gap-3">
                        <legend className="text-xs font-bold text-slate-500 px-2 uppercase tracking-wide">Filter Criteria</legend>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase">Match Severities</label>
                          <div className="flex flex-wrap gap-3 mt-1 bg-slate-950/40 p-2.5 rounded border border-slate-800">
                            {["critical", "high", "medium", "low", "info"].map((sev) => {
                              const active = ruleForm.criteria.severities.includes(sev);
                              return (
                                <label key={sev} className="flex items-center gap-1.5 select-none text-xs font-medium cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={active}
                                    onChange={(e) => {
                                      const updated = e.target.checked
                                        ? [...ruleForm.criteria.severities, sev]
                                        : ruleForm.criteria.severities.filter((s) => s !== sev);
                                      setRuleForm((prev) => ({
                                        ...prev,
                                        criteria: { ...prev.criteria, severities: updated },
                                      }));
                                    }}
                                    className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-950 text-sky-600 focus:ring-sky-500"
                                  />
                                  <span className="text-slate-300 uppercase">{sev}</span>
                                </label>
                              );
                            })}
                          </div>
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase">Match Rule IDs (comma-separated)</label>
                          <input
                            type="text"
                            value={ruleForm.criteria.rule_ids.join(", ")}
                            onChange={(e) => {
                              const list = e.target.value.split(",").map((s) => s.trim());
                              setRuleForm((prev) => ({
                                ...prev,
                                criteria: { ...prev.criteria, rule_ids: list },
                              }));
                            }}
                            placeholder="e.g. 5a8a478b-302a-4db5-b82b-8a8b13c7dbba"
                            className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none font-mono"
                          />
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase">Match MITRE Technique IDs (comma-separated)</label>
                          <input
                            type="text"
                            value={ruleForm.criteria.tags.join(", ")}
                            onChange={(e) => {
                              const list = e.target.value.split(",").map((s) => s.trim());
                              setRuleForm((prev) => ({
                                ...prev,
                                criteria: { ...prev.criteria, tags: list },
                              }));
                            }}
                            placeholder="e.g. T1110, T1078"
                            className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none font-mono"
                          />
                        </div>
                      </fieldset>

                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Escalation Delay (Minutes)</label>
                        <input
                          type="number"
                          value={ruleForm.escalation_delay_min}
                          onChange={(e) => setRuleForm((prev) => ({ ...prev, escalation_delay_min: e.target.value }))}
                          placeholder="e.g. 15 (leave blank for immediate send)"
                          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                        />
                        <p className="text-2xs text-slate-500 italic mt-0.5">If set, escalates unacknowledged open alerts matching this rule after N minutes.</p>
                      </div>

                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          id="rule_active"
                          checked={ruleForm.is_active}
                          onChange={(e) => setRuleForm((prev) => ({ ...prev, is_active: e.target.checked }))}
                          className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-sky-600 focus:ring-sky-500"
                        />
                        <label htmlFor="rule_active" className="text-sm text-slate-300 font-semibold select-none">
                          Rule is Active
                        </label>
                      </div>

                      <div className="flex justify-end gap-2 border-t border-slate-800 pt-4 mt-2">
                        <button
                          type="button"
                          onClick={() => setShowRuleForm(false)}
                          className="rounded bg-slate-800 border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 transition"
                        >
                          Save Rule
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Silences */}
          {activeTab === "silences" && (
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold text-white">Muting Silences</h2>
                  <p className="text-sm text-slate-400">Temporarily silence notification triggers matching specific filters.</p>
                </div>
                <button
                  onClick={handleOpenCreateSilence}
                  className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 transition"
                >
                  Add Silence
                </button>
              </div>

              {/* Silences Grid */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {silences.map((sil) => {
                  const now = new Date();
                  const start = new Date(sil.start_time);
                  const end = new Date(sil.end_time);
                  const isMuted = sil.is_active && start <= now && now <= end;
                  const isExpired = end < now;
                  
                  return (
                    <div key={sil.id} className="rounded-xl border border-slate-800 bg-slate-900/30 p-5 flex flex-col gap-4 relative">
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-semibold text-slate-100">{sil.name || `Silence Rule #${sil.id}`}</h3>
                          <span
                            className={`inline-block rounded-full px-1.5 py-0.5 text-3xs font-semibold border mt-1.5 ${
                              isMuted
                                ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                : isExpired
                                ? "bg-slate-800 text-slate-500 border-slate-700"
                                : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                            }`}
                          >
                            {isMuted ? "MUTING NOW" : isExpired ? "EXPIRED" : "SCHEDULED"}
                          </span>
                        </div>
                        <button
                          onClick={() => handleToggleSilence(sil)}
                          className={`text-2xs font-semibold border px-2 py-0.5 rounded ${
                            sil.is_active
                              ? "bg-slate-800 text-slate-300 hover:bg-slate-750 border-slate-700/50"
                              : "bg-emerald-950/20 border-emerald-900/30 text-emerald-400 hover:bg-emerald-950/40"
                          }`}
                        >
                          {sil.is_active ? "Disable" : "Enable"}
                        </button>
                      </div>

                      {/* Filters info */}
                      <div className="flex flex-col gap-1 text-xs bg-slate-950/40 p-3 rounded-lg border border-slate-800/60 font-mono text-slate-400">
                        {sil.filters.severity && (
                          <div>
                            <span className="text-slate-500">severity:</span> {sil.filters.severity}
                          </div>
                        )}
                        {sil.filters.rule_id && (
                          <div>
                            <span className="text-slate-500">rule_id:</span> {sil.filters.rule_id.substring(0, 16)}...
                          </div>
                        )}
                        {sil.filters.entity_value && (
                          <div>
                            <span className="text-slate-500">entity:</span> {sil.filters.entity_value}
                          </div>
                        )}
                        {!sil.filters.severity && !sil.filters.rule_id && !sil.filters.entity_value && (
                          <div className="italic text-slate-600">Silence All Notifications</div>
                        )}
                      </div>

                      {/* Time window info */}
                      <div className="text-2xs text-slate-400 flex flex-col gap-0.5">
                        <div>
                          <span className="text-slate-500 font-semibold uppercase">Start:</span>{" "}
                          {start.toLocaleString()}
                        </div>
                        <div>
                          <span className="text-slate-500 font-semibold uppercase">End:</span>{" "}
                          {end.toLocaleString()}
                        </div>
                      </div>

                      <div className="flex gap-3 justify-end mt-auto pt-2 border-t border-slate-800/50 text-xs">
                        <button
                          onClick={() => handleOpenEditSilence(sil)}
                          className="font-semibold text-sky-400 hover:text-sky-300"
                        >
                          Edit
                        </button>
                        <span className="text-slate-700">|</span>
                        <button
                          onClick={() => handleDeleteSilence(sil.id)}
                          className="font-semibold text-red-400 hover:text-red-300"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  );
                })}
                
                {silences.length === 0 && (
                  <div className="col-span-full text-center py-12 border border-dashed border-slate-800 rounded-xl bg-slate-900/5 text-slate-500">
                    No muting silences scheduled. Click &quot;Add Silence&quot; to create one.
                  </div>
                )}
              </div>

              {/* Silence Form Modal */}
              {showSilenceForm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                  <div className="w-full max-w-lg rounded-xl border border-slate-800 bg-slate-900 p-6 flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
                    <header className="flex justify-between items-center border-b border-slate-800 pb-3">
                      <h3 className="text-lg font-bold text-white">
                        {editingSilence ? "Edit Muting Silence" : "New Muting Silence"}
                      </h3>
                      <button
                        onClick={() => setShowSilenceForm(false)}
                        className="text-slate-400 hover:text-white"
                      >
                        ✕
                      </button>
                    </header>

                    <form onSubmit={handleSaveSilence} className="flex flex-col gap-4">
                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Silence Description</label>
                        <input
                          type="text"
                          required
                          value={silenceForm.name}
                          onChange={(e) => setSilenceForm((prev) => ({ ...prev, name: e.target.value }))}
                          placeholder="e.g. Mute Low alerts during scheduled maintenance"
                          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                        />
                      </div>

                      {/* Criteria filters */}
                      <fieldset className="border border-slate-800 p-4 rounded-lg flex flex-col gap-3">
                        <legend className="text-xs font-bold text-slate-500 px-2 uppercase tracking-wide">Mute Filters</legend>
                        
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase">Mute Severity</label>
                          <select
                            value={silenceForm.filters.severity}
                            onChange={(e) =>
                              setSilenceForm((prev) => ({
                                ...prev,
                                filters: { ...prev.filters, severity: e.target.value },
                              }))
                            }
                            className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none"
                          >
                            <option value="">Any Severity</option>
                            <option value="critical">Critical</option>
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                            <option value="info">Info</option>
                          </select>
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase">Mute Rule ID</label>
                          <input
                            type="text"
                            value={silenceForm.filters.rule_id}
                            onChange={(e) =>
                              setSilenceForm((prev) => ({
                                ...prev,
                                filters: { ...prev.filters, rule_id: e.target.value.trim() },
                              }))
                            }
                            placeholder="e.g. 5a8a478b-302a-4db5-b82b-8a8b13c7dbba"
                            className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none font-mono"
                          />
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase">Mute Target Entity Value</label>
                          <input
                            type="text"
                            value={silenceForm.filters.entity_value}
                            onChange={(e) =>
                              setSilenceForm((prev) => ({
                                ...prev,
                                filters: { ...prev.filters, entity_value: e.target.value.trim() },
                              }))
                            }
                            placeholder="e.g. 192.168.1.50"
                            className="rounded border border-slate-750 bg-slate-950 px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none font-mono"
                          />
                        </div>
                      </fieldset>

                      {/* Time pickers */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Start Time</label>
                          <input
                            type="datetime-local"
                            required
                            value={silenceForm.start_time}
                            onChange={(e) => setSilenceForm((prev) => ({ ...prev, start_time: e.target.value }))}
                            className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none text-white font-mono"
                          />
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">End Time</label>
                          <input
                            type="datetime-local"
                            required
                            value={silenceForm.end_time}
                            onChange={(e) => setSilenceForm((prev) => ({ ...prev, end_time: e.target.value }))}
                            className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none text-white font-mono"
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          id="silence_active"
                          checked={silenceForm.is_active}
                          onChange={(e) => setSilenceForm((prev) => ({ ...prev, is_active: e.target.checked }))}
                          className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-sky-600 focus:ring-sky-500"
                        />
                        <label htmlFor="silence_active" className="text-sm text-slate-300 font-semibold select-none">
                          Silence is Active
                        </label>
                      </div>

                      <div className="flex justify-end gap-2 border-t border-slate-800 pt-4 mt-2">
                        <button
                          type="button"
                          onClick={() => setShowSilenceForm(false)}
                          className="rounded bg-slate-800 border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 transition"
                        >
                          Save Silence
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </main>
  );
}
