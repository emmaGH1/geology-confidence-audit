"""Phase 3 grading.

Step 1 (default):  python src/grade.py
  - reads results/raw.jsonl (final successful call per model/question/repeat)
  - auto-marks correct=1 when the normalised answer equals the normalised
    gold_answer or any accepted_variant
  - everything else goes to results/needs_review.csv (one row per distinct
    normalised answer per model/question; `n` = how many responses share it)
  - responses that failed to parse or errored go to results/unusable.csv
    and are excluded (never guessed)

Step 2 (after the author fills `correct` with 1 or 0):
  python src/grade.py --merge
  - writes results/graded.csv: one row per response, with grade_source auto|manual
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw.jsonl"
QUESTIONS = ROOT / "data" / "questions.csv"
REVIEW = ROOT / "results" / "needs_review.csv"
UNUSABLE = ROOT / "results" / "unusable.csv"
GRADED = ROOT / "results" / "graded.csv"


def norm(s):
    s = str(s).lower().replace("-", " ").replace("/", " ")
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^the ", "", s)
    return s


def load_questions():
    with open(QUESTIONS, newline="", encoding="utf-8") as f:
        qs = {r["id"]: r for r in csv.DictReader(f)}
    for q in qs.values():
        keys = [q["gold_answer"]] + [v for v in q["accepted_variants"].split("|") if v.strip()]
        q["_keys"] = {norm(k) for k in keys}
    return qs


def load_responses():
    """Final record per (model, question_id, repeat): the ok one if any, else the last error."""
    recs = {}
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            k = (r["model"], r["question_id"], r["repeat"])
            if recs.get(k, {}).get("status") == "ok":
                continue
            recs[k] = r
    return recs


def first_pass(qs, recs):
    auto, review, unusable = [], {}, []
    for (model, qid, rep), r in sorted(recs.items()):
        q = qs[qid]
        usable = (
            r.get("status") == "ok"
            and r.get("parse_ok")
            and r.get("parsed_answer") not in (None, "")
            and isinstance(r.get("parsed_confidence"), (int, float))
        )
        if not usable:
            unusable.append({"id": qid, "model": model, "repeat": rep,
                             "status": r.get("status"), "error": r.get("error"),
                             "raw_response_text": r.get("raw_response_text")})
            continue
        if norm(r["parsed_answer"]) in q["_keys"]:
            auto.append((model, qid, rep))
        else:
            k = (qid, model, norm(r["parsed_answer"]))
            if k not in review:
                review[k] = {"id": qid, "model": model, "question": q["question"],
                             "gold_answer": q["gold_answer"],
                             "accepted_variants": q["accepted_variants"],
                             "model_answer": r["parsed_answer"], "n": 0, "correct": ""}
            review[k]["n"] += 1
    return auto, review, unusable


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    qs = load_questions()
    recs = load_responses()
    auto, review, unusable = first_pass(qs, recs)

    if not args.merge:
        if REVIEW.exists():
            sys.exit(f"{REVIEW} already exists; refusing to overwrite hand grades. Delete it first to regenerate.")
        rows = sorted(review.values(), key=lambda r: (r["id"], r["model"]))
        write_csv(REVIEW, rows, ["id", "model", "question", "gold_answer", "accepted_variants",
                                 "model_answer", "n", "correct"])
        write_csv(UNUSABLE, unusable, ["id", "model", "repeat", "status", "error", "raw_response_text"])
        print(f"responses={len(recs)} auto_correct={len(auto)} "
              f"needs_review_rows={len(rows)} (responses={sum(r['n'] for r in rows)}) unusable={len(unusable)}")
        return

    manual = {}
    with open(REVIEW, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = r["correct"].strip()
            if c not in ("0", "1"):
                sys.exit(f"needs_review.csv: row {r['id']}/{r['model']} '{r['model_answer']}' has correct='{c}'; must be 0 or 1")
            manual[(r["id"], r["model"], norm(r["model_answer"]))] = (int(c), (r.get("graded_by") or "author").strip())

    auto_set = set(auto)
    out = []
    for (model, qid, rep), r in sorted(recs.items()):
        if not (r.get("status") == "ok" and r.get("parse_ok") and r.get("parsed_answer")
                and isinstance(r.get("parsed_confidence"), (int, float))):
            continue
        if (model, qid, rep) in auto_set:
            correct, src = 1, "auto"
        else:
            key = (qid, model, norm(r["parsed_answer"]))
            if key not in manual:
                sys.exit(f"missing manual grade for {key}")
            correct, who = manual[key]
            src = f"manual_{who}"
        out.append({"id": qid, "set": qs[qid]["set"], "difficulty": qs[qid]["difficulty"],
                    "model": model, "repeat": rep, "model_answer": r["parsed_answer"],
                    "confidence": r["parsed_confidence"], "correct": correct, "grade_source": src})
    write_csv(GRADED, out, ["id", "set", "difficulty", "model", "repeat", "model_answer",
                            "confidence", "correct", "grade_source"])
    print(f"graded rows={len(out)} auto={sum(o['grade_source']=='auto' for o in out)} "
          f"manual={sum(o['grade_source'].startswith('manual') for o in out)} excluded_unusable={len(unusable)}")


if __name__ == "__main__":
    main()
