import React, { useState } from 'react';
import { MCPToolEvent } from '../types';

interface MCPToolStripProps {
  toolEvent: MCPToolEvent | null;
}

export const MCPToolStrip: React.FC<MCPToolStripProps> = ({ toolEvent }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  if (!toolEvent) return null;

  const isError = Boolean(toolEvent.output && toolEvent.output.error);

  return (
    <div className="border-b-2 border-[#141413] bg-[#EFECE6] p-4 text-[#141413]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <span className="bg-[#141413] px-2 py-0.5 font-mono text-[11px] font-bold uppercase tracking-wider text-[#00D4E5]">
            MCP SERVER
          </span>
          <span className="font-mono text-xs font-bold uppercase tracking-tight text-[#141413]">
            {toolEvent.server}
          </span>
          <span className="text-[#8C8275]">/</span>
          <span className="font-mono text-xs font-semibold text-[#E85D2A]">
            {toolEvent.tool}()
          </span>
          <span className="ml-2 border border-[#154734] bg-[#E1EFEA] px-1.5 py-0.5 font-mono text-[10px] font-bold text-[#154734]">
            FERPA GOVERNED
          </span>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="border border-[#141413] bg-white px-2 py-0.5 font-mono text-[11px] font-bold uppercase tracking-wider text-[#141413] hover:bg-[#141413] hover:text-white"
        >
          {isExpanded ? 'Collapse Payload' : 'Expand Payload'}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          {/* Tool Input */}
          <div className="border border-[#141413] bg-white p-2.5">
            <div className="mb-1 flex items-center justify-between border-b border-[#E5DFD5] pb-1">
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-[#8C8275]">
                Tool Arguments (Pre-Redacted)
              </span>
              <span className="font-mono text-[10px] text-[#154734]">✓ Scrubbed</span>
            </div>
            <pre className="max-h-36 overflow-auto font-mono text-[11px] leading-tight text-[#141413]">
              {JSON.stringify(toolEvent.input, null, 2)}
            </pre>
          </div>

          {/* Tool Output */}
          <div className={`border border-[#141413] bg-white p-2.5 ${isError ? 'border-red-600' : ''}`}>
            <div className="mb-1 flex items-center justify-between border-b border-[#E5DFD5] pb-1">
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-[#8C8275]">
                Tool Output
              </span>
              <span
                className={`font-mono text-[10px] font-bold ${
                  isError ? 'text-red-600' : 'text-[#00D4E5]'
                }`}
              >
                {isError ? 'ERROR' : 'SUCCESS'}
              </span>
            </div>
            <pre className="max-h-36 overflow-auto font-mono text-[11px] leading-tight text-[#141413]">
              {JSON.stringify(toolEvent.output, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
