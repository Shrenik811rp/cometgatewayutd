import {
  ChatRequestPayload,
  HealthStatus,
  MCPStatusResponse,
  MCPToolEvent,
  MetricsSummary,
  PrivacyEvent,
  TelemetryEvent,
} from '../types';
import { API_BASE_URL } from './config';

export interface StreamCallbacks {
  onPrivacy?: (data: PrivacyEvent) => void;
  onMCPTool?: (data: MCPToolEvent) => void;
  onDelta?: (content: string) => void;
  onTelemetry?: (data: TelemetryEvent) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchMetrics(): Promise<MetricsSummary> {
  const res = await fetch(`${API_BASE_URL}/v1/metrics`);
  if (!res.ok) {
    throw new Error(`Metrics fetch failed with HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchMCPStatus(): Promise<MCPStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/mcp/status`);
  if (!res.ok) {
    throw new Error(`MCP status fetch failed with HTTP ${res.status}`);
  }
  return res.json();
}

export async function streamChat(
  payload: ChatRequestPayload,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported by server response');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;
        const dataStr = line.slice(6).trim();

        if (dataStr === '[DONE]') {
          callbacks.onDone?.();
          return;
        }

        try {
          const parsed = JSON.parse(dataStr);
          if (parsed.type === 'privacy') {
            callbacks.onPrivacy?.(parsed as PrivacyEvent);
          } else if (parsed.type === 'mcp_tool') {
            callbacks.onMCPTool?.(parsed as MCPToolEvent);
          } else if (parsed.type === 'delta') {
            callbacks.onDelta?.(parsed.content || '');
          } else if (parsed.type === 'telemetry') {
            callbacks.onTelemetry?.(parsed as TelemetryEvent);
          } else if (parsed.type === 'error') {
            callbacks.onError?.(new Error(parsed.message || 'Upstream stream error'));
          }
        } catch (parseErr) {
          console.warn('Failed to parse SSE line:', dataStr, parseErr);
        }
      }
    }

    callbacks.onDone?.();
  } catch (err: unknown) {
    if (signal?.aborted) return;
    const errorObj = err instanceof Error ? err : new Error(String(err));
    callbacks.onError?.(errorObj);
  }
}
