import React from 'react';
import { MCPStatusResponse } from '../types';

interface MCPRegistryModalProps {
  isOpen: boolean;
  onClose: () => void;
  mcpStatus: MCPStatusResponse | null;
  onRefresh: () => Promise<void>;
  isRefreshing: boolean;
}

const TOOL_GOVERNANCE_MAP: Record<string, { label: string; badgeColor: string }> = {
  lookup_utd_it_policy: {
    label: 'DCL-2 Protected • Read-Only Policy Grounding',
    badgeColor: 'bg-[#154734] text-white',
  },
  check_campus_service_status: {
    label: 'Zero-PII Status Probe • Infrastructure Telemetry',
    badgeColor: 'bg-[#00D4E5] text-[#141413]',
  },
  create_sanitized_oit_ticket: {
    label: 'FERPA Enforced • Strict Zero-PII Regex Gate',
    badgeColor: 'bg-[#E85D2A] text-white',
  },
};

export const MCPRegistryModal: React.FC<MCPRegistryModalProps> = ({
  isOpen,
  onClose,
  mcpStatus,
  onRefresh,
  isRefreshing,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-3xl bg-[#F7F4EF] border-2 border-[#141413] shadow-[8px_8px_0px_#141413] flex flex-col max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-[#141413] bg-[#E5DFD5]">
          <div className="flex items-center space-x-3">
            <span className="w-3 h-3 bg-[#00D4E5] border border-[#141413]" />
            <h2 className="font-display text-lg font-bold uppercase tracking-tight text-[#141413]">
              MCP Server Registry • FastMCP Inspector
            </h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center border-2 border-[#141413] bg-white font-mono font-bold text-sm text-[#141413] shadow-[2px_2px_0px_#141413] hover:bg-[#E85D2A] hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex flex-col gap-6">
          {/* Server Status Ribbon */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-white border-2 border-[#141413] shadow-[3px_3px_0px_#141413]">
            <div className="flex items-center space-x-3">
              <span
                className={`w-3 h-3 ${
                  mcpStatus?.status === 'online' ? 'bg-[#154734]' : 'bg-[#E85D2A]'
                }`}
              />
              <div>
                <div className="font-mono text-xs font-bold uppercase tracking-wider text-[#141413]">
                  Server: <span className="text-[#E85D2A]">{mcpStatus?.server || 'UTD-OIT-Tools'}</span>
                </div>
                <div className="font-mono text-[11px] text-[#8C8275]">
                  Status: {mcpStatus?.status === 'online' ? 'ONLINE • IN-MEMORY TRANSPORT' : 'OFFLINE'}
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="px-2.5 py-1 bg-[#141413] font-mono text-xs font-bold text-[#00D4E5]">
                {mcpStatus?.tool_count ?? 3} TOOLS REGISTERED
              </div>
              <button
                type="button"
                disabled={isRefreshing}
                onClick={onRefresh}
                className="px-3 py-1 font-mono text-xs font-bold uppercase border-2 border-[#141413] bg-[#F7F4EF] text-[#141413] shadow-[2px_2px_0px_#141413] hover:bg-[#141413] hover:text-white transition-all disabled:opacity-50"
              >
                {isRefreshing ? 'PINGING...' : 'REFRESH PING'}
              </button>
            </div>
          </div>

          {/* Tools Grid Table */}
          <div className="border-2 border-[#141413] bg-white shadow-[3px_3px_0px_#141413] overflow-hidden">
            <div className="px-4 py-2.5 bg-[#141413] text-white flex justify-between items-center">
              <span className="font-mono text-xs font-bold tracking-wider uppercase">
                Registered Tool Schemas (FastMCP Client Verified)
              </span>
              <span className="font-mono text-[10px] text-[#00D4E5]">UTD OIT SOVEREIGN PROTOCOL</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs border-collapse">
                <thead>
                  <tr className="border-b-2 border-[#141413] bg-[#E5DFD5] text-[#141413]">
                    <th className="py-2.5 px-4 font-bold uppercase tracking-wider w-1/4">Tool Name</th>
                    <th className="py-2.5 px-4 font-bold uppercase tracking-wider w-1/3">FERPA Governance</th>
                    <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5DFD5]">
                  {(mcpStatus?.tools || [
                    {
                      name: 'lookup_utd_it_policy',
                      description: 'Look up official UT Dallas OIT policies, security standards, and FERPA governance guidelines.',
                    },
                    {
                      name: 'check_campus_service_status',
                      description: 'Check real-time health, latency, and uptime for UT Dallas campus IT services.',
                    },
                    {
                      name: 'create_sanitized_oit_ticket',
                      description: 'Create an official UT Dallas OIT Help Desk incident ticket with strict regex-level zero-PII assertion.',
                    },
                  ]).map((tool) => {
                    const gov = TOOL_GOVERNANCE_MAP[tool.name] || {
                      label: 'Standard Governance',
                      badgeColor: 'bg-[#141413] text-white',
                    };
                    return (
                      <tr key={tool.name} className="hover:bg-[#F7F4EF] transition-colors">
                        <td className="py-3 px-4 font-bold text-[#E85D2A] align-top">
                          {tool.name}()
                        </td>
                        <td className="py-3 px-4 align-top">
                          <span
                            className={`inline-block px-2 py-0.5 font-bold text-[10px] border border-[#141413] ${gov.badgeColor}`}
                          >
                            {gov.label}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-[#52504A] leading-relaxed align-top">
                          {tool.description}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recruiter Callout */}
          <div className="p-3 bg-[#E5DFD5] border border-[#141413] font-mono text-[11px] text-[#141413] leading-normal flex items-start space-x-2">
            <span className="text-[#E85D2A] font-bold">●</span>
            <div>
              <strong>Architecture Note for OIT ETIS Engineering:</strong> Tools run inside the Gateway host via FastMCP in-memory transport. Before any tool executes, user inputs pass through the pre-inference FERPA regex scrubber; ticket creation strictly rejects raw SSNs, 10-digit UTD IDs, and emails.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t-2 border-[#141413] bg-[#E5DFD5] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-1.5 font-mono text-xs font-bold uppercase border-2 border-[#141413] bg-white text-[#141413] shadow-[2px_2px_0px_#141413] hover:bg-[#141413] hover:text-white transition-all"
          >
            Close Registry
          </button>
        </div>
      </div>
    </div>
  );
};
