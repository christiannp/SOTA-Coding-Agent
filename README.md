# State-of-the-art Coding Agent

<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/29cd6596-9d1e-42f1-a913-7a80ab93edde" />

Managing library updates is still manageable, however, upgrading algorithms is often time-consuming and error-prone. To address this, we build a coding agent capable of refactoring complex code using the latest state-of-the-art algorithms. It has to be cost-effective in terms of token usage and seamlessly integrated into VS Code, so developers can work without the friction of copy-paste code back and forth. We utilizes a "Map-Reduce" strategy for efficient context handling and a "Safe Diff" engine to ensure zero-hallucination patch generation.

---

## High-Level Architecture

The system operates via a split architecture: a VS Code Extension (Frontend) and a Dockerized Python Backend (AI Brain).

Flow:
1. VS Code Extension -> Sends File Skeletons -> Backend (/plan)
2. Backend (Gemini) -> Selects Targets -> Returns Target List
3. VS Code Extension -> Sends Full Content -> Backend (/refactor)
4. Backend -> Calls Firecrawl (Research) & Gemini (Generation)
5. Backend -> Runs Safe Diff Strategy -> Returns Diff Stream
6. VS Code Extension -> Renders Virtual Side-by-Side Diff

---

## Core Features

### 1. Map-Reduce Token Strategy
To avoid overflowing the context window, the agent never reads the entire repository at once.
- Phase 1 (Map): Reads only the file tree + first 50 lines (Skeleton) to plan.
- Phase 2 (Reduce): Reads full content only for files identified as relevant.

### 2. "Safe Diff" Guarantee
Unlike standard coding copilots, this agent does not predict patches directly (which often leads to hallucinated line numbers).
1. The Agent rewrites the *entire* file.
2. The Backend runs a formatter (Black) on both Original and New code.
3. Python's `difflib` mathematically computes the patch.
Result: 100% syntactically valid patches.

### 3. Rootless Docker Infrastructure
The backend runs in a container but accepts your host UID/GID. Generated files are owned by your user, not root.

### 4. Virtual Document UX
Changes are not written to disk immediately. The extension creates a 'ai-refactor:/' virtual document scheme, allowing you to review changes in a native VS Code "Compare" window before applying.

---

## Tech Stack

- Orchestration: Google Agent Development Kit
- LLM: Gemini 1.5 Pro (Long Context)
- Research: Self-hosted Firecrawl (Docker)
- Backend: FastAPI (Python 3.11)
- Frontend: VS Code Extension (TypeScript)

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js & npm
- A Google AI Studio API Key

### Step 1: Environment Setup
Create a .env file in the root directory:
GOOGLE_API_KEY=your_gemini_api_key_here
UID=1000  # Run 'id -u' to find yours
GID=1000  # Run 'id -g' to find yours

### Step 2: Start the Backend
Launch the AI Brain and Firecrawl services:
$ docker-compose up --build

*The API will be available at http://localhost:8000.*

### Step 3: Launch the Extension
1. Open the /vscode-extension folder in VS Code.
2. Install dependencies:
   $ npm install
3. Press F5 to open the Extension Development Host.

---

## Usage Guide

1. In the Extension Development Host window, open a Python project you wish to refactor.
2. Open the Command Palette (Ctrl+Shift+P / Cmd+Shift+P).
3. Run: "AI Refiner: Start Refactoring".
4. Enter your instruction (e.g., "Refactor the database connector to use a connection pool and add type hints").
5. Watch the status bar as the Agent plans and executes.
6. A Diff Window will open automatically showing the SOTA refactor.

---

## System Prompts

The Agent operates under the following strict system instructions:
"You are a Google Senior Engineer. You must prioritize Type Hints and Big-O Notation efficiency. You must cite the research paper or algorithm source in the docstring. Retain the original variable naming style unless objectively incorrect."

---

## License

Distributed under the MIT License.
