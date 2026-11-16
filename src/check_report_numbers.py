"""Check every 4-decimal number in report/report.md appears in a results/ file; print abstract word count."""
import glob, re, sys
rep = open("report/report.md", encoding="utf-8").read()
pool = set()
for f in glob.glob("results/*.csv"):
    for n in re.findall(r"-?\d+\.\d{4}", open(f).read()):
        pool.add(n.lstrip("-"))
nums = re.findall(r"\d+\.\d{4}", re.sub(r"https?://\S+", "", rep))
missing = sorted({n for n in nums if n not in pool})
print(f"4-decimal numbers in report: {len(nums)}, missing from results/: {missing}")
abs_ = rep.split("## Abstract")[1].split("## 1.")[0]
print("abstract words:", len(abs_.split()))
sys.exit(1 if missing else 0)
