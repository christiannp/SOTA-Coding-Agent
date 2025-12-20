import os
from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

# System prompt for the Coder agent (from spec:contentReference[oaicite:0]{index=0})
system_prompt = (
    "You are a Google Senior Engineer. Use ADK with deterministic settings.\n"
    "For every file you modify:\n"
    "1. Output ONLY the full new file content.\n"
    "2. Add a top-of-file changelog comment:\n"
    "   AI-REF: { timestamp, agent: 'coder', reason_id }\n"
    "3. Use explicit type hints and document Big-O complexity.\n"
    "4. Cite sources in docstrings as [Title, Year, URL]. If none, say 'No SOTA found'.\n"
    "5. Preserve original variable naming unless objectively incorrect.\n"
    "6. Do not change public APIs unless explicitly instructed.\n"
    "7. Provide or update unit tests when behavior changes.\n"
    "8. Use language-appropriate formatting.\n"
    "9. Do NOT include chain-of-thought or internal reasoning.\n"
    "If a file cannot be safely refactored, return it unchanged with a short reason."
)

# Use Gemini 1.5 Pro in deterministic mode
gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-long")

# Planner Agent (selects files to refactor)
PlannerAgent = Agent(
    model=gemini_model,
    name="PlannerAgent",
    description="Agent to decide which files need refactoring",
    instruction="Analyze the file tree and skeleton code to choose files for refactoring. Output JSON list of target files with reasons.",
    tools=[],
)

# Research Agent (searches SOTA references via Firecrawl)
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
firecrawl_api_url = os.getenv("FIRECRAWL_API_URL")
tools = []
if firecrawl_api_key:
    base_url = firecrawl_api_url.rstrip("/") if firecrawl_api_url else "https://mcp.firecrawl.dev"
    mcp_url = f"{base_url}/{firecrawl_api_key}/v2/mcp"
    params = StreamableHTTPServerParams(url=mcp_url)
    tools = [MCPToolset(connection_params=params)]
ResearchAgent = Agent(
    model=gemini_model,
    name="ResearchAgent",
    description="Agent to find state-of-the-art coding best practices",
    instruction="Search for current best practices for the code being refactored. Return citations and summaries.",
    tools=tools,
)

# Coder Agent (performs code refactoring)
CoderAgent = Agent(
    model=gemini_model,
    name="CoderAgent",
    description="Agent to rewrite code files according to plan and research",
    instruction=system_prompt,
    tools=[],
)