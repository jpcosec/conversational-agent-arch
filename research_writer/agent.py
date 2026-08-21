"""
Multi-agent research system con ADK.

Demuestra:
  - Agentes en modo task con I/O estructurado
  - Delegación padre → sub-agentes
  - Pydantic schemas para input/output
  - Session state management
  - Vertex AI via ADC
"""

from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent


# ─── Schemas estructurados ────────────────────────────────────────────────

class ResearchInput(BaseModel):
    topic: str = Field(description="Topic to research")
    depth: str = Field(default="medium", description="Research depth: brief, medium, detailed")

class ResearchOutput(BaseModel):
    summary: str = Field(description="Research summary")
    key_points: list[str] = Field(description="Key findings")
    sources: list[str] = Field(description="Sources referenced")

class WritingInput(BaseModel):
    topic: str = Field(description="Topic to write about")
    audience: str = Field(default="general", description="Target audience: general, technical, executive")
    style: str = Field(default="informative", description="Writing style")

class WritingOutput(BaseModel):
    title: str = Field(description="Article title")
    content: str = Field(description="Article body in markdown")
    word_count: int = Field(description="Approximate word count")

class FactCheckOutput(BaseModel):
    verdict: str = Field(description="One of: PASS, FLAG, FAIL")
    issues: list[str] = Field(description="List of issues found")
    explanation: str = Field(description="Detailed explanation")


# ─── Sub-agentes ──────────────────────────────────────────────────────────

researcher = LlmAgent(
    name="researcher",
    instruction="""
        You are a research specialist. Given a topic and depth, produce structured research.
        - For 'brief': 2-3 key points, 1-2 sources
        - For 'medium': 5-7 key points, 3-5 sources
        - For 'detailed': 10+ key points, 5+ sources
        Call finish_task() only when research is complete.
        You can ask the user clarifying questions if the topic is ambiguous.
    """,
    mode="task",
    input_schema=ResearchInput,
    output_schema=ResearchOutput,
)

writer = LlmAgent(
    name="writer",
    instruction="""
        You are a professional writer. Produce engaging, well-structured content.
        Adapt tone based on audience (general, technical, executive) and style.
        Output markdown with proper headings, lists, and formatting.
        Call finish_task() when the article is complete.
    """,
    mode="task",
    input_schema=WritingInput,
    output_schema=WritingOutput,
)

fact_checker = LlmAgent(
    name="fact_checker",
    instruction="""
        You verify factual claims in content.
        Given a piece of text, identify any claims that sound dubious or need citation.
        Return a verdict: 'PASS', 'FLAG', or 'FAIL' with explanation.
        Call finish_task() when done.
    """,
    mode="task",
    input_schema=WritingOutput,
    output_schema=FactCheckOutput,
)


# ─── Coordinador (root agent) ─────────────────────────────────────────────

root_agent = LlmAgent(
    name="research_coordinator",
    instruction="""
        You are a research content coordinator.

        You have 3 specialized agents available as tools:
        1. researcher - deep research on any topic
        2. writer - produces polished articles
        3. fact_checker - verifies factual accuracy

        Workflow:
        1. First, research the user's topic using the researcher agent
        2. Then, have the writer produce an article based on the research
        3. Finally, run fact_checker on the article
        4. Present the final result to the user with the fact-check verdict

        Always follow this sequence. If fact_checker flags issues, ask the writer to revise.
    """,
    sub_agents=[researcher, writer, fact_checker],
)