# State-of-the-art Coding Agent

A **production-ready AI code refinement system** built with **Google Agent Development Kit (ADK)** and **FastAPI** as a **VS Code Extension**. It performs **deterministic, safe, reviewable refactoring** using a multi-agent architecture and a virtual diff-based UX.

This system is designed for **professional engineering workflows** where correctness, traceability, and developer control are mandatory.

---

## Key Features

- **Google ADK–based multi-agent system**
  - Planner Agent (structure-only analysis)
  - Research Agent (SOTA search via Firecrawl MCP)
  - Coder Agent (deterministic full-file rewriting)

- **Strict Map–Reduce Context Strategy**
  - Phase 1: File tree + skeletons only
  - Phase 2: Full content for selected files only

- **Safe Diff Strategy**
  - AI generates **full file content only**
  - Both original and new code are formatted
  - Unified diffs computed server-side
  - SHA hashes for integrity verification

- **Virtual Document UX (VS Code)**
  - No files overwritten by default
  - Native side-by-side diff (`vscode.diff`)
  - Changes applied only on explicit user action

- **Deterministic & Auditable**
  - Gemini 1.5 Pro via ADK
  - Temperature = 0
  - Explicit seeds, hashes, and versions
  - Structured JSON logging and metrics

---

## Tech Stack

**Backend**
- Python 3.11
- FastAPI
- Google Agent Development Kit (`google-adk`)
- Gemini 1.5 Pro (via ADK)
- Firecrawl MCP (self-hosted)
- GitPython
- Black, isort, Ruff
- Prometheus metrics

**Frontend**
- VS Code Extension
- TypeScript
- Native diff rendering

**Infrastructure**
- Docker Compose
- Rootless-compatible containers

---

## Supported Languages (Initial Scope)

- Python
- TypeScript / JavaScript

---

## Core Design Principles

### 1. Map–Reduce Context Strategy

The system **never sends the entire codebase to the LLM at once**.

- **Planning phase**
  - File tree metadata
  - First 50 lines of each file
  - Planner Agent selects target files deterministically

- **Execution phase**
  - Only selected files are sent
  - Execution is rejected if planning was skipped

### 2. Safe Diff Strategy

- No patch or diff generation by the LLM
- AI outputs **full rewritten files only**
- Backend:
  1. Formats original and new code
  2. Computes unified diff
  3. Calculates SHA-256 hashes
- Failures are isolated per file

### 3. Virtual Document UX

- Backend does **not** write files by default
- VS Code renders AI output as virtual documents
- Developers review changes exactly like a Git diff
- Optional apply mode:
  - Creates `ai-refactor/<timestamp>` branch
  - Commits via GitPython

---

## API Overview

### `POST /plan`

Analyzes project structure and selects files for refactoring.

**Input**
- Workspace root
- File tree metadata
- Base64-encoded skeletons
- Hard limits enforced

**Output**
- Deterministic list of target files with reasons
- Planner version and seed
- Estimated token cost

### `POST /refactor`

Refactors selected files using Research + Coder agents.

**Input**
- Full content of target files only
- Research constraints
- Dry-run or apply mode

**Output**
- Per-file diffs, hashes, formatting status
- AI-generated full file content
- Git branch name if applied

### Other Endpoints

- `GET /health` – Health check
- `GET /metrics` – Prometheus-compatible metrics

---

## VS Code Extension Workflow

1. Scan workspace for supported files
2. Send skeletons to `/plan`
3. Display planned target files and reasons
4. User chooses:
   - **Dry Run** (default)
   - **Apply Changes**
5. Call `/refactor`
6. Open native side-by-side diffs
7. Optionally apply and commit changes

---

## Running Locally

### 1. Environment Setup

```bash
cp backend/.env.example backend/.env
```

Fill in:
- GOOGLE_API_KEY
- GEMINI_MODEL (default: gemini-1.5-pro-long)
- FIRECRAWL_API_KEY

### 2. Start Services
```bash
docker compose up
```

Backend: http://localhost:8000
Firecrawl MCP: http://localhost:3000

### 3. Use the VS Code Extension

1. Open the workspace you want to refactor
2. Run command: “Code Refine: Run Refactor”
3. Review diffs
4. Apply only if satisfied

---

## Security & Safety

- Workspace path validation and sandboxing
- Path traversal prevention
- Read-only behavior by default
- Non-root containers
- Rate-limited research tooling
- Deterministic LLM execution

---

## Intended Use

This system is designed for:
- Senior engineers and tech leads
- Large or sensitive codebases
- Regulated or high-assurance environments
- AI-assisted refactoring with human control

It is not intended for:
- Blind auto-apply refactoring
- Non-deterministic experimentation
- Patch-based code mutation