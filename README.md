# Explainable LLM Summarizer

[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)

> **Compliance-grade summarization with transparent sentence-level evidence mapping.**

`explainable-summarizer` is a Python toolkit and CLI microservice that transforms long PDF or text documents into concise, executive-ready bullet summaries, each paired with precise citations to the original sentences. Ideal for regulated industries (finance, insurance, legal) where auditability and explainability are mandatory.

---

## 🚩 Key Features

- **Explainability-first**: Each bullet point lists the exact sentence indices that support its claim.
- **Dual backends**: Seamlessly switch between OpenAI GPT-4o-mini (cloud) and Llama 3.2 (local via Ollama).
- **Flexible inputs**: Accepts local `.pdf`/`.txt` files or in-memory uploads (e.g., Streamlit, STDIN).
- **Cost- & resource-aware**: Cloud usage stays within low-cost GPT-4o-mini rates; local Llama runs offline on consumer hardware.
- **Bilingual-ready**: Optional EN↔FR translation layer (planned in v1.0).

---

## 🧰 Installation

This project uses **Poetry** for dependency management and packaging. Ensure you have Python 3.10+ and Poetry installed.

```bash
# Clone the repo and install dependencies
git clone https://github.com/your-handle/llm-evidence-summarizer.git
cd llm-evidence-summarizer
poetry install
poetry shell
```

> **Note:** We do not support `pip install .`—please use Poetry throughout.

---

## ⚙️ Configuration

Set up your environment variables before running the CLI or Python API:

```bash
# For GPT-4o-mini (cloud)
export OPENAI_API_KEY="sk-..."

# For Ollama (local Llama)
# Only if you run Ollama under a custom host or port
export OLLAMA_BASE_URL="http://localhost:11434/v1"
```

---

## 🚀 Quickstart

### CLI Usage

```bash
# Summarize with GPT-4o-mini (cloud)
poetry run summarize --backend gpt4o --file path/to/document.pdf

# Summarize with Llama 3.2 (local via Ollama)
# Ensure Ollama is running:
ollama pull llama3.2:8b-chat
ollama run llama3.2:8b-chat &
poetry run summarize --backend llama --file path/to/document.pdf
```

**Sample Output**:
```json
[
  {
    "bullet": "Institutions must maintain a tier-one capital buffer equal to 2.5% of risk-weighted assets.",
    "evidence_ids": [2]
  },
  {
    "bullet": "OSFI will assess compliance starting January 1, 2026.",
    "evidence_ids": [3]
  }
]
```

### Python API

```python
from summarizer.pipeline import summarize

# From a file path
summary = summarize("docs/guideline.pdf", backend="gpt4o")
print(summary)

# From an uploaded file-like object (e.g., Streamlit)
# uploaded = st.file_uploader(...)
# summary = summarize(uploaded, backend="llama")
# st.write(summary)
```

### Streamlit Demo

You can spin up a quick web UI to upload files and inspect summaries:

```python
# demo_app.py
import streamlit as st
from summarizer.pipeline import summarize

st.title("Explainable LLM Summarizer")
file = st.file_uploader("Upload PDF or TXT", type=["pdf","txt"])
backend = st.selectbox("Backend", ["gpt4o","llama"]);
if file and st.button("Summarize"):
    result = summarize(file, backend=backend)
    st.json(result)
```

```bash
poetry run streamlit run demo_app.py
```

---

## 🔍 How It Works

1. **Text Extraction**: `_extract_text` reads local files or file-like streams and uses `pdfplumber` for PDFs.
2. **Sentence Numbering**: The `extract.txt` prompt labels each sentence with a 1-based index without altering content.
3. **Summarization & Citation**: The `abstract.txt` prompt produces up to 8 bullet points, appending `| id1,id2` after each.
4. **Parsing**: A simple regex converts the LLM’s bullet list into a JSON array of `{ bullet, evidence_ids }`.
5. **Backend Switch**: Both GPT-4o-mini and Ollama Llama are driven via the same OpenAI-compatible client—only the `base_url` and `model` parameters differ.

---

## 🌟 Roadmap

- **v1.0**: Add EN↔FR translation layer, improve chunking and caching, include performance dashboard.
- **v1.1**: Support DOCX ingestion, audio transcript summaries, configurable bullet count.
- **v2.0**: Deploy a hosted web UI (e.g., Hugging Face Space), plugin architecture for domain-specific prompts.

---

## 🏗️ Scalable Architecture
Below is an AWS‑based deployment sketch showing how the pipeline could run at scale:

<img src="./system_architecture.svg" alt="Screenshot" width="400"/>

### How Each AWS Component Fits In

| Layer | AWS service | What it does for this project |
|-------|-------------|--------------------------------|
| **Clients** | *N/A* | CLI scripts and the Streamlit web UI send `POST /summarize` requests to the public endpoint. |
| **API entry** | **API Gateway** | Provides a secure HTTPS endpoint that triggers Lambda. Handles auth (e.g., IAM roles / API keys) and rate‑limiting. |
| **Text extraction** | **Lambda (Text Extraction)** | Runs the `_extract_text` routine (pdfplumber/DOCX, etc.) on the raw upload and stores the raw text into **S3 Raw Documents**. Scales to thousands of concurrent files without servers. |
| **Storage (raw)** | **S3 ‘Raw Documents’ bucket** | Durable storage for original uploads. Versioning lets you re‑process later. |
| **Sentence numbering** | **Lambda (Sentence Numbering)** | Calls the `extract.txt` prompt via the selected LLM backend, stores the numbered text in memory, then hands off to the next Lambda. |
| **LLM summarization** | **Lambda (Summarization & Citation)** | Invokes either GPT‑4o‑mini (over the internet) or the **Llama 3.2** container running in ECS/EKS, using the `abstract.txt` prompt. Writes the bullet + evidence map to **S3 Summaries** and DynamoDB. |
| **Model hosting** | **OpenAI GPT‑4o‑mini** | Fully managed; pay‑per‑token. Ideal for low‑latency / high‑accuracy calls. |
| | **ECS/EKS (Llama 3.2)** | Optional self‑hosted alternative. You build a Docker image with the GGUF model and expose it via Ollama’s OpenAI‑compatible API.  Scales horizontally with Fargate or node autoscaling. |
| **Storage (results)** | **S3 ‘Summaries’ bucket** | Stores JSON outputs for later download or audit. Triggers an EventBridge rule (optional) to invalidate CloudFront cache. |
| **Cache / metadata** | **DynamoDB** | Quick key‑value look‑ups: `document_id → latest_summary`, stores token counts, cost, and evidence mapping for dashboards. |
| **Delivery** | **CloudFront CDN** | Speeds up downloads of summary files or embedded PDFs for global users. |
| **Observability** | **CloudWatch Logs & Metrics** | Each Lambda writes a log; you can create dashboards for throughput, duration, and cost.  Alarms can notify you when token spend crosses a threshold. |

> **Tip for learning**: start by deploying just the *Text Extraction* and *Summarization* Lambdas behind API Gateway. Once that round‑trip works, layer in S3 for persistence and CloudWatch for metrics. Add ECS/EKS only if you truly need an on‑prem model. This incremental path keeps AWS costs and complexity low while still mirroring an enterprise‑ready architecture.


## 🤝 Contributing

Contributions are welcome! Please fork the repo, create a feature branch, and open a pull request with a clear description of your changes.

---

## 📄 License

This project is released under the **MIT License**. See the `LICENSE` file for more details.
