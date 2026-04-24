import type {
  AnalyzeRequest,
  ScamGuardianResponse,
  CaseRecord,
  ConfigStatusResponse,
  DeepHealthResponse,
  HealthResponse,
  PromptInfo,
  SimulationRecord,
  SimulationRequest,
} from './types';

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL !== undefined) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  if (typeof window !== 'undefined') {
    return window.location.origin;
  }

  return 'http://localhost:7860';
}

export class MiroOrgClient {
  private baseUrl?: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl;
  }

  private getBaseUrl(): string {
    return this.baseUrl ?? getApiBaseUrl();
  }

  // Health endpoints
  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.getBaseUrl()}/health`);
    if (!response.ok) throw new Error('Health check failed');
    return response.json();
  }

  async getDeepHealth(): Promise<DeepHealthResponse> {
    const response = await fetch(`${this.getBaseUrl()}/health/deep`);
    if (!response.ok) throw new Error('Deep health check failed');
    return response.json();
  }

  async getConfigStatus(): Promise<ConfigStatusResponse> {
    const response = await fetch(`${this.getBaseUrl()}/config/status`);
    if (!response.ok) throw new Error('Config status check failed');
    return response.json();
  }

  // AI Assistant endpoints
  async run(userInput: string, context?: any): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: userInput, context }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "AI query failed");
    }
    return response.json();
  }

  // Backward compatibility / General analysis
  async analyze(request: AnalyzeRequest): Promise<ScamGuardianResponse> {
    const response = await fetch(`${this.getBaseUrl()}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: request.user_input,
        url: request.url,
        image_base64: request.image_base64,
        source: request.source || 'janus-client',
      }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Analysis failed');
    }
    return response.json();
  }

  // Case endpoints
  async getCases(): Promise<CaseRecord[]> {
    const response = await fetch(`${this.getBaseUrl()}/cases`);
    if (!response.ok) throw new Error('Failed to fetch cases');
    const data = await response.json();
    return Array.isArray(data) ? data : (data.cases ?? []);
  }

  async getCase(caseId: string): Promise<CaseRecord> {
    const response = await fetch(`${this.getBaseUrl()}/cases/${caseId}`);
    if (!response.ok) throw new Error('Failed to fetch case');
    return response.json();
  }

  // Simulation endpoints
  async createSimulation(request: SimulationRequest): Promise<SimulationRecord> {
    const response = await fetch(`${this.getBaseUrl()}/simulation/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Simulation creation failed');
    }
    return response.json();
  }

  async getSimulations(): Promise<SimulationRecord[]> {
    const response = await fetch(`${this.getBaseUrl()}/simulation/list`);
    if (!response.ok) throw new Error('Failed to fetch simulations');
    return response.json();
  }

  async getSimulation(simulationId: string): Promise<SimulationRecord> {
    const response = await fetch(`${this.getBaseUrl()}/simulation/${simulationId}`);
    if (!response.ok) throw new Error('Failed to fetch simulation');
    return response.json();
  }

  async getSimulationStatus(simulationId: string): Promise<{ status: string }> {
    const response = await fetch(`${this.getBaseUrl()}/simulation/${simulationId}`);
    if (!response.ok) throw new Error('Failed to fetch simulation status');
    const data = await response.json();
    return { status: data.status };
  }

  async getSimulationReport(simulationId: string): Promise<{ report: string }> {
    const response = await fetch(`${this.getBaseUrl()}/simulation/${simulationId}/report`);
    if (!response.ok) throw new Error('Failed to fetch simulation report');
    const data = await response.json();
    return { report: data.report };
  }

  async runNativeSimulation(userInput: string, context?: any): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/simulation/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: userInput, context }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Simulation failed');
    }
    return response.json();
  }

  async chatWithSimulation(simulationId: string, message: string): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/simulation/${simulationId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    if (!response.ok) throw new Error('Simulation chat failed');
    return response.json();
  }

  // Sentinel endpoints
  async getSentinelStatus(): Promise<any> {
    const r = await fetch(`${this.getBaseUrl()}/sentinel/status`);
    if (!r.ok) return null;
    return r.json();
  }

  async getSentinelAlerts(limit = 20): Promise<any[]> {
    const r = await fetch(`${this.getBaseUrl()}/sentinel/alerts?limit=${limit}`);
    if (!r.ok) return [];
    return r.json();
  }

  async getSentinelCapability(): Promise<any> {
    const r = await fetch(`${this.getBaseUrl()}/sentinel/capability/current`);
    if (!r.ok) return null;
    return r.json();
  }

  // Prompt endpoints
  async getPrompts(): Promise<PromptInfo[]> {
    const response = await fetch(`${this.getBaseUrl()}/prompts`);
    if (!response.ok) throw new Error('Failed to fetch prompts');
    return response.json();
  }

  async getPrompt(name: string): Promise<PromptInfo> {
    const response = await fetch(`${this.getBaseUrl()}/prompts/${name}`);
    if (!response.ok) throw new Error('Failed to fetch prompt');
    return response.json();
  }

  async updatePrompt(name: string, content: string): Promise<{ message: string }> {
    const response = await fetch(`${this.getBaseUrl()}/prompts/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Prompt update failed');
    }
    return response.json();
  }
}

// Export singleton instance
export const apiClient = new MiroOrgClient();

// Finance Intelligence endpoints
export class FinanceClient {
  private baseUrl?: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl;
  }

  private getBaseUrl(): string {
    return this.baseUrl ?? getApiBaseUrl();
  }

  async analyzeText(text: string, sources: string[] = []) {
    const r = await fetch(`${this.getBaseUrl()}/finance/analyze/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, sources }),
    });
    if (!r.ok) throw new Error('Text analysis failed');
    return r.json();
  }

  async getTickerIntelligence(symbol: string) {
    const r = await fetch(`${this.getBaseUrl()}/finance/ticker/${symbol}`);
    if (!r.ok) throw new Error(`Failed to fetch ${symbol}`);
    return r.json();
  }

  async searchTicker(query: string) {
    const r = await fetch(`${this.getBaseUrl()}/finance/search/${encodeURIComponent(query)}`);
    if (!r.ok) return [];
    return r.json();
  }

  async analyzeNews(query: string, limit = 8) {
    const r = await fetch(`${this.getBaseUrl()}/finance/news/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit }),
    });
    if (!r.ok) throw new Error('News analysis failed');
    return r.json();
  }

  async getHeadlines() {
    const r = await fetch(`${this.getBaseUrl()}/finance/headlines`);
    if (!r.ok) return [];
    return r.json();
  }
}


export const financeClient = new FinanceClient();

// Scam Guardian endpoints
export class GuardianClient {
  private baseUrl?: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl;
  }

  private getBaseUrl(): string {
    return this.baseUrl ?? getApiBaseUrl();
  }

  async analyze(payload: { text?: string; url?: string; image_base64?: string; source?: string }): Promise<ScamGuardianResponse> {
    const res = await fetch(`${this.getBaseUrl()}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Analysis failed");
    return res.json();
  }

  async getHistory(): Promise<ScamGuardianResponse[]> {
    const res = await fetch(`${this.getBaseUrl()}/history`);
    if (!res.ok) throw new Error("Failed to fetch history");
    return res.json();
  }

  async getEvent(id: string): Promise<ScamGuardianResponse> {
    const res = await fetch(`${this.getBaseUrl()}/history/${id}`);
    if (!res.ok) throw new Error("Failed to fetch event detail");
    return res.json();
  }

  async submitFeedback(payload: { analyze_id: string; is_scam: boolean; correct_category?: string; notes?: string }) {
    const res = await fetch(`${this.getBaseUrl()}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Feedback submission failed");
    return res.json();
  }

  async getGuardianStatus() {
    const res = await fetch(`${this.getBaseUrl()}/guardian/status`, {
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) return null;
    return res.json();
  }
}

export const guardianClient = new GuardianClient();
