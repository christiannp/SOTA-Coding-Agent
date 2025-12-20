from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import List, Optional
import logging, json, os, base64, hashlib, datetime
from agent_logic import PlannerAgent, ResearchAgent, CoderAgent
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.middleware.cors import CORSMiddleware

# Setup structured JSON logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = FastAPI()

# Metrics counters
plan_counter = Counter('plan_requests_total', 'Total /plan requests')
refactor_counter = Counter('refactor_requests_total', 'Total /refactor requests')

# Allow CORS if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}

# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    content = generate_latest()
    return Response(content=content, media_type=CONTENT_TYPE_LATEST)

# Request/Response models
class FileTreeItem(BaseModel):
    path: str
    type: str
    size: int

class SkeletonItem(BaseModel):
    path: str
    content: str  # base64-encoded skeleton

class PlanRequest(BaseModel):
    request_id: str
    workspace_root: str
    file_tree: List[FileTreeItem]
    skeletons: List[SkeletonItem]
    max_skeleton_bytes: int

class TargetFile(BaseModel):
    path: str
    reason: str

class PlanResponse(BaseModel):
    request_id: str
    target_files: List[TargetFile]
    planner_version: str
    seed: int
    estimated_token_cost: int

class RefactorFile(BaseModel):
    path: str
    content: str  # base64-encoded full file

class ResearchConstraints(BaseModel):
    max_papers: int
    allowed_sources: List[str]

class RefactorRequest(BaseModel):
    request_id: str
    target_files: List[RefactorFile]
    research_constraints: ResearchConstraints
    dry_run: bool

class ResultItem(BaseModel):
    path: str
    orig_sha: str
    new_sha: str
    diff: str
    new_content: str
    formatting_ok: bool
    error: Optional[str] = None

class RefactorResponse(BaseModel):
    request_id: str
    results: List[ResultItem]
    branch: Optional[str] = None

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(json.dumps({"error": "validation_error", "message": str(exc)}))
    return JSONResponse(status_code=422, content={"error": "validation_error", "message": str(exc)})

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(json.dumps({"error": "internal_error", "message": str(exc)}))
    return JSONResponse(status_code=500, content={"error": "internal_error", "message": str(exc)})

@app.post("/plan", response_model=PlanResponse)
async def plan(request: PlanRequest):
    plan_counter.inc()
    # Basic validations
    if ".." in request.workspace_root.split(os.sep):
        raise HTTPException(status_code=400, detail="Invalid workspace_root")

    total_bytes = sum(len(item.content) for item in request.skeletons)
    if total_bytes > request.max_skeleton_bytes:
        raise HTTPException(status_code=400, detail="max_skeleton_bytes exceeded")

    # Planner logic (stubbed): select all files sorted
    paths = sorted(item.path for item in request.file_tree)
    target_files = []
    for p in paths:
        target_files.append({"path": p, "reason": f"Refactor recommended for {p}"})

    seed = int(hashlib.sha256(request.request_id.encode()).hexdigest(), 16) % (10**8)
    estimated_token_cost = total_bytes // 4

    response = {
        "request_id": request.request_id,
        "target_files": target_files,
        "planner_version": "1.0.0",
        "seed": seed,
        "estimated_token_cost": estimated_token_cost,
    }
    logger.info(json.dumps({"event": "plan_completed", "request_id": request.request_id, "targets": target_files}))
    return response

@app.post("/refactor", response_model=RefactorResponse)
async def refactor(request: RefactorRequest):
    refactor_counter.inc()
    results = []
    for item in request.target_files:
        path = item.path
        if ".." in path.split(os.sep):
            results.append({
                "path": path,
                "orig_sha": "",
                "new_sha": "",
                "diff": "",
                "new_content": "",
                "formatting_ok": False,
                "error": "validation_error: invalid path"
            })
            continue

        # Decode original content
        try:
            orig_content = base64.b64decode(item.content).decode('utf-8', errors='ignore')
        except Exception as e:
            results.append({
                "path": path,
                "orig_sha": "",
                "new_sha": "",
                "diff": "",
                "new_content": "",
                "formatting_ok": False,
                "error": f"decoding_error: {e}"
            })
            continue

        # (Placeholder) Research agent logic could go here

        # Coder agent logic (stubbed): prepend AI-REF comment
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        reason_id = hashlib.sha256((request.request_id + path).encode()).hexdigest()[:8]
        if path.endswith(".py"):
            comment = f"# AI-REF: {{timestamp: {timestamp}, agent: 'coder', reason_id: {reason_id}}}\n"
        else:
            comment = f"// AI-REF: {{timestamp: {timestamp}, agent: 'coder', reason_id: {reason_id}}}\n"
        new_content = comment + orig_content

        # Format code with isort+Black
        formatting_ok = True
        error_msg = None
        try:
            import isort
            from black import format_str, FileMode
            formatted_orig = format_str(isort.code(orig_content, profile="black"), mode=FileMode())
            formatted_new = format_str(isort.code(new_content, profile="black"), mode=FileMode())
        except Exception as e:
            formatting_ok = False
            formatted_orig = orig_content
            formatted_new = new_content
            error_msg = str(e)

        # Compute unified diff
        import difflib
        orig_lines = formatted_orig.splitlines(keepends=True)
        new_lines = formatted_new.splitlines(keepends=True)
        diff = ''.join(difflib.unified_diff(orig_lines, new_lines, fromfile=path, tofile=path, lineterm=''))

        orig_sha = hashlib.sha256(formatted_orig.encode()).hexdigest()
        new_sha = hashlib.sha256(formatted_new.encode()).hexdigest()

        results.append({
            "path": path,
            "orig_sha": orig_sha,
            "new_sha": new_sha,
            "diff": diff,
            "new_content": formatted_new,
            "formatting_ok": formatting_ok,
            "error": error_msg
        })

        # If apply mode, commit changes
        if not request.dry_run:
            from git import Repo
            try:
                repo = Repo(os.getcwd())
                branch_name = f"ai-refactor/{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                repo.git.checkout('-b', branch_name)
                file_path = os.path.join(request.workspace_root, path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_new)
                repo.index.add([file_path])
                repo.index.commit('AI refactor commit')
            except Exception as e:
                logger.error(json.dumps({"error": "git_error", "message": str(e)}))

    branch_name = None
    if not request.dry_run:
        branch_name = f"ai-refactor/{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {
        "request_id": request.request_id,
        "results": results,
        "branch": branch_name
    }