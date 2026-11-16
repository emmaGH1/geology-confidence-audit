#!/usr/bin/env python3
"""Phase 2 harness: query configured LLMs on geology questions and log raw calls."""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

PROMPT_TEMPLATE = (
    "answer the geology question below. reply in json only:\n"
    '{{"answer": "<short answer>", "confidence": <0-100 integer>}}\n'
    "confidence is your probability that your answer is correct.\n"
    "question: {question}"
)

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 60


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_json_fences(text: str) -> str:
    s = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", s, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return s


def parse_model_json(raw_text: str):
    """Parse JSON response without guessing. Returns (answer, confidence, parse_ok)."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None, None, False
    cleaned = strip_json_fences(raw_text)
    try:
        obj = json.loads(cleaned)
    except Exception:
        return None, None, False
    if not isinstance(obj, dict):
        return None, None, False
    if "answer" not in obj or "confidence" not in obj:
        return None, None, False

    ans = obj["answer"]
    conf = obj["confidence"]

    if not isinstance(ans, str) or not ans.strip():
        return None, None, False
    if isinstance(conf, bool) or not isinstance(conf, (int, float)):
        return None, None, False
    if isinstance(conf, float) and not conf.is_integer():
        return None, None, False
    conf_int = int(conf)
    if conf_int < 0 or conf_int > 100:
        return None, None, False

    return ans.strip(), conf_int, True


def load_completed_keys(output_path: Path) -> set[tuple[str, str, int]]:
    completed: set[tuple[str, str, int]] = set()
    if not output_path.exists():
        return completed
    with output_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("status") == "ok":
                completed.add((str(rec.get("model")), str(rec.get("question_id")), int(rec.get("repeat"))))
    return completed


def append_jsonl(output_path: Path, record: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def load_questions(csv_path: Path) -> list[dict]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run geology confidence calibration queries.")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--questions", default="data/questions.csv", help="Path to data/questions.csv")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run 2 questions (1 Set A, 1 Set B) x 1 model x n_repeats into results/raw_dryrun.jsonl",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    dotenv_path = repo_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)

    api_key = os.environ.get("BANKR_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BANKR_API_KEY is not set in environment or .env", file=sys.stderr)
        return 1

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    base_url: str = cfg["base_url"]
    models: list[str] = list(cfg["models"])
    temperature: float = float(cfg["temperature"])
    n_repeats: int = int(cfg["n_repeats"])

    questions_path = Path(args.questions)
    if not questions_path.is_absolute():
        questions_path = repo_root / questions_path
    questions = load_questions(questions_path)

    if args.dry_run:
        models = models[:1]
        first_a = next((q for q in questions if q["set"] == "A"), None)
        first_b = next((q for q in questions if q["set"] == "B"), None)
        if not first_a or not first_b:
            print("ERROR: Could not find both Set A and Set B questions for --dry-run", file=sys.stderr)
            return 1
        questions = [first_a, first_b]
        output_path = repo_root / "results" / "raw_dryrun.jsonl"
    else:
        output_path = repo_root / "results" / "raw.jsonl"

    completed = load_completed_keys(output_path)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    total_combos = len(models) * len(questions) * n_repeats
    skipped = 0
    ok_count = 0
    parse_ok_count = 0
    error_count = 0
    calls_made = 0

    print(
        f"Mode={'dry-run' if args.dry_run else 'full'} | models={len(models)} | "
        f"questions={len(questions)} | repeats={n_repeats} | target_combos={total_combos} | "
        f"output={output_path.relative_to(repo_root)}"
    )

    session = requests.Session()

    for model in models:
        for q in questions:
            qid = q["id"]
            qset = q["set"]
            prompt = PROMPT_TEMPLATE.format(question=q["question"])

            for repeat in range(1, n_repeats + 1):
                if (model, qid, repeat) in completed:
                    skipped += 1
                    continue

                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }

                for attempt in range(1, MAX_ATTEMPTS + 1):
                    calls_made += 1
                    ts = utc_now_iso()
                    raw_text = None
                    usage = None
                    err_msg = None

                    try:
                        resp = session.post(
                            base_url,
                            headers=headers,
                            json=payload,
                            timeout=REQUEST_TIMEOUT_SECONDS,
                        )
                        if resp.status_code == 200:
                            body = resp.json()
                            usage = body.get("usage")
                            choices = body.get("choices") or []
                            if choices and isinstance(choices[0], dict):
                                msg = choices[0].get("message") or {}
                                raw_text = msg.get("content")
                            if isinstance(raw_text, str) and raw_text.strip():
                                parsed_answer, parsed_confidence, parse_ok = parse_model_json(raw_text)
                                record = {
                                    "timestamp": ts,
                                    "model": model,
                                    "question_id": qid,
                                    "set": qset,
                                    "repeat": repeat,
                                    "attempt": attempt,
                                    "prompt": prompt,
                                    "raw_response_text": raw_text,
                                    "parsed_answer": parsed_answer,
                                    "parsed_confidence": parsed_confidence,
                                    "parse_ok": parse_ok,
                                    "status": "ok",
                                    "error": None,
                                    "usage": usage,
                                }
                                append_jsonl(output_path, record)
                                completed.add((model, qid, repeat))
                                ok_count += 1
                                if parse_ok:
                                    parse_ok_count += 1
                                break
                            else:
                                err_msg = "HTTP 200 but empty or missing choices[0].message.content"
                        else:
                            snippet = resp.text[:500]
                            err_msg = f"HTTP {resp.status_code}: {snippet}"
                    except Exception as exc:
                        # Ensure API key is never leaked in exception strings
                        err_msg = f"{type(exc).__name__}: {str(exc)}".replace(api_key, "[REDACTED]")

                    is_final = attempt == MAX_ATTEMPTS
                    status_val = "error" if is_final else "retry_error"
                    record = {
                        "timestamp": ts,
                        "model": model,
                        "question_id": qid,
                        "set": qset,
                        "repeat": repeat,
                        "attempt": attempt,
                        "prompt": prompt,
                        "raw_response_text": raw_text,
                        "parsed_answer": None,
                        "parsed_confidence": None,
                        "parse_ok": False,
                        "status": status_val,
                        "error": err_msg,
                        "usage": usage,
                    }
                    append_jsonl(output_path, record)

                    if is_final:
                        error_count += 1
                        print(
                            f"[ERROR] model={model} q={qid} repeat={repeat} failed after {MAX_ATTEMPTS} attempts: {err_msg}",
                            file=sys.stderr,
                        )
                    else:
                        sleep_s = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                        time.sleep(sleep_s)

    print(
        f"Done. calls_made={calls_made} ok={ok_count} parse_ok={parse_ok_count} "
        f"final_errors={error_count} skipped_existing={skipped}"
    )
    return 0 if error_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
