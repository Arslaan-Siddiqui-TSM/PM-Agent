"""
Diagram Generator Agent

Generates visual diagrams from project plans using direct rendering services.

Supports multiple diagram types:
- Gantt charts (timeline/milestones) - via Mermaid.ink
- WBS diagrams (work breakdown structure) - via PlantUML.com
"""

import httpx
import asyncio
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import base64
import json
import logging

from src.config.llm_config import model

logger = logging.getLogger(__name__)


class DiagramType(Enum):
    """Supported diagram types with their rendering engines."""
    GANTT = ("mermaid", "Timeline/Gantt chart")
    GRAPH = ("graphviz", "Dependency graph")
    BPMN = ("bpmn", "Workflow diagram")
    SEQUENCE = ("plantuml", "Sequence diagram")
    ERD = ("plantuml", "Data model (ERD)")
    COMPONENT = ("plantuml", "Architecture/Component diagram")
    FLOWCHART = ("mermaid", "Flowchart")


class DiagramSpec(BaseModel):
    """Specification for a single diagram."""
    type: str = Field(description="Diagram type (gantt, graph, bpmn, etc.)")
    title: str = Field(description="Diagram title")
    source_code: str = Field(description="Diagram DSL source code")
    description: str = Field(description="Brief description of what the diagram shows")
    engine: str = Field(description="Rendering engine (mermaid, plantuml, graphviz, etc.)")


class GeneratedDiagram(BaseModel):
    """A generated diagram with its data URL."""
    type: str
    title: str
    description: str
    url: str  # Data URL (base64 encoded SVG)
    source_code: str  # Original DSL for debugging


class DiagramGenerator:
    """
    Generate visual diagrams from project plans using direct rendering services.
    
    - Mermaid diagrams (Gantt) via Mermaid.ink
    - PlantUML diagrams (WBS) via PlantUML.com
    """
    
    def __init__(self, llm=None, mermaid_url: str = "https://mermaid.ink", plantuml_url: str = "https://www.plantuml.com/plantuml"):
        """
        Initialize the diagram generator.
        
        Args:
            llm: Language model for analyzing plans and generating DSL
            mermaid_url: Mermaid rendering service URL
            plantuml_url: PlantUML rendering service URL
        """
        self.llm = llm or model
        self.mermaid_url = mermaid_url
        self.plantuml_url = plantuml_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.max_retries = 3
    
    async def analyze_plan(self, plan_text: str, diagram_types: Optional[List[str]] = None) -> List[DiagramSpec]:
        """
        Analyze a project plan and identify opportunities for visual diagrams.
        
        Args:
            plan_text: The full project plan text
            diagram_types: Specific diagram types to generate (None = auto-detect)
            
        Returns:
            List of DiagramSpec objects ready for rendering
        """
        logger.info(f"Analyzing plan for diagrams (length: {len(plan_text)} chars)")
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(plan_text, diagram_types)
        
        try:
            # Get LLM response (using invoke which is synchronous)
            # Run in executor to make it async-compatible
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.llm.invoke(prompt))
            response_text = str(response.content) if response.content else ""
            
            # Parse JSON response
            diagram_specs = self._parse_diagram_specs(response_text)
            
            logger.info(f"Generated {len(diagram_specs)} diagram specifications")
            return diagram_specs
            
        except Exception as e:
            logger.error(f"Error analyzing plan for diagrams: {e}")
            return []
    
    def _build_analysis_prompt(self, plan_text: str, diagram_types: Optional[List[str]] = None) -> str:
        """Build the prompt for diagram analysis."""
        
        available_types = """
1. **gantt** (Mermaid) - for project timelines, milestones, phases, schedules
2. **wbs** (PlantUML) - for work breakdown structure, task hierarchy
"""
        
        type_filter = ""
        if diagram_types:
            type_filter = f"\n**Focus on these diagram types**: {', '.join(diagram_types)}\n"
        else:
            type_filter = "\n**Focus ONLY on: gantt and wbs diagrams**\n"
        
        return f"""Analyze this project plan and generate visual diagrams to enhance understanding.

For each diagrammable section, generate the appropriate diagram DSL code.

**Available diagram types:**
{available_types}
{type_filter}

**Project Plan:**
```
{plan_text[:15000]}  # Truncate if too long
```

**Instructions:**
1. Identify 1-2 key sections that would benefit from visualization
2. Generate a Gantt chart for the timeline
3. Generate a WBS diagram for the task hierarchy
4. Provide syntactically correct DSL code for each diagram
5. Provide a clear title and description

**Output Format (JSON):**
```json
[
  {{
    "type": "gantt",
    "title": "Project Timeline",
    "engine": "mermaid",
    "source_code": "gantt\\n    title Project Timeline\\n    dateFormat YYYY-MM-DD\\n    section Phase 1\\n    Task 1: 2024-01-01, 30d",
    "description": "Shows 4 phases over 9 months with key milestones"
  }},
  {{
    "type": "wbs",
    "title": "Work Breakdown Structure",
    "engine": "plantuml",
    "source_code": "@startwbs\\n* Project\\n** Phase 1\\n*** Task 1\\n@endwbs",
    "description": "Hierarchical breakdown of project tasks"
  }}
]
```

Generate the JSON array now (no other text):"""
    
    def _parse_diagram_specs(self, response_text: str) -> List[DiagramSpec]:
        """Parse LLM response into DiagramSpec objects."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            
            json_text = json_text.strip()
            
            # Parse JSON
            specs_data = json.loads(json_text)
            
            # Convert to DiagramSpec objects
            specs = []
            for spec_data in specs_data:
                try:
                    spec = DiagramSpec(**spec_data)
                    specs.append(spec)
                except Exception as e:
                    logger.warning(f"Failed to parse diagram spec: {e}")
                    continue
            
            return specs
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse diagram specs JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            return []
        except Exception as e:
            logger.error(f"Error parsing diagram specs: {e}")
            return []
    
    async def generate_diagram(self, spec: DiagramSpec, format: str = "svg") -> Optional[str]:
        """
        Generate a diagram using direct rendering services (Mermaid.ink or PlantUML).
        
        Args:
            spec: Diagram specification
            format: Output format (svg, png)
            
        Returns:
            Data URL (base64 encoded) or None if generation fails
        """
        logger.info(f"Generating {spec.type} diagram: {spec.title}")
        
        # Log the source code for debugging (first 500 chars)
        logger.debug(f"Diagram source ({spec.engine}):\n{spec.source_code[:500]}...")
        
        # Retry with exponential backoff on transient errors
        for attempt in range(self.max_retries):
            try:
                if spec.engine == "mermaid":
                    # Use Mermaid.ink for Gantt charts
                    content = await self._render_mermaid(spec.source_code, format)
                elif spec.engine == "plantuml":
                    # Use PlantUML server for WBS diagrams
                    content = await self._render_plantuml(spec.source_code, format)
                else:
                    logger.error(f"Unsupported engine: {spec.engine}")
                    return None
                
                if not content:
                    raise Exception(f"Empty response from {spec.engine} renderer")
                
                # Log content preview for debugging
                if format == "svg":
                    try:
                        content_preview = content.decode('utf-8')[:200]
                        logger.debug(f"SVG content preview: {content_preview}")
                    except Exception:
                        pass
                
                # Encode as data URL
                encoded = base64.b64encode(content).decode('utf-8')
                
                # Use correct MIME type for SVG
                mime_type = "image/svg+xml" if format == "svg" else "image/png"
                data_url = f"data:{mime_type};base64,{encoded}"
                
                logger.info(f"Successfully generated {spec.type} diagram ({len(content)} bytes)")
                logger.info(f"Data URL length: {len(data_url)} characters")
                logger.debug(f"Data URL preview: {data_url[:100]}...")
                
                return data_url
                
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                
                # Retry on server errors (5xx) but not client errors (4xx)
                if status_code >= 500 and attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"{spec.engine} server error {status_code} for {spec.type} "
                        f"(attempt {attempt + 1}/{self.max_retries}). "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"{spec.engine} HTTP error for {spec.type}: {status_code}")
                    logger.error(f"Response: {e.response.text[:500]}")
                    
                    # Save the diagram source code for debugging
                    logger.error(f"Failed diagram source ({spec.engine}):\n{spec.source_code}")
                    
                    # Provide helpful error message
                    if status_code == 500:
                        logger.error(
                            f"{spec.engine} returned 500 Internal Server Error. "
                            f"This may be due to invalid {spec.engine} syntax or service issues. "
                            f"Check the source code above or try again later."
                        )
                    elif status_code == 400:
                        logger.error(
                            f"{spec.engine} rejected the source code (400 Bad Request). "
                            f"The generated diagram syntax may be invalid. Check the source code above."
                        )
                    
                    return None
                    
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"{spec.engine} timeout for {spec.type} "
                        f"(attempt {attempt + 1}/{self.max_retries}). "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"{spec.engine} timeout for {spec.type} after {self.max_retries} attempts")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error generating {spec.type} diagram: {e}")
                return None
        
        # If all retries failed
        logger.error(f"Failed to generate {spec.type} diagram after {self.max_retries} attempts")
        return None
    
    async def _render_mermaid(self, source_code: str, format: str = "svg") -> bytes:
        """
        Render Mermaid diagram using Mermaid.ink service.
        
        Args:
            source_code: Mermaid diagram code
            format: Output format (svg or png)
            
        Returns:
            Rendered diagram bytes
        """
        # Encode the source code
        encoded_source = base64.urlsafe_b64encode(source_code.encode('utf-8')).decode('utf-8')
        
        # Build URL for Mermaid.ink
        url = f"{self.mermaid_url}/img/{encoded_source}"
        if format == "png":
            url = f"{self.mermaid_url}/img/{encoded_source}?type=png"
        
        logger.info(f"Requesting Mermaid rendering from: {self.mermaid_url}")
        
        # Make GET request
        response = await self.client.get(url)
        response.raise_for_status()
        
        return response.content
    
    async def _render_plantuml(self, source_code: str, format: str = "svg") -> bytes:
        """
        Render PlantUML diagram using PlantUML server.
        
        Args:
            source_code: PlantUML diagram code
            format: Output format (svg or png)
            
        Returns:
            Rendered diagram bytes
        """
        import zlib
        
        logger.info(f"Rendering PlantUML diagram (format={format})")
        logger.debug(f"PlantUML source code:\n{source_code}")
        
        # PlantUML encoding algorithm
        plantuml_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
        
        def encode3bytes(b1, b2, b3):
            c1 = b1 >> 2
            c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
            c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
            c4 = b3 & 0x3F
            return (plantuml_alphabet[c1 & 0x3F] +
                    plantuml_alphabet[c2 & 0x3F] +
                    plantuml_alphabet[c3 & 0x3F] +
                    plantuml_alphabet[c4 & 0x3F])
        
        # Compress using deflate
        compressed = zlib.compress(source_code.encode('utf-8'))[2:-4]
        
        # Encode compressed data
        result = []
        for i in range(0, len(compressed), 3):
            if i + 2 < len(compressed):
                result.append(encode3bytes(compressed[i], compressed[i + 1], compressed[i + 2]))
            elif i + 1 < len(compressed):
                result.append(encode3bytes(compressed[i], compressed[i + 1], 0))
            else:
                result.append(encode3bytes(compressed[i], 0, 0))
        
        encoded = ''.join(result)
        
        # Build URL for PlantUML server
        format_path = "svg" if format == "svg" else "png"
        url = f"{self.plantuml_url}/{format_path}/{encoded}"
        
        logger.info(f"PlantUML server: {self.plantuml_url}")
        logger.info(f"PlantUML URL: {url}")
        
        # Make GET request
        try:
            response = await self.client.get(url, timeout=60.0)
            logger.info(f"PlantUML response status: {response.status_code}")
            logger.info(f"PlantUML response size: {len(response.content)} bytes")
            logger.info(f"PlantUML response content-type: {response.headers.get('content-type', 'unknown')}")
            
            response.raise_for_status()
            
            # Check if we got an actual SVG/PNG or an error page
            content_type = response.headers.get('content-type', '').lower()
            if format == "svg" and 'svg' not in content_type and 'xml' not in content_type:
                logger.error(f"PlantUML returned unexpected content-type: {content_type}")
                logger.error(f"Response preview: {response.text[:500]}")
                raise Exception(f"PlantUML returned {content_type} instead of SVG")
            
            # Log SVG content preview
            if format == "svg":
                try:
                    svg_preview = response.content.decode('utf-8')[:300]
                    logger.debug(f"SVG response preview:\n{svg_preview}")
                except Exception:
                    pass
            
            return response.content
        except Exception as e:
            logger.error(f"PlantUML rendering failed: {e}")
            if hasattr(e, 'response'):
                logger.error(f"Response content: {e.response.text[:500]}")
            raise
    
    async def generate_all_diagrams(
        self,
        plan_text: str,
        diagram_types: Optional[List[str]] = None,
        format: str = "svg",
        include_failed: bool = False
    ) -> List[GeneratedDiagram]:
        """
        Analyze plan and generate all identified diagrams.
        
        Args:
            plan_text: The full project plan
            diagram_types: Specific types to generate (None = auto-detect)
            format: Output format (svg, png)
            include_failed: If True, include diagrams that failed to render with placeholder URL
            
        Returns:
            List of GeneratedDiagram objects
        """
        # Step 1: Analyze plan and generate specs
        specs = await self.analyze_plan(plan_text, diagram_types)
        
        if not specs:
            logger.warning("No diagrams identified in plan")
            return []
        
        # Step 2: Generate diagrams in parallel
        tasks = [self.generate_diagram(spec, format) for spec in specs]
        urls = await asyncio.gather(*tasks)
        
        # Step 3: Build result objects
        generated_diagrams = []
        for spec, url in zip(specs, urls):
            if url:  # Successfully generated
                generated_diagrams.append(GeneratedDiagram(
                    type=spec.type,
                    title=spec.title,
                    description=spec.description,
                    url=url,
                    source_code=spec.source_code
                ))
            elif include_failed:  # Include failed diagrams with source code for debugging
                # Use a more robust placeholder error image (simpler SVG)
                error_svg = '''<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#fff3cd" stroke="#856404" stroke-width="2"/>
  <text x="50%" y="40%" text-anchor="middle" font-family="Arial" font-size="18" fill="#856404">
    ⚠️ Diagram Generation Failed
  </text>
  <text x="50%" y="55%" text-anchor="middle" font-family="Arial" font-size="14" fill="#856404">
    The rendering service encountered an error
  </text>
  <text x="50%" y="70%" text-anchor="middle" font-family="Arial" font-size="14" fill="#856404">
    Please check the source code below for details
  </text>
</svg>'''
                placeholder_url = f"data:image/svg+xml;base64,{base64.b64encode(error_svg.encode()).decode()}"
                logger.warning(f"Including failed diagram: {spec.title}")
                generated_diagrams.append(GeneratedDiagram(
                    type=spec.type,
                    title=f"{spec.title} (FAILED)",
                    description=f"{spec.description} [Rendering failed - check source code]",
                    url=placeholder_url,
                    source_code=spec.source_code
                ))
        
        logger.info(f"Successfully generated {len(generated_diagrams)}/{len(specs)} diagrams")
        return generated_diagrams
    
    def embed_in_markdown(self, plan: str, diagrams: List[GeneratedDiagram]) -> str:
        """
        Insert generated diagrams into the plan markdown.
        
        Args:
            plan: Original plan text
            diagrams: Generated diagrams to embed
            
        Returns:
            Enhanced plan with embedded diagrams
        """
        if not diagrams:
            return plan
        
        # Create diagrams section
        diagrams_section = "\n\n---\n\n## 📊 Visual Diagrams\n\n"
        diagrams_section += "*Auto-generated visual representations of the project plan*\n\n"
        
        for diagram in diagrams:
            diagrams_section += f"### {diagram.title}\n\n"
            diagrams_section += f"*{diagram.description}*\n\n"
            diagrams_section += f"![{diagram.title}]({diagram.url})\n\n"
            
            # Add collapsible source code (for debugging)
            diagrams_section += "<details>\n<summary>View diagram source</summary>\n\n"
            diagrams_section += f"```{diagram.type}\n{diagram.source_code}\n```\n\n"
            diagrams_section += "</details>\n\n"
        
        # Insert before "## Summary" or at end
        if "## Summary" in plan:
            enhanced = plan.replace("## Summary", diagrams_section + "## Summary")
        elif "## Conclusion" in plan:
            enhanced = plan.replace("## Conclusion", diagrams_section + "## Conclusion")
        else:
            enhanced = plan + diagrams_section
        
        return enhanced
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()





