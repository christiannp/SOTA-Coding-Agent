import os
import difflib
import black
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from agent_logic import AgentBrain

app = FastAPI()
agent = AgentBrain(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Pydantic Models ---
class FileSkeleton(BaseModel):
    file_path: str
    content_head: str  # First 50 lines

class PlanRequest(BaseModel):
    skeletons: List[FileSkeleton]
    user_instruction: str

class RefactorRequest(BaseModel):
    file_path: str
    full_content: str
    research_context: Optional[str] = ""

class RefactorResponse(BaseModel):
    original_file: str
    refactored_code: str
    diff: str

# --- Endpoints ---

@app.post("/plan")
async def create_plan(request: PlanRequest):
    """
    Phase 1: Map-Reduce Planning.
    Analyzes skeletons to decide which files need reading.
    """
    try:
        target_files = agent.plan_refactoring(request.skeletons, request.user_instruction)
        return {"target_files": target_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refactor")
async def execute_refactor(request: RefactorRequest):
    """
    Phase 2 & 3: Execution & Safe Diff.
    Research -> Generate -> Format -> Diff.
    """
    # Step 1: Research (Mocked integration for brevity, usually calls Firecrawl)
    # research_data = requests.post(FIRECRAWL_URL, ...)
    
    # Step 2: Coder Agent Generates Full Code
    raw_ai_code = agent.generate_code(request.full_content, request.file_path)

    # Step 3: Sanitization (The Safe Diff Strategy)
    # We normalize both original and new code using Black to ensure
    # the diff is purely semantic, not whitespace noise.
    try:
        # Format Original (if possible)
        norm_original = black.format_str(request.full_content, mode=black.Mode())
    except:
        norm_original = request.full_content # Fallback if syntax error in original

    try:
        # Format AI Code
        norm_ai = black.format_str(raw_ai_code, mode=black.Mode())
    except:
        # If AI generates invalid syntax, we return raw but flag it implies error
        norm_ai = raw_ai_code 

    # Step 4: Mathematical Diff Calculation
    diff_gen = difflib.unified_diff(
        norm_original.splitlines(keepends=True),
        norm_ai.splitlines(keepends=True),
        fromfile=request.file_path,
        tofile=f"ai_{request.file_path}",
    )
    diff_text = "".join(diff_gen)

    return RefactorResponse(
        original_file=request.file_path,
        refactored_code=norm_ai,
        diff=diff_text
    )