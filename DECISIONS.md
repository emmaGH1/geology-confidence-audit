# Decisions Log

All autonomous orchestrator decisions made between human gates are logged here.

## 2026-11-16 (07:30 WAT start — Phase 1)

1. **BRIEF.md placement**: Copied attached `apart-sprint-harness.md` to repo root `BRIEF.md` per instructions.
2. **Question Set Design (`data/questions.csv`)**:
   - Drafted 20 Set A (`A01`–`A20`, global textbook geology) and 25 Set B (`B01`–`B25`, Nigerian regional geology) rows so the author can trim Set B down to the best 20 at Gate 1 (per Phase 1 in `BRIEF.md`).
   - Added `source_verified` column alongside `id,set,question,gold_answer,accepted_variants,source,difficulty` as requested in Phase 1 prompt (`yes` for textbook-verified Set A, `no` for all Set B pending author verification).
   - **Difficulty matching**: Balanced Set A (6 easy / 8 medium / 6 hard) against Set B (7 easy / 10 medium / 8 hard) at university undergraduate (B.Tech) geology level across matched subdisciplines (stratigraphic units, basin types/structures, tectonic events, igneous/metamorphic petrology, ore geology) to avoid an unfair trivia-vs-specialist gap.
   - **Coverage of Nigerian geological provinces**: Covered all provinces listed in `BRIEF.md`: Basement Complex (`B02`, `B03`), Benue Trough (`B05`, `B10`, `B11`, `B18`, `B20`), Niger Delta (`B01`, `B08`, `B09`), Anambra Basin (`B12`, `B13`, `B19`, `B25`), Jos Younger Granites (`B04`, `B14`, `B15`, `B16`, `B24`), Chad/Bornu Basin (`B20`, `B21`), Sokoto/Iullemmeden Basin (`B07`, `B17`, `B23`), Bida/Mid-Niger Basin (`B22`), Dahomey Basin (`B06`), and mineral occurrences (`B04`, `B05`, `B06`, `B12`, `B15`, `B17`, `B22`, `B25`).
   - Removed answer-leaking parenthetical nicknames (`'False-bedded Sandstone'` in `B13`, `'Continental Terminal'` in `B23`) from question stems while keeping `False-bedded Sandstone` in `B13` `accepted_variants`.
3. **API & Model Plan for Phase 2 (verified upfront)**:
   - Confirmed `BANKR_API_KEY` is active in the environment (`https://llm.bankr.bot/v1`, OpenAI-compatible `/v1/chat/completions`), providing multi-provider models (OpenAI, Anthropic, Google, DeepSeek, Qwen, Meta). Will configure 3–4 distinct provider models in `config.yaml` once Gate 1 is approved (`go`), reading `BANKR_API_KEY` (or `OPENROUTER_API_KEY` if preferred) via `.env` / environment.

## 2026-11-16 — Gate 1 review applied (author-directed: "fix them")

4. **Set B trimmed 25 → 20** (IDs kept stable, not renumbered): dropped B04 (cassiterite = generic tin ore), B09 (rollover anticline = generic delta concept), B16 (ambiguous answer: ring complex / cauldron subsidence / ring dykes), B24 (directional, guessable), B06 (Dahomey Basin not in brief's province list; state names give it away).
5. **Set B rewordings**: B11 removed "Abakaliki" leak; B22 removed "Agbaja" leak, localised to southern Bida Basin near Lokoja (northern Bida Batati Fm also hosts ironstones), age → Maastrichtian; B12 removed contested "Maastrichtian" qualifier; B20 "(Albian)" → "(Early Cretaceous)"; B23 removed contested age range, added `Continental Terminal` as accepted variant.
6. **Set A source_verified → no for all rows**: the agent drafted them; nobody had verified them. Author to verify.
7. **Question-type confound**: Set B had 12 local formation-name items, Set A had none. Replaced the 5 easiest Set A items (A01 olivine, A02 quartzite, A03 nonconformity, A04 kimberlite, A06 transform) with well-represented regional formation-name items: Marcellus Shale, Burgess Shale, Morrison Formation, Navajo Sandstone, Bakken Formation. Their `source` = `TODO: author to add source` (no reference invented).

## Phase 2

8. **Environment & Secret Hygiene**:
   - Verified `BANKR_API_KEY` was present in environment, wrote `.env` (`chmod 600`) without printing or logging the key, and created `.gitignore` excluding `.env`, `.venv/`, `__pycache__/`, and `*.pyc`.
9. **Gateway Model Probing (`https://llm.bankr.bot/v1/chat/completions` at `temperature=0.7` with `"say ok"`)**:
   - Queried `/v1/models` (86 listed IDs; note no Meta `llama-*` models are hosted on this gateway) and probed candidate ID spellings across providers:
   - **Worked (HTTP 200, valid non-empty completion at `temperature=0.7`)**:
     - OpenAI: `gpt-5.4-mini` (0.88s)
     - Anthropic: `claude-haiku-4.5` (0.48s), `claude-sonnet-4.6` (1.15s)
     - Google: `gemini-3-flash` (0.97s), `gemini-3.5-flash` (1.23s), `gemini-3.8-flash` (2.35s)
     - DeepSeek: `deepseek-v3.2` (0.35s), `deepseek-v4-flash` (1.53s)
     - Qwen: `qwen3.6-flash` (returned `content: null` when `max_tokens=32` because reasoning tokens consumed the budget; succeeded in 2.30s with 164 reasoning tokens when `max_tokens` was omitted)
   - **Failed**:
     - `claude-3-5-haiku-latest` → HTTP 400 (`Unsupported model: claude-3-5-haiku-latest`)
     - `gemini-2.5-flash` → HTTP 410 (`Model gemini-2.5-flash has been removed. Please use gemini-3.8-flash instead.`)
     - `llama-3.3-70b-instruct` → HTTP 400 (`Unsupported model: llama-3.3-70b-instruct`)
     - `deepseek-chat` → HTTP 400 (`Unsupported model: deepseek-chat`)
10. **Selected Models in `config.yaml` & Rationale**:
    - Chose 4 models from 4 distinct providers at matched fast/mid capability tier: `gpt-5.4-mini` (OpenAI), `claude-haiku-4.5` (Anthropic), `gemini-3-flash` (Google), and `deepseek-v3.2` (DeepSeek).
    - Rationale: spans 4 independent model families, all accepted `temperature: 0.7` cleanly with sub-second latency (`0.35s–0.97s`), and avoids `qwen3.6-flash`'s heavy reasoning-token overhead so `max_tokens` truncation cannot cause empty completions. Also omitted `max_tokens` in `src/run.py` payloads so reasoning-enabled models (e.g., Gemini 3 Flash) are never truncated mid-JSON.
11. **Harness Design (`src/run.py`) & Dry-Run Verification**:
    - Plain Python (`requests`, `python-dotenv`, `pyyaml`), exact specified prompt, strict JSON parser (strips optional ```` ```json ```` fences, `json.loads`, validates string `answer` and integer `0..100` `confidence`, never guesses on failure).
    - Logs every API attempt (including `retry_error` and final `error` after 3 exponential-backoff attempts) to JSONL with UTC ISO timestamp, `usage`, and API key redaction in exception strings; resumes by skipping `(model, question_id, repeat)` tuples already logged with `status == "ok"`.
    - `--dry-run` writes to `results/raw_dryrun.jsonl` (1 model × 2 questions `A01` + `B01` × 3 repeats = 6 calls) to keep `results/raw.jsonl` untouched. All 6/6 calls returned `status="ok"` and `parse_ok=true`; a second `--dry-run` invocation confirmed resumability (`skipped_existing=6`, `calls_made=0`).

## 2026-11-16 — Phase 3 grading script (written by orchestrator)

8. **`src/grade.py` normalisation**: lowercase, hyphens/slashes → spaces, strip punctuation, collapse whitespace, strip a leading "the". Exact match against gold_answer or any accepted_variant → auto-correct. Everything else → `results/needs_review.csv`.
9. **Deduplication for hand grading**: needs_review.csv has one row per (question, model, normalised answer), with an `n` column for how many of the 3 repeats gave it, plus an `accepted_variants` column for context. The author's grade applies to all responses that share that answer.
10. **Unusable responses** (API error after retries, JSON parse failure, missing confidence) go to `results/unusable.csv` and are excluded from analysis, not guessed. Count to be reported.
11. `grade.py` refuses to overwrite an existing needs_review.csv so hand grades cannot be clobbered.

## 2026-11-16 — Gate 3 (author-directed: "can you fix it, i don't have time to grade")

12. The orchestrator (Claude) graded the 62 needs_review rows (94 responses) at the author's request. 35 were graded 1 and 27 were graded 0. These are labelled `graded_by=claude` and `grade_source=manual_claude` so they are never presented as the author's expert grading. Rules and borderline calls are in `grading_notes.md`. The report must disclose this.

## 2026-11-16 — Phase 4 analysis (written by orchestrator)

13. `src/analyze.py`: confidence is divided by 100. Gap = mean confidence − accuracy. Brier score = mean (conf − correct)². ECE uses 10 equal-width bins, with conf = 1.0 placed in the top bin. A pooled "ALL" row is added across all 4 models.
14. Bootstrap: a **question-level cluster bootstrap** with 2000 resamples and seed 20261116. Questions are resampled with replacement within each set, and all repeats (and, for ALL, all models) of a question stay together. Resampling individual responses would treat the 3 correlated repeats as independent and make the CIs too narrow. Percentile 95% CI. Output goes to `results/bootstrap.csv`.
15. Installed matplotlib and numpy with `pip --user --break-system-packages` because the system Python is externally managed.

## 2026-11-16 — Phase 6 report (written by orchestrator)

16. No Apart template in the repo, so the report was written as `report/report.md` with the required sections. TODO: author ports it into the official template.
17. References were limited to 5 works whose identity was checked against arXiv (Kadavath 2022, Tian 2023, Xiong 2023, Guo 2017) or Crossref (Obaje 2009 DOI). Sharma et al. 2023 was omitted because Phase 5 was not run. Two claims without a verified source are marked [CITE?].
18. Added `results/per_question.csv` and `results/grading_counts.csv` to analyze.py so that every number in the report traces to results/. The bootstrap output was verified unchanged after this edit.
19. `src/check_report_numbers.py` confirms every 4-decimal number in the report appears in results/*.csv and reports the abstract word count.
20. Phase 5 (pushback) was skipped: phases 1–4 finished after 9:30.

## 2026-11-16 — Pre-submission tasks (author-directed: "can you handle those yourself", 11:02 WAT)

21. Answer-key verification was delegated to two research agents (Set A, Set B). They check each gold answer against openable web sources and write `data/source_check_A.csv` / `data/source_check_B.csv`. questions.csv is not edited by them.
22. Blind second grader: `src/second_grader.py` sent the 62 needs_review answers to `deepseek-v4-flash` (temperature 0), without the first grade. Raw calls are in `results/second_grader.jsonl`. Agreement with Claude's grades was 62/62 distinct answers and 94/94 responses (`results/grading_agreement.csv`). Reported in the report as LLM–LLM agreement, not expert validation.
23. Replaced both [CITE?] markers with three arXiv-verified works: Kandpal et al. 2022 (2211.08411), Manvi et al. 2024 (2402.02680), Deng et al. 2023 (2306.05064). Each was cited only for what its abstract states.
24. PDF: `src/export_pdf.py` renders report.md → HTML → PDF with headless Chromium. The Apart template is not available offline. The main body ends on p.5 (limit 8) and both figures are embedded.

## 2026-11-16 — Cross-check (author: "cross-check again especially the models mentioned")

25. The run log (`raw.jsonl`) records only the requested gateway id. `src/model_identity.py` probed each id once after the run (`results/model_identity.jsonl`). Served as: gpt-5.4-mini → gpt-5.4-mini-2026-03-17; claude-haiku-4.5 → anthropic/claude-haiku-4.5; gemini-3-flash → gemini-3-flash-preview (preview release); deepseek-v3.2 → deepseek/deepseek-v3.2; deepseek-v4-flash → deepseek-v4-flash. The report now states this and that per-call versions were not logged.
26. Report corrections: (a) the abstract and results said only gpt-5.4-mini's CI excluded zero, but gemini-3-flash's also does (in the negative direction), so both now say "in the hypothesised direction"; (b) the Methods sentence about the second grader implied it came from a developer independent of the evaluated models, but deepseek-v4-flash shares a developer with deepseek-v3.2, so it now says so; (c) the claim that Guo et al. "popularised ECE" is not in their abstract, so it was softened; (d) added Xiong et al.'s abstract finding that methods struggle on professional-knowledge tasks.
27. Re-fetched all 7 arXiv abstracts. Each related-work claim now matches its abstract.
28. Set A/B web checks: 40/40 confirmed. Filled the 5 TODO Set A sources with the opened pages proposed by the checker. `source_verified` = `web_checked` for all 40 (LLM web check, not an author textbook check). A03 "most prolific" and A15 "downlap surface" caveats are disclosed in the limitations; question wording was not changed post-run.
29. Checked that the API key string appears in no file outside .env.
