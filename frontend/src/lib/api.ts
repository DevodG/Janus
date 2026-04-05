import type {
  AnalyzeRequest,
  CaseRecord,
  ConfigStatusResponse,
  DeepHealthResponse,
  HealthResponse,
  PromptInfo,
  SimulationRecord,
  SimulationRequest,
} from './types';

export class MiroOrgClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  // Health endpoints
  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) throw new Error('Health check failed');
    return response.json();
  }

  async getDeepHealth(): Promise<DeepHealthResponse> {
    const response = await fetch(`${this.baseUrl}/health/deep`);
    if (!response.ok) throw new Error('Deep health check failed');
    return response.json();
  }

  async getConfigStatus(): Promise<ConfigStatusResponse> {
    const response = await fetch(`${this.baseUrl}/config/status`);
    if (!response.ok) throw new Error('Config status check failed');
    return response.json();
  }

  // Analysis endpoints
  async analyze(request: AnalyzeRequest): Promise<CaseRecord> {
    const response = await fetch(`${this.baseUrl}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Analysis failed');
    }
    return response.json();
  }

  // Case endpoints
  async getCases(): Promise<CaseRecord[]> {
    const response = await fetch(`${this.baseUrl}/cases`);
    if (!response.ok) throw new Error('Failed to fetch cases');
    return response.json();
  }

  async getCase(caseId: string): Promise<CaseRecord> {
    const response = await fetch(`${this.baseUrl}/cases/${caseId}`);
    if (!response.ok) throw new Error('Failed to fetch case');
    return response.json();
  }

  // Simulation endpoints
  async createSimulation(request: SimulationRequest): Promise<SimulationRecord> {
    const response = await fetch(`${this.baseUrl}/simulation/run`, {
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
    const response = await fetch(`${this.baseUrl}/simulation/list`);
    if (!response.ok) throw new Error('Failed to fetch simulations');
    return response.json();
  }

  async getSimulation(simulationId: string): Promise<SimulationRecord> {
    const response = await fetch(`${this.baseUrl}/simulation/${simulationId}`);
    if (!response.ok) throw new Error('Failed to fetch simulation');
    return response.json();
  }

  async getSimulationStatus(simulationId: string): Promise<{ status: string }> {
    const response = await fetch(`${this.baseUrl}/simulation/${simulationId}`);
    if (!response.ok) throw new Error('Failed to fetch simulation status');
    const data = await response.json();
    return { status: data.status };
  }

  async getSimulationReport(simulationId: string): Promise<{ report: string }> {
    const response = await fetch(`${this.baseUrl}/simulation/${simulationId}/report`);
    if (!response.ok) throw new Error('Failed to fetch simulation report');
    const data = await response.json();
    return { report: data.report };
  }

  async runNativeSimulation(userInput: string, context?: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}/simulation/run`, {
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
    const response = await fetch(`${this.baseUrl}/simulation/${simulationId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    if (!response.ok) throw new Error('Simulation chat failed');
    return response.json();
  }

  // Sentinel endpoints
  async getSentinelStatus(): Promise<any> {
    const r = await fetch(`${this.baseUrl}/sentinel/status`);
    if (!r.ok) return null;
    return r.json();
  }

  async getSentinelAlerts(limit = 20): Promise<any[]> {
    const r = await fetch(`${this.baseUrl}/sentinel/alerts?limit=${limit}`);
    if (!r.ok) return [];
    return r.json();
  }

  async getSentinelCapability(): Promise<any> {
    const r = await fetch(`${this.baseUrl}/sentinel/capability/current`);
    if (!r.ok) return null;
    return r.json();
  }

  // Prompt endpoints
  async getPrompts(): Promise<PromptInfo[]> {
    const response = await fetch(`${this.baseUrl}/prompts`);
    if (!response.ok) throw new Error('Failed to fetch prompts');
    return response.json();
  }

  async getPrompt(name: string): Promise<PromptInfo> {
    const response = await fetch(`${this.baseUrl}/prompts/${name}`);
    if (!response.ok) throw new Error('Failed to fetch prompt');
    return response.json();
  }

  async updatePrompt(name: string, content: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/prompts/${name}`, {
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

  // Session endpoints
  async createSession(): Promise<any> {
    const r = await fetch(`${this.baseUrl}/sessions`, { method: 'POST' });
    if (!r.ok) throw new Error('Failed to create session');
    return r.json();
  }

  async getSession(sessionId: string): Promise<any> {
    const r = await fetch(`${this.baseUrl}/sessions/${sessionId}`);
    if (!r.ok) throw new Error('Failed to fetch session');
    return r.json();
  }

  async listSessions(limit: number = 20): Promise<any[]> {
    const r = await fetch(`${this.baseUrl}/sessions?limit=${limit}`);
    if (!r.ok) return [];
    return r.json();
  }

  async addMessage(sessionId: string, role: string, content: string): Promise<any> {
    const r = await fetch(`${this.baseUrl}/sessions/${sessionId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, content }),
    });
    if (!r.ok) throw new Error('Failed to add message');
    return r.json();
  }

  // Workflow endpoints
  async createResearchWorkflow(query: string, depth: string = 'standard'): Promise<any> {
    const r = await fetch(`${this.baseUrl}/workflows/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, depth }),
    });
    if (!r.ok) throw new Error('Failed to create research workflow');
    return r.json();
  }

  async createSimulationWorkflow(scenario: string): Promise<any> {
    const r = await fetch(`${this.baseUrl}/workflows/simulation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario }),
    });
    if (!r.ok) throw new Error('Failed to create simulation workflow');
    return r.json();
  }

  async listWorkflows(limit: number = 20, type?: string): Promise<any[]> {
    const url = type ? `${this.baseUrl}/workflows?limit=${limit}&type=${type}` : `${this.baseUrl}/workflows?limit=${limit}`;
    const r = await fetch(url);
    if (!r.ok) return [];
    return r.json();
  }

  async getWorkflow(wfId: string): Promise<any> {
    const r = await fetch(`${this.baseUrl}/workflows/${wfId}`);
    if (!r.ok) throw new Error('Workflow not found');
    return r.json();
  }

  async runWorkflow(wfId: string): Promise<any> {
    const r = await fetch(`${this.baseUrl}/workflows/${wfId}/run`, { method: 'POST' });
    if (!r.ok) throw new Error('Failed to run workflow');
    return r.json();
  }

  // Curiosity endpoints
  async getCuriosity(): Promise<any> {
    const r = await fetch(`${this.baseUrl}/daemon/curiosity`);
    if (!r.ok) return { total_discoveries: 0, total_interests: 0, discoveries: [] };
    return r.json();
  }

  async triggerCuriosity(): Promise<any> {
    const r = await fetch(`${this.baseUrl}/daemon/curiosity/now`, { method: 'POST' });
    if (!r.ok) throw new Error('Failed to trigger curiosity');
    return r.json();
  }
}

// Export singleton instance
export const apiClient = new MiroOrgClient(
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
);

// Finance Intelligence endpoints
export class FinanceClient {
  private baseUrl: string;
  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async analyzeText(text: string, sources: string[] = []) {
    const r = await fetch(`${this.baseUrl}/finance/analyze/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, sources }),
    });
    if (!r.ok) throw new Error('Text analysis failed');
    return r.json();
  }

  async getTickerIntelligence(symbol: string) {
    const r = await fetch(`${this.baseUrl}/finance/ticker/${symbol}`);
    if (!r.ok) throw new Error(`Failed to fetch ${symbol}`);
    return r.json();
  }

  async searchTicker(query: string) {
    const r = await fetch(`${this.baseUrl}/finance/search/${encodeURIComponent(query)}`);
    if (!r.ok) return [];
    return r.json();
  }

  async analyzeNews(query: string, limit = 8) {
    const r = await fetch(`${this.baseUrl}/finance/news/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit }),
    });
    if (!r.ok) throw new Error('News analysis failed');
    return r.json();
  }

  async getHeadlines() {
    const r = await fetch(`${this.baseUrl}/finance/headlines`);
    if (!r.ok) return [];
    return r.json();
  }
}

export const financeClient = new FinanceClient(
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
);
