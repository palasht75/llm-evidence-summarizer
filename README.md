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

This project uses **Poetry** for dependency management and packaging. Ensure you have Python 3.11+ and Poetry installed.

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
poetry run summarize --backend gpt4o --file path/to/document.txt

# Summarize with Llama 3.2 (local via Ollama)
# Ensure Ollama is running:
ollama pull llama3.2
ollama run llama3.2 &
poetry run summarize --backend llama --file path/to/document.txt
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

```

### Streamlit Demo

You can spin up a quick web UI to upload files and inspect summaries:

```bash
poetry run streamlit run app.py
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

## 🤝 Contributing

Contributions are welcome! Please fork the repo, create a feature branch, and open a pull request with a clear description of your changes.

---

## 📄 License

This project is released under the **MIT License**. See the `LICENSE` file for more details.
