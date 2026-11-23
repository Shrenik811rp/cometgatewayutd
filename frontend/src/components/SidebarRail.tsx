import React, { useEffect, useState } from 'react';
import { fetchHealth } from '../api/streamClient';
import { HealthStatus, MCPStatusResponse } from '../types';

interface SidebarRailProps {
  provider: 'openai' | 'anthropic' | 'gemini' | 'cometai';
  onProviderChange: (p: 'openai' | 'anthropic' | 'gemini' | 'cometai') => void;
  enablePii: boolean;
  onEnablePiiChange: (val: boolean) => void;
  promptVersion: 'v1' | 'v2';
  onPromptVersionChange: (ver: 'v1' | 'v2') => void;
  onSelectPreset: (text: string) => void;
  isStreaming: boolean;
  mcpStatus?: MCPStatusResponse | null;
  onOpenMCPModal?: () => void;
}

const PRESET_CASES = [
  {
    label: 'FERPA TICKET (UTD ID)',
    primary: true,
    prompt: 'Hi, my student ID is 2025123456 and email is netid@utdallas.edu. I cannot connect my laptop to CometNet Wi-Fi.',
  },
  {
    label: 'MULTI-PII (SSN + PHONE)',
    primary: false,
    prompt: 'Urgent financial aid inquiry: SSN 123-45-6789, Phone (972) 555-0199. Why is my Texas Public Education Grant hold still active in Galaxy?',
  },
  {
    label: 'COMETAI CLUSTER (OIT)',
    primary: false,
    prompt: 'Explain the UT Dallas CometAI architecture, student data classification standard DCL-2, and how queries are routed through campus sovereign enclaves.',
  },
  {
    label: 'MCP SERVICE HEALTH',
    primary: false,
    prompt: 'Is the campus Galaxy PeopleSoft portal down or operational right now?',
  },
  {
    label: 'CAMPUS IT POLICY',
    primary: false,
    prompt: 'What are the required security procedures for enrolling a replacement smartphone in Duo Mobile MFA and accessing the campus GlobalProtect VPN?',
  },
];

export const SidebarRail: React.FC<SidebarRailProps> = ({
  provider,
  onProviderChange,
  enablePii,
  onEnablePiiChange,
  promptVersion,
  onPromptVersionChange,
  onSelectPreset,
  isStreaming,
  mcpStatus,
  onOpenMCPModal,
}) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchHealth()
      .then((data) => {
        if (mounted) setHealth(data);
      })
      .catch(() => {
        if (mounted) setHealth(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <aside className="w-full lg:w-[340px] shrink-0 bg-[#E5DFD5] border-b-2 lg:border-b-0 lg:border-r-2 border-[#141413] p-7 lg:p-8 flex flex-col justify-between gap-7">
      <div className="flex flex-col gap-7">
        {/* Masthead */}
        <div>
          <div className="font-display text-4xl font-bold tracking-tight leading-[0.95] text-[#141413]">
            COMET<br />GATEWAY
          </div>
          <div className="text-xs font-semibold text-[#E85D2A] mt-2 tracking-wide uppercase font-mono">
            UTD OIT • AI ORCHESTRATOR
          </div>

          {/* Single Status Pill & Clickable FastMCP Pill */}
          <div className="mt-4 flex flex-col gap-2.5">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-white border-2 border-[#141413] shadow-[2px_2px_0px_#141413] font-mono text-[11px] font-bold uppercase tracking-wider text-[#141413]">
              <span className={`w-2 h-2 ${health?.status === 'ok' ? 'bg-[#154734]' : 'bg-[#E85D2A]'}`} />
              <span>
                {health?.status === 'ok'
                  ? health.mock_mode
                    ? 'ONLINE • MOCK'
                    : 'ONLINE • LIVE'
                  : 'OFFLINE'}
              </span>
            </div>

            <button
              type="button"
              onClick={onOpenMCPModal}
              className="inline-flex items-center justify-between gap-2 px-2.5 py-1.5 bg-[#141413] text-[#00D4E5] border-2 border-[#141413] shadow-[3px_3px_0px_#8C8275] font-mono text-[10px] font-bold uppercase tracking-wider hover:-translate-x-[1px] hover:-translate-y-[1px] hover:shadow-[4px_4px_0px_#8C8275] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#8C8275] transition-all cursor-pointer text-left"
              title="Click to inspect live FastMCP tool registry"
            >
              <div className="flex items-center space-x-1.5">
                <span className={`w-2 h-2 ${mcpStatus?.status === 'online' ? 'bg-[#154734]' : 'bg-[#E85D2A]'}`} />
                <span>MCP: {mcpStatus?.server || 'UTD-OIT-TOOLS'} ({mcpStatus?.tool_count ?? 3} TOOLS)</span>
              </div>
              <span className="text-[9px] bg-[#E85D2A] text-white px-1.5 py-0.5">INSPECT ↗</span>
            </button>
          </div>
        </div>

        {/* Section: MODEL (2x2 Grid) */}
        <div>
          <label className="block font-mono text-[13px] font-bold uppercase text-[#141413] mb-2 tracking-[0.08em]">
            MODEL
          </label>
          <div className="grid grid-cols-2 gap-2">
            {(
              [
                { id: 'openai', label: 'OPENAI' },
                { id: 'anthropic', label: 'CLAUDE' },
                { id: 'gemini', label: 'GEMINI' },
                { id: 'cometai', label: 'COMETAI' },
              ] as const
            ).map((m) => {
              const active = provider === m.id;
              return (
                <button
                  key={m.id}
                  type="button"
                  disabled={isStreaming}
                  onClick={() => onProviderChange(m.id)}
                  className={`py-2.5 px-1 text-center font-mono font-bold text-xs uppercase border-2 border-[#141413] transition-all duration-150 disabled:opacity-50 ${
                    active
                      ? 'bg-[#E85D2A] text-white shadow-[3px_3px_0px_#141413] ring-2 ring-[#141413]/20'
                      : 'bg-white text-[#141413] shadow-[3px_3px_0px_#141413] hover:bg-[#FFFDF9] hover:-translate-x-[1px] hover:-translate-y-[1px] hover:shadow-[4px_4px_0px_#141413] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#141413]'
                  }`}
                >
                  {m.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Section: PROMPT */}
        <div>
          <label className="block font-mono text-[13px] font-bold uppercase text-[#141413] mb-2 tracking-[0.08em]">
            PROMPT
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              disabled={isStreaming}
              onClick={() => onPromptVersionChange('v1')}
              className={`py-2.5 px-2 text-center font-mono font-bold text-xs uppercase border-2 border-[#141413] transition-all duration-150 disabled:opacity-50 ${
                promptVersion === 'v1'
                  ? 'bg-[#00D4E5] text-[#141413] shadow-[3px_3px_0px_#141413] ring-2 ring-[#141413]/20'
                  : 'bg-white text-[#141413] shadow-[3px_3px_0px_#141413] hover:bg-[#FFFDF9] hover:-translate-x-[1px] hover:-translate-y-[1px] hover:shadow-[4px_4px_0px_#141413] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#141413]'
              }`}
            >
              V1: CONCISE
            </button>
            <button
              type="button"
              disabled={isStreaming}
              onClick={() => onPromptVersionChange('v2')}
              className={`py-2.5 px-2 text-center font-mono font-bold text-xs uppercase border-2 border-[#141413] transition-all duration-150 disabled:opacity-50 ${
                promptVersion === 'v2'
                  ? 'bg-[#00D4E5] text-[#141413] shadow-[3px_3px_0px_#141413] ring-2 ring-[#141413]/20'
                  : 'bg-white text-[#141413] shadow-[3px_3px_0px_#141413] hover:bg-[#FFFDF9] hover:-translate-x-[1px] hover:-translate-y-[1px] hover:shadow-[4px_4px_0px_#141413] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#141413]'
              }`}
            >
              V2: POLICY
            </button>
          </div>
        </div>

        {/* Section: PRIVACY */}
        <div>
          <label className="block font-mono text-[13px] font-bold uppercase text-[#141413] mb-2 tracking-[0.08em]">
            PRIVACY
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              disabled={isStreaming}
              onClick={() => onEnablePiiChange(true)}
              className={`py-2.5 px-2 text-center font-mono font-bold text-xs uppercase border-2 border-[#141413] transition-all duration-150 disabled:opacity-50 ${
                enablePii
                  ? 'bg-[#154734] text-white shadow-[3px_3px_0px_#141413] ring-2 ring-[#141413]/20'
                  : 'bg-white text-[#141413] shadow-[3px_3px_0px_#141413] hover:bg-[#FFFDF9] hover:-translate-x-[1px] hover:-translate-y-[1px] hover:shadow-[4px_4px_0px_#141413] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#141413]'
              }`}
            >
              REDACTION: ON
            </button>
            <button
              type="button"
              disabled={isStreaming}
              onClick={() => onEnablePiiChange(false)}
              className={`py-2.5 px-2 text-center font-mono font-bold text-xs uppercase border-2 border-[#141413] transition-all duration-150 disabled:opacity-50 ${
                !enablePii
                  ? 'bg-[#E85D2A] text-white shadow-[3px_3px_0px_#141413] ring-2 ring-[#141413]/20'
                  : 'bg-white text-[#141413] shadow-[3px_3px_0px_#141413] hover:bg-[#FFFDF9] hover:-translate-x-[1px] hover:-translate-y-[1px] hover:shadow-[4px_4px_0px_#141413] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#141413]'
              }`}
            >
              OFF
            </button>
          </div>
        </div>

        {/* Section: DEMO PRESETS */}
        <div>
          <label className="block font-mono text-[13px] font-bold uppercase text-[#141413] mb-2.5 tracking-[0.08em]">
            DEMO PRESETS
          </label>
          <div className="flex flex-col gap-2.5">
            {PRESET_CASES.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                disabled={isStreaming}
                onClick={() => onSelectPreset(preset.prompt)}
                className={`w-full text-left font-mono font-bold text-xs uppercase tracking-wider py-3 px-3.5 border-2 border-[#141413] transition-all duration-150 disabled:opacity-50 ${
                  preset.primary
                    ? 'bg-[#E85D2A] text-white shadow-[3px_3px_0px_#141413] hover:bg-[#D64E1D] hover:-translate-x-[1px] hover:-translate-y-[1px] hover:shadow-[4px_4px_0px_#141413] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#141413]'
                    : 'bg-white text-[#141413] shadow-[3px_3px_0px_#141413] hover:bg-[#FFFDF9] hover:-translate-x-[1px] hover:-translate-y-[1px] hover:shadow-[4px_4px_0px_#141413] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#141413]'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
};
