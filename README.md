# Voice-Enabled Agentic RAG

A modular, local Retrieval-Augmented Generation (RAG) pipeline for multi-domain document Q&A, featuring PDF cleaning, adaptive markdown chunking, FAISS vector indexing, multi-agent retrieval, and both text and voice CLI interfaces.

---

## 📝 Project Description

This project enables advanced question answering over multiple expert domains (AI, Cybersecurity, Digital Health, Human Development, Renewable Energy Jobs) using a local RAG pipeline. It processes PDFs into cleaned markdown, chunks them into embedding-ready passages, builds FAISS vector indices per agent, and serves queries via a multi-agent router. You can interact via a text CLI or a voice CLI (Deepgram-powered).

**Key Features:**
- PDF → cleaned markdown → chunked passages → FAISS vector store
- Multi-agent RAG runtime with agent registry
- Text CLI and Deepgram-based voice CLI
- Modular pipeline: cleaning, chunking, indexing, retrieval
- Extensible to new domains and function agents (weather, finance, etc.)

---

## 📂 Project Structure

```
voice-enabled-ai-agent/
├─ .env                      # API keys and config
├─ README.md                 # This file
├─ requirements.txt          # Python dependencies
├─ clean_pdfs.py             # PDF cleaning pipeline
├─ chunking.py               # Markdown chunking utilities
├─ create_faiss_store.py     # Embedding + FAISS index creation
├─ langchain_groq_rag.py     # RAG runtime and agent router
├─ function_agents.py        # Live/function agents (weather, finance)
├─ cli_chat.py               # Text CLI interface
├─ voice_cli.py              # Voice CLI (Deepgram STT/TTS)
├─ cleaned_texts/            # Cleaned markdown outputs
├─ chunks/                   # Chunk outputs, stats, per-chunk files
│   ├─ chunks.json           # All chunks (JSON)
│   ├─ chunks.jsonl          # All chunks (JSONL)
│   ├─ chunks.csv            # All chunks (CSV)
│   ├─ chunking_statistics.json
│   └─ chunks_txt/           # Individual chunk text files
├─ extracted_pdfs/           # Source PDFs
├─ vector_store/             # FAISS indices and agent_registry.json
│   └─ agents/               # Per-agent FAISS index folders
└─ voice_history/            # Generated TTS audio files
```

---

## 🛠 Prerequisites

- Python **3.10+**
- [Install dependencies](#installation--setup) via `requirements.txt`
- API keys:
  - `GROQ_API_KEY` (LLM, required)
  - `DEEPGRAM_API_KEY` (voice CLI, required for TTS/STT)
  - `TAVILY_API_KEY` (optional, for live function agents)
  - `VECTOR_STORE_DIR` (optional, override vector store path)

---

## ⚙️ Installation & Setup

### 1. Clone the repo
```bash
git clone <your-repo-url>
cd voice-enabled-ai-agent
```

### 2. Create and activate a virtual environment
```bash
python -m venv _env
# Windows:
_env\Scripts\activate
# macOS/Linux:
source _env/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API keys
Create a `.env` file at project root:
```ini
GROQ_API_KEY=sk-xxxxxxxx
DEEPGRAM_API_KEY=dg-xxxxxxxx
TAVILY_API_KEY=tv-xxxxxxxx   
```

---

## 📄 Data Preparation

### 1. Place PDFs
Copy your source PDFs into `extracted_pdfs/`. Example files:
- Artificial_Intelligence.pdf
- Cybersecurity.pdf
- Digital_Health.pdf
- Human_Development.pdf
- Renewable_Energy_Jobs.pdf

### 2. Clean PDFs → Markdown
Run the PDF cleaning pipeline:
```bash
python clean_pdfs.py
```
- Outputs cleaned markdown files to `cleaned_texts/`
- Auto-detects document type and applies custom cleaning heuristics

### 3. Chunk Markdown
Chunk cleaned markdown into embedding-ready passages:
```bash
python chunking.py
```
- Outputs: `chunks/chunks.json`, `chunks.jsonl`, `chunks.csv`, `chunks_txt/`, `chunking_statistics.json`
- Chunk sizes/config can be adjusted in `MarkdownChunker.default_config()` in [chunking.py](chunking.py)

### 4. Build FAISS Indices
Generate embeddings and build FAISS indices per agent:
```bash
python create_faiss_store.py
```
- Outputs: `vector_store/agents/` (FAISS indices), `vector_store/agent_registry.json`
- Embedding model and batch size configurable in [create_faiss_store.py](create_faiss_store.py)

---

## 🚀 End-to-End Running Guide

### 1. Prepare Environment
- Activate your virtualenv
- Ensure `.env` is set with required API keys

### 2. Data Pipeline
- Place PDFs in `extracted_pdfs/`
- Run `clean_pdfs.py` → check `cleaned_texts/`
- Run `chunking.py` → check `chunks/` and `chunking_statistics.json`
- Run `create_faiss_store.py` → check `vector_store/` and `agent_registry.json`

### 3. Start Text CLI
```bash
python cli_chat.py
```
- Interact with the multi-agent RAG system via terminal
- Supports `/help`, `/agents`, `/history`, `/stats`, `/exit` commands

### 4. Start Voice CLI (requires Deepgram API key)
```bash
python voice_cli.py
```
- Speak or provide audio files for Q&A
- Responses are converted to audio and saved in `voice_history/`

---

## 🧠 RAG Runtime & Agents

- **UnifiedAgentSystem** in [langchain_groq_rag.py](langchain_groq_rag.py) loads `vector_store/agent_registry.json` and serves `.query(user_query)`
- **AgentRetriever** utilities in [create_faiss_store.py](create_faiss_store.py) for retrieval inspection
- **Function agents** (weather, finance) in [function_agents.py](function_agents.py)

---

## 🗂 References & Outputs

- Cleaned markdown: [cleaned_texts/Artificial_Intelligence.md](cleaned_texts/Artificial_Intelligence.md)
- Chunks: [chunks/chunks.json](chunks/chunks.json), [chunks/chunks_txt/](chunks/chunks_txt/)
- Vector registry: [vector_store/agent_registry.json](vector_store/agent_registry.json)
- Voice history: [voice_history/](voice_history/)

---

## 🐞 Troubleshooting

- **Missing API keys:** Scripts will error if required keys are absent—set them in `.env` or your environment.
- **Chunking:** Falls back to char-estimation if `tiktoken` is not installed.
- **FAISS:** On Windows, install `faiss-cpu` or platform-specific wheel; GPU variants need GPU-compatible packages.
- **Embeddings:** Change embedding model / batch size in `create_faiss_store.py` to reduce memory use.

---

## 💡 Extending & Customizing

- Add new PDFs to `extracted_pdfs/` and rerun the pipeline
- Add new agent definitions in [create_faiss_store.py](create_faiss_store.py)
- Modify chunking logic in [chunking.py](chunking.py)
- Add new function agents in [function_agents.py](function_agents.py)

---

