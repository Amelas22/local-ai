"""
AI Agent Configuration Settings
Contains model configurations and prompting strategies
"""

from dataclasses import dataclass
from typing import Dict, Optional
from pydantic import BaseModel


class ModelConfig(BaseModel):
    """Configuration for a specific AI model"""

    name: str
    provider: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 300  # seconds
    retry_attempts: int = 3
    retry_delay: int = 2  # seconds


class AgentConfig(BaseModel):
    """Configuration for an AI agent"""

    name: str
    description: str
    model_settings: ModelConfig
    system_prompt: Optional[str] = None
    max_context_length: int = 8000
    response_format: Optional[str] = None  # "json", "text", etc.


@dataclass
class AgentSettings:
    """Global settings for AI agents in the Clerk system"""

    # Model configurations
    models: Dict[str, ModelConfig] = None

    # Agent configurations
    agents: Dict[str, AgentConfig] = None

    # Global settings
    default_temperature: float = 0.7
    default_max_tokens: int = 4000
    enable_streaming: bool = False
    enable_caching: bool = True
    cache_ttl: int = 3600  # seconds

    # Rate limiting
    max_concurrent_requests: int = 5
    rate_limit_per_minute: int = 60

    # Logging
    log_prompts: bool = True
    log_responses: bool = True
    log_tokens: bool = True

    def __post_init__(self):
        """Initialize default configurations"""
        if self.models is None:
            self.models = self._get_default_models()

        if self.agents is None:
            self.agents = self._get_default_agents()

    def _get_default_models(self) -> Dict[str, ModelConfig]:
        """Get default model configurations"""
        return {
            "gpt-4.1-mini-2025-04-14": ModelConfig(
                name="gpt-4.1-mini-2025-04-14",
                provider="openai",
                temperature=0.7,
                max_tokens=4000,
                timeout=300,
            ),
            "gpt-4": ModelConfig(
                name="gpt-4",
                provider="openai",
                temperature=0.7,
                max_tokens=4000,
                timeout=300,
            ),
            "claude-3-opus": ModelConfig(
                name="claude-3-opus-20240229",
                provider="anthropic",
                temperature=0.7,
                max_tokens=4000,
                timeout=300,
            ),
            "claude-3-sonnet": ModelConfig(
                name="claude-3-5-sonnet-20241022",
                provider="anthropic",
                temperature=0.7,
                max_tokens=4000,
                timeout=300,
            ),
        }

    def _get_default_agents(self) -> Dict[str, AgentConfig]:
        """Get default agent configurations"""
        return {
            "legal_writer": AgentConfig(
                name="legal_writer",
                description="Expert legal document writer",
                model_settings=self.models["gpt-4.1-mini-2025-04-14"],
                max_context_length=8000,
            ),
            "citation_checker": AgentConfig(
                name="citation_checker",
                description="Legal citation verification specialist",
                model_settings=self.models["gpt-4.1-mini-2025-04-14"],
                max_context_length=4000,
                response_format="json",
            ),
            "document_reviewer": AgentConfig(
                name="document_reviewer",
                description="Senior legal document reviewer",
                model_settings=self.models["gpt-4.1-mini-2025-04-14"],
                max_context_length=16000,
                response_format="json",
            ),
            "research_analyst": AgentConfig(
                name="research_analyst",
                description="Legal research and analysis expert",
                model_settings=self.models["gpt-4.1-mini-2025-04-14"],
                max_context_length=8000,
            ),
        }

    def get_model(self, model_name: str) -> ModelConfig:
        """Get model configuration by name"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found in configurations")
        return self.models[model_name]

    def get_agent(self, agent_name: str) -> AgentConfig:
        """Get agent configuration by name"""
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found in configurations")
        return self.agents[agent_name]

    def update_model_temperature(self, model_name: str, temperature: float):
        """Update temperature for a specific model"""
        if model_name in self.models:
            self.models[model_name].temperature = temperature

    def update_agent_model(self, agent_name: str, model_name: str):
        """Update the model used by an agent"""
        if agent_name in self.agents and model_name in self.models:
            self.agents[agent_name].model_settings = self.models[model_name]


# Global instance
agent_settings = AgentSettings()


# Prompting best practices
PROMPTING_STRATEGIES = {
    "chain_of_thought": """
Let's approach this step-by-step:
1. First, identify the key components of the problem
2. Then, analyze each component systematically
3. Finally, synthesize the findings into a coherent conclusion
""",
    "legal_analysis": """
Apply the IRAC method:
- Issue: What is the legal question?
- Rule: What law governs this issue?
- Application: How does the law apply to these facts?
- Conclusion: What is the legal outcome?
""",
    "document_structure": """
Structure your response with:
1. Executive Summary
2. Detailed Analysis
3. Supporting Evidence
4. Recommendations
5. Conclusion
""",
    "citation_format": """
Format all legal citations according to Bluebook rules:
- Cases: Party v. Party, Volume Reporter Page (Court Year)
- Statutes: Title U.S.C. § Section (Year)
- Regulations: Title C.F.R. § Section (Year)
Always include pincites and parenthetical explanations where relevant.
""",
}


# Model selection strategies
def select_model_for_task(task_type: str) -> str:
    """Select the best model for a given task type"""
    task_model_mapping = {
        "drafting": "gpt-4-turbo",
        "review": "claude-3-opus",
        "citation_check": "gpt-4",
        "research": "gpt-4-turbo",
        "summarization": "claude-3-sonnet",
        "extraction": "gpt-4",
        "classification": "claude-3-sonnet",
    }

    return task_model_mapping.get(task_type, "gpt-4-turbo")


# Token management strategies
def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate token count for text"""
    # Rough estimation: 1 token ≈ 4 characters for English text
    # This is a simplified version - in production, use tiktoken
    return len(text) // 4


def should_use_streaming(expected_tokens: int, task_type: str) -> bool:
    """Determine if streaming should be used based on expected response size"""
    # Use streaming for large responses or interactive tasks
    streaming_threshold = 1000  # tokens
    streaming_tasks = ["drafting", "generation", "creative_writing"]

    return expected_tokens > streaming_threshold or task_type in streaming_tasks
