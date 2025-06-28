# Bot Review Assistant

An intelligent code review assistant powered by LangChain, LangGraph, and local LLM models. This tool analyzes pull request diffs and provides comprehensive feedback on code quality, naming conventions, syntax, and logic.

## Features

- **Multi-language Support**: Automatically detects programming language
- **Code Structure Analysis**: Scans for classes, functions, and variables
- **Naming Convention Checks**: Reviews naming patterns and conventions
- **Syntax Validation**: Checks for syntax errors and issues
- **Logic Review**: Analyzes code logic and provides suggestions
- **Interactive UI**: Clean Streamlit interface with organized results
- **RAG Architecture**: Uses FAISS vector store for context-aware reviews

## Quick Start

### Prerequisites

- Python 3.13
- At least 8GB RAM (for local LLM)
- GGUF model file (DeepSeek-Coder recommended)
- **CMake** (required for llama-cpp-python compilation)

#### Installing CMake on Windows

For Windows users, install CMake using Chocolatey package manager:

**Step 1**: Install Chocolatey (if not already installed)
```powershell
# Run as Administrator in PowerShell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
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

> **Note**: CMake is essential for compiling llama-cpp-python which enables GGUF model support. Without CMake, the installation will fail.

### Installation

**Step 1**: Setup virtual environment
```bash
cd bot-assistance
python -m venv venv
source venv/bin/activate.bat  # On Windows
```

**Step 2**: Install dependencies
```bash
pip install -r requirements.txt
```

**Step 3**: Download model
- Download `DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf`
- Download `all-MiniLM-L6-v2-Q4_K_M.gguf`
- Place it in `./models/` directory

**Step 4**: Configure environment
```bash
cp .env.example .env
```
**Then filled .env*

**Step 5**: Run the application
```bash
streamlit run main.py
```

## Usage

1. **Open the web interface** (usually http://localhost:8501)
2. **Paste your PR diff** in the text area
3. **Click "Review Code"** to start analysis
4. **View organized results** in different tabs:
   - Summary: Overall assessment
   - Language: Detected programming language
   - Structure: Found classes, functions, variables
   - Naming: Naming convention feedback
   - Syntax: Syntax validation results
   - Logic: Logic review and suggestions

## Architecture

The Bot Review Assistant follows a **RAG-based architecture** with **LangGraph state graphs** for orchestrating the code review workflow. The system combines local LLM inference with vector-based retrieval for context-aware code analysis.

### Project Structure

```
bot-assistance/
├── src/                              # Source code
│   └── code_review/                  # Main package
│       ├── __init__.py               # Package exports
│       ├── agents/                   # Specialized review agents
│       │   ├── __init__.py
│       │   ├── base.py               # BaseAgent class + LLM management
│       │   ├── naming.py             # NamingAgent - naming conventions
│       │   ├── syntax.py             # SyntaxAgent - syntax validation
│       │   ├── logic.py              # LogicAgent - logic analysis
│       │   └── summary.py            # SummaryAgent - feedback synthesis
│       ├── pipeline/                 # Workflow orchestration
│       │   ├── __init__.py
│       │   ├── nodes.py              # LangGraph node functions
│       │   └── workflow.py           # Main ReviewPipeline class
│       ├── core/                     # Core utilities
│       │   ├── __init__.py
│       │   ├── tools.py              # Code analysis tools
│       │   └── vector_store.py       # Vector operations
├── models/                           # Model files only
│   ├── DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf
│   └── all-MiniLM-L6-v2-Q4_K_M.gguf
├── main.py                           # Streamlit web interface
├── test_agents.py                    # Agent and pipeline tests
├── requirements.txt                  # Dependencies
└── README.md                         # This documentation
```

### Agent-Based Workflow

The system uses **specialized AI agents** orchestrated by **LangGraph** in a sequential workflow:

1. **Language Detection** → Identifies programming language from diff
2. **Code Chunking** → AST-based parsing and chunking of code changes
3. **Structure Scanning** → Extracts classes, functions, variables
4. **NamingAgent** → Reviews naming conventions and patterns
5. **SyntaxAgent** → Validates syntax correctness
6. **LogicAgent** → Analyzes code logic and provides suggestions
7. **SummaryAgent** → Creates comprehensive review summary

### Specialized Agents

#### **NamingAgent**
- Focus on naming conventions and code clarity
- Language-specific naming rules (camelCase, snake_case, PascalCase)
- Boolean naming patterns (is_, has_, can_, should_)
- Identifies unclear abbreviations and misleading names

#### **SyntaxAgent**
- Focus on syntax validation and error detection
- Language-specific syntax rules
- Compilation/interpretation errors
- Missing semicolons, brackets, parentheses

#### **LogicAgent**
- Focus on logic correctness and code quality
- Performance and security considerations
- Code smells and anti-patterns
- Edge cases and error scenarios

#### **SummaryAgent**
- Focus on synthesis and communication
- Natural language summaries
- Prioritized feedback
- Actionable recommendations

### RAG Components

- **Vector Store**: FAISS-based vector database for code context
- **Embeddings**: HuggingFace sentence-transformers (all-MiniLM-L6-v2)
- **Chunking Strategy**: AST-based code segmentation for better context
- **Retrieval**: Context-aware code snippet retrieval for enhanced reviews

### Technology Stack

- **LangChain/LangGraph**: Workflow orchestration and LLM integration
- **llama-cpp-python**: Local LLM inference (DeepSeek-Coder)
- **Streamlit**: Interactive web interface
- **FAISS**: Vector similarity search
- **HuggingFace**: Embeddings and model management

#### Web Interface
```bash
streamlit run app.py
```

## TODO

- [ ] Setup API with LangGraph platform - [docs](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/)
- [ ] Fix code all in tools, agents which currently working not as expected
- [ ] Optimize agent system prompts based on usage patterns
- [ ] Add more specialized agents if needed
- [ ] Implement parallel agent processing
- [ ] POC git API integration
- [ ] Performance monitoring and optimization