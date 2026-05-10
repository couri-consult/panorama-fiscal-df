"""Orchestrator: builds data.json by combining live API data with the manual XLSX.

Strategy
--------
The dashboard's index.html consumes a JSON whose top-level keys mirror the previous Excel
sheet names (kpis, investimentos, caixa, capag, capag_historico, pessoal, clp_ranking,
ppps, ppps_projecao). We start from the manual XLSX as a baseline and overlay API-derived
values when the loaders succeed. If an API call fails, the manual value is preserved.

Run:
    python scripts/build_data.py
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
    """Try fn(); on exception or empty return, log and return fallback."""
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
    import openpyxl
    wb = openpyxl.load_workbook(MANUAL_XLSX, data_only=True)
    return {sheet: manual.read_sheet(wb, sheet) for sheet in wb.sheetnames}


def fmt_bi(reais, decimals=1):
    return f"R$ {reais/1e9:.{decimals}f} bi".replace(".", ",")


def fmt_mi(reais):
    return f"R$ {reais/1e6:.0f} mi"


def update_kpi(kpis, chave, **fields):
    """Find the kpi row by `chave` and update the given fields in place."""
    for row in kpis:
        if row.get("chave") == chave:
            row.update(fields)
            return True
    return False


def update_pessoal(pessoal_rows, chave, value):
    for row in pessoal_rows:
        if row.get("chave") == chave:
            row["valor"] = value
            return True
    return False


def build():
    print(f"Building data.json (root={ROOT})\n")
    sources = {}

    # ---- 1. Manual baseline ----
    print("[1/4] Loading manual XLSX baseline...")
    sheets = load_all_manual_sheets()
    print(f"  sheets: {list(sheets.keys())}")
    for k in sheets:
        sources[k] = "manual"

    # ---- 2. CAPAG (CSV local) ----
    print("\n[2/4] Loading CAPAG (CSVs)...")
    capag_history, ok = safely("CAPAG", lambda: capag.load_history(CAPAG_DIR), {})
    if ok:
        sheets["capag"] = transforms.build_capag_current(capag_history, DEFAULT_RREO_YEAR)
        sheets["capag_historico"] = transforms.build_capag_history(capag_history)
        sources["capag"] = "csv-local"
        sources["capag_historico"] = "csv-local"
        print(f"  override CAPAG (years {sorted(capag_history.keys())})")
    capag_nota = capag_history.get(DEFAULT_RREO_YEAR, {}).get("consolidado") if capag_history else None

    # ---- 3. IBGE população ----
    print(f"\n[3/4] Loading IBGE população {DEFAULT_POP_YEAR}...")
    populacao_df, ok_pop = safely("IBGE", lambda: ibge.fetch_population(DEFAULT_POP_YEAR), None)
    if ok_pop:
        print(f"  população DF {DEFAULT_POP_YEAR}: {populacao_df:,}")

    # ---- 4. SICONFI (RREO + RGF) ----
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

    # Extract specific values & overlay into kpis/pessoal
    rreo_vals = siconfi.extract_rreo_balanco(rreo_balanco) if ok_rreo else {}
    rgf_dtp_vals = siconfi.extract_rgf_dtp(rgf_dtp) if ok_rgf_dtp else {}
    rgf_caixa_vals = siconfi.extract_rgf_caixa(rgf_caixa) if ok_rgf_caixa else {}

    print("\nValores extraídos do SICONFI:")
    for k, v in {**rreo_vals, **rgf_dtp_vals, **rgf_caixa_vals}.items():
        if v is not None:
            unit = "" if k.startswith("pct") else " R$" if isinstance(v, (int, float)) and abs(v) > 1e6 else ""
            print(f"  {k} = {v}{unit}")

    # Overlay on KPIs and pessoal sheet
    kpis = sheets.get("kpis", [])
    if rreo_vals.get("orcamento_dotacao_atualizada"):
        update_kpi(kpis, "orcamento_df", valor_bilhoes=fmt_bi(rreo_vals["orcamento_dotacao_atualizada"]))
        sources["kpi.orcamento_df"] = "siconfi-rreo-anexo01"

    rcl = rgf_dtp_vals.get("rcl")
    inv = rreo_vals.get("investimento_liquidado")
    if rcl and inv:
        pct = (inv / rcl) * 100
        update_kpi(kpis, "investimento_rcl",
                   valor_bilhoes=f"{pct:.1f}%".replace(".", ","))
        sources["kpi.investimento_rcl"] = "siconfi-rreo+rgf"

    if capag_nota:
        update_kpi(kpis, "capag", valor_bilhoes=capag_nota)
        sources["kpi.capag"] = "csv-local"

    # NOTE: 'caixa' KPI value depends on the right TOTAL row (vinculados + não vinculados)
    # which we still need to confirm. Leaving as manual until then.

    # Pessoal sheet from RGF DTP
    pessoal = sheets.get("pessoal", [])
    if rgf_dtp_vals.get("pct_pessoal_rcl_ajustada") is not None:
        update_pessoal(pessoal, "atual_pct", round(rgf_dtp_vals["pct_pessoal_rcl_ajustada"], 2))
        sources["pessoal.atual_pct"] = "siconfi-rgf"
    if rcl:
        update_pessoal(pessoal, "rcl_bi", round(rcl / 1e9, 2))
        sources["pessoal.rcl_bi"] = "siconfi-rgf"

    # ---- Compose final data.json ----
    data = {
        "_meta": {
            "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "rreo_period": f"{DEFAULT_RREO_YEAR}/{DEFAULT_RREO_BIM}",
            "rgf_period": f"{DEFAULT_RGF_YEAR}/{DEFAULT_RGF_QUAD}",
            "populacao_df_year": DEFAULT_POP_YEAR,
            "populacao_df": populacao_df,
            "capag_nota_consolidada": capag_nota,
            "raw_siconfi": {
                "rreo_balanco": rreo_vals,
                "rgf_dtp": rgf_dtp_vals,
                "rgf_caixa": rgf_caixa_vals,
            },
            "sources": sources,
        },
        "kpis": kpis,
        "investimentos": sheets.get("investimentos", []),
        "caixa": sheets.get("caixa", []),
        "capag": sheets.get("capag", []),
        "capag_historico": sheets.get("capag_historico", []),
        "pessoal": pessoal,
        "clp_ranking": sheets.get("clp_ranking", []),
        "ppps": sheets.get("ppps", []),
        "ppps_projecao": sheets.get("ppps_projecao", []),
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nWrote {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")
    print(f"Sources used: {json.dumps(sources, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    try:
        build()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
