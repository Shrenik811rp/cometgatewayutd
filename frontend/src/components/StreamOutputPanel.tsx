import React, { useState } from 'react';

interface StreamOutputPanelProps {
  responseText: string;
  isStreaming: boolean;
  activeModel: string;
  error: string | null;
  failoverInfo?: {
    triggered: boolean;
    requestedModel: string;
    modelUsed: string;
    reason?: string;
  } | null;
}

const ROUTING_MATRIX = [
  {
    provider: 'CometAI (UTD OIT)',
    modelId: 'cometai.utdallas.edu (Sovereign)',
    tier: 'UTD Enterprise Sovereign Enclave',
    piiPolicy: 'Pre-Inference FERPA Scrubbing',
    fallback: 'Failover → Gemini 3.5 Flash-Lite',
  },
  {
    provider: 'OpenAI',
    modelId: 'gpt-4o-mini',
    tier: 'Primary General',
    piiPolicy: 'Pre-Inference Scrubbing',
    fallback: 'Failover → Gemini 3.5 Flash-Lite',
  },
  {
    provider: 'Anthropic',
    modelId: 'claude-3-5-haiku-latest',
    tier: 'Policy & Long-Context',
    piiPolicy: 'Pre-Inference Scrubbing',
    fallback: 'Failover → Gemini 3.5 Flash-Lite',
  },
  {
    provider: 'Google Gemini',
    modelId: 'gemini/gemini-3.5-flash-lite',
    tier: 'High-Throughput (Auto-Discovered)',
    piiPolicy: 'Pre-Inference Scrubbing',
    fallback: 'Secondary: gemini-4-hydrogen',
  },
];

export const StreamOutputPanel: React.FC<StreamOutputPanelProps> = ({
  responseText,
  isStreaming,
  activeModel,
  error,
  failoverInfo,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!responseText) return;
    navigator.clipboard.writeText(responseText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatInline = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return (
          <strong key={i} className="font-bold text-[#141413]">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
        return (
          <em key={i} className="italic text-[#52504A]">
            {part.slice(1, -1)}
          </em>
        );
      }
      return part;
    });
  };

  const renderFormattedContent = (raw: string) => {
    const lines = raw.split('\n');
    return lines.map((line, idx) => {
      if (line.startsWith('### ')) {
        return (
          <h3 key={idx} className="font-display text-lg font-bold text-[#141413] mt-4 mb-2 tracking-tight">
            {formatInline(line.slice(4))}
          </h3>
        );
      }
      if (line.startsWith('## ')) {
        return (
          <h2 key={idx} className="font-display text-xl font-bold text-[#141413] mt-5 mb-2 tracking-tight">
            {formatInline(line.slice(3))}
          </h2>
        );
      }
      if (line.startsWith('# ')) {
        return (
          <h1 key={idx} className="font-display text-2xl font-bold text-[#141413] mt-6 mb-3 tracking-tight">
            {formatInline(line.slice(2))}
          </h1>
        );
      }
      const numMatch = line.match(/^(\d+)\.\s+(.*)$/);
      if (numMatch) {
        return (
          <div key={idx} className="flex gap-2.5 my-1.5 pl-1">
            <span className="font-mono font-bold text-[#E85D2A] shrink-0 text-[15px]">{numMatch[1]}.</span>
            <span className="flex-1">{formatInline(numMatch[2])}</span>
          </div>
        );
      }
      if (line.match(/^[-*]\s+(.*)$/)) {
        const content = line.replace(/^[-*]\s+/, '');
        return (
          <div key={idx} className="flex gap-2.5 my-1 pl-1">
            <span className="font-mono font-bold text-[#141413] shrink-0">•</span>
            <span className="flex-1">{formatInline(content)}</span>
          </div>
        );
      }
      if (!line.trim()) {
        return <div key={idx} className="h-3" />;
      }
      return (
        <p key={idx} className="my-1.5">
          {formatInline(line)}
        </p>
      );
    });
  };

  return (
    <div className="border-2 border-[#141413] shadow-[4px_4px_0px_#141413] bg-white flex-1 flex flex-col min-h-[380px]">
      {/* Header Bar */}
      <div className="bg-[#E5DFD5] border-b-2 border-[#141413] px-6 py-3 flex flex-wrap justify-between items-center gap-2">
        <div className="flex items-center gap-2 font-mono text-[13px] font-bold uppercase tracking-[0.08em] text-[#141413]">
          <span className="w-2.5 h-2.5 bg-[#E85D2A] border border-[#141413]" />
          <span>RESPONSE</span>
          {isStreaming && (
            <span className="text-[#E85D2A] text-xs animate-pulse font-bold">
              [STREAMING...]
            </span>
          )}
        </div>

        <div className="flex items-center gap-2.5">
          {responseText && !isStreaming && (
            <button
              onClick={handleCopy}
              className="px-2.5 py-1 border-2 border-[#141413] bg-white hover:bg-[#FFFDF9] font-mono text-xs font-bold uppercase text-[#141413] transition-all shadow-[2px_2px_0px_#141413] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none"
            >
              {copied ? '✓ COPIED' : 'COPY'}
            </button>
          )}

          <div className="font-mono text-xs font-bold uppercase px-2.5 py-1 bg-[#00D4E5] text-[#141413] border-2 border-[#141413] shadow-[2px_2px_0px_#141413]">
            {activeModel.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Failover Status Banner */}
      {failoverInfo?.triggered && (
        <div className="bg-[#FFF3CD] border-b-2 border-[#141413] px-5 py-2.5 font-mono text-xs font-bold text-[#E85D2A] flex flex-wrap items-center justify-between gap-2 tracking-wide">
          <span className="flex items-center gap-2">
            <span>⚡</span>
            <span>
              FAILOVER TAKING PLACE: {failoverInfo.requestedModel.toUpperCase()} UNAVAILABLE → AUTOMATICALLY SWITCHED TO {failoverInfo.modelUsed.toUpperCase()}
            </span>
          </span>
          <span className="px-2 py-0.5 bg-[#E85D2A] text-white text-[10px] font-bold uppercase tracking-wider">
            FAILOVER ACTIVE
          </span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-[#FFEBE6] border-b-2 border-[#141413] font-mono text-xs text-[#E85D2A] font-bold">
          GATEWAY STREAM ERROR: {error}
        </div>
      )}

      {/* Body Canvas */}
      <div className="flex-1 p-7 lg:p-8 overflow-y-auto">
        {!responseText && !isStreaming && !error ? (
          <div className="h-full flex flex-col justify-center">
            <div className="mb-4">
              <h3 className="font-display text-xl font-bold uppercase tracking-tight text-[#141413]">
                SYSTEM ROUTING MATRIX
              </h3>
            </div>

            <div className="overflow-x-auto border-2 border-[#141413]">
              <table className="w-full text-left font-mono text-xs">
                <thead className="bg-[#E5DFD5] text-[#141413] border-b-2 border-[#141413] uppercase font-bold">
                  <tr>
                    <th className="p-3">PROVIDER</th>
                    <th className="p-3">MODEL ID</th>
                    <th className="p-3">TIER</th>
                    <th className="p-3">PII POLICY</th>
                    <th className="p-3">FALLBACK</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#141413] bg-white">
                  {ROUTING_MATRIX.map((row, idx) => (
                    <tr key={idx} className="hover:bg-[#F7F4EF]">
                      <td className="p-3 font-bold text-[#141413]">{row.provider}</td>
                      <td className="p-3 text-[#E85D2A] font-bold">{row.modelId}</td>
                      <td className="p-3 text-[#52504A]">{row.tier}</td>
                      <td className="p-3 text-[#154734] font-semibold">{row.piiPolicy}</td>
                      <td className="p-3 text-[#52504A]">{row.fallback}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="text-[17px] leading-[1.75] tracking-[-0.01em] text-[#141413] font-sans">
            {renderFormattedContent(responseText)}
            {isStreaming && (
              <span className="inline-block font-mono text-base font-bold text-[#E85D2A] animate-pulse ml-0.5">
                █
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
