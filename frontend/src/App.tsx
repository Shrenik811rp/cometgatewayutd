import { useState, useRef, useEffect, useCallback } from 'react';
import { SidebarRail } from './components/SidebarRail';
import { QueryBar } from './components/QueryBar';
import { PrivacyAuditStrip } from './components/PrivacyAuditStrip';
import { MCPToolStrip } from './components/MCPToolStrip';
import { MCPRegistryModal } from './components/MCPRegistryModal';
import { StreamOutputPanel } from './components/StreamOutputPanel';
import { TelemetryLedger } from './components/TelemetryLedger';
import { fetchMCPStatus, fetchMetrics, streamChat } from './api/streamClient';
import { MCPStatusResponse, MCPToolEvent, MetricsSummary, PrivacyEvent, TelemetryEvent } from './types';

const MODEL_MAP: Record<string, string> = {
  openai: 'gpt-4o-mini',
  anthropic: 'claude-3-5-haiku',
  gemini: 'gemini-3.5-flash-lite',
  cometai: 'openai/cometai-default',
};

export default function App() {
  const [prompt, setPrompt] = useState<string>('');
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini' | 'cometai'>('openai');
  const [enablePii, setEnablePii] = useState<boolean>(true);
  const [promptVersion, setPromptVersion] = useState<'v1' | 'v2'>('v2');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [privacyEvent, setPrivacyEvent] = useState<PrivacyEvent | null>(null);
  const [mcpToolEvent, setMcpToolEvent] = useState<MCPToolEvent | null>(null);
  const [mcpStatus, setMcpStatus] = useState<MCPStatusResponse | null>(null);
  const [isMCPModalOpen, setIsMCPModalOpen] = useState<boolean>(false);
  const [isRefreshingMCP, setIsRefreshingMCP] = useState<boolean>(false);
  const [responseText, setResponseText] = useState<string>('');
  const [telemetry, setTelemetry] = useState<TelemetryEvent | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const handleRefreshMCP = useCallback(async () => {
    setIsRefreshingMCP(true);
    try {
      const data = await fetchMCPStatus();
      setMcpStatus(data);
    } catch (err) {
      console.warn('Failed to fetch MCP status:', err);
    } finally {
      setIsRefreshingMCP(false);
    }
  }, []);

  const handleRefreshMetrics = useCallback(async () => {
    setLoadingMetrics(true);
    try {
      const data = await fetchMetrics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to sync metrics:', err);
    } finally {
      setLoadingMetrics(false);
    }
  }, []);

  useEffect(() => {
    handleRefreshMetrics();
    handleRefreshMCP();
  }, [handleRefreshMetrics, handleRefreshMCP]);

  const handleSubmit = async () => {
    if (!prompt.trim() || isStreaming) return;

    setError(null);
    setResponseText('');
    setPrivacyEvent(null);
    setMcpToolEvent(null);
    setIsStreaming(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    await streamChat(
      {
        prompt: prompt.trim(),
        provider,
        prompt_version: promptVersion,
        enable_pii_redaction: enablePii,
      },
      {
        onPrivacy: (p) => setPrivacyEvent(p),
        onMCPTool: (m) => setMcpToolEvent(m),
        onDelta: (chunk) => setResponseText((prev) => prev + chunk),
        onTelemetry: (t) => {
          setTelemetry(t);
          handleRefreshMetrics();
        },
        onDone: () => setIsStreaming(false),
        onError: (err) => {
          setError(err.message || 'Stream connection interrupted');
          setIsStreaming(false);
        },
      },
      controller.signal
    );
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  };

  const handleSelectPreset = (presetText: string) => {
    setPrompt(presetText);
  };

  const activeModelDisplay = telemetry?.model_used || MODEL_MAP[provider];

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-[#F7F4EF] text-[#141413]">
      {/* Left Control Rail */}
      <SidebarRail
        provider={provider}
        onProviderChange={setProvider}
        enablePii={enablePii}
        onEnablePiiChange={setEnablePii}
        promptVersion={promptVersion}
        onPromptVersionChange={setPromptVersion}
        onSelectPreset={handleSelectPreset}
        isStreaming={isStreaming}
        mcpStatus={mcpStatus}
        onOpenMCPModal={() => setIsMCPModalOpen(true)}
      />

      {/* Right Main Workspace */}
      <main className="flex-1 p-6 lg:p-8 flex flex-col gap-6 overflow-x-hidden">
        {/* Top Query Bar */}
        <QueryBar
          prompt={prompt}
          onPromptChange={setPrompt}
          onSubmit={handleSubmit}
          onStop={handleStop}
          isStreaming={isStreaming}
        />

        {/* Pre-Inference FERPA Audit Strip */}
        {privacyEvent && <PrivacyAuditStrip privacyEvent={privacyEvent} />}

        {/* Governed UTD OIT MCP Tool Execution Strip */}
        {mcpToolEvent && <MCPToolStrip toolEvent={mcpToolEvent} />}

        {/* Inference Stream Output Panel */}
        <StreamOutputPanel
          responseText={responseText}
          isStreaming={isStreaming}
          activeModel={activeModelDisplay}
          error={error}
        />

        {/* Bottom Telemetry & Gateway Audit Grid */}
        <TelemetryLedger
          telemetry={telemetry}
          metrics={metrics}
          onRefreshMetrics={handleRefreshMetrics}
          loadingMetrics={loadingMetrics}
        />
      </main>

      {/* Live FastMCP Server Health & Tool Registry Inspector Modal */}
      <MCPRegistryModal
        isOpen={isMCPModalOpen}
        onClose={() => setIsMCPModalOpen(false)}
        mcpStatus={mcpStatus}
        onRefresh={handleRefreshMCP}
        isRefreshing={isRefreshingMCP}
      />
    </div>
  );
}
