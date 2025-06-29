from __future__ import annotations

import json
import re
from pathlib import Path
from typing import IO, List, Dict, Literal, Union
from io import BytesIO, TextIOBase
from summarizer.backends import choose_backend, BaseBackend
import pdfplumber


def _load_prompt(name: Literal["extract", "abstract"]) -> str:
    """Return raw prompt text from prompts/ directory."""
    here = Path(__file__).with_suffix("").parent / "prompts"
    return (here / f"{name}.txt").read_text(encoding="utf-8")


Source = Union[str, Path, bytes, IO[bytes]]


def _extract_text(source: Source) -> str:
    """Return plain text from a variety of inputs.

    * **Path / str** – points to a .txt or .pdf file on disk.
    * **bytes / BytesIO / UploadedFile** – usually from a web upload.
    """

    def _pdf_bytes_to_text(data: bytes) -> str:  # local helper
        with pdfplumber.open(BytesIO(data)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)

    if isinstance(source, (str, Path)):
        path = Path(source)
        ext = path.suffix.lower()
        if ext == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        if ext == ".pdf":
            return _pdf_bytes_to_text(path.read_bytes())
        raise ValueError(f"Unsupported file extension: {ext}")

    if isinstance(source, bytes):
        # Heuristic: if bytes start with %PDF‑, treat as PDF.
        if source[:4] == b"%PDF":
            return _pdf_bytes_to_text(source)
        return source.decode("utf-8", errors="ignore")

    # ----------------------------------------------------
    # Case – File‑like object (BytesIO, Django/Flask file, Streamlit upload)
    #          Must support .read() and optionally .name
    # ----------------------------------------------------

    if hasattr(source, "read"):
        data = source.read()
        name = getattr(source, "name", "uploaded")
        if (
            isinstance(name, str)
            and name.lower().endswith(".pdf")
            or data[:4] == b"%PDF"
        ):
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

    numbered: List[str] = []
    extract_prompt = _load_prompt("extract")
    for chunk in _chunk_text(text):
        reply = client.chat(
            [{"role": "user", "content": f"{extract_prompt}\n\n{chunk}"}],
            temperature=temperature,
        )
        numbered.append(reply)

    numbered_text = "\n".join(numbered)

    abstract_prompt = _load_prompt("abstract")
    summary_raw = client.chat(
        [{"role": "user", "content": f"{abstract_prompt}\n\n{numbered_text}"}],
        temperature=temperature,
    )

    return _parse_bullets(summary_raw)
