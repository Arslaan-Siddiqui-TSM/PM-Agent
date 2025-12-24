"""
LLM Service - Business Logic for LLM Interactions

Handles LLM API calls for generating Graphviz DOT code from natural language,
including retry logic, token tracking, and error handling.
Uses LangChain for provider abstraction (OpenAI, NVIDIA NIM).
"""
import re
import asyncio
from typing import Optional, Tuple
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from src.core.config import settings
from src.core.exceptions import LLMError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service class for LLM interactions to generate diagram code."""
    
    # System prompts for different diagram types
    SYSTEM_PROMPTS = {
        "graphviz": """You are a specialized assistant that converts natural-language descriptions into Graphviz DOT code.

RULES:
1. Output ONLY the DOT code, optionally wrapped in triple backticks with "dot" language tag
2. Do NOT include any explanation, commentary, or text outside the code
3. Use 'digraph' for directed graphs (flowcharts, processes, hierarchies)
4. Use 'graph' for undirected graphs (relationships, networks)
5. Use short, safe node IDs (alphanumeric, no spaces)
6. Add meaningful labels to nodes and edges
7. Choose appropriate Graphviz layout: dot (hierarchical), neato (spring), fdp (force), circo (circular), etc.
8. Keep the graph concise and readable

EXAMPLE INPUT: "Draw a flowchart for user login with username/password validation"
EXAMPLE OUTPUT:
```dot
digraph login {
    rankdir=TB;
    node [shape=box, style=rounded];
    
    start [label="Start"];
    input [label="Enter Username\\nand Password"];
    validate [label="Validate Credentials"];
    success [label="Login Success", shape=ellipse, style=filled, fillcolor=lightgreen];
    error [label="Login Failed", shape=ellipse, style=filled, fillcolor=lightcoral];
    
    start -> input;
    input -> validate;
    validate -> success [label="Valid"];
    validate -> error [label="Invalid"];
}
```

Now generate DOT code based on the user's request.""",

        "plantuml_wbs": """You are an expert at creating Work Breakdown Structure (WBS) diagrams using PlantUML.

Generate valid PlantUML WBS syntax based on the user's description.

WBS Syntax Rules:
- Start with @startwbs
- End with @endwbs
- Use * for root/level 1 items
- Use ** for level 2 items
- Use *** for level 3 items, etc.
- Use + for additional items at the same level (optional)
- Keep it hierarchical and organized
- Use clear, concise labels

Example:
@startwbs
* Project Name
** Phase 1
*** Task 1.1
*** Task 1.2
** Phase 2
*** Task 2.1
**** Subtask 2.1.1
**** Subtask 2.1.2
*** Task 2.2
@endwbs

Generate ONLY the PlantUML WBS code, no explanations or commentary.""",

        "mermaid_gantt": """You are an expert at creating Gantt charts using Mermaid syntax based on the official Mermaid.js documentation.

Generate valid Mermaid Gantt chart syntax that follows these exact specifications:

=== STRUCTURE ===
1. Start with 'gantt' keyword
2. Optional: Add title using 'title Your Title Here'
3. Required: Set date format using 'dateFormat YYYY-MM-DD' (or custom format)
4. Optional: Set axis format using 'axisFormat %Y-%m-%d' (or custom format)
5. Optional: Exclude dates using 'excludes weekends' or 'excludes 2024-01-01, 2024-12-25' or 'excludes sunday'
6. Optional: Set weekend start day using 'weekend friday' or 'weekend saturday' (default: saturday)
7. Optional: Set tick interval using 'tickInterval 1day' or '1week' or '1month' (format: [1-9][0-9]*(millisecond|second|minute|hour|day|week|month))
8. Optional: Set weekday for week-based intervals using 'weekday monday' (default: sunday)
9. Define sections using 'section Section Name'
10. Define tasks within sections

=== DATE FORMATS ===
Input date format (dateFormat):
- YYYY = 4 digit year (e.g., 2014)
- YY = 2 digit year (e.g., 14)
- Q = Quarter (1-4)
- M or MM = Month number (1-12)
- MMM or MMMM = Month name (Jan, January)
- D or DD = Day of month (1-31)
- Do = Day with ordinal (1st, 2nd, 3rd)
- DDD or DDDD = Day of year (1-365)
- H or HH = 24-hour time (0-23)
- h or hh = 12-hour time (1-12)
- a or A = am/pm
- m or mm = Minutes (0-59)
- s or ss = Seconds (0-59)
- S, SS, SSS = Fractional seconds
- X = Unix timestamp
- x = Unix ms timestamp

Output axis format (axisFormat):
- %Y = Year with century (2024)
- %y = Year without century (24)
- %m = Month as number (01-12)
- %b = Abbreviated month (Jan)
- %B = Full month (January)
- %d = Day of month (01-31)
- %e = Day of month space-padded (1-31)
- %a = Abbreviated weekday (Mon)
- %A = Full weekday (Monday)
- %H = 24-hour (00-23)
- %I = 12-hour (01-12)
- %M = Minutes (00-59)
- %S = Seconds (00-61)
- %p = AM/PM
- %w = Weekday number (0-6)
- %U or %W = Week number
- %x = Date (%m/%d/%Y)
- %X = Time (%H:%M:%S)

=== TASK SYNTAX ===
Format: Task Name :metadata

Metadata is comma-separated with this structure:
Task Name :[tags], [taskId], [startDate|after taskId], [endDate|duration|until taskId]

TAGS (optional, first):
- done = Completed task (appears gray)
- active = Current task (appears blue)
- crit = Critical path (appears red)
- milestone = Milestone marker (point in time)
- Multiple tags can be combined: 'crit, done' or 'crit, active'

TASK ID (optional):
- Alphanumeric identifier (e.g., des1, task_a, t1)
- Used for dependencies with 'after' keyword
- No spaces or special characters

START DATE/DEPENDENCY:
- Absolute date: Use dateFormat (e.g., 2014-01-06)
- After dependency: 'after taskId' or 'after task1 task2 task3' (starts after latest end)
- If omitted: Starts after previous task

END DATE/DURATION:
- Absolute end date: Use dateFormat (e.g., 2014-01-08)
- Duration: '3d' (days), '2w' (weeks), '24h' (hours), '20m' (minutes)
- Until dependency: 'until taskId' (runs until another task starts)
- If omitted for milestone: defaults to 0d

TASK EXAMPLES:
- Basic task: 'Task name :2014-01-01, 30d'
- With ID: 'Task name :t1, 2014-01-01, 30d'
- After dependency: 'Task name :after t1, 20d'
- Multiple dependencies: 'Task name :after t1 t2, 15d'
- Until dependency: 'Task name :t3, 2014-01-01, until t4'
- With status: 'Task name :done, t1, 2014-01-01, 5d'
- Critical active: 'Task name :crit, active, t2, after t1, 3d'
- Milestone: 'Project Start :milestone, m1, 2014-01-01, 0d'
- Completed critical: 'Important task :crit, done, 2014-01-06, 24h'

=== SECTIONS ===
Use 'section Section Name' to group related tasks.
Tasks defined after a section belong to that section until next section is declared.

Example:
section Planning
Task 1 :2014-01-01, 5d
Task 2 :after Task 1, 3d

section Development
Task 3 :2014-01-06, 10d

=== MILESTONES ===
Milestones represent a point in time (zero duration).
Use 'milestone' tag and typically '0d' or '2m' (minutes) duration.
Position is calculated as: start_date + duration/2

Example:
Project Kickoff :milestone, m1, 2014-01-01, 0d
Release v1.0 :milestone, m2, after testing, 0d

=== VERTICAL MARKERS ===
Use 'vert' keyword to add vertical reference lines across the chart.
Format: Marker Name :vert, id, date, duration

Example:
Deadline :vert, v1, 2014-01-15, 2m
Review Date :vert, v2, 2014-02-01, 4m

=== EXCLUDES ===
Exclude non-working days from duration calculation:
- 'excludes weekends' - Excludes Sat-Sun (or configured weekend days)
- 'excludes 2024-01-01, 2024-12-25' - Specific dates (YYYY-MM-DD)
- 'excludes monday, friday' - Specific weekdays
- 'excludes weekends, 2024-01-01' - Combined

Note: Excluded dates extend task duration to maintain specified work days.

=== COMMENTS ===
Use %% for comments (must be on their own line):
%% This is a comment

=== COMPACT MODE ===
Enable via frontmatter (YAML at top):
---
displayMode: compact
---
gantt
    ...

=== COMPLETE EXAMPLE ===
gantt
    title Software Development Project
    dateFormat YYYY-MM-DD
    axisFormat %b %d
    excludes weekends
    
    section Planning
    Requirements gathering :done, req, 2024-01-01, 7d
    Design mockups :done, design, after req, 5d
    Architecture planning :active, arch, after design, 3d
    
    section Development
    Backend API :crit, backend, 2024-01-15, 15d
    Frontend UI :frontend, after design, 20d
    Database setup :db, 2024-01-15, 10d
    Integration :integrate, after backend frontend, 7d
    
    section Testing
    Unit tests :test1, after backend, 5d
    Integration tests :crit, active, test2, after integrate, 7d
    UAT :test3, after test2, 5d
    
    section Deployment
    Staging deploy :deploy1, after test3, 2d
    Production deploy :crit, deploy2, after deploy1, 1d
    Go Live :milestone, after deploy2, 0d

=== CRITICAL RULES ===
1. Output ONLY valid Mermaid Gantt code - no explanations before or after
2. Use proper indentation (4 spaces recommended)
3. Task IDs must be alphanumeric (no spaces, hyphens OK: task-1)
4. Date format must match dateFormat setting
5. Duration format: number + unit (3d, 2w, 24h)
6. Dependency format: 'after taskId' or 'after task1 task2'
7. Tags come first in metadata, before taskId
8. Each task must be on its own line
9. Section names can have spaces
10. Milestone tasks should have 0d duration or very short duration
11. Start with 'gantt' keyword on first line
12. Use consistent date formats throughout

Generate ONLY the Mermaid Gantt code based on the user's description. No explanations, no commentary, just valid Mermaid syntax."""
    }
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.llm: Optional[BaseChatModel] = None
        self._use_llm = False
        
        # Initialize LLM based on provider
        if self.provider == "openai" and settings.OPENAI_API_KEY and settings.OPENAI_MODEL:
            try:
                from langchain_openai import ChatOpenAI
                init_params = {
                    "api_key": settings.OPENAI_API_KEY,
                    "model": settings.OPENAI_MODEL,
                    "temperature": 0.3,
                    "max_tokens": settings.MAX_TOKENS,
                    "timeout": 120
                }
                if settings.OPENAI_BASE_URL:
                    init_params["base_url"] = settings.OPENAI_BASE_URL
                
                self.llm = ChatOpenAI(**init_params)
                self._use_llm = True
                logger.info(f"Initialized LangChain with OpenAI: {settings.OPENAI_MODEL}")
            except ImportError as e:
                logger.warning(
                    f"Failed to import langchain_openai: {e}. "
                    "Install with: pip install langchain-openai"
                )
        
        elif self.provider == "nvidia" and settings.NVIDIA_API_KEY and settings.NVIDIA_MODEL:
            try:
                from langchain_nvidia_ai_endpoints import ChatNVIDIA
                init_params = {
                    "api_key": settings.NVIDIA_API_KEY,
                    "model": settings.NVIDIA_MODEL,
                    "temperature": 0.3,
                    "max_tokens": settings.MAX_TOKENS,
                    "timeout": 120
                }
                if settings.NVIDIA_BASE_URL:
                    init_params["base_url"] = settings.NVIDIA_BASE_URL
                
                self.llm = ChatNVIDIA(**init_params)
                self._use_llm = True
                logger.info(f"Initialized LangChain with NVIDIA NIM: {settings.NVIDIA_MODEL}")
            except ImportError as e:
                logger.warning(
                    f"Failed to import langchain_nvidia_ai_endpoints: {e}. "
                    "Install with: pip install langchain-nvidia-ai-endpoints"
                )
        
        elif self.provider == "gemini" and settings.GOOGLE_API_KEY and settings.GEMINI_MODEL:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.llm = ChatGoogleGenerativeAI(
                    google_api_key=settings.GOOGLE_API_KEY,
                    model=settings.GEMINI_MODEL,
                    temperature=0.3,
                    max_output_tokens=settings.MAX_TOKENS,
                    timeout=120
                )
                self._use_llm = True
                logger.info(f"Initialized LangChain with Google Gemini: {settings.GEMINI_MODEL}")
            except ImportError as e:
                logger.warning(
                    f"Failed to import langchain_google_genai: {e}. "
                    "Install with: pip install langchain-google-genai"
                )
        
        if not self._use_llm:
            logger.warning(
                f"No valid configuration for provider '{self.provider}'. Using fallback mock implementation."
            )
    
    async def generate_dot_code(
        self,
        prompt: str,
        max_tokens: int = 1024,
        max_retries: int = 3
    ) -> Tuple[str, Optional[int], int]:
        """
        Generate Graphviz DOT code from a natural language prompt.
        
        Args:
            prompt: Natural language description of the diagram
            max_tokens: Maximum tokens for LLM response
            max_retries: Number of retry attempts on transient errors
            
        Returns:
            Tuple of (dot_code, tokens_used, latency_ms)
            
        Raises:
            LLMError: If LLM call fails after retries
        """
        start_time = datetime.now(timezone.utc)
        
        if not self._use_llm:
            dot_code = self._fallback_mock(prompt)
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return dot_code, None, latency_ms
        
        # Try with retries and exponential backoff
        for attempt in range(max_retries):
            try:
                response, tokens_used = await self._call_llm_with_prompt(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    system_prompt=self.SYSTEM_PROMPTS["graphviz"]
                )
                dot_code = self._extract_dot(response)
                latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                
                logger.info(
                    f"Successfully generated DOT code "
                    f"(tokens: {tokens_used}, latency: {latency_ms}ms)"
                )
                
                return dot_code, tokens_used, latency_ms
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    logger.error(f"LLM call failed after {max_retries} attempts: {e}")
                    raise LLMError(
                        f"Failed to generate DOT code after {max_retries} attempts: {str(e)}"
                    )
        
        # Defensive: should not be reachable because the loop either returns or raises;
        # add an explicit raise to satisfy static type checkers that a Tuple is always returned or an exception raised.
        raise LLMError(
            "LLM generation ended unexpectedly: no result produced. Internal error in generate_dot_code control flow"
        )
    
    async def _call_llm_with_prompt(
        self,
        prompt: str,
        max_tokens: int,
        system_prompt: str
    ) -> Tuple[str, Optional[int]]:
        """
        Generic method to call LLM API asynchronously with a specific system prompt.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens for response
            system_prompt: System prompt to use for this generation
            
        Returns:
            Tuple of (response_text, tokens_used)
        """
        try:
            # Prepare messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ]
            # Call LLM using LangChain's async invoke
            if self.llm is None:
                raise LLMError("LLM is not initialized; check provider configuration")
            response = await self.llm.ainvoke(messages)
            
            content = response.content
            if not content:
                raise LLMError("Empty response from LLM")
            # Normalize content to a string (LangChain may return list/dict parts)
            if isinstance(content, list):
                normalized_parts = []
                for part in content:
                    if isinstance(part, str):
                        normalized_parts.append(part)
                    elif isinstance(part, dict):
                        text_val = part.get("text") or part.get("content") or ""
                        if text_val:
                            normalized_parts.append(str(text_val))
                content = "".join(normalized_parts).strip()
            else:
                content = str(content).strip()
            if not content:
                raise LLMError("Empty response from LLM after normalization")
            
            # Extract token usage from response metadata
            tokens_used = None
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                tokens_used = usage.get('total_tokens')
            
            return content, tokens_used
            
        except Exception as e:
            logger.error(f"LLM API error ({self.provider}): {e}")
            raise LLMError(f"LLM API call failed: {str(e)}")
    
    def _extract_dot(self, llm_response: str) -> str:
        """
        Extract clean DOT code from LLM response.
        
        Handles triple-backtick code fences and removes markdown formatting.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            Clean DOT code
            
        Raises:
            LLMError: If no valid DOT code found
        """
        # Try to extract from code fence first (```dot or ```graphviz or just ```)
        code_fence_pattern = r"```(?:dot|graphviz)?\s*\n(.*?)\n```"
        match = re.search(code_fence_pattern, llm_response, re.DOTALL)
        
        if match:
            dot_code = match.group(1).strip()
        else:
            # No code fence, use the entire response
            dot_code = llm_response.strip()
        
        # Basic validation: should contain 'graph' or 'digraph'
        if not re.search(r'\b(di)?graph\b', dot_code, re.IGNORECASE):
            raise LLMError(
                "Invalid DOT code: must contain 'graph' or 'digraph' declaration"
            )
        
        return dot_code
    
    async def generate_wbs_code(
        self,
        prompt: str,
        max_tokens: int = 1024,
        max_retries: int = 3
    ) -> Tuple[str, Optional[int], int]:
        """
        Generate PlantUML WBS code from a natural language prompt.
        
        Args:
            prompt: Natural language description of the work breakdown structure
            max_tokens: Maximum tokens for LLM response
            max_retries: Number of retry attempts on transient errors
            
        Returns:
            Tuple of (plantuml_code, tokens_used, latency_ms)
            
        Raises:
            LLMError: If LLM call fails after retries
        """
        start_time = datetime.now(timezone.utc)
        
        if not self._use_llm:
            plantuml_code = self._fallback_mock_wbs(prompt)
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return plantuml_code, None, latency_ms
        
        # Try with retries and exponential backoff
        for attempt in range(max_retries):
            try:
                response, tokens_used = await self._call_llm_wbs_async(prompt, max_tokens)
                plantuml_code = self._extract_plantuml(response)
                latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                
                logger.info(
                    f"Successfully generated PlantUML WBS code "
                    f"(tokens: {tokens_used}, latency: {latency_ms}ms)"
                )
                
                return plantuml_code, tokens_used, latency_ms
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    logger.error(f"LLM call failed after {max_retries} attempts: {e}")
                    raise LLMError(
                        f"Failed to generate PlantUML WBS code after {max_retries} attempts: {str(e)}"
                    )
        raise LLMError(
            "WBS generation ended unexpectedly: no result produced. Internal error in generate_wbs_code control flow"
        )
    
    async def _call_llm_wbs_async(
        self,
        prompt: str,
        max_tokens: int
    ) -> Tuple[str, Optional[int]]:
        """
        Call LLM API asynchronously for WBS generation.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens for response
            
        Returns:
            Tuple of (response_text, tokens_used)
        """
        return await self._call_llm_with_prompt(
            prompt=prompt,
            max_tokens=max_tokens,
            system_prompt=self.SYSTEM_PROMPTS["plantuml_wbs"]
        )
    
    def _extract_plantuml(self, llm_response: str) -> str:
        """
        Extract clean PlantUML code from LLM response.
        
        Handles triple-backtick code fences and removes markdown formatting.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            Clean PlantUML code
            
        Raises:
            LLMError: If no valid PlantUML code found
        """
        # Try to extract from code fence first (```plantuml or just ```)
        code_fence_pattern = r"```(?:plantuml)?\s*\n(.*?)\n```"
        match = re.search(code_fence_pattern, llm_response, re.DOTALL)
        
        if match:
            plantuml_code = match.group(1).strip()
        else:
            # No code fence, use the entire response
            plantuml_code = llm_response.strip()
        
        # Ensure proper tags
        if not plantuml_code.startswith("@startwbs") and not plantuml_code.startswith("@startuml"):
            plantuml_code = "@startwbs\n" + plantuml_code
        
        if not plantuml_code.endswith("@endwbs") and not plantuml_code.endswith("@enduml"):
            plantuml_code = plantuml_code + "\n@endwbs"
        
        # Basic validation: should contain '@startwbs' or '@startuml'
        if not re.search(r'@start(wbs|uml)', plantuml_code, re.IGNORECASE):
            raise LLMError(
                "Invalid PlantUML code: must contain '@startwbs' or '@startuml' declaration"
            )
        
        return plantuml_code
    
    def _fallback_mock_wbs(self, prompt: str) -> str:
        """
        Fallback mock implementation for WBS when LLM API is not available.
        
        Returns a simple example WBS based on prompt keywords.
        
        Args:
            prompt: User prompt (used to customize output slightly)
            
        Returns:
            Simple PlantUML WBS code
        """
        logger.info("Using fallback mock WBS generation")
        
        # Extract potential project name from prompt
        words = prompt.split()[:3]
        project_name = " ".join(words).title() if words else "Example Project"
        
        return f"""@startwbs
* {project_name}
** Planning Phase
*** Requirements Gathering
*** Resource Allocation
** Execution Phase
*** Task Development
*** Quality Assurance
** Completion Phase
*** Testing
*** Deployment
@endwbs"""
    
    def _fallback_mock(self, prompt: str) -> str:
        """
        Fallback mock implementation when OpenAI API is not available.
        
        Returns a simple example DOT graph based on prompt keywords.
        
        Args:
            prompt: User prompt (used to customize output slightly)
            
        Returns:
            Simple DOT graph
        """
        logger.info("Using fallback mock DOT generation")
        
        # Create a simple graph based on prompt keywords
        is_directed = any(
            word in prompt.lower() 
            for word in ["flow", "process", "step", "sequence", "hierarchy"]
        )
        
        if is_directed:
            return """digraph example {
    rankdir=TB;
    node [shape=box, style=rounded];
    
    start [label="Start", shape=ellipse];
    step1 [label="Process Step"];
    step2 [label="Decision", shape=diamond];
    end [label="End", shape=ellipse];
    
    start -> step1;
    step1 -> step2;
    step2 -> end [label="Complete"];
}"""
        else:
            return """graph example {
    node [shape=circle];
    
    A [label="Node A"];
    B [label="Node B"];
    C [label="Node C"];
    D [label="Node D"];
    
    A -- B;
    B -- C;
    C -- D;
    D -- A;
    A -- C;
}"""
    
    async def generate_gantt_code(
        self,
        prompt: str,
        max_tokens: int = 1024,
        max_retries: int = 3
    ) -> Tuple[str, Optional[int], int]:
        """
        Generate Mermaid Gantt chart code from a natural language prompt.
        
        Args:
            prompt: Natural language description of the project timeline
            max_tokens: Maximum tokens for LLM response
            max_retries: Number of retry attempts on transient errors
            
        Returns:
            Tuple of (mermaid_code, tokens_used, latency_ms)
            
        Raises:
            LLMError: If LLM call fails after retries
        """
        start_time = datetime.now(timezone.utc)
        
        if not self._use_llm:
            mermaid_code = self._fallback_mock_gantt(prompt)
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return mermaid_code, None, latency_ms
        
        # Try with retries and exponential backoff
        for attempt in range(max_retries):
            try:
                response, tokens_used = await self._call_llm_gantt_async(prompt, max_tokens)
                mermaid_code = self._extract_mermaid(response)
                latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                
                logger.info(
                    f"Successfully generated Mermaid Gantt code "
                    f"(tokens: {tokens_used}, latency: {latency_ms}ms)"
                )
                
                return mermaid_code, tokens_used, latency_ms
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    logger.error(f"LLM call failed after {max_retries} attempts: {e}")
                    raise LLMError(
                        f"Failed to generate Mermaid Gantt code after {max_retries} attempts: {str(e)}"
                    )
        raise LLMError(
            "Gantt generation ended unexpectedly: no result produced. Internal error in generate_gantt_code control flow"
        )
    
    async def _call_llm_gantt_async(
        self,
        prompt: str,
        max_tokens: int
    ) -> Tuple[str, Optional[int]]:
        """
        Call LLM API asynchronously for Gantt chart generation.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens for response
            
        Returns:
            Tuple of (response_text, tokens_used)
        """
        return await self._call_llm_with_prompt(
            prompt=prompt,
            max_tokens=max_tokens,
            system_prompt=self.SYSTEM_PROMPTS["mermaid_gantt"]
        )
    
    def _extract_mermaid(self, llm_response: str) -> str:
        """
        Extract clean Mermaid code from LLM response.
        
        Handles triple-backtick code fences and removes markdown formatting.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            Clean Mermaid code
            
        Raises:
            LLMError: If no valid Mermaid code found
        """
        # Try to extract from code fence first (```mermaid or just ```)
        code_fence_pattern = r"```(?:mermaid)?\s*\n(.*?)\n```"
        match = re.search(code_fence_pattern, llm_response, re.DOTALL)
        
        if match:
            mermaid_code = match.group(1).strip()
        else:
            # No code fence, use the entire response
            mermaid_code = llm_response.strip()
        
        # Basic validation: should contain 'gantt'
        if not re.search(r'\bgantt\b', mermaid_code, re.IGNORECASE):
            raise LLMError(
                "Invalid Mermaid code: must contain 'gantt' declaration"
            )
        
        return mermaid_code
    
    def _fallback_mock_gantt(self, prompt: str) -> str:
        """
        Fallback mock implementation for Gantt chart when LLM API is not available.
        
        Returns a simple example Gantt chart based on prompt keywords.
        
        Args:
            prompt: User prompt (used to customize output slightly)
            
        Returns:
            Simple Mermaid Gantt code
        """
        logger.info("Using fallback mock Gantt generation")
        
        # Extract potential project name from prompt
        words = prompt.split()[:3]
        project_name = " ".join(words).title() if words else "Example Project"
        
        return f"""gantt
    title {project_name}
    dateFormat YYYY-MM-DD
    axisFormat %b %d
    
    section Planning
    Requirements :done, req, 2025-01-01, 5d
    Design :active, design, after req, 7d
    
    section Development
    Backend :dev1, after design, 10d
    Frontend :dev2, after design, 8d
    
    section Testing
    QA Testing :crit, test, after dev1 dev2, 5d
    
    section Deployment
    Deploy :milestone, after test, 0d"""

