# Nyaya Darshan

**AI-powered Legal Intelligence Operating System for Indian Law**

**Nyaya Darshan** combines authoritative Indian statutory retrieval, evidence-grounded legal answers, verification safeguards, and a configurable NVIDIA-hosted language model. The repository also includes an experimental legal-model training pipeline; a production-ready fine-tuned model should not be assumed until its weights and evaluation results have been verified.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (recommended)
- **NVIDIA API key** for live AI-generated legal responses
- **Tesseract OCR** — [download here](https://github.com/UB-Mannheim/tesseract/wiki) (optional, for scanned PDFs)

### 1. Install Dependencies

```powershell
cd "D:\Nyaya Darshan"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```powershell
copy .env.example .env
# Edit .env with your settings
```

**For NVIDIA NIM (cloud API):**
```
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-key
NVIDIA_LLM_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1
NYAYA_JWT_SECRET=replace-with-a-random-secret-of-at-least-32-characters
```

### 3. Start the Server

```powershell
python run.py
```

### 4. Open Nyaya Darshan

Navigate to **http://localhost:8000** in your browser.

---

## 🏗️ Architecture

```
Nyaya Darshan
├── app/                          # FastAPI web application
│   ├── main.py                   # App entry point + lifespan
│   ├── config.py                 # Environment & path config
│   ├── database.py               # SQLite schema (11 tables)
│   ├── models.py                 # Pydantic request/response schemas
│   ├── routers/                  # API endpoints
│   │   ├── vault.py              # Knowledge Vault (upload, search, CRUD)
│   │   ├── chat.py               # AI Chat with RAG
│   │   ├── classifier.py         # Document classification
│   │   ├── dashboard.py          # Dashboard & analytics
│   │   ├── knowledge_graph.py    # Citation network
│   │   └── proactive.py          # Compliance gaps & deadlines
│   ├── intelligence/             # AI brain modules
│   │   ├── summarizer.py         # Document summaries & briefings
│   │   ├── clause_detector.py    # Legal clause detection
│   │   ├── risk_scorer.py        # Risk analysis
│   │   ├── knowledge_graph.py    # Citation graph builder
│   │   ├── deadline_extractor.py # Date/deadline extraction
│   │   └── search_engine.py      # Enhanced semantic search
│   └── static/
│       └── index.html            # Nyaya Darshan frontend
│
├── Indian Legal/                 # Backend engines (existing, unmodified)
│   ├── gyana_darshan_rag_nvidia.py  # FAISS + BM25 hybrid RAG
│   ├── gyana_darshan_classifier.py  # 36-category legal classifier
│   ├── gyana_darshan_corpus_builder.py  # PDF → text pipeline
│   ├── raw/                      # Uploaded PDFs
│   ├── processed_corpus/         # Processed text chunks
│   ├── Category/                 # Classified documents
│   └── nova_rag_index/           # FAISS vector index
│
├── training/                     # Experimental Nyaya Darshan training pipeline
│   ├── generate_dataset.py       # Generate training data from corpus
│   ├── finetune_colab.py         # QLoRA fine-tuning (Google Colab)
│   ├── evaluate.py               # Indian Legal Benchmark
│   └── README.md                 # Training documentation
│
├── requirements.txt
├── run.py
├── .env.example
└── README.md                     # ← You are here
```

## 🧠 Intelligence Features

| Feature | Description |
|---------|-------------|
| **RAG-Powered Chat** | Ask questions about Indian law — answers cite specific sections and pages |
| **Streaming Responses** | See the AI think in real-time with reasoning chain visualization |
| **Smart Document Processing** | Upload a PDF → auto-classify, extract entities, detect clauses, score risk |
| **Knowledge Graph** | Documents auto-link via shared citations and section references |
| **Semantic Search** | Natural language search: "contracts about data protection from 2023" |
| **Proactive Alerts** | Compliance gaps, outdated references, and deadline tracking |
| **AI Daily Briefing** | Dashboard shows AI-generated summary of your corpus state |

## 🎓 Experimental Model Training

See [training/README.md](training/README.md) for complete instructions on:
1. Generating training data from your legal corpus
2. Fine-tuning Phi-3.5-mini on Google Colab (free)
3. Evaluating on the Indian Legal Benchmark
4. Comparing adapter quality against the existing grounded retrieval baseline

The training pipeline is experimental. Do not advertise a proprietary fine-tuned production model unless the model weights, evaluation results, and deployment are independently verified.

## 📡 API Reference

Once running, visit **http://localhost:8000/docs** for the interactive Swagger API documentation.

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vault/upload` | POST | Upload a PDF for processing |
| `/api/vault/documents` | GET | List all documents |
| `/api/vault/search` | POST | Semantic search |
| `/api/chat/ask` | POST | Ask a legal question |
| `/api/chat/ask/stream` | POST | Streaming RAG response |
| `/api/dashboard/stats` | GET | Dashboard statistics |
| `/api/dashboard/briefing` | GET | AI daily briefing |
| `/api/graph/network` | GET | Citation network data |
| `/api/proactive/compliance-gaps` | GET | Compliance gap analysis |

## Production deployment

`render.yaml` defines a Python 3.11 service with an attached persistent disk for
SQLite databases, uploads, and application logs. **Render persistent disks and
the web-service plan that supports them are paid features**; do not deploy this
configuration on an ephemeral free instance if conversations or uploads must
survive restarts. Configure `NVIDIA_API_KEY` and explicit HTTPS
`ALLOWED_ORIGINS` in Render before deployment. The blueprint generates separate
`NYAYA_API_KEY` and `NYAYA_JWT_SECRET` values automatically. Set both Razorpay
credentials together only when payment processing is enabled.

The deployment runs these release gates automatically:

```bash
python scripts/release_preflight.py --repository-only
python scripts/release_preflight.py --environment-only
```

The first checks deployment files and secret exclusions without requiring live
credentials; the second fails startup on missing secrets, insecure origins,
unsupported providers, or incomplete payment configuration. GitHub Actions
installs the full dependency set and runs statutory, deployment, authentication,
authorization, legal-generation, and application regression suites.

For Docker, mount persistent storage at `/var/lib/nyaya`, pass secrets through
your hosting platform, and expose the configured `PORT`. The image runs as an
unprivileged user and checks `/health` automatically.

## 📄 License

Nyaya Darshan application code and project-specific legal datasets are proprietary. Any future fine-tuned model remains subject to the selected base model's license and independently verified training results.

---

*Built with ❤️ for Indian Legal Intelligence*
