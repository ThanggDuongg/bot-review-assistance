# Bot Review Assistant

An intelligent code review assistant powered by LangChain, LangGraph, and local LLM models. This tool analyzes pull request diffs and provides comprehensive feedback on code quality, naming conventions, syntax, and logic.

## Features

- **Multi-language Support**: Automatically detects programming language
- **AST-based Code Chunking**: Uses Tree-sitter for intelligent code parsing and chunking
- **Logic Review**: Analyzes code logic and provides suggestions
- **Interactive UI**: Clean Streamlit interface with organized results
- **RAG Architecture**: Uses FAISS vector store for context-aware reviews
- **API Server**: LangGraph Platform CLI for production deployment

## Quick Start

### Prerequisites

- Python 3.13
- At least 8GB RAM (for local LLM)
- GGUF model file (DeepSeek-Coder recommended)
- **CMake** (required for llama-cpp-python compilation)
- **Node.js & npm** (required for tree-sitter grammars)
- **Git** (required for cloning grammar repositories)

#### Installing CMake on Windows

For Windows users, install CMake using Chocolatey package manager:

**Step 1**: Install Chocolatey (if not already installed)
```powershell
# Run as Administrator in PowerShell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager].SecurityProtocol = [System.Net.ServicePointManager].SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

**Step 2**: Install CMake with Chocolatey
```powershell
# Run as Administrator
choco install cmake
```

**Step 3**: Verify installation
```bash
cmake --version
```

#### Installing Tree-sitter CLI(v0.20.8)

**Step 1**: Install Node.js (if not already installed)
```bash
# Download from https://nodejs.org/ or use package manager
```

**Step 2**: Install tree-sitter-cli globally
```bash
npm install -g tree-sitter-cli@0.20.8
```

**Step 3**: Verify installation
```bash
tree-sitter --version
```

> **Note**: CMake and tree-sitter-cli are essential for the setup. CMake enables GGUF model support, while tree-sitter-cli enables AST-based code parsing.

### Installation

**Step 1**: Setup virtual environment
```bash
cd bot-assistance
python -m venv venv
.\venv\Scripts\activate  # On Windows
```

**Step 2**: Install dependencies
```bash
pip install -r requirements.txt
```

If you encountered any errors
```bash
winget install Microsoft.VisualStudio.2022.BuildTools --force --override "--wait --passive --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621"
```
then
```bash
pip install llama-cpp-python -C cmake.args="-DLLAMA_BLAS=ON;-DGGML_BLAS=ON;-DGGML_BLAS_VENDOR=OpenBLAS"
```

**Step 3**: Setup Tree-sitter parsers
```bash
python setup_parser.py
```

**Step 4**: Download model
- Download `DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf`
- Download `all-MiniLM-L6-v2-Q4_K_M.gguf`
- Place it in `./models/` directory

**Step 5**: Configure environment
```bash
cp .env.example .env
```
**Then filled .env*

**Step 6**: Run the application
```bash
streamlit run main.py
```

## LangGraph Platform CLI Setup

For API deployment and production use:

### 1. Install LangGraph CLI
```bash
pip install --upgrade "langgraph-cli[inmem]"
```

### 2. Create LangGraph app (if starting fresh)
```bash
langgraph new path/to/your/app --template new-langgraph-project-python
cd path/to/your/app
pip install -e .
```

### 3. Setup langgraph.json
Create `langgraph.json`

### 4. Run API Server
```bash
langgraph dev
```

Server will be available at:
- **API**: http://localhost:2024
- **Docs**: http://localhost:2024/docs
- **Studio**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

## Usage

1. **Open the web interface** (usually http://localhost:8501)
2. **Paste your PR diff** in the text area
3. **Click "Review Code"** to start analysis
4. **View organized results** in different tabs:
   - Summary: Overall assessment
   - Logic: Logic review and suggestions

## Architecture

The Bot Review Assistant follows a **RAG-based architecture** with **LangGraph state graphs** for orchestrating the code review workflow. The system combines local LLM inference with vector-based retrieval for context-aware code analysis.

### Project Structure

```
bot-assistance/
├── src/
│   └── code_review/
│       ├── __init__.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── logic.py
│       │   └── summary.py
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── nodes.py
│       │   └── workflow.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── utils.py
│       │   ├── vector_store.py
│       │   ├── tools/
│       │   │   ├── __init__.py
│       │   │   ├── file_fetcher.py
│       │   │   └── mock_file_fetcher.py
│       │   └── chunkers/
│       │       ├── __init__.py
│       │       ├── base_chunker.py
│       │       ├── diff_chunker.py
│       │       ├── chunker_factory.py
│       │       ├── js_chunker.py
│       │       ├── angular_chunker.py
│       │       ├── react_chunker.py
│       │       └── csharp_chunker.py
├── build/                  # Tree-sitter parser binaries
├── data/
│   └── best_practices.json # Best practice definitions and embeddings
├── models/                 # GGUF model files
│   ├── Codestral-22B-v0.1-Q6_K.gguf
│   ├── starcoder2-15b-Q5_K_M.gguf
│   ├── Qwen2.5-Coder-32B-Instruct-Q5_K_M.gguf
│   ├── Qwen2.5-3B-WebArena-Lite-SFT.Q4_K_M.gguf
│   ├── all-MiniLM-L6-v2-Q4_K_M.gguf
│   └── DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf
├── setup_parser.py         # Tree-sitter parser setup
├── main.py                 # Streamlit web UI
├── requirements.txt
└── README.md
```

### Agent-Based Workflow

1. User submits a code diff via the web interface.
2. Code is parsed and chunked using AST (Tree-sitter).
3. LogicAgent analyzes logic, bugs, performance, security, and best practices.
4. SummaryAgent generates technical and business summaries.
5. Results are displayed in the UI, including per-file, per-line feedback and suggested unit tests.

### Specialized Agents

- **LogicAgent**: Detects bugs, performance issues, security risks, anti-patterns, and best practice violations. Provides actionable suggestions and relevant unit tests.
- **SummaryAgent**: Synthesizes technical and business summaries to help reviewers quickly understand the pull request.

### RAG Components

- **Vector Store (FAISS)**: Stores and retrieves relevant best practices using embeddings.
- **Embeddings**: Uses all-MiniLM-L6-v2 for semantic similarity between code and best practices.
- **Chunking**: AST-based chunking with Tree-sitter for precise code analysis.

### Technology Stack

- **LangChain/LangGraph**: Workflow orchestration and LLM integration
- **llama-cpp-python**: Local LLM inference (DeepSeek-Coder)
- **Tree-sitter**: AST-based code parsing and analysis
- **Streamlit**: Interactive web interface
- **FAISS**: Vector similarity search
- **HuggingFace**: Embeddings and model management

#### Web Interface
```bash
streamlit run main.py
```

## TODO

- [x] Setup API with LangGraph platform - [docs](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/)
- [ ] Combine with TYI's code
- [ ] Optimize agent system prompts based on usage patterns
- [ ] Add more specialized agents if needed
- [ ] Implement parallel agent processing
- [ ] POC git API integration
- [ ] Performance monitoring and optimization
  - Advance:
    - [ ] Full codebase context: AI reviews changes with awareness of related files, dependencies, and architectural impact.
    - [ ] In-line comments and suggestions: Developers receive actionable feedback directly in the pull request, reducing back-and-forth. (Currently)
    - [x] Natural language summaries: AI generates concise summaries of PRs, making it easier for reviewers to understand the scope and intent (Currently)
    - [ ] Customizable review focus: Teams can specify which types of changes or issues the AI should prioritize (UI)
    - [x] Support for multiple languages: Modern tools handle CSharp, Java, JavaScript, and more (Currently)
      - Example Code Review Flow:
        - Developer opens a pull request, then clicks the button to trigger.
        - Analyzes the PR, referencing the entire codebase graph.
        - Leaves in-line comments highlighting bugs, architectural issues, and style violations.
        - Expert (human) review once again to validate and add missing points.