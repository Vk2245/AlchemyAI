<div align="center">

<img src="DEV/frontend/LOGO/logo_square.png" alt="Alchemy AI Logo" width="150"/>

# Alchemy AI

### *Transforming Chaos into Intelligence*

**Adaptive AI-Powered Document Intelligence & Product Data Platform**

[![Live Demo](https://img.shields.io/badge/Live_Demo-Vercel-black?style=for-the-badge&logo=vercel)](https://alchemyai.vercel.app/)
[![Next.js](https://img.shields.io/badge/Next.js_14-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent_AI-orange?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)

> *"Don't just read documents. Understand them."*

</div>

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [System Architecture](#system-architecture)
- [9-Stage Intelligence Pipeline](#9-stage-intelligence-pipeline)
- [Dual-Track Processing](#dual-track-processing-pdf--excel)
- [LLM Provider Fallback Chain](#llm-provider-fallback-chain)
- [OCR Fallback Chain](#4-tier-ocr-fallback-chain)
- [Risk Radar & Agentic Research](#risk-radar--agentic-research)
- [Models Used](#models-used)
- [Tech Stack](#tech-stack)
- [Running Online (Cloud Deployment)](#running-online-cloud-deployment)
- [Running Offline (Local vLLM)](#running-offline-local-vllm--zero-cost-air-gapped)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)

---

## The Problem

Enterprise procurement and supply chain teams drown in **thousands of unstructured product datasheets, invoices, and catalogs** every month. These documents arrive as:

- Scanned PDFs with tables, diagrams, and handwritten notes
- Messy Excel catalogs with 1000+ rows of inconsistent descriptions
- Contracts with hidden compliance risks buried in legalese

**Manual processing costs $15-$50 per document**, takes hours, and still produces errors. Existing OCR tools extract text but don't *understand* it.

---

## The Solution

**Alchemy AI** is a full-stack, production-grade AI platform that takes any document — PDF, image, or bulk Excel catalog — and runs it through a **9-stage zero-shot intelligence pipeline** to produce:

- **Structured JSON records** with validated entities, confidence scores, and provenance
- **Adaptive risk assessment** with fraud detection and compliance flagging
- **AI-generated executive reports** (PDF/HTML) with narrative analysis
- **Agentic web research** that autonomously verifies vendor legitimacy
- **LangGraph RAG chatbot** grounded exclusively in the user's own data
- **Human-in-the-loop review** with inline field-level corrections

All of this at **near-zero cost** using a Two-Tier Inference Architecture (Local vLLM + Cloud APIs).

---

## System Architecture

The platform is built as a **3-layer decoupled system**: a Next.js 14 frontend, a FastAPI async backend, and a modular AI-ML engine with 25+ specialized Python modules.

```mermaid
graph TB
    classDef frontend fill:#0f172a,stroke:#6366f1,stroke-width:3px,color:#e0e7ff
    classDef backend fill:#1e1b4b,stroke:#8b5cf6,stroke-width:3px,color:#e0e7ff
    classDef aiml fill:#14532d,stroke:#22c55e,stroke-width:3px,color:#dcfce7
    classDef db fill:#7c2d12,stroke:#f97316,stroke-width:3px,color:#ffedd5
    classDef external fill:#581c87,stroke:#d946ef,stroke-width:3px,color:#fae8ff

    subgraph "Frontend — Next.js 14 + TailwindCSS"
        UI["Upload / Dashboard / Chat"]:::frontend
        SSE["SSE Real-Time Progress"]:::frontend
        REVIEW["Human Review Panel"]:::frontend
    end

    subgraph "Backend — FastAPI + SQLAlchemy"
        API["REST API + JWT Auth"]:::backend
        PROC["Process Orchestrator"]:::backend
        WS["SSE Stream Manager"]:::backend
        DB["PostgreSQL / SQLite"]:::db
    end

    subgraph "AI-ML Engine — 25+ Modules"
        INGEST["Ingestion & OCR"]:::aiml
        EXTRACT["Entity Extraction"]:::aiml
        RISK["Risk Radar"]:::aiml
        AGENT["Agentic Research"]:::aiml
        REPORT["Report Generator"]:::aiml
        CHAT["LangGraph RAG Agent"]:::aiml
    end

    subgraph "External Services"
        GROQ["Groq LPU"]:::external
        GEMINI["Gemini Flash"]:::external
        VLLM["Local vLLM"]:::external
        TAVILY["Tavily / Serper"]:::external
    end

    UI -->|"Upload PDF/Excel"| API
    API --> PROC
    PROC -->|"Yields Progress"| WS
    WS -->|"SSE Events"| SSE
    PROC --> INGEST --> EXTRACT --> RISK --> AGENT --> REPORT
    API --> CHAT
    PROC -->|"Save Records"| DB
    DB -->|"Fetch Records"| REVIEW
    EXTRACT -->|"Structured Output"| GROQ
    EXTRACT -->|"Fallback"| GEMINI
    EXTRACT -->|"Offline"| VLLM
    AGENT --> TAVILY
```

---

## 9-Stage Intelligence Pipeline

Every document passes through **9 discrete, deterministic AI stages**. Each stage is a specialized zero-shot module with its own schema, validation, and fallback logic — never a single monolithic prompt.

```mermaid
graph LR
    classDef stage1 fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#fff
    classDef stage2 fill:#1a4731,stroke:#34d399,stroke-width:2px,color:#fff
    classDef stage3 fill:#4a1942,stroke:#c084fc,stroke-width:2px,color:#fff
    classDef stage4 fill:#713f12,stroke:#fbbf24,stroke-width:2px,color:#fff

    S1["1. Document<br/>Ingestion"]:::stage1
    S2["2. OCR &<br/>Vision Audit"]:::stage1
    S3["3. Industry<br/>Detection"]:::stage2
    S4["4. Adaptive NER<br/>Extraction"]:::stage2
    S5["5. Dynamic<br/>Classification"]:::stage2
    S6["6. Confidence<br/>Scoring"]:::stage3
    S7["7. Risk Radar &<br/>Compliance"]:::stage3
    S8["8. Agentic Web<br/>Research"]:::stage4
    S9["9. Intelligence<br/>Report Gen"]:::stage4

    S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8 --> S9
```

| Stage | Module | What It Does |
|:-----:|--------|-------------|
| **1** | `ingestion/parse_pdf.py` | Extracts raw text and tables from PDF pages using PyMuPDF |
| **2** | `ingestion/ocr_fallback.py` | 4-tier OCR chain: Tesseract → OCR.space → Groq Vision → Gemini Vision |
| **3** | `extraction/extract_entities.py` | Detects document vertical (Invoice, Contract, Medical, etc.) and loads the matching extraction schema |
| **4** | `extraction/extract_attributes.py` | Schema-first structured extraction via `instructor` + Pydantic validation |
| **5** | `pipeline/run.py` | Dynamic taxonomy classification and category mapping |
| **6** | `confidence/score_record.py` | Weighted confidence: 70% avg entity confidence + 30% field completeness |
| **7** | `risk_radar/detect_risk.py` | Static fraud checks, email validation, missing-field flagging, collusion graph analysis |
| **8** | `agent/web_research.py` | Autonomous vendor research via Tavily → Serper → Gemini Search with red-flag detection |
| **9** | `report/generate_report.py` | AI narrative report generation → rendered as PDF/HTML via WeasyPrint |

---

## Dual-Track Processing: PDF & Excel

The platform detects the file type at upload and routes it to the appropriate pipeline branch:

```mermaid
graph TD
    classDef upload fill:#312e81,stroke:#818cf8,stroke-width:3px,color:#e0e7ff
    classDef pdf fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#fff
    classDef excel fill:#14532d,stroke:#34d399,stroke-width:2px,color:#fff
    classDef shared fill:#4a1942,stroke:#c084fc,stroke-width:2px,color:#fff
    classDef output fill:#713f12,stroke:#fbbf24,stroke-width:2px,color:#fff

    UPLOAD["File Upload"]:::upload

    UPLOAD -->|".pdf / .png / .jpg"| PDF_BRANCH
    UPLOAD -->|".xlsx / .xls / .csv"| EXCEL_BRANCH

    subgraph "PDF_BRANCH [Unstructured Document Pipeline]"
        P1["Parse PDF Pages<br/>(PyMuPDF)"]:::pdf
        P2["OCR Fallback Chain<br/>(4 Tiers)"]:::pdf
        P3["Build Evidence<br/>(Markdown + Tables)"]:::pdf
        P4["Adaptive NER<br/>(instructor + Pydantic)"]:::pdf
        P1 --> P2 --> P3 --> P4
    end

    subgraph "EXCEL_BRANCH [Bulk Catalog Pipeline]"
        E1["Load Excel<br/>(Polars DataFrame)"]:::excel
        E2["Detect Description<br/>Column"]:::excel
        E3["Row-by-Row LLM<br/>Enrichment (Groq)"]:::excel
        E4["Category Grouping<br/>& Statistics"]:::excel
        E1 --> E2 --> E3 --> E4
    end

    P4 --> MERGE
    E4 --> MERGE

    subgraph "MERGE [Shared Intelligence Layer]"
        M1["Confidence Scoring"]:::shared
        M2["Risk Radar"]:::shared
        M3["Agentic Research"]:::shared
        M4["Report Generation"]:::shared
        M1 --> M2 --> M3 --> M4
    end

    M4 --> OUT1["Dashboard Record"]:::output
    M4 --> OUT2["PDF/HTML Report"]:::output
    M4 --> OUT3["JSON/CSV Export"]:::output
```

### Excel Pipeline Deep Dive

For bulk Excel catalogs (e.g., 1000-row industrial part lists):

1. **Polars** reads the file (10x faster than pandas, zero-copy memory)
2. Auto-detects the description column via fuzzy header matching
3. Each row is sent to **Groq LPU** for structured extraction (Category, Material, Size, Description)
4. Results are grouped into categories with sample items and statistics
5. A dedicated PDF report is generated with category distribution charts

> **Rate Limit Protection:** Free-tier APIs allow 15 RPM. The system batches items with automatic throttling to prevent `429 RateLimitError` crashes.

---

## LLM Provider Fallback Chain

The `llm_client.py` implements a **silent, automatic fallback chain**. If the primary provider fails (rate limit, timeout, or error), the system seamlessly escalates to the next provider without user intervention:

```mermaid
graph LR
    classDef primary fill:#166534,stroke:#22c55e,stroke-width:3px,color:#fff
    classDef fallback1 fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#fff
    classDef fallback2 fill:#581c87,stroke:#d946ef,stroke-width:2px,color:#fff
    classDef fail fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#fff

    subgraph "Online Mode (Cloud Deploy)"
        G["Groq LPU<br/>~800 tok/s"]:::primary
        GEM["Gemini Flash<br/>Fallback"]:::fallback1
        G -->|"429 Rate Limit<br/>or Timeout"| GEM
        GEM -->|"All Failed"| ERR1["Error + Log"]:::fail
    end

    subgraph "Offline Mode (Local GPU)"
        V["vLLM - Qwen 4-bit<br/>Local GPU"]:::primary
        G2["Groq<br/>Fallback"]:::fallback1
        GEM2["Gemini<br/>Last Resort"]:::fallback2
        V -->|"OOM / Context<br/>Too Large"| G2
        G2 -->|"Rate Limit"| GEM2
        GEM2 -->|"All Failed"| ERR2["Error + Log"]:::fail
    end
```

### How Fallback Works (Code Level)

```python
# In llm_client.py — simplified
providers_to_try = [provider]  # e.g., ["groq"]

if provider == "groq":
    if GEMINI_API_KEY:
        providers_to_try.append("gemini")  # -> ["groq", "gemini"]

for current_provider in providers_to_try:
    try:
        result = _structured_output_single(provider=current_provider, ...)
        return result  # Success — return immediately
    except Exception:
        print(f"Provider '{current_provider}' failed, falling back...")

raise last_error  # All providers exhausted
```

---

## 4-Tier OCR Fallback Chain

For scanned PDFs, image-heavy pages, and engineering diagrams, the OCR module implements a 4-tier escalation:

```mermaid
graph TD
    classDef tier1 fill:#166534,stroke:#22c55e,stroke-width:2px,color:#fff
    classDef tier2 fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#fff
    classDef tier3 fill:#581c87,stroke:#d946ef,stroke-width:2px,color:#fff
    classDef tier4 fill:#713f12,stroke:#fbbf24,stroke-width:2px,color:#fff
    classDef check fill:#374151,stroke:#9ca3af,stroke-width:1px,color:#d1d5db

    PAGE["PDF Page"]
    CHECK{"Text >= 50<br/>characters?"}:::check

    PAGE --> CHECK
    CHECK -->|"Yes"| SKIP["Skip OCR<br/>Use Raw Text"]
    CHECK -->|"No — Scanned/Image"| T1

    T1["Tier 1: Tesseract<br/>(Local, Free, Instant)"]:::tier1
    T1_OK{"Good<br/>Output?"}:::check
    T1 --> T1_OK
    T1_OK -->|"Yes"| DONE["Text Extracted"]
    T1_OK -->|"No / Not Installed"| T2

    T2["Tier 2: OCR.space API<br/>(Cloud OCR, Free Tier)"]:::tier2
    T2_OK{"Good<br/>Output?"}:::check
    T2 --> T2_OK
    T2_OK -->|"Yes"| DONE
    T2_OK -->|"No / Rate Limited"| T3

    T3["Tier 3: Groq Vision<br/>(Multimodal LLM)"]:::tier3
    T3_OK{"Good<br/>Output?"}:::check
    T3 --> T3_OK
    T3_OK -->|"Yes"| DONE
    T3_OK -->|"No"| T4

    T4["Tier 4: Gemini Vision<br/>(Deep Reasoning VLM)"]:::tier4
    T4 --> DONE
```

> **Fraud Detection Bonus:** Tiers 3 & 4 (Vision LLMs) don't just extract text — they also perform a **Multimodal Fraud Audit**, detecting signs of image manipulation, pixel inconsistencies, and suspicious formatting.

---

## Risk Radar & Agentic Research

The Risk Radar module runs **static compliance checks** on every extracted record, and conditionally triggers **autonomous web research** for high-risk documents:

```mermaid
graph TD
    classDef risk fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#fff
    classDef agent fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#fff
    classDef safe fill:#166534,stroke:#22c55e,stroke-width:2px,color:#fff
    classDef check fill:#374151,stroke:#9ca3af,stroke-width:1px,color:#d1d5db

    RECORD["Extracted Record"]

    RECORD --> R1["Missing Critical Info?<br/>(Vendor, Amount)"]
    RECORD --> R2["Suspicious Email Domain?<br/>(Gmail on B2B Invoice)"]
    RECORD --> R3["Collusion Graph Check<br/>(Shared addresses/phones)"]

    R1 --> LEVEL{"Risk Level?"}:::check
    R2 --> LEVEL
    R3 --> LEVEL

    LEVEL -->|"Low"| SAFE["Auto-Approve<br/>+ Mock ERP Sync"]:::safe
    LEVEL -->|"Medium"| FLAG["Flag for Review"]:::risk
    LEVEL -->|"High"| AGENT_TRIGGER

    subgraph "AGENT_TRIGGER [Autonomous Agent Research]"
        A1["Tavily Search<br/>(AI-Optimized)"]:::agent
        A2["Serper.dev<br/>(Google Search)"]:::agent
        A3["Gemini Grounding<br/>(Last Resort)"]:::agent
        A1 -->|"Failed"| A2 -->|"Failed"| A3
    end

    AGENT_TRIGGER --> VERDICT["Final Verdict<br/>+ Evidence Report"]:::risk
```

### What the Agent Researches

When triggered, the agent autonomously searches for:
- **Company legitimacy** — Does this vendor have a real website?
- **Shell company indicators** — Zero online presence is a massive red flag
- **Regulatory actions** — Any lawsuits, recalls, or sanctions?

Results are appended to the document record with full provenance and source URLs.

---

## Models Used

Specialized models are selected for different stages to optimize for the exact task:

| Stage | Model | Provider | Why This Model? |
|-------|-------|----------|----------------|
| **Structured Extraction** | `gpt-oss-20b` | Groq LPU | Ultra-fast JSON schema adherence at ~800 tok/s |
| **Fallback & Reasoning** | `gemini-2.5-flash` | Google AI | Deep reasoning for complex risk analysis and reports |
| **Local Vision & OCR** | `Qwen2-VL-2B-Instruct-AWQ` | vLLM (Local) | Best open-source VLM at 2B params, runs on 6GB VRAM |
| **Text Embeddings** | `nomic-embed-text-v1.5` | Local (sentence-transformers) | Outperforms OpenAI ada-002, fully local |
| **Image Embeddings** | `nomic-embed-vision-v1.5` | Local (transformers) | Visual similarity matching for product images |
| **RAG Chat Agent** | `gpt-oss-20b` | Groq LPU | Fast conversational responses grounded in user data |

---

## Tech Stack

### Frontend
| Technology | Purpose |
|-----------|---------|
| **Next.js 14** (App Router) | React framework with SSR and file-based routing |
| **TailwindCSS** | Utility-first styling with dark mode |
| **Recharts** | Interactive charts (category distribution, confidence gauges) |
| **SSE (EventSource)** | Real-time pipeline progress streaming |

### Backend
| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Async Python API framework |
| **SQLAlchemy 2.0** (async) | ORM with PostgreSQL (Railway) / SQLite (local) |
| **JWT + bcrypt** | Stateless authentication and password hashing |
| **WeasyPrint** | PDF report generation from HTML/Markdown |

### AI-ML Engine
| Technology | Purpose |
|-----------|---------|
| **LiteLLM** | Unified interface to 100+ LLM providers |
| **Instructor** | Schema-enforced structured output via Pydantic |
| **LangGraph** | Stateful RAG agent with `retrieve -> generate` graph |
| **Polars** | Lightning-fast DataFrame processing for Excel catalogs |
| **PyMuPDF** | PDF text and image extraction |
| **Pytesseract** | Local OCR engine |
| **ChromaDB** | Vector store for semantic search and embeddings |
| **vLLM** | High-throughput local LLM serving with PagedAttention |

### Infrastructure
| Technology | Purpose |
|-----------|---------|
| **Railway** | Cloud deployment (Backend + PostgreSQL + AI-ML) |
| **Vercel** | Frontend deployment (Next.js optimized) |
| **Docker Compose** | Local multi-service orchestration |
| **Pinggy SSH** | Zero-config public URL tunneling for demos |

---

## Running Online (Cloud Deployment)

The live production instance runs on **Railway** with automatic deploys from the `main` branch.

**Environment Variables Required:**

```env
# LLM Providers
GROQ_API_KEY=gsk_xxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxx

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Security
SECRET_KEY=your-random-secret-key
HMAC_KEY=your-hmac-key

# Agentic Research (Optional)
TAVILY_API_KEY=tvly-xxxxxxxxxxxx
SERPER_API_KEY=xxxxxxxxxxxx
```

### Quick Local Start (No GPU Required)

```bash
# 1. Clone and install
git clone https://github.com/Vk2245/AlchemyAI.git
cd AlchemyAI

# 2. Backend
cd DEV/backend
pip install -r ../../AI-ML/requirements.txt
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 6104 --reload

# 3. Frontend (new terminal)
cd DEV/frontend
npm install
npm run dev
```

> **Note:** Without a GPU or vLLM, the system automatically uses Groq/Gemini cloud APIs for all AI tasks.

---

## Running Offline (Local vLLM — Zero Cost, Air-Gapped)

For environments that require **zero data egress** (government, defense, healthcare), Alchemy AI can run entirely offline using a local GPU.

### Prerequisites

| Component | Requirement |
|-----------|------------|
| **OS** | Windows 10/11 with WSL2, or native Linux |
| **GPU** | NVIDIA GPU with >=6GB VRAM (RTX 3050, 3060, 4060, etc.) |
| **CUDA** | CUDA 12.x + cuDNN installed |
| **Python** | 3.10 or 3.11 |
| **Tesseract** | Optional — for Tier 1 local OCR |

### Step 1: Install vLLM in WSL2

```bash
# Enter your WSL2 Ubuntu environment
wsl

# Create a dedicated Python environment
python3 -m venv ~/vllm-env
source ~/vllm-env/bin/activate

# Install vLLM with CUDA support
pip install vllm

# Verify GPU access
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"
```

### Step 2: Download & Serve the Model

AWQ 4-bit quantized models are used to fit powerful LLMs within consumer GPU memory:

```bash
# Serve the text extraction model (fits in 4GB VRAM)
vllm serve Qwen/Qwen2.5-3B-Instruct-AWQ \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 8192 \
    --quantization awq \
    --gpu-memory-utilization 0.85 \
    --enable-auto-tool-choice
```

For **Vision OCR** (requires ~6GB VRAM):

```bash
# Serve the vision model on a separate port
vllm serve Qwen/Qwen2-VL-2B-Instruct-AWQ \
    --host 0.0.0.0 \
    --port 8001 \
    --max-model-len 4096 \
    --quantization awq \
    --trust-remote-code
```

### Step 3: Install Local OCR (Tesseract)

```bash
# Ubuntu/WSL2
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng

# Verify
tesseract --version
```

For Windows (native):
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Add to PATH: `C:\Program Files\Tesseract-OCR`
3. Set env var: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

### Step 4: Install Python Dependencies

```bash
# Core AI-ML dependencies
pip install -r AI-ML/requirements.txt

# Local-specific dependencies
pip install pytesseract Pillow torch torchvision sentence-transformers
```

### Step 5: Configure for Offline Mode

Update your `.env` file:

```env
# Point to your local vLLM server
VLLM_BASE_URL=http://127.0.0.1:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-3B-Instruct-AWQ

# Set local as the default (no cloud calls)
DEFAULT_PROVIDER=vllm
VISION_PROVIDER=vllm

# Remove or leave blank to prevent any cloud calls
GROQ_API_KEY=
GEMINI_API_KEY=

# Database (local SQLite)
DATABASE_URL=sqlite+aiosqlite:///./catalogx.db
```

### Step 6: Start Everything

```bash
# Terminal 1: vLLM server (in WSL2)
vllm serve Qwen/Qwen2.5-3B-Instruct-AWQ --host 0.0.0.0 --port 8000 ...

# Terminal 2: FastAPI backend (in Windows PowerShell)
cd DEV\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 6104

# Terminal 3: Next.js frontend
cd DEV\frontend
npm run dev
```

### Offline Architecture Flow

```mermaid
graph LR
    classDef local fill:#166534,stroke:#22c55e,stroke-width:2px,color:#fff
    classDef app fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#fff

    subgraph "Your Machine (Zero Internet)"
        FE["Next.js<br/>localhost:3000"]:::app
        BE["FastAPI<br/>localhost:6104"]:::app
        VLLM["vLLM Server<br/>localhost:8000"]:::local
        TESS["Tesseract OCR<br/>(Local Binary)"]:::local
        EMBED["Nomic Embeddings<br/>(sentence-transformers)"]:::local
        DB["SQLite<br/>(Local File)"]:::local
    end

    FE -->|"HTTP"| BE
    BE -->|"OpenAI API"| VLLM
    BE -->|"subprocess"| TESS
    BE -->|"Python"| EMBED
    BE -->|"SQLAlchemy"| DB
```

> **Zero Internet Required:** In offline mode, ALL processing happens on your local machine. No API calls, no data leaves your network. Perfect for classified or sensitive documents.

---

## Project Structure

```
AlchemyAI/
|-- AI-ML/                          # AI-ML Engine (25+ modules)
|   |-- agent/                      #   LangGraph RAG chatbot + web research
|   |   |-- chat_agent.py           #     Stateful RAG agent (retrieve -> generate)
|   |   +-- web_research.py         #     3-tier autonomous vendor research
|   |-- confidence/                 #   Confidence scoring
|   |   +-- score_record.py         #     Weighted record-level scoring
|   |-- config/                     #   Configuration layer
|   |   |-- settings.py             #     Central settings, paths, provider keys
|   |   |-- llm_client.py           #     Unified LLM client with fallback chains
|   |   +-- toon_utils.py           #     Token optimization utilities
|   |-- extraction/                 #   Structured data extraction
|   |   |-- schema_models.py        #     Pydantic models (DocumentRecord, Entity)
|   |   |-- extract_attributes.py   #     Schema-first attribute extraction
|   |   +-- extract_entities.py     #     Adaptive NER with dynamic schemas
|   |-- ingestion/                  #   Document ingestion
|   |   |-- parse_pdf.py            #     PyMuPDF page extraction
|   |   |-- ocr_fallback.py         #     4-tier OCR escalation chain
|   |   +-- evidence_builder.py     #     Evidence assembly (markdown + tables)
|   |-- pipeline/                   #   Orchestration
|   |   |-- run.py                  #     Master pipeline (9-stage PDF)
|   |   +-- unilog_enrichment.py    #     Bulk Excel enrichment pipeline
|   |-- report/                     #   Report generation
|   |   +-- generate_report.py      #     AI narrative + markdown -> PDF/HTML
|   |-- risk_radar/                 #   Risk & compliance
|   |   |-- detect_risk.py          #     Static risk checks + email validation
|   |   +-- collusion_graph.py      #     Cross-document collusion detection
|   |-- onepager/                   #   One-pager rendering
|   |   +-- render_output.py        #     HTML/PDF rendering via WeasyPrint
|   |-- taxonomy/                   #   Classification
|   |-- knowledge/                  #   Knowledge base & vector store
|   |-- memory/                     #   Conversation memory
|   +-- requirements.txt
|
|-- DEV/                            # Application Layer
|   |-- backend/                    #   FastAPI Backend
|   |   |-- app/
|   |   |   |-- main.py             #     App entry point + CORS + lifespan
|   |   |   |-- api/
|   |   |   |   |-- auth.py         #     JWT registration + login
|   |   |   |   |-- process.py      #     Upload + SSE processing orchestrator
|   |   |   |   |-- records.py      #     CRUD for document records + PDF export
|   |   |   |   |-- chat.py         #     LangGraph chat endpoint (streaming)
|   |   |   |   +-- review.py       #     Human-in-the-loop review API
|   |   |   |-- core/
|   |   |   |   |-- database.py     #     Async SQLAlchemy engine + sessions
|   |   |   |   +-- security.py     #     JWT encode/decode + password hashing
|   |   |   +-- models/
|   |   |       +-- models.py       #     SQLAlchemy ORM models
|   |   +-- Dockerfile
|   |
|   +-- frontend/                   #   Next.js 14 Frontend
|       |-- src/app/
|       |   |-- page.tsx            #     Landing page + file upload
|       |   |-- dashboard/          #     Main dashboard (records table)
|       |   |-- process/            #     Real-time processing view (SSE)
|       |   |-- record/             #     Individual record detail view
|       |   |-- review/             #     Human review panel
|       |   |-- chat/               #     RAG chatbot interface
|       |   |-- admin/              #     Admin panel
|       |   |-- login/              #     Auth pages
|       |   +-- register/
|       |-- src/components/         #     Reusable UI components
|       +-- Dockerfile
|
|-- docker-compose.yml              # Multi-service orchestration
|-- .env.example                    # Environment variable template
+-- README.md                       # This file
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and receive JWT token |
| `POST` | `/api/upload` | Upload a PDF or Excel file |
| `GET` | `/api/process/{doc_id}` | SSE stream — real-time pipeline progress |
| `GET` | `/api/records` | List all processed document records |
| `GET` | `/api/records/{doc_id}` | Get detailed record for a document |
| `GET` | `/api/records/{doc_id}/pdf` | Download the generated PDF report |
| `POST` | `/api/chat` | Send a message to the RAG chatbot |
| `PUT` | `/api/review/{record_id}` | Submit human review corrections |

---

## Sharing Publicly (Pinggy SSH Tunnels)

For demos without cloud deployment, use secure SSH tunnels:

```bash
# Terminal 1: Start backend
cd DEV/backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 6104

# Terminal 2: Expose backend
ssh -p 443 -R0:127.0.0.1:6104 a.pinggy.io

# Terminal 3: Start frontend (update .env with Pinggy URL first)
cd DEV/frontend && npm run dev

# Terminal 4: Expose frontend
ssh -p 443 -R0:127.0.0.1:3000 a.pinggy.io
```

> [!WARNING]
> Do not close any of the 4 terminals while sharing. The public URLs go offline immediately if the SSH tunnels are terminated.

---

<div align="center">

**Alchemy AI — Transforming Chaos into Intelligence**

</div>
