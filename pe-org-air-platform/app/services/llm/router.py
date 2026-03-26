"""Multi-model routing with LiteLLM and streaming support."""
from typing import AsyncIterator, Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from litellm import acompletion
import structlog

from app.models.rag import TaskType, ModelConfig, DailyBudget

logger = structlog.get_logger()

# --- Model Routing Table (from CS4 PDF Page 13) ---
MODEL_ROUTING: Dict[TaskType, ModelConfig] = {
    TaskType.EVIDENCE_EXTRACTION: ModelConfig(
        primary="openai/gpt-4o-2024-08-06",
        fallbacks=["anthropic/claude-3-5-sonnet-20240620"],
        temperature=0.3,
        max_tokens=4000,
        cost_per_1k_tokens=0.015,
    ),
    TaskType.JUSTIFICATION_GENERATION: ModelConfig(
        primary="openai/gpt-4o-2024-08-06",
        fallbacks=["anthropic/claude-3-5-sonnet-20240620"],
        temperature=0.2,
        max_tokens=2000,
        cost_per_1k_tokens=0.012,
    ),
    TaskType.CHAT_RESPONSE: ModelConfig(
        primary="openai/gpt-3.5-turbo",
        fallbacks=["anthropic/claude-3-haiku-20240307"],
        temperature=0.7,
        max_tokens=1000,
        cost_per_1k_tokens=0.002,
    ),
}

class ModelRouter:
    """Route LLM requests with fallbacks and cost tracking."""

    def __init__(self, daily_limit_usd: float = 50.0):
        self.daily_budget = DailyBudget(limit_usd=Decimal(str(daily_limit_usd)))

    async def complete(
        self, 
        task: TaskType, 
        messages: List[Dict[str, str]], 
        stream: bool = False, 
        **kwargs
    ) -> Any:
        """Route completion request with fallbacks as per Case Study 4."""
        if task not in MODEL_ROUTING:
            logger.error(f"Task type {task} not found in model routing")
            raise ValueError(f"Unknown task type: {task}")

        config = MODEL_ROUTING[task]
        
        # Combined list of primary + fallbacks verified in simulation
        models_to_try = [config.primary] + config.fallbacks
        
        last_exception = None
        for model in models_to_try:
            try:
                # Budget Tracking
                if self.daily_budget.spent_usd >= self.daily_budget.limit_usd:
                    logger.critical("LLM_BUDGET_EXCEEDED", spent=str(self.daily_budget.spent_usd))
                    raise RuntimeError("Daily LLM budget exceeded")

                if stream:
                    return self._stream_complete(model, messages, config)

                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    **kwargs
                )
                
                # Perform cost calculation verified in prototyping
                usage = response.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                cost = (Decimal(total_tokens) / 1000) * Decimal(str(config.cost_per_1k_tokens))
                
                self.daily_budget.spent_usd += cost
                
                logger.info(
                    "llm_complete", 
                    model=model, 
                    task=task.value, 
                    tokens=total_tokens, 
                    cost=float(cost),
                    daily_spent=float(self.daily_budget.spent_usd)
                )
                
                return response
                
            except Exception as e:
                logger.warning("model_failed", model=model, task=task.value, error=str(e))
                last_exception = e
                continue
        
        # If all models failed
        logger.error("all_models_failed", task=task.value)
        if last_exception:
            raise last_exception
        raise RuntimeError("All models failed to respond")

    async def _stream_complete(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        config: ModelConfig
    ) -> AsyncIterator[str]:
        """Async iterator for streaming responses."""
        response = await acompletion(
            model=model,
            messages=messages,
            stream=True,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
