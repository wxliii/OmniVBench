# OmniVBench

Project website for OmniVBench and the Omni-R2V Dataset.

Live site: https://wxliii.github.io/OmniVBench/

This `gh-pages` branch contains the website and its media assets. The [`main` branch](https://github.com/wxliii/OmniVBench/tree/main) contains the project introduction and is reserved for evaluation code.

This repository is self-contained: HTML, CSS, JavaScript, figures, and the referenced dataset / benchmark media. No backend or external filesystem paths are required.

## Preview

Run `python3 -m http.server 8000` in this directory and open `http://localhost:8000`.

## GitHub Pages

In Settings → Pages, choose Deploy from a branch, `gh-pages`, and `/ (root)`. Keep `.nojekyll` in the repository.

## Media

Benchmark: selected examples with all available model outputs. Videos retain their full duration, resized to a maximum dimension of 720px, encoded as silent H.264 up to 24fps. Reference images use WebP up to 1280px. Dataset media retain the current preview versions. Original research media and paper scores are unchanged.

Benchmark dataset: [OmniVBench on Hugging Face](https://huggingface.co/datasets/wxli318/OmniVBench).

## Editing

`index.html` / `dataset.js` control the dataset page. `benchmark.html` / `benchmark.js` control the benchmark page. `styles.css` and `immersive.css` define the presentation. `data.js` and `benchmark-data.js` contain the current sample selection and relative asset paths.

Do not commit local audit logs, caches, archives, or full source datasets.

## Updating the website

Edit and preview this branch, then commit and push to `gh-pages`. GitHub Pages publishes updates automatically. Keep website media on this branch; add evaluation code to `main`.
