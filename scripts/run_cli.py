from summarizer.pipeline import summarize
from summarizer.pipeline import Source
from pathlib import Path
import json
import argparse, sys

def main() -> None:
    p = argparse.ArgumentParser(description="Summarize a document (txt/pdf)")
    p.add_argument("--file", required=True, help="Path to file OR '-' for stdin")
    p.add_argument("--backend", choices=["gpt4o", "llama"], default="llama")
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

if __name__ == "__main__":
    main()