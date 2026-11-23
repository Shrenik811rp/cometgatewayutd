import React, { KeyboardEvent } from 'react';

interface QueryBarProps {
  prompt: string;
  onPromptChange: (val: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  isStreaming: boolean;
}

export const QueryBar: React.FC<QueryBarProps> = ({
  prompt,
  onPromptChange,
  onSubmit,
  onStop,
  isStreaming,
}) => {
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!isStreaming && prompt.trim()) {
        onSubmit();
      }
    }
  };

  return (
    <div className="border-2 border-[#141413] shadow-[4px_4px_0px_#141413] focus-within:-translate-x-[1px] focus-within:-translate-y-[1px] focus-within:shadow-[6px_6px_0px_#141413] transition-all duration-200 bg-white flex flex-col md:flex-row items-stretch">
      <div className="flex-1 flex flex-col p-6 lg:p-7">
        <textarea
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          rows={3}
          placeholder="Ask CometGateway anything..."
          className="w-full bg-transparent font-sans text-[17px] text-[#141413] placeholder-[#52504A]/50 outline-none resize-none leading-[1.75] tracking-[-0.01em]"
        />
        <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#E5DFD5] font-mono text-xs text-[#52504A] font-semibold">
          <span>{prompt.length} CHARS</span>
          <span>⌘/CTRL + ENTER</span>
        </div>
      </div>

      <div className="border-t-2 md:border-t-0 md:border-l-2 border-[#141413] flex shrink-0">
        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="w-full md:w-auto px-8 py-5 bg-[#141413] hover:bg-[#52504A] text-white font-mono font-bold text-xs uppercase tracking-[0.08em] flex items-center justify-center gap-2 transition-all duration-150 active:translate-x-[2px] active:translate-y-[2px]"
          >
            <span className="w-2.5 h-2.5 bg-[#E85D2A]" />
            <span>STOP ■</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={onSubmit}
            disabled={!prompt.trim()}
            className="w-full md:w-auto px-8 py-5 bg-[#E85D2A] hover:bg-[#D64E1D] disabled:bg-[#E5DFD5] disabled:text-[#52504A] text-white font-mono font-bold text-xs uppercase tracking-[0.08em] flex items-center justify-center gap-2 transition-all duration-150 hover:-translate-x-[1px] hover:-translate-y-[1px] active:translate-x-[2px] active:translate-y-[2px] disabled:cursor-not-allowed"
          >
            <span>RUN</span>
            <span className="text-base leading-none font-sans">→</span>
          </button>
        )}
      </div>
    </div>
  );
};
