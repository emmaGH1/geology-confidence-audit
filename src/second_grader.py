"""Blind second grader for results/needs_review.csv (does not see the first grade).
Logs every call to results/second_grader.jsonl; writes results/agreement.csv."""
import csv, json, os, re, time
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
load_dotenv()
MODEL = "deepseek-v4-flash"
URL = "https://llm.bankr.bot/v1/chat/completions"
KEY = os.environ["BANKR_API_KEY"]
PROMPT = ("You are grading a short answer to a geology question against an answer key.\n"
          "Mark correct=1 if the answer's primary claim names the same unit/concept as the key "
          "(ignore articles, spelling variants, added abbreviations or descriptors). "
          "If it names a different formation, basin, stage or concept, correct=0. "
          "Hedged 'X (or Y)' answers are graded on X.\n"
          "Reply in json only: {\"correct\": 0 or 1, \"reason\": \"<short>\"}\n\n"
          "question: {q}\nanswer key: {g}\naccepted variants: {v}\nanswer to grade: {a}")
rows = list(csv.DictReader(open("results/needs_review.csv", encoding="utf-8")))
out = open("results/second_grader.jsonl", "a", encoding="utf-8")
res = []
for r in rows:
    prompt = (PROMPT.replace("{q}", r["question"]).replace("{g}", r["gold_answer"])
              .replace("{v}", r["accepted_variants"]).replace("{a}", r["model_answer"]))
    grade, text, err = None, None, None
    for attempt in range(1, 4):
        try:
            resp = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"}, timeout=90,
                                 json={"model": MODEL, "temperature": 0,
                                       "messages": [{"role": "user", "content": prompt}]})
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", text or "", re.S)
            grade = int(json.loads(m.group(0))["correct"]) if m else None
            err = None if grade in (0, 1) else "unparseable"
        except Exception as e:
            err = str(e)[:300]
        out.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "model": MODEL,
                              "id": r["id"], "eval_model": r["model"], "attempt": attempt,
                              "prompt": prompt, "response": text, "grade": grade, "error": err}) + "\n")
        out.flush()
        if err is None:
            break
        time.sleep(2 * attempt)
    res.append({"id": r["id"], "model": r["model"], "model_answer": r["model_answer"], "n": r["n"],
                "grade_claude": r["correct"], "grade_second": "" if grade is None else grade})
with open("results/agreement.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(res[0].keys())); w.writeheader(); w.writerows(res)
