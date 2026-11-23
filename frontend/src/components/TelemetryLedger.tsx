import React, { useState } from 'react';
import { MetricsSummary, TelemetryEvent } from '../types';

interface TelemetryLedgerProps {
  telemetry: TelemetryEvent | null;
  metrics: MetricsSummary | null;
  onRefreshMetrics: () => void;
  loadingMetrics: boolean;
}

export const TelemetryLedger: React.FC<TelemetryLedgerProps> = ({
  telemetry,
  metrics,
  onRefreshMetrics,
  loadingMetrics,
}) => {
  const [showAuditDrawer, setShowAuditDrawer] = useState(false);

  return (
    <div className="border-2 border-[#141413] bg-white shadow-[4px_4px_0px_#141413] flex flex-col">
      {/* Current Stream Live Telemetry Strip */}
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-[13px] tabular-nums">
          <thead className="bg-[#E5DFD5] text-[#141413] border-b-2 border-[#141413] font-bold uppercase tracking-[0.08em]">
            <tr>
              <th className="py-3 px-5">MODEL</th>
              <th className="py-3 px-5">TTFT</th>
              <th className="py-3 px-5">TOTAL LATENCY</th>
              <th className="py-3 px-5">TOKENS</th>
              <th className="py-3 px-5">EST. COST</th>
              <th className="py-3 px-5">PII SCRUBBED</th>
              <th className="py-3 px-5 text-right">AUDIT</th>
            </tr>
          </thead>
          <tbody className="bg-white text-[#141413]">
            <tr className="hover:bg-[#F7F4EF] transition-colors">
              <td className="py-4 px-5 font-bold text-[#E85D2A] text-[15px]">
                {telemetry ? telemetry.model_used : '—'}
              </td>
              <td className="py-4 px-5 font-semibold text-[15px]">
                {telemetry ? `${telemetry.ttft_ms.toFixed(1)} ms` : '—'}
              </td>
              <td className="py-4 px-5 font-semibold text-[15px]">
                {telemetry ? `${telemetry.total_ms.toFixed(1)} ms` : '—'}
              </td>
              <td className="py-4 px-5 text-[15px]">
                {telemetry
                  ? `${telemetry.prompt_tokens} in / ${telemetry.completion_tokens} out`
                  : '—'}
              </td>
              <td className="py-4 px-5 font-bold text-[#154734] text-[15px]">
                {telemetry ? `$${telemetry.cost_usd.toFixed(6)}` : '—'}
              </td>
              <td className="py-4 px-5">
                {telemetry ? (
                  <span className={`px-2 py-0.5 border border-[#141413] font-bold text-xs ${
                    telemetry.redacted_count > 0 ? 'bg-[#FFF3CD] text-[#E85D2A]' : 'bg-[#E5DFD5]'
                  }`}>
                    {telemetry.redacted_count} ENTITIES
                  </span>
                ) : (
                  '—'
                )}
              </td>
              <td className="py-4 px-5 text-right">
                <button
                  type="button"
                  onClick={() => {
                    const next = !showAuditDrawer;
                    setShowAuditDrawer(next);
                    if (next) onRefreshMetrics();
                  }}
                  className="px-3.5 py-1.5 bg-[#141413] hover:bg-[#52504A] text-white font-mono font-bold text-xs uppercase tracking-wider transition-all duration-150 shadow-[2px_2px_0px_#141413] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none"
                >
                  {showAuditDrawer ? 'HIDE AUDIT ▲' : `AUDIT LOG (${metrics?.total_requests ?? 0}) ▼`}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Fallback Warning Strip */}
      {telemetry?.fallback_triggered && (
        <div className="bg-[#FFEBE6] border-t-2 border-[#141413] px-5 py-2.5 font-mono text-xs font-bold text-[#E85D2A] flex items-center justify-between">
          <span>⚠️ PROVIDER FAILOVER GATE → ROUTED THROUGH GEMINI FLASH-LITE / COMETAI ENCLAVE</span>
          <span className="uppercase">STATUS: OK</span>
        </div>
      )}

      {/* FinOps: UT Dallas CometAI $5.00 Monthly User Quota Cap */}
      {(() => {
        const totalCost = metrics?.total_cost_usd ?? (telemetry?.cost_usd ?? 0);
        const budgetCap = 5.0;
        const pctUsed = Math.min(100, (totalCost / budgetCap) * 100);
        return (
          <div className="border-t-2 border-[#141413] bg-[#EFECE6] px-5 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 bg-[#154734] border border-[#141413]" />
              <span className="font-bold uppercase tracking-wider text-[#141413]">
                DCL-2 / $5.00 MONTHLY SPEND CAP:
              </span>
              <span className="font-bold text-[#154734]">
                ${totalCost.toFixed(4)} / ${budgetCap.toFixed(2)} CAP
              </span>
              <span className="text-[#8C8275]">•</span>
              <span className="text-[#52504A]">
                {pctUsed.toFixed(2)}% USED
              </span>
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-60">
              <div className="flex-1 h-3 border border-[#141413] bg-white p-0.5">
                <div
                  className="h-full bg-[#154734] transition-all duration-300"
                  style={{ width: `${Math.max(1, pctUsed)}%` }}
                />
              </div>
              <span className="font-bold text-[10px] text-[#141413]">
                FINOPS ACTIVE
              </span>
            </div>
          </div>
        );
      })()}

      {/* Expandable Gateway Audit Ledger with Smooth Entrance */}
      {showAuditDrawer && (
        <div className="border-t-2 border-[#141413] bg-[#F7F4EF] p-6 flex flex-col gap-5 animate-panel-reveal">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="font-display text-base font-bold uppercase text-[#141413] tracking-tight">
                GATEWAY TELEMETRY AGGREGATES (/V1/METRICS)
              </div>
            </div>

            <button
              onClick={onRefreshMetrics}
              disabled={loadingMetrics}
              className="px-3 py-1 border-2 border-[#141413] bg-white hover:bg-[#E5DFD5] font-mono text-xs font-bold uppercase transition-all shadow-[2px_2px_0px_#141413] active:translate-x-[1px] active:translate-y-[1px] disabled:opacity-50"
            >
              {loadingMetrics ? 'SYNCING...' : 'REFRESH ⟳'}
            </button>
          </div>

          {metrics && (
            <>
              {/* Aggregates Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
                <div className="p-3 bg-white border-2 border-[#141413]">
                  <div className="font-mono text-[11px] uppercase text-[#52504A]">REQUESTS</div>
                  <div className="font-mono text-lg font-bold text-[#141413] mt-0.5">{metrics.total_requests}</div>
                </div>
                <div className="p-3 bg-white border-2 border-[#141413]">
                  <div className="font-mono text-[11px] uppercase text-[#52504A]">AVG TTFT</div>
                  <div className="font-mono text-lg font-bold text-[#141413] mt-0.5">{metrics.avg_ttft_ms} ms</div>
                </div>
                <div className="p-3 bg-white border-2 border-[#141413]">
                  <div className="font-mono text-[11px] uppercase text-[#52504A]">AVG LATENCY</div>
                  <div className="font-mono text-lg font-bold text-[#141413] mt-0.5">{metrics.avg_total_ms} ms</div>
                </div>
                <div className="p-3 bg-white border-2 border-[#141413]">
                  <div className="font-mono text-[11px] uppercase text-[#52504A]">TOKENS</div>
                  <div className="font-mono text-lg font-bold text-[#141413] mt-0.5">{metrics.total_tokens}</div>
                </div>
                <div className="p-3 bg-white border-2 border-[#141413]">
                  <div className="font-mono text-[11px] uppercase text-[#52504A]">TOTAL COST</div>
                  <div className="font-mono text-lg font-bold text-[#154734] mt-0.5">${metrics.total_cost_usd.toFixed(6)}</div>
                </div>
                <div className="p-3 bg-white border-2 border-[#141413]">
                  <div className="font-mono text-[11px] uppercase text-[#52504A]">PII SCRUBBED</div>
                  <div className="font-mono text-lg font-bold text-[#E85D2A] mt-0.5">{metrics.total_pii_redacted}</div>
                </div>
                <div className="p-3 bg-white border-2 border-[#141413]">
                  <div className="font-mono text-[11px] uppercase text-[#52504A]">FAILOVERS</div>
                  <div className="font-mono text-lg font-bold text-[#141413] mt-0.5">{metrics.fallback_count}</div>
                </div>
              </div>

              {/* Recent Requests Table */}
              {metrics.recent_requests.length > 0 && (
                <div className="overflow-x-auto border-2 border-[#141413] bg-white">
                  <table className="w-full text-left font-mono text-xs tabular-nums">
                    <thead className="bg-[#E5DFD5] border-b-2 border-[#141413] uppercase font-bold text-[#141413]">
                      <tr>
                        <th className="p-2.5">REQUEST ID</th>
                        <th className="p-2.5">TIMESTAMP</th>
                        <th className="p-2.5">MODEL</th>
                        <th className="p-2.5">VER</th>
                        <th className="p-2.5">TTFT</th>
                        <th className="p-2.5">TOTAL</th>
                        <th className="p-2.5">TOKENS</th>
                        <th className="p-2.5">COST</th>
                        <th className="p-2.5">PII</th>
                        <th className="p-2.5">FAILOVER</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E5DFD5]">
                      {metrics.recent_requests.map((r, i) => (
                        <tr key={i} className="hover:bg-[#F7F4EF] transition-colors">
                          <td className="p-2.5 font-bold">{r.request_id}</td>
                          <td className="p-2.5 text-[#52504A]">{r.timestamp.split('T')[1]?.split('.')[0] || r.timestamp}</td>
                          <td className="p-2.5 text-[#E85D2A] font-semibold">{r.model_used}</td>
                          <td className="p-2.5">{r.prompt_version}</td>
                          <td className="p-2.5">{r.ttft_ms.toFixed(1)} ms</td>
                          <td className="p-2.5">{r.total_ms.toFixed(1)} ms</td>
                          <td className="p-2.5">{r.prompt_tokens + r.completion_tokens}</td>
                          <td className="p-2.5 text-[#154734]">${r.cost_usd.toFixed(6)}</td>
                          <td className="p-2.5 font-bold">{r.redacted_count}</td>
                          <td className="p-2.5">
                            {r.fallback_triggered ? (
                              <span className="text-[#E85D2A] font-bold">YES</span>
                            ) : (
                              <span className="text-[#52504A]">NO</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
