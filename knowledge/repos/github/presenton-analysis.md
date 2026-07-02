# Presenton Analysis Report

**Repository**: https://github.com/presenton/presenton  
**Stars**: ~335 (GitHub trending)  
**License**: Apache 2.0  
**Date**: May 26, 2026  

---

## 1. Repository Overview

**Presenton** is a fully open-source AI-powered presentation generator positioned as a self-hosted alternative to SaaS platforms like Gamma, Beautiful.ai, and Decktopus. It enables users to generate professional presentations from prompts or documents using AI, with full control over models and data.

**Key selling points**:
- No SaaS lock-in — run entirely on your own infrastructure
- Self-hosted via Docker or native desktop app (Electron)
- Multi-model support: OpenAI, Google Gemini, Anthropic Claude, Vertex AI, Azure OpenAI, Amazon Bedrock, Ollama, LM Studio, and any OpenAI-compatible endpoint
- Built-in MCP (Model Context Protocol) server for AI agent integration
- Full PPTX export with professional formatting
- Template system with HTML/Tailwind CSS customization

---

## 2. Features

### Core Features
- **AI Presentation Generation**: Generate slides from text prompts or uploaded documents (PDF, DOCX)
- **Template System**: Create/modify presentation templates using HTML and Tailwind CSS
- **AI Template Generation**: Create templates from existing PowerPoint documents
- **Multi-Provider LLM Support**: 11+ model providers (OpenAI, Google, Vertex, Azure, Bedrock, Anthropic, Fireworks, Together AI, Ollama, LM Studio, Custom OpenAI-compatible)
- **Multi-Provider Image Generation**: DALL-E 3, Gemini Flash, Pexels, Pixabay, ComfyUI, Open WebUI, or any OpenAI-compatible image endpoint
- **MCP Server**: Built-in Model Context Protocol server for agentic workflows
- **Web Search Grounding**: Enable live web search for presentations (OpenAI, Google, Anthropic)
- **Presentation Memory**: Mem0 OSS integration for persistent context across presentation sessions
- **Document Parsing**: LiteParse OCR for PDF/image-to-content extraction
- **Export Formats**: PowerPoint (PPTX), PDF
- **Authentication**: Single admin account per instance with hashed credentials

### Desktop App Features
- Electron-based cross-platform desktop app (Windows, macOS, Linux)
- Local model execution via Ollama/LM Studio
- BYOK (Bring Your Own Key) for API-based providers
- No browser required — runs as native application

### Deployment Options
- **Docker**: Single-command deployment with GPU support
- **Cloud**: Railway, DigitalOcean one-click deploys
- **Desktop**: Native Electron app
- **API**: Self-hosted API service for team use

---

## 3. Architecture

### System Components

```
Presenton Architecture
├── Electron Desktop App
│   ├── TypeScript + Tailwind CSS UI
│   └── Bundled FastAPI backend + Next.js
├── Web Deployment (Docker)
│   ├── Next.js Frontend (Port 3000)
│   └── FastAPI Backend (Port 8000)
└── Services
    ├── Mem0 (Memory/Context)
    ├── LiteParse (Document OCR)
    └── MCP Server (Agent Integration)
```

### Backend (FastAPI + Python)
- **Framework**: FastAPI with SQLModel ORM
- **Database**: SQLite (default) or PostgreSQL/MySQL via DATABASE_URL
- **AI Integration**: OpenAI SDK, Google GenAI, Anthropic, Bedrock, etc.
- **Memory**: Mem0ai with Qdrant + SQLite (local vectors)
- **Document Processing**: LiteParse for OCR, pdfplumber for PDF parsing
- **Migrations**: Alembic for database schema management
- **Server**: Uvicorn ASGI server

### Frontend (Next.js + TypeScript)
- **Framework**: Next.js 14+ with App Router
- **Styling**: Tailwind CSS 4.x
- **State Management**: Zustand or similar
- **API Proxy**: Next.js proxies API calls to FastAPI backend

### Desktop App (Electron)
- **Main Process**: Node.js with TypeScript
- **Renderer**: Bundled Next.js app
- **IPC**: Electron IPC for native functionality
- **Build**: Electron Builder for cross-platform distribution

### Key Services

| Service | Purpose | Technology |
|---------|---------|------------|
| FastAPI Backend | REST API, business logic | Python 3.11, FastAPI, SQLModel |
| Next.js Frontend | Web UI | TypeScript, Next.js, Tailwind |
| Mem0 | Presentation memory/context | Qdrant + SQLite, spaCy |
| LiteParse | Document OCR | @llamaindex/liteparse |
| MCP Server | Agent protocol bridge | FastMCP, OpenAPI spec |
| Image Generation | Slide images | DALL-E, Gemini, Pexels, Pixabay |

---

## 4. Tech Stack

### Backend
- **Language**: Python 3.11
- **Framework**: FastAPI >= 0.116.1
- **ORM**: SQLModel (SQLAlchemy wrapper)
- **Database**: SQLite (default), PostgreSQL/MySQL (optional)
- **AI SDKs**: openai, google-genai, anthropic, boto3 (Bedrock)
- **Vector Store**: fastembed-vectorstore + Qdrant
- **Memory**: mem0ai[nlp] with spaCy
- **Document Parsing**: @llamaindex/liteparse, pdfplumber
- **Export**: python-pptx, fonttools, sharp (image processing)
- **MCP**: fastmcp >= 2.11.0

### Frontend
- **Framework**: Next.js 14+
- **Language**: TypeScript 5.x
- **Styling**: Tailwind CSS 4.x
- **Icons**: Custom vector store indexed icons
- **Image Processing**: Sharp (server-side)

### Desktop
- **Runtime**: Electron 42.x
- **Build Tool**: Electron Builder 26.x
- **Bundler**:esbuild for TypeScript

### Infrastructure
- **Container**: Docker + docker-compose
- **Deployment**: Railway, DigitalOcean App Platform
- **Authentication**: JWT-based sessions, bcrypt password hashing

---

## 5. Competitive Analysis

### Presenton vs SaaS Alternatives

| Feature | Presenton | Gamma | Beautiful.ai | Decktopus |
|---------|-----------|-------|---------------|------------|
| **License** | Apache 2.0 (open source) | Proprietary SaaS | Proprietary SaaS | Proprietary SaaS |
| **Self-hosted** | Yes (Docker/Desktop) | No | No | No |
| **Data Privacy** | Complete (local processing) | Limited (cloud) | Limited (cloud) | Limited (cloud) |
| **Model Providers** | 11+ (OpenAI, Google, Anthropic, Ollama, etc.) | Limited (built-in) | Limited (built-in) | Limited (built-in) |
| **LLM Customization** | Full BYOK support | No | No | No |
| **Local Models** | Ollama, LM Studio, custom | No | No | No |
| **PPTX Export** | Full editability | Limited | Limited | Limited |
| **MCP Server** | Built-in | No | No | No |
| **Template System** | Custom HTML/Tailwind | Proprietary | Proprietary | Proprietary |
| **API Access** | Full REST API | Limited | Limited | Limited |
| **Pricing** | Free (own infrastructure) | $15-30/user/mo | $15-30/user/mo | $10-20/user/mo |

### Competitive Advantages of Presenton

1. **No SaaS Lock-in**: Full control over infrastructure, data, and models
2. **Multi-Model Flexibility**: Use any LLM provider or local models
3. **MCP Integration**: Native support for AI agent workflows
4. **Memory System**: Mem0 integration for persistent context
5. **PPTX Export**: Truly editable PowerPoint output
6. **Template Ownership**: Create, modify, share templates freely

### Competitive Risks

1. **UX Maturity**: SaaS products have more polished UI/UX
2. **Maintenance Burden**: Self-hosted requires DevOps attention
3. **Feature Velocity**: SaaS competitors move faster on new features
4. **Enterprise Support**: No dedicated enterprise support tier mentioned

---

## 6. Why Presenton is Interesting for Hermes

### Strategic Alignment

1. **Agentic Workflow Integration**
   - Built-in MCP server enables direct AI agent interaction
   - Hermes could leverage Presenton as a document generation tool for agents
   - API-first design fits Hermes's tool-oriented architecture

2. **Local/Private Execution**
   - Matches Hermes's focus on local, private AI workflows
   - All processing can happen on-premise — no data leaves the system
   - Ollama/LM Studio support enables fully local presentation generation

3. **Document Generation Capability**
   - Hermes currently lacks a native presentation generator
   - Presenton fills this gap with a production-ready solution
   - Full PPTX export enables downstream editing

4. **Multi-Provider Flexibility**
   - Works with any LLM provider — aligns with Hermes's provider-agnostic approach
   - BYOK model support means users can use their own keys
   - No vendor lock-in

5. **Open Source Foundation**
   - Apache 2.0 license allows modification and integration
   - Active development (335+ stars, regular commits)
   - Community-driven improvements

### Potential Hermes Integrations

1. **Presentation Tool Skill**: Register Presenton as a Hermes skill for slide generation
2. **MCP Bridge**: Connect Hermes agents to Presenton's MCP server for dynamic presentation creation
3. **Template Library**: Pre-built Presenton templates for common presentation types
4. **Document Pipeline**: Use Presenton as the output format for research/summary agents

### Technical Considerations

- **API Complexity**: Presenton exposes a comprehensive REST API with authentication
- **Deployment Flexibility**: Can run as Docker container or standalone service
- **Dependencies**: Python 3.11 backend, Node.js frontend — compatible with Hermes stack
- **Resource Requirements**: Moderate (CPU sufficient, GPU optional for local models)

---

## 7. Summary

**Presenton** is a production-ready, open-source AI presentation generator that fills a significant gap in the tooling ecosystem. Its combination of multi-model support, MCP integration, self-hosted deployment, and PPTX export makes it highly relevant for Hermes.

**Key strengths**:
- Fully open-source (Apache 2.0)
- 11+ LLM provider support
- Built-in MCP server for agentic workflows
- Local/private execution capability
- Full PPTX export

**For Hermes, Presenton represents**:
- A turnkey presentation generation solution
- An MCP server that can be leveraged by agents
- A model-agnostic document generation backend
- A reference implementation for AI document tools

---

*Report generated: May 26, 2026*  
*Repository: presenton/presenton (GitHub trending, ~335 stars)*