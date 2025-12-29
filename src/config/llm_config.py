import os
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Dict
import logging

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage as LangChainAIMessage
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

load_dotenv()

logger = logging.getLogger(__name__)

# Create a console instance for beautiful token tracking
token_console = Console()


class TokenSessionTracker:
    """Track cumulative token usage across a session."""
    
    def __init__(self):
        self.calls = []
        self.total_input = 0
        self.total_output = 0
        self.session_start = time.time()
    
    def add_call(self, usage: dict, cost: float = 0.0):
        """Add a call to the session tracker."""
        self.calls.append(usage)
        self.total_input += usage['input_tokens']
        self.total_output += usage['output_tokens']
    
    def print_summary(self):
        """Print beautiful session summary."""
        if not self.calls:
            token_console.print("[yellow]No LLM calls recorded in this session.[/yellow]")
            return
        
        session_duration = time.time() - self.session_start
        
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="green", justify="right", width=20)
        
        table.add_row("Total Calls", f"{len(self.calls):,}")
        table.add_row("Total Input Tokens", f"[bright_blue]{self.total_input:,}[/bright_blue]")
        table.add_row("Total Output Tokens", f"[bright_green]{self.total_output:,}[/bright_green]")
        table.add_row("Total Tokens", f"[bold bright_yellow]{self.total_input + self.total_output:,}[/bold bright_yellow]")
        table.add_row("Session Duration", f"[dim]{session_duration:.1f}s[/dim]")
        
        panel = Panel(
            table,
            title="📊 Session Token Summary",
            border_style="magenta",
            padding=(0, 1)
        )
        
        token_console.print(panel)
    
    def reset(self):
        """Reset the session tracker."""
        self.calls = []
        self.total_input = 0
        self.total_output = 0
        self.session_start = time.time()


# Global session tracker
session_tracker = TokenSessionTracker()


def _coerce_to_text(input_data: Any) -> str:
    """Best-effort conversion of various invoke() inputs to a single user text string.

    Supports:
    - str
    - List of objects with .content (e.g., LangChain HumanMessage[])
    - Any other object (fallback to str())
    """
    if isinstance(input_data, str):
        return input_data
    if isinstance(input_data, list):
        parts: List[str] = []
        for item in input_data:
            content = getattr(item, "content", None)
            parts.append(str(content if content is not None else item))
        return "\n\n".join(parts)
    return str(input_data)


@dataclass
class _AIMessage:
    """Minimal message-like container to mirror LangChain's result.content."""
    content: str


class UnifiedLLM:
    """Provider-agnostic LLM wrapper using LangChain's init_chat_model().

    Supports three providers with automatic fallback:
    - NVIDIA NIM (nvidia_ai_endpoints)
    - OpenAI (openai)
    - Google Gemini (google_genai)
    
    Key features:
    - Pure LangChain ecosystem (no OpenAI SDK)
    - Automatic fallback if primary provider fails
    - Runtime provider switching via config
    - Backward compatible invoke() interface
    """

    def __init__(
        self,
        provider: str = "openai",
        temperature: Optional[float] = None,
        openai_model: str = "gpt-4o-mini",
        gemini_model: str = "gemini-2.5-pro",
        nvidia_model: str = "qwen3-next-80b-a3b-instruct",
        max_output_tokens: int = 16284,
        request_timeout: int = 120,
    ) -> None:
        self.provider = provider.lower().strip()
        self.temperature = temperature  # Can be None
        self.openai_model = os.getenv("OPENAI_MODEL", openai_model)
        self.gemini_model = os.getenv("GEMINI_MODEL", gemini_model)
        self.nvidia_model = os.getenv("NVIDIA_MODEL", nvidia_model)
        self.max_output_tokens = max_output_tokens
        self.request_timeout = request_timeout

        # Initialize the chat model with fallback support
        self._init_chat_model()

    def _init_chat_model(self) -> None:
        """Initialize LangChain chat model with fallback support."""
        
        # Determine provider and model based on configuration
        provider_map = {
            "nvidia": ("nvidia", self.nvidia_model),
            "openai": ("openai", self.openai_model),
            "gemini": ("google_genai", self.gemini_model),
            "google": ("google_genai", self.gemini_model),  # Alias
        }
        
        if self.provider not in provider_map:
            logger.warning(f"Unknown provider '{self.provider}', defaulting to 'openai'")
            self.provider = "openai"
        
        provider_name, model_name = provider_map[self.provider]
        
        # Prepare model initialization kwargs
        kwargs = {
            "model": model_name,
            "model_provider": provider_name,
            "timeout": self.request_timeout,
            "max_tokens": self.max_output_tokens,
        }
        
        # Only add temperature if specified (some models don't support it)
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        
        # Try to initialize the primary provider
        try:
            logger.info(f"Initializing {provider_name} with model {model_name}")
            self.chat_model = init_chat_model(**kwargs)
            self.active_provider = self.provider
            logger.info(f"✓ Successfully initialized {self.active_provider}")
            return
        except Exception as e:
            logger.warning(f"Failed to initialize {self.provider}: {e}")
        
        # Fallback logic: try other available providers
        # Order: OpenAI → Gemini → NVIDIA (as documented in ENV_VARS.md)
        fallback_order = ["openai", "gemini", "nvidia"]
        # Remove the failed primary provider from fallback list
        fallback_order = [p for p in fallback_order if p != self.provider]
        
        for fallback_provider in fallback_order:
            if fallback_provider not in provider_map:
                continue
            
            fallback_provider_name, fallback_model = provider_map[fallback_provider]
            
            # Check if API key is available for fallback provider
            api_key_map = {
                "nvidia": "NVIDIA_API_KEY",
                "openai": "OPENAI_API_KEY",
                "gemini": "GOOGLE_API_KEY",
            }
            
            api_key_env = api_key_map.get(fallback_provider)
            if not api_key_env or not os.getenv(api_key_env):
                logger.debug(f"Skipping {fallback_provider}: no API key found ({api_key_env})")
                continue
            
            try:
                logger.info(f"Attempting fallback to {fallback_provider_name} ({fallback_model})")
                fallback_kwargs = {
                    "model": fallback_model,
                    "model_provider": fallback_provider_name,
                    "timeout": self.request_timeout,
                    "max_tokens": self.max_output_tokens,
                }
                
                if self.temperature is not None:
                    fallback_kwargs["temperature"] = self.temperature
                
                self.chat_model = init_chat_model(**fallback_kwargs)
                self.active_provider = fallback_provider
                logger.info(f"✓ Fallback successful: now using {self.active_provider}")
                return
            except Exception as e:
                logger.warning(f"Fallback to {fallback_provider} failed: {e}")
                continue
        
        # If all providers fail, raise error
        raise RuntimeError(
            f"Failed to initialize any LLM provider. Tried: {self.provider}, {', '.join(fallback_order)}. "
            f"Please check your API keys (NVIDIA_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY) in .env file."
        )

    def get_current_model(self) -> str:
        """Get the currently active model name."""
        if self.active_provider == "nvidia":
            return self.nvidia_model
        elif self.active_provider == "openai":
            return self.openai_model
        elif self.active_provider in ["gemini", "google"]:
            return self.gemini_model
        return "unknown"

    def _extract_token_usage(self, result) -> Optional[Dict]:
        """Extract token usage from LangChain response metadata."""
        
        # LangChain standardizes usage_metadata across all providers
        if hasattr(result, 'usage_metadata') and result.usage_metadata:
            return {
                'input_tokens': result.usage_metadata.get('input_tokens', 0),
                'output_tokens': result.usage_metadata.get('output_tokens', 0),
                'total_tokens': result.usage_metadata.get('total_tokens', 0),
                'estimated': False
            }
        
        return None


    def _display_token_usage(self, result, input_text: str, output_text: str, duration: float):
        """Display beautiful token usage information using rich."""
        
        # Extract token usage from metadata
        token_usage = self._extract_token_usage(result)
        
        if not token_usage:
            # Fallback to estimation if no metadata
            token_usage = {
                'input_tokens': len(input_text) // 4,  # Rough estimate
                'output_tokens': len(output_text) // 4,
                'total_tokens': (len(input_text) + len(output_text)) // 4,
                'estimated': True
            }
        
        # Create a beautiful table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan", width=18)
        table.add_column("Value", style="green", justify="right", width=18)
        
        # Provider and model
        current_model = self.get_current_model()
        provider_display = f"[bold yellow]{self.active_provider.upper()}[/bold yellow]"
        model_display = f"[dim]{current_model}[/dim]"
        
        # Add rows
        table.add_row("Provider", provider_display)
        table.add_row("Model", model_display)
        table.add_row("─" * 18, "─" * 18)  # Separator
        
        # Token counts with formatting
        input_color = "bright_blue"
        output_color = "bright_green"
        total_color = "bright_yellow"
        
        table.add_row(
            "Input Tokens",
            f"[{input_color}]{token_usage['input_tokens']:,}[/{input_color}]"
        )
        table.add_row(
            "Output Tokens",
            f"[{output_color}]{token_usage['output_tokens']:,}[/{output_color}]"
        )
        table.add_row(
            "Total Tokens",
            f"[bold {total_color}]{token_usage['total_tokens']:,}[/bold {total_color}]"
        )
        
        # Duration and speed
        table.add_row("─" * 18, "─" * 18)  # Separator
        table.add_row("Duration", f"[bright_cyan]{duration:.2f}s[/bright_cyan]")
        
        tokens_per_sec = token_usage['output_tokens'] / duration if duration > 0 else 0

        # Enrich usage for downstream logging/exports
        token_usage.update({
            'provider': self.active_provider,
            'model': current_model,
            'duration': duration,
            'tokens_per_sec': tokens_per_sec,
            'timestamp': time.time(),
        })
        table.add_row("Speed", f"[dim]{tokens_per_sec:.0f} tok/s[/dim]")
        
        # Add to session tracker
        session_tracker.add_call(token_usage, 0.0)
        
        # Add estimated badge if applicable
        title = "🤖 LLM Token Usage"
        if token_usage.get('estimated'):
            title += " [dim](estimated)[/dim]"
        
        # Display in a panel
        panel = Panel(
            table,
            title=title,
            border_style="blue",
            padding=(0, 1)
        )
        
        token_console.print(panel)

    def invoke(self, input_data: Any, show_tokens: bool = True) -> _AIMessage:
        """Unified invoke accepting either str or LangChain-style messages list.
        
        Args:
            input_data: Can be:
                - str: Plain text prompt
                - List[HumanMessage]: LangChain message format
                - Any other format (will be coerced to string)
            show_tokens: Whether to display token usage (default: True)
        
        Returns:
            _AIMessage with content field containing the response
        """
        start_time = time.time()
        
        # Convert input to text for token tracking
        input_text = _coerce_to_text(input_data)
        
        try:
            # Convert input to appropriate format
            if isinstance(input_data, str):
                # Direct string input
                messages = [HumanMessage(content=input_data)]
            elif isinstance(input_data, list):
                # Already a list of messages or needs conversion
                if input_data and hasattr(input_data[0], "content"):
                    # Already LangChain messages
                    messages = input_data
                else:
                    # Convert list to text and wrap in HumanMessage
                    text = _coerce_to_text(input_data)
                    messages = [HumanMessage(content=text)]
            else:
                # Coerce to text and wrap
                text = _coerce_to_text(input_data)
                messages = [HumanMessage(content=text)]
            
            # Invoke the chat model
            result = self.chat_model.invoke(messages)
            
            # Extract content from result
            if isinstance(result, LangChainAIMessage):
                content = result.content
            else:
                content = str(getattr(result, "content", result))
            
            output_text = str(content)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Display token usage
            if show_tokens:
                self._display_token_usage(result, input_text, output_text, duration)
            
            return _AIMessage(content=output_text)
            
        except Exception as e:
            logger.error(f"Error invoking {self.active_provider}: {e}")
            raise RuntimeError(f"LLM invocation failed: {e}")


# Read provider preference from environment, default to OpenAI
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

model = UnifiedLLM(provider=LLM_PROVIDER, max_output_tokens=32000)

logger.info(f"LLM Configuration: Model={model.active_provider}")