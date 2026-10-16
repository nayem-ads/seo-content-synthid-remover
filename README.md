# Antigravity SEO & Watermark Purifier Studio

A Google Helpful Content & SpamBrain footprint purifier designed to scrub statistical AI signatures, invisible Unicode watermarks, and overused LLM transitions while **100% locking** your target SEO keywords, Markdown headers, bold tags, and links.

## Features
- **3 Purification Modes:**
  - **Deep Resample (`EN → DE → EN`):** Parallelized grammar-safe translation resampling with automatic fallback (`deep-translator` / Google Translate / MyMemory API).
  - **Multi-Hop Beast (`EN → ES → DE → EN`):** Double-pivot resampling for maximum 3-gram token chain destruction.
  - **Instant Local (`<50ms`):** Zero-latency cliché, Unicode, contraction, and burstiness humanizer.
- **100% SEO Keyword & Link Lock:** Uses citation-anchored quote locking so sentence grammar stays natural and prepositions are never dropped around keywords or Markdown links.
- **Live Google Algorithm Scorecard:** Measures Before vs. After Google Safety Score, 3-Gram Scramble %, Burstiness Index, and per-keyword count verification.

## Local Quickstart
```bash
python3 app.py
# Open http://localhost:8080
```

## Deploy on Railway
This repository includes `Procfile`, `railway.json`, and `requirements.txt` for 1-click deployment on [Railway](https://railway.app).
