export interface RedactedEntity {
  entity_type: string;
  start: number;
  end: number;
  text: string;
}

export interface PrivacyEvent {
  type: 'privacy';
  request_id: string;
  sanitized_prompt: string;
  redacted_count: number;
  entities: RedactedEntity[];
}

export interface MCPToolEvent {
  type: 'mcp_tool';
  server: string;
  tool: string;
  input: Record<string, any>;
  output: any;
}

export interface ErrorEvent {
  type: 'error';
  message: string;
}

export interface DeltaEvent {
  type: 'delta';
  content: string;
}

export interface TelemetryEvent {
  type: 'telemetry';
  request_id: string;
  timestamp: string;
  model_used: string;
  prompt_version: string;
  ttft_ms: number;
  total_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  redacted_count: number;
  fallback_triggered: boolean;
  mcp_tools_used?: string[];
}

export type SSEEvent = PrivacyEvent | MCPToolEvent | DeltaEvent | TelemetryEvent | ErrorEvent;

export interface MCPToolInfo {
  name: string;
  description: string;
}

export interface MCPStatusResponse {
  status: 'online' | 'offline';
  server: string;
  transport?: string;
  tool_count?: number;
  tools?: MCPToolInfo[];
  error?: string;
}

export interface ChatRequestPayload {
  prompt: string;
  provider: 'openai' | 'anthropic' | 'gemini' | 'cometai';
  model?: string;
  prompt_version: 'v1' | 'v2';
  enable_pii_redaction: boolean;
}

export interface RequestLogEntry {
  timestamp: string;
  request_id: string;
  model_used: string;
  prompt_version: string;
  ttft_ms: number;
  total_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  redacted_count: number;
  fallback_triggered: number;
}

export interface MetricsSummary {
  total_requests: number;
  avg_ttft_ms: number;
  avg_total_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  total_pii_redacted: number;
  fallback_count: number;
  recent_requests: RequestLogEntry[];
}

export interface HealthStatus {
  status: string;
  mock_mode: boolean;
}
