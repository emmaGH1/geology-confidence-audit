"""report/report.md -> report/report.html -> report/report.pdf (headless Chromium)."""
import subprocess, markdown
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "report"
body = markdown.markdown((R / "report.md").read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
css = """body{font-family:Georgia,serif;font-size:10.5pt;line-height:1.4;max-width:7in;margin:auto}
h1{font-size:17pt}h2{font-size:13pt;margin-top:1.2em}h3{font-size:11pt}
table{border-collapse:collapse;font-size:8.5pt;margin:.6em 0}td,th{border:1px solid #999;padding:2px 5px;vertical-align:top}
img{max-width:100%}pre{font-size:8.5pt;background:#f4f4f4;padding:6px;white-space:pre-wrap}
@page{size:A4;margin:2cm}"""
(R / "report.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>Confidently Wrong Underground</title><style>{css}</style></head><body>{body}</body></html>", encoding="utf-8")
subprocess.run(["chromium", "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={R/'report.pdf'}", (R / "report.html").as_uri()], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("wrote", R / "report.pdf")
