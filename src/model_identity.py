"""Record which model the gateway actually serves for each requested id (response 'model' field)."""
import json, os, requests
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv(".env")
K = os.environ["BANKR_API_KEY"]
out = open("results/model_identity.jsonl", "a")
for m in ["gpt-5.4-mini", "claude-haiku-4.5", "gemini-3-flash", "deepseek-v3.2", "deepseek-v4-flash"]:
    prompt = "Which model are you? Reply in one short line."
    r = requests.post("https://llm.bankr.bot/v1/chat/completions", headers={"Authorization": f"Bearer {K}"},
                      timeout=90, json={"model": m, "temperature": 0, "messages": [{"role": "user", "content": prompt}]})
    j = r.json()
    rec = {"timestamp": datetime.now(timezone.utc).isoformat(), "requested_model": m, "http_status": r.status_code,
           "served_model": j.get("model"), "system_fingerprint": j.get("system_fingerprint"),
           "self_report": (j.get("choices") or [{}])[0].get("message", {}).get("content"), "prompt": prompt}
    out.write(json.dumps(rec) + "\n")
    print(m, "->", rec["served_model"], "|", (rec["self_report"] or "")[:90].replace("\n", " "))
