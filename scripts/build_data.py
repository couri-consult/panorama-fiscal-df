"""Orchestrator: builds data.json by combining live API data with the manual XLSX.

Strategy
--------
The dashboard's index.html consumes a JSON whose top-level keys mirror the previous Excel
sheet names (kpis, investimentos, caixa, capag, capag_historico, pessoal, clp_ranking,
ppps, ppps_projecao). We start from the manual XLSX (which has all of them today) and
overlay API-derived values as their loaders come online. If an API call fails, we keep
whatever was in the manual sheet — the dashboard always renders.

Run:
    python scripts/build_data.py

Outputs data.json in the project root.
"""
import json
import os
import sys
import datetime
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from loaders import siconfi, ibge, capag, manual  # noqa: E402
import transforms  # noqa: E402

MANUAL_XLSX = os.path.join(ROOT, "manual", "panorama_manual.xlsx")
CAPAG_DIR = os.path.join(ROOT, "capag")
OUTPUT = os.path.join(ROOT, "data.json")

# Reference period for the current dashboard snapshot.
DEFAULT_RREO_YEAR = 2025
DEFAULT_RREO_BIM = 6
DEFAULT_RGF_YEAR = 2025
DEFAULT_RGF_QUAD = 3
DEFAULT_POP_YEAR = 2024


def safely(label, fn, fallback):
    """Try fn(); on any exception or empty return, log and return fallback."""
    try:
        result = fn()
    except Exception as e:
        print(f"  [{label}] FAILED: {type(e).__name__}: {e} — using fallback")
        return fallback, False
    if result is None or (hasattr(result, "__len__") and len(result) == 0):
        print(f"  [{label}] empty — using fallback")
        return fallback, False
    return result, True


def load_all_manual_sheets():
    """Load every sheet from manual.xlsx into a dict keyed by sheet name."""
    import openpyxl
    wb = openpyxl.load_workbook(MANUAL_XLSX, data_only=True)
    return {sheet: manual.read_sheet(wb, sheet) for sheet in wb.sheetnames}


def build():
    print(f"Building data.json (root={ROOT})\n")

    sources_used = {}  # tracks which sections came from API vs manual

    # ---- 1. Manual XLSX (always-available baseline) ----
    print("[1/4] Loading manual XLSX baseline...")
    sheets = load_all_manual_sheets()
    print(f"  sheets loaded: {list(sheets.keys())}")
    for k in sheets:
        sources_used[k] = "manual"

    # ---- 2. CAPAG (local CSVs) — overrides capag and capag_historico ----
    print("\n[2/4] Loading CAPAG history (local CSVs)...")
    capag_history, ok = safely("CAPAG", lambda: capag.load_history(CAPAG_DIR), {})
    if ok:
        sheets["capag"] = transforms.build_capag_current(capag_history, DEFAULT_RREO_YEAR)
        sheets["capag_historico"] = transforms.build_capag_history(capag_history)
        sources_used["capag"] = "csv-local"
        sources_used["capag_historico"] = "csv-local"
        print(f"  override capag/capag_historico (years: {sorted(capag_history.keys())})")

    capag_nota = capag_history.get(DEFAULT_RREO_YEAR, {}).get("consolidado") if capag_history else None

    # ---- 3. IBGE (population) — used for per-capita derivations ----
    print(f"\n[3/4] Loading IBGE population for {DEFAULT_POP_YEAR}...")
    populacao_df, ok = safely("IBGE", lambda: ibge.fetch_population(DEFAULT_POP_YEAR), None)
    if ok:
        print(f"  população DF {DEFAULT_POP_YEAR}: {populacao_df:,}")

    # ---- 4. SICONFI (RREO + RGF) — overlay specific values when available ----
    # The Oracle ORDS pool throttles aggressively; we accept failures and keep manual values.
    print(f"\n[4/4] Loading SICONFI RREO {DEFAULT_RREO_YEAR}/{DEFAULT_RREO_BIM}º bim and RGF {DEFAULT_RGF_YEAR}/{DEFAULT_RGF_QUAD}º quad...")
    rreo_balanco, ok_rreo = safely(
        "RREO Anexo 01",
        lambda: siconfi.fetch_rreo(DEFAULT_RREO_YEAR, DEFAULT_RREO_BIM, "RREO-Anexo 01"),
        [],
    )
    rgf_dtp, ok_rgf_dtp = safely(
        "RGF Anexo 01",
        lambda: siconfi.fetch_rgf(DEFAULT_RGF_YEAR, DEFAULT_RGF_QUAD, "RGF-Anexo 01"),
        [],
    )
    rgf_caixa, ok_rgf_caixa = safely(
        "RGF Anexo 05",
        lambda: siconfi.fetch_rgf(DEFAULT_RGF_YEAR, DEFAULT_RGF_QUAD, "RGF-Anexo 05"),
        [],
    )

    if ok_rreo:
        # TODO: extract specific rows once we confirm the column shape:
        #   - Despesa com investimento liquidada até o bimestre
        #   - Receita de impostos realizada
        #   - Dotação autorizada
        sources_used["_siconfi_rreo_rows"] = len(rreo_balanco)
    if ok_rgf_dtp:
        # TODO: RCL line; Despesa com pessoal % RCL
        sources_used["_siconfi_rgf_dtp_rows"] = len(rgf_dtp)
    if ok_rgf_caixa:
        # TODO: Disponibilidade de caixa líquida; recursos não vinculados
        sources_used["_siconfi_rgf_caixa_rows"] = len(rgf_caixa)

    # ---- Compose final data.json ----
    data = {
        "_meta": {
            "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "rreo_period": f"{DEFAULT_RREO_YEAR}/{DEFAULT_RREO_BIM}",
            "rgf_period": f"{DEFAULT_RGF_YEAR}/{DEFAULT_RGF_QUAD}",
            "populacao_df_year": DEFAULT_POP_YEAR,
            "populacao_df": populacao_df,
            "capag_nota_consolidada": capag_nota,
            "sources": sources_used,
        },
        "kpis": sheets.get("kpis", []),
        "investimentos": sheets.get("investimentos", []),
        "caixa": sheets.get("caixa", []),
        "capag": sheets.get("capag", []),
        "capag_historico": sheets.get("capag_historico", []),
        "pessoal": sheets.get("pessoal", []),
        "clp_ranking": sheets.get("clp_ranking", []),
        "ppps": sheets.get("ppps", []),
        "ppps_projecao": sheets.get("ppps_projecao", []),
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nWrote {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")
    print(f"Sources: {json.dumps(sources_used, ensure_ascii=False)}")


if __name__ == "__main__":
    try:
        build()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
