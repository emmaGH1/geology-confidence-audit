<img src="assets/icon.svg" width="64" height="64" alt="">

# apart research

Created in [T3 Code](https://t3.codes).

## How to run

1. **Install dependencies** (Python 3.10+):
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **Configure `.env`**:
   Create `.env` in the repository root (listed in `.gitignore`) with your Bankr LLM gateway key:
   ```bash
   BANKR_API_KEY=your_api_key_here
   ```

3. **Dry run** (2 questions: 1 Set A + 1 Set B, 1 model, 3 repeats → `results/raw_dryrun.jsonl`):
   ```bash
   .venv/bin/python src/run.py --dry-run
   ```

4. **Full run** (all 40 questions × all models in `config.yaml` × 3 repeats → `results/raw.jsonl`, resumable):
   ```bash
   .venv/bin/python src/run.py
   ```
