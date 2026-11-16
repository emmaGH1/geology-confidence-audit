# Grading notes

## Who graded
- 386 / 480 responses: auto-graded by `src/grade.py` (normalised exact match to gold answer or accepted variants).
- 94 / 480 responses (62 distinct answers in `results/needs_review.csv`): **graded by Claude (LLM orchestrator), not by the author**, at the author's request because of time pressure. Marked `graded_by=claude` in needs_review.csv and `grade_source=manual_claude` in graded.csv. The author has not yet reviewed these grades. This must be stated in the report (an LLM grading LLM answers is a limitation).

## Rules applied
1. Correct (1) if the primary answer names the gold unit/concept or an accepted variant, ignoring articles, parenthetical abbreviations (e.g. "(K-Pg)", "(MVT)", "(MFS)"), alternate spellings, and added descriptors ("deposits", "Formation", "invariant point").
2. Hedged answers of the form "X (or Y)" are graded on X, the primary answer.
3. A more specific but consistent answer is correct (B14 "Late Jurassic" for gold "Jurassic").
4. A full sentence that names the gold answer is correct (B01 gpt-5.4-mini).
5. Incorrect (0) if the answer names a different formation, basin, stage or granite suite.

## Borderline calls (sensitivity candidates)
- **B18** gpt-5.4-mini, "The Abakaliki Shale (often referred to as the Asu River Group)" (1 response): graded 1, because it explicitly equates its answer with the Asu River Group.
- **B22** "Patti Formation" (claude-haiku-4.5 ×2, deepseek-v3.2 ×1, gpt-5.4-mini ×2): graded 0. The Agbaja ironstone overlies the Patti Formation, but some literature reports ironstone beds within the Patti, so the author may wish to revisit.
- **B22** "Lokoja Formation" (2 responses): graded 0.
