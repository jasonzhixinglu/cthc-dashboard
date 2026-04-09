# CTHC Dashboard

Interactive dashboard for **"A Practical Model for Estimating China's Potential Growth Rate and Output Gap"** (Gonzalez, Lu, Radzikowski, 2026). The model — **CTHC** (Cointegrated Trends Harvey Cycle) — is a linear Gaussian state-space system estimated via Kalman filtering and Rauch-Tung-Striebel smoothing. This dashboard displays the model's key outputs — output gap, potential growth, and sectoral decompositions — with 68% and 95% posterior credible interval bands, deployed as a static GitHub Pages site. The working paper link will be added once available on the IMF Working Paper series.

**Live site:** https://jasonzhixinglu.github.io/cthc-dashboard/

---

## Updating the dashboard

The frontend reads pre-computed JSON files committed to the repo. To update the dashboard with new model output:

```bash
# 1. Regenerate the JSON payloads from the processed dataset
PYTHONPATH=. python scripts/export_site_payload.py data/processed/model_dataset.csv

# 2. If the underlying data has changed, rebuild the dataset first
PYTHONPATH=. python scripts/build_dataset.py

# 3. Commit the updated JSON files and push
git add web/public/data/
git commit -m "Update model output $(date +%Y-%m-%d)"
git push origin main
```

Pushing to `main` triggers the GitHub Actions workflow, which rebuilds the frontend and deploys to the `gh-pages` branch. The live site updates within about a minute.

---

## Local development

```bash
# Install frontend dependencies (one-time)
cd web && npm install

# Start the dev server (hot-reloads on file changes)
npm run dev
```

The dev server runs at `http://localhost:5173` and reads JSON from `web/public/data/`. Run the export script first (see above) to populate those files with real model output before starting the dev server.

```bash
# Production build (output goes to web/dist/)
npm run build
```

---

## Repository structure

```
configs/         Fixed-parameter YAML (rho_c, lambda_c, sigma_*, loadings)
data/
  raw/           One CSV per indicator
  processed/     Quarterly model-ready dataset (committed)
scripts/
  build_dataset.py       Rebuild data/processed/ from raw sources
  export_site_payload.py Run model → write web/public/data/*.json
src/cthc/
  kalman.py              Kalman filter
  smoother.py            Rauch-Tung-Striebel smoother
  model_matrices.py      State-space matrix construction
  run_model.py           Orchestration
  export_json.py         JSON serialization with posterior bands
web/
  src/           React + TypeScript frontend
  public/data/   Pre-computed JSON payloads (committed, read by site)
  dist/          Vite build output (not committed; built by CI)
.github/
  workflows/deploy.yml   Build + deploy to gh-pages on push to main
```
