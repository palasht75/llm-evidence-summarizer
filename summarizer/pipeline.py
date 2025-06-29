"""summarizer.pipeline
=====================
End‑to‑end pipeline that:
1. Extracts raw text from **.txt** / **.pdf** files **or from file‑like objects / bytes** (handy for web uploads).
2. Numbers every sentence via `prompts/extract.txt`.
3. Produces ≤ 8 bullet summaries with sentence‑ID evidence using
   `prompts/abstract.txt`.

Works with GPT‑4o‑mini (cloud) or Llama 3.2 via Ollama (local).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import IO, List, Dict, Literal, Union
from io import BytesIO, TextIOBase

from .backends import choose_backend, BaseBackend

# Optional PDF dependency
try:
    import pdfplumber  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    pdfplumber = None

# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------


def _load_prompt(name: Literal["extract", "abstract"]) -> str:
    """Return raw prompt text from prompts/ directory."""
    here = Path(__file__).with_suffix("").parent / "prompts"
    return (here / f"{name}.txt").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Text extraction (Path | str | bytes | file‑like)
# ---------------------------------------------------------------------------


Source = Union[str, Path, bytes, IO[bytes]]


def _extract_text(source: Source) -> str:
    """Return plain text from a variety of inputs.

    * **Path / str** – points to a .txt or .pdf file on disk.
    * **bytes / BytesIO / UploadedFile** – usually from a web upload.
    """

    # ----------------------------------------------------
    # Helper: dispatch once we know the file extension.
    # ----------------------------------------------------

    def _pdf_bytes_to_text(data: bytes) -> str:  # local helper
        if pdfplumber is None:
            raise ValueError("pdfplumber missing ‑ run `poetry add pdfplumber`.")
        with pdfplumber.open(BytesIO(data)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)

    # ----------------------------------------------------
    # Case 1 – Disk pathname
    # ----------------------------------------------------

    if isinstance(source, (str, Path)):
        path = Path(source)
        ext = path.suffix.lower()
        if ext == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        if ext == ".pdf":
            return _pdf_bytes_to_text(path.read_bytes())
        raise ValueError(f"Unsupported file extension: {ext}")

    # ----------------------------------------------------
    # Case 2 – Raw bytes (e.g., uploaded via web‑framework)
    # ----------------------------------------------------

    if isinstance(source, bytes):
        # Heuristic: if bytes start with %PDF‑, treat as PDF.
        if source[:4] == b"%PDF":
            return _pdf_bytes_to_text(source)
        return source.decode("utf-8", errors="ignore")

    # ----------------------------------------------------
    # Case 3 – File‑like object (BytesIO, Django/Flask file, Streamlit upload)
    #          Must support .read() and optionally .name
    # ----------------------------------------------------

    if hasattr(source, "read"):
        data = source.read()
        name = getattr(source, "name", "uploaded")
        if isinstance(name, str) and name.lower().endswith(".pdf") or data[:4] == b"%PDF":
            return _pdf_bytes_to_text(data)
        return data.decode("utf-8", errors="ignore")

    raise TypeError("source must be Path | str | bytes | file‑like")


# ---------------------------------------------------------------------------
# Chunking (simple)
# ---------------------------------------------------------------------------


def _chunk_text(text: str, max_chars: int = 6_000) -> List[str]:
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


# ---------------------------------------------------------------------------
# Bullet parser
# ---------------------------------------------------------------------------

_bullet_re = re.compile(r"^[•\-*]\s*(.+?)\s*\|\s*([\d,\s]+)$")


def _parse_bullets(raw: str) -> List[Dict]:
    out: List[Dict] = []
    for line in raw.splitlines():
        m = _bullet_re.match(line.strip())
        if not m:
            continue
        bullet, ids = m.groups()
        id_list = [int(x) for x in re.split(r"[\s,]+", ids) if x.isdigit()]
        if bullet:
            out.append({"bullet": bullet, "evidence_ids": id_list})
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def summarize(
    source: Source,
    *,
    backend: Literal["gpt4o", "llama"] = "gpt4o",
    model: str | None = None,
    temperature: float = 0.2,
) -> List[Dict]:
    """Generate an explainable summary from a local file path *or* an uploaded file.

    Examples
    --------
    >>> summarize("docs/guideline.pdf", backend="gpt4o")
    >>> summarize(uploaded_file, backend="llama")  # in Streamlit
    """
    client: BaseBackend = choose_backend(backend, model)
    text: str = _extract_text(source)

    # 1️⃣ Number sentences
    numbered: List[str] = []
    extract_prompt = _load_prompt("extract")
    for chunk in _chunk_text(text):
        reply = client.chat([
            {"role": "user", "content": f"{extract_prompt}\n\n{chunk}"}
        ], temperature=temperature)
        numbered.append(reply)

    numbered_text = "\n".join(numbered)

    # 2️⃣ Summarize + cite
    abstract_prompt = _load_prompt("abstract")
    summary_raw = client.chat([
        {"role": "user", "content": f"{abstract_prompt}\n\n{numbered_text}"}
    ], temperature=temperature)

    return _parse_bullets(summary_raw)


# ---------------------------------------------------------------------------
# CLI entry‑point used by `poetry run summarize …`
# ---------------------------------------------------------------------------

import argparse, sys

def main() -> None:  # console‑script in pyproject
    p = argparse.ArgumentParser(description="Summarize a document (txt/pdf)")
    p.add_argument("--file", required=True, help="Path to file OR '-' for stdin")
    p.add_argument("--backend", choices=["gpt4o", "llama"], default="gpt4o")
    p.add_argument("--model", help="Override Ollama model name")
    p.add_argument("--temperature", type=float, default=0.2)
    args = p.parse_args()

    if args.file == "-":
        data = sys.stdin.buffer.read()
        src: Source = data
    else:
        src = Path(args.file)

    out = summarize(src, backend=args.backend, model=args.model, temperature=args.temperature)
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":  # pragma: no cover
    main()
