# OmniVBench

Project website for OmniVBench and the Omni-R2V Dataset.

This repository is self-contained: HTML, CSS, JavaScript, figures, and the referenced dataset / benchmark media. No backend or external filesystem paths are required.

## Preview

Run `python3 -m http.server 8000` in this directory and open `http://localhost:8000`.

## GitHub Pages

In Settings → Pages, choose Deploy from a branch, `main`, and `/ (root)`. Keep `.nojekyll` in the repository.

## Media

Benchmark: selected examples with all available model outputs. Videos retain their full duration, resized to a maximum dimension of 720px, encoded as silent H.264 up to 24fps. Reference images use WebP up to 1280px. Dataset media retain the current preview versions. Original research media and paper scores are unchanged.

## Editing

`index.html` / `dataset.js` control the dataset page. `benchmark.html` / `benchmark.js` control the benchmark page. `styles.css` and `immersive.css` define the presentation. `data.js` and `benchmark-data.js` contain the current sample selection and relative asset paths.

Do not commit local audit logs, caches, archives, or full source datasets.
