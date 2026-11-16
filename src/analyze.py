"""Phase 4 analysis. Reads results/graded.csv, writes:
  results/summary.csv    per model (and pooled 'ALL') per set: n, n_questions, accuracy,
                         mean_confidence, gap, brier, ece_10bin
  results/bootstrap.csv  per model (and ALL): gap(B) - gap(A), 95% percentile CI
                         (2000 cluster-bootstrap resamples; questions resampled with
                         replacement within each set, all repeats of a question kept together)
  figures/reliability.png, figures/gap.png
Prints numbers only, no interpretation.
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
GRADED = ROOT / "results" / "graded.csv"
SUMMARY = ROOT / "results" / "summary.csv"
BOOT = ROOT / "results" / "bootstrap.csv"
FIG = ROOT / "figures"
N_BOOT = 2000
SEED = 20261116
BINS = 10


def ece(conf, corr, bins=BINS):
    idx = np.minimum((conf * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.sum() / len(conf) * abs(corr[m].mean() - conf[m].mean())
    return total


def metrics(conf, corr):
    acc, mc = corr.mean(), conf.mean()
    return {"n": len(conf), "accuracy": acc, "mean_confidence": mc, "gap": mc - acc,
            "brier": float(np.mean((conf - corr) ** 2)), "ece_10bin": ece(conf, corr)}


def load():
    rows = list(csv.DictReader(open(GRADED, newline="", encoding="utf-8")))
    for r in rows:
        r["conf"] = float(r["confidence"]) / 100.0
        r["corr"] = float(r["correct"])
    return rows


def by_question(rows):
    """{set: {qid: (conf array, corr array)}}"""
    d = defaultdict(lambda: defaultdict(lambda: ([], [])))
    for r in rows:
        c, k = d[r["set"]][r["id"]]
        c.append(r["conf"]); k.append(r["corr"])
    return {s: {q: (np.array(c), np.array(k)) for q, (c, k) in qs.items()} for s, qs in d.items()}


def gap_of(qmap, qids):
    conf = np.concatenate([qmap[q][0] for q in qids])
    corr = np.concatenate([qmap[q][1] for q in qids])
    return conf.mean() - corr.mean()


def bootstrap(rows, rng):
    bq = by_question(rows)
    A, B = bq["A"], bq["B"]
    qa, qb = sorted(A), sorted(B)
    point = gap_of(B, qb) - gap_of(A, qa)
    diffs = np.empty(N_BOOT)
    for i in range(N_BOOT):
        sa = rng.choice(qa, size=len(qa), replace=True)
        sb = rng.choice(qb, size=len(qb), replace=True)
        diffs[i] = gap_of(B, sb) - gap_of(A, sa)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return point, lo, hi


def main():
    rows = load()
    models = sorted({r["model"] for r in rows})
    groups = models + ["ALL"]
    rng = np.random.default_rng(SEED)
    FIG.mkdir(exist_ok=True)

    summary, boot = [], []
    for g in groups:
        sub = rows if g == "ALL" else [r for r in rows if r["model"] == g]
        for s in ("A", "B"):
            ss = [r for r in sub if r["set"] == s]
            m = metrics(np.array([r["conf"] for r in ss]), np.array([r["corr"] for r in ss]))
            summary.append({"model": g, "set": s, "n_questions": len({r["id"] for r in ss}), **m})
        point, lo, hi = bootstrap(sub, rng)
        boot.append({"model": g, "gap_B_minus_gap_A": point, "ci95_low": lo, "ci95_high": hi,
                     "n_boot": N_BOOT, "seed": SEED})

    fields = ["model", "set", "n", "n_questions", "accuracy", "mean_confidence", "gap", "brier", "ece_10bin"]
    with open(SUMMARY, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in summary:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    with open(BOOT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(boot[0].keys()))
        w.writeheader()
        for r in boot:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})

    print(open(SUMMARY).read())
    print(open(BOOT).read())

    # reliability diagram
    fig, axes = plt.subplots(1, len(models), figsize=(4 * len(models), 4), sharey=True)
    for ax, mdl in zip(np.atleast_1d(axes), models):
        for s, col in (("A", "tab:blue"), ("B", "tab:orange")):
            ss = [r for r in rows if r["model"] == mdl and r["set"] == s]
            conf = np.array([r["conf"] for r in ss]); corr = np.array([r["corr"] for r in ss])
            idx = np.minimum((conf * BINS).astype(int), BINS - 1)
            xs, ys, ns = [], [], []
            for b in range(BINS):
                m = idx == b
                if m.any():
                    xs.append(conf[m].mean()); ys.append(corr[m].mean()); ns.append(m.sum())
            ax.plot(xs, ys, "o-", color=col, label=f"Set {s}")
            for x, y, n in zip(xs, ys, ns):
                ax.annotate(str(n), (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points", color=col)
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.set_title(mdl, fontsize=10); ax.set_xlabel("stated confidence")
        ax.set_xlim(0, 1.02); ax.set_ylim(0, 1.02)
    np.atleast_1d(axes)[0].set_ylabel("accuracy"); np.atleast_1d(axes)[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "reliability.png", dpi=150); plt.close(fig)

    # gap bar chart with per-set cluster-bootstrap 95% CIs
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(groups)); wbar = 0.38
    for j, (s, col) in enumerate((("A", "tab:blue"), ("B", "tab:orange"))):
        vals, errs = [], [[], []]
        for g in groups:
            sub = [r for r in rows if (g == "ALL" or r["model"] == g) and r["set"] == s]
            qmap = by_question(sub)[s]; q = sorted(qmap)
            pt = gap_of(qmap, q)
            bs = [gap_of(qmap, rng.choice(q, size=len(q), replace=True)) for _ in range(N_BOOT)]
            lo, hi = np.percentile(bs, [2.5, 97.5])
            vals.append(pt); errs[0].append(pt - lo); errs[1].append(hi - pt)
        ax.bar(x + (j - 0.5) * wbar, vals, wbar, yerr=errs, capsize=3, color=col, label=f"Set {s}")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(groups, fontsize=8)
    ax.set_ylabel("overconfidence gap (mean conf - accuracy)"); ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "gap.png", dpi=150); plt.close(fig)

    # per-question accuracy and mean confidence (all models pooled + per model)
    pq = defaultdict(list)
    for r in rows:
        pq[(r["id"], r["set"], r["model"])].append(r)
        pq[(r["id"], r["set"], "ALL")].append(r)
    with open(ROOT / "results" / "per_question.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "set", "model", "n", "accuracy", "mean_confidence"])
        for (qid, s, g), rs in sorted(pq.items()):
            w.writerow([qid, s, g, len(rs), f"{np.mean([r['corr'] for r in rs]):.4f}",
                        f"{np.mean([r['conf'] for r in rs]):.4f}"])
    srcs = defaultdict(int)
    for r in rows:
        srcs[r["grade_source"]] += 1
    with open(ROOT / "results" / "grading_counts.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["grade_source", "n"])
        for k, v in sorted(srcs.items()):
            w.writerow([k, v])


if __name__ == "__main__":
    main()
