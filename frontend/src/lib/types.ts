// Core types
export interface RouteDecision {
  task_family: string;
  domain_pack: string;
  complexity: string;
  execution_mode: string;
  risk_level: string;
}

export interface AgentOutput {
  agent: string;
  summary: string;
  details: Record<string, unknown>;
  confidence: number;
}

export interface CaseRecord {
  case_id: string;
  user_input: string;
  route?: RouteDecision;
  outputs?: AgentOutput[];
  final_answer?: string;
  final_answer_preview?: string;
  saved_at?: string;
  simulation_id?: string;
}

export interface SimulationRecord {
  simulation_id: string;
  title: string;
  prediction_goal: string;
  status: 'submitted' | 'running' | 'completed' | 'failed';
  report?: string;
  case_id?: string;
  remote_payload?: Record<string, unknown>;
}

// Health and config types
export interface HealthResponse {
  status: string;
  version: string;
}

export interface ProviderHealth {
  configured: boolean;
  reachable: boolean;
  status_code: number | null;
}

export interface DeepHealthResponse extends HealthResponse {
  checks: {
    memory_dir_writable: boolean;
    prompt_files: Record<string, boolean>;
    prompts_loaded: boolean;
    primary_provider: string;
    primary_provider_health: ProviderHealth;
    fallback_provider: string;
    fallback_provider_health: ProviderHealth;
    openrouter_key_present: boolean;
    openai_key_present: boolean;
    ollama_enabled: boolean;
    tavily_enabled: boolean;
    newsapi_enabled: boolean;
    alphavantage_enabled: boolean;
    mirofish_enabled: boolean;
    mirofish_health: {
      reachable: boolean;
      status_code: number | null;
      body: string;
    };
    httpx_available: boolean;
    langgraph_available: boolean;
    dotenv_available: boolean;
  };
}

export interface ConfigStatusResponse {
  app_version: string;
  primary_provider: string;
  fallback_provider: string;
  openrouter_key_present: boolean;
  ollama_enabled: boolean;
  mirofish_enabled: boolean;
  tavily_enabled: boolean;
  newsapi_enabled: boolean;
  alphavantage_enabled: boolean;
  memory_dir: string;
  prompts_dir: string;
}

// Request types
export interface AnalyzeRequest {
  user_input: string;
}

export interface SimulationRequest {
  title: string;
  seed_text: string;
  prediction_goal: string;
  mode?: string;
  metadata?: {
    case_id?: string;
  };
}

// Prompt types
export interface PromptInfo {
  name: string;
  content: string;
}
