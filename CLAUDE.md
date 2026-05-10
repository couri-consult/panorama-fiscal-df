# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Single-page dashboard ("Panorama Fiscal do DF") that visualizes fiscal indicators for the Brazilian Federal District. The entire app is a single static `index.html` — no build step, no package manager, no tests. It fetches data at runtime from a published Excel workbook and renders KPIs, tables, and Chart.js charts.

## Architecture

- **`index.html`** — the whole app. Inline CSS + inline JS (ES5-style, no modules). Loaded via CDN: Chart.js 4.4.1 and SheetJS (`xlsx`) 0.18.5.
- **Data source** — `EXPORT_URL` at the top of the `<script>` block (currently `https://couri-consult.github.io/panorama-fiscal-df/panorama_fiscal_df.xlsx`). The local `panorama_fiscal_df.xlsx` in this directory is the authoring copy; the published copy on GitHub Pages is what the dashboard actually reads at runtime.
- **`panorama_fiscal_df.gsheet`** — Google Sheets shortcut to the same data (editing surface for non-devs). The `.xlsx` is exported from there.
- **`dashboard_fiscal_df_v2.pdf`** — static design/spec reference.

### Runtime flow (`init()` near the bottom of index.html)

1. `fetch(EXPORT_URL)` → `XLSX.read()` parses the workbook.
2. Each named sheet is read via `readSheet(wb, name)` into an array of objects (rows keyed by header name).
3. One `renderXxx` function per section writes into a pre-declared DOM node by `id`.

### Sheet → renderer map

| Sheet | Renderer | DOM target |
|---|---|---|
| `kpis` | `renderKpis` | `#kpi-grid` (expects columns: `chave`, `valor_bilhoes`, `sub`, `cor`; `chave` is looked up in `labelMap`) |
| `investimentos` | `renderInvestimento` | `#inv-table` (columns: `estado`, `pct`, `ranking`, `destaque`) |
| `caixa` | `renderCaixaChart` | `#chartCaixa` (columns: `ano`, `caixa_liquido`, `nao_vinculado` in reais) |
| `capag` | `renderCapag` | `#capag-table` (columns: `indicador`, `nota`, `badge`, `valor`, `obs`, `conceito`) |
| `capag_historico` | `renderCapagHist` | `#capag-hist` (columns: `ano`, `endividamento`, `poupanca`, `liquidez`, `consolidado`) |
| `pessoal` | `renderPessoal` | `#pessoal-table` (key/value shape: `chave`/`valor`; keys `atual_pct`, `alerta_pct`, `prudencial_pct`, `maximo_pct`, `rcl_bi`) |
| `clp_ranking` | `renderCLP` | `#clp-table` (columns: `indicador`, `posicao`, `conceito`) |
| `ppps` | `renderPPPs` | `#ppp-list` (columns: `nome`, `status` — "A contratar"/"Suspenso"/else) |
| `ppps_projecao` | `renderPPPProj` | `#ppp-kpis`, `#chartPPP` (columns: `ano`, `pct`, `despesas_ppp`) |

Helpers: `num()` parses Brazilian-style decimals (comma → dot); `fbi()` formats reais as `R$ X.X bi`; `clean()` trims; `bdg()` builds colored badges. The CAPAG consolidated nota is currently hardcoded (`renderCapag(capag, 'C')` in `init`) rather than read from the sheet.

## Running / developing

No build. Open `index.html` in a browser — but `fetch` against the published URL requires either serving the file over HTTP (e.g. `python -m http.server` from this directory) or opening via a file:// path that the browser's CORS rules allow for the GitHub Pages URL. For local data iteration, change `EXPORT_URL` to a local path and serve via a local HTTP server.

When changing data shape: update the sheet in `panorama_fiscal_df.xlsx`, re-publish to the GitHub Pages URL, and if columns changed, update the matching `renderXxx` function (column names are referenced as string literals).

## Conventions

- All UI copy and data labels are in Portuguese (pt-BR). Preserve the language when editing.
- Color system lives in `:root` CSS variables at the top of `<style>` — reuse these rather than adding new hex values.
- Keep the single-file structure; do not introduce a bundler or framework unless explicitly asked.

## Design system

Fonts loaded from Google Fonts (added as `<link>` tags before the `<style>` block):
- Titles / KPI values / card-titles / section-titles: **Poppins** 600, 700 → `var(--font-title)`
- Body / nav / legends: **Inter** 400, 500 → `var(--font-body)`

CSS variables (`:root`):

| Variable | Value | Usage |
|---|---|---|
| `--g800` | `#1B5E20` | Header bg, tooltip bg, dark text on green |
| `--g700` | `#2E7D32` | Section titles, card titles, links |
| `--g600` / `--g500` | `#4CAF50` | Primary green (buttons, KPI top border, highlights) |
| `--g300` | `#66BB6A` | Hover states, light green accents |
| `--g200` | `#A5D6A7` | Section title border, header sub-text |
| `--g100` | `#E8F5E9` | Table headers bg, badge bg, positive backgrounds |
| `--red` | `#c0392b` | Negative indicators (unchanged) |
| `--amber` | `#c47a10` | Warning indicators (unchanged) |
| `--blue` | `#1a5fa6` | Informational indicators (unchanged) |
| `--lgray` / `--muted` | `#6B7280` | Secondary text, legends, fonte labels |
| `--bg` | `#F5F5F5` | Page background |
| `--card` | `#FFFFFF` | Card / KPI background |
| `--border` | `#E5E7EB` | Card borders, table separators |
| `--text` | `#1A1A1A` | Primary text |
| `--font-title` | `'Poppins',sans-serif` | Title font stack |
| `--font-body` | `'Inter',sans-serif` | Body font stack |
| `--radius` | `14px` | Card / KPI / agenda-box border-radius |
| `--shadow` | `0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)` | Soft shadow on cards, KPIs, nav |
