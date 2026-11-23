import React from 'react';
import { PrivacyEvent } from '../types';

interface PrivacyAuditStripProps {
  privacyEvent: PrivacyEvent;
}

export const PrivacyAuditStrip: React.FC<PrivacyAuditStripProps> = ({ privacyEvent }) => {
  const renderHighlightedPrompt = (text: string) => {
    const parts = text.split(/(\[REDACTED_[A-Z_]+\])/g);
    return parts.map((part, idx) => {
      if (part.startsWith('[REDACTED_') && part.endsWith(']')) {
        return (
          <span
            key={idx}
            className="bg-[#FFF3CD] border border-[#141413] px-1.5 py-0.5 font-mono font-semibold text-[#141413] mx-1 inline-block"
          >
            {part}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className="border-2 border-[#141413] bg-white shadow-[4px_4px_0px_#141413] animate-panel-reveal">
      {/* Header Strip */}
      <div className="bg-[#E5DFD5] border-b-2 border-[#141413] px-5 py-2.5 flex flex-wrap justify-between items-center gap-2">
        <div className="flex items-center gap-2 font-mono text-[13px] font-bold uppercase tracking-[0.08em] text-[#141413]">
          <span className="w-2.5 h-2.5 bg-[#154734] border border-[#141413]" />
          <span>PRIVACY GUARD</span>
        </div>

        <div className="flex items-center gap-2">
          {privacyEvent.entities.map((entity, i) => (
            <span
              key={i}
              className="bg-[#00D4E5] text-[#141413] border-2 border-[#141413] font-mono text-xs font-bold px-2 py-0.5"
            >
              {entity.entity_type}
            </span>
          ))}

          <span
            className={`border-2 border-[#141413] font-mono text-xs font-bold px-2.5 py-0.5 uppercase ${
              privacyEvent.redacted_count > 0
                ? 'bg-[#E85D2A] text-white'
                : 'bg-[#154734] text-white'
            }`}
          >
            {privacyEvent.redacted_count > 0
              ? `${privacyEvent.redacted_count} PII REDACTED`
              : '0 PII SCRUBBED'}
          </span>
        </div>
      </div>

      {/* Sanitized Upstream Prompt Body (Direct, clean) */}
      <div className="p-5 font-mono text-[13px] text-[#141413] leading-relaxed break-words bg-[#F7F4EF]">
        {renderHighlightedPrompt(privacyEvent.sanitized_prompt)}
      </div>
    </div>
  );
};
