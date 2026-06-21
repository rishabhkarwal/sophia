## data/

```bash
# generate self-play FENs
venv/bin/python tune/generate_fens.py tune/data/fens_raw.txt 5000

# annotate with SF WDL (for Texel tuning)
venv/bin/python tune/annotate_fens.py tune/data/fens_raw.txt tune/data/fens_wdl.txt

# annotate with SF HCE CP (for CP tuning)
venv/bin/python tune/annotate_fens_cp.py tune/data/fens_wdl.txt tune/data/fens_cp.txt
```

## eval tuning

```bash
# WDL Texel
venv/bin/python tune/texel_tune_mp.py tune/data/fens_wdl.txt 200000 12 10

# CP regression
venv/bin/python tune/texel_tune_cp.py tune/data/fens_cp.txt 200000 40 4
```

promote a candidate:

```bash
venv/bin/python tune/promote_eval_candidate.py tune/output/candidates/<candidate>.json
```

## search tuning

```bash
venv/bin/python tune/search_tune.py 50 160 8
```

resumable via `tune/search_optuna_cython.db`; best params saved to `tune/output/search_params.json`.

## output/

- `output/eval_params.json` — promoted eval params (830k WDL tune)
- `output/search_params.json` — promoted search params (Optuna, 50 trials)
- `output/candidates/` — all evaluated candidates with their reports in `reports/`
