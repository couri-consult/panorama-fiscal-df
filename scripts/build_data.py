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


def _load_dotenv(path):
    """Tiny inline .env reader (KEY=value, ignores comments/blanks). Avoids dotenv dep."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


_load_dotenv(os.path.join(ROOT, ".env"))

from loaders import siconfi, ibge, capag, manual, transparencia  # noqa: E402
import transforms  # noqa: E402

MANUAL_XLSX = os.path.join(ROOT, "manual", "panorama_manual.xlsx")
CAPAG_DIR = os.path.join(ROOT, "capag")
OUTPUT = os.path.join(ROOT, "data.json")

# Reference periods for the current dashboard snapshot.
# We use TWO RREO snapshots for different reasons:
#   - RREO_CURRENT (2026/1): latest published, used for "Orçamento DF em 2026"
#   - RREO_CLOSED  (2025/6): closing of 2025, used for investimento liquidado + receita
#     de impostos realizada (so we compare full-year fiscal values, not partial 2026).
RREO_CURRENT_YEAR = 2026
RREO_CURRENT_BIM = 1
RREO_CLOSED_YEAR = 2025
RREO_CLOSED_BIM = 6
DEFAULT_RGF_YEAR = 2025
DEFAULT_RGF_QUAD = 3
DEFAULT_POP_YEAR = 2024
FCDF_BUDGET_YEAR = 2026  # ano do orçamento FCDF a buscar no Portal da Transparência


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
        sheets["capag"] = transforms.build_capag_current(capag_history, RREO_CLOSED_YEAR)
        sheets["capag_historico"] = transforms.build_capag_history(capag_history)
        sources["capag"] = "csv-local"
        sources["capag_historico"] = "csv-local"
        print(f"  override CAPAG (years {sorted(capag_history.keys())})")
    capag_nota = capag_history.get(RREO_CLOSED_YEAR, {}).get("consolidado") if capag_history else None

    # ---- 3. IBGE população ----
    print(f"\n[3/4] Loading IBGE população {DEFAULT_POP_YEAR}...")
    populacao_df, ok_pop = safely("IBGE", lambda: ibge.fetch_population(DEFAULT_POP_YEAR), None)
    if ok_pop:
        print(f"  população DF {DEFAULT_POP_YEAR}: {populacao_df:,}")

    # ---- 4. SICONFI (RREO atual + fechamento) + RGF + Transparência ----
    print(f"\n[4/4] Loading APIs (Transparência FCDF, SICONFI RREO atual+fechamento, RGF {DEFAULT_RGF_YEAR}/{DEFAULT_RGF_QUAD}º quad)...")

    # FCDF *dotação atualizada* (web scrape — não tem API)
    fcdf_dotacao, ok_fcdf = safely(
        "Transparência FCDF (dotação)",
        lambda: transparencia.fetch_fcdf_dotacao_atualizada(FCDF_BUDGET_YEAR),
        None,
    )
    if ok_fcdf and fcdf_dotacao:
        update_kpi(sheets["kpis"], "fcdf",
                   valor_bilhoes=fmt_bi(fcdf_dotacao),
                   sub=f"Dotação atualizada {FCDF_BUDGET_YEAR}")
        sources["kpi.fcdf"] = "portal-transparencia-scrape"

    # RREO atual (orçamento DF 2026)
    rreo_current, ok_rreo_current = safely(
        f"RREO {RREO_CURRENT_YEAR}/{RREO_CURRENT_BIM} Anexo 01",
        lambda: siconfi.fetch_rreo(RREO_CURRENT_YEAR, RREO_CURRENT_BIM, "RREO-Anexo 01"),
        [],
    )
    # RREO fechamento (investimento e receita de impostos do ano completo anterior)
    rreo_balanco, ok_rreo = safely(
        f"RREO {RREO_CLOSED_YEAR}/{RREO_CLOSED_BIM} Anexo 01",
        lambda: siconfi.fetch_rreo(RREO_CLOSED_YEAR, RREO_CLOSED_BIM, "RREO-Anexo 01"),
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
    rreo_current_vals = siconfi.extract_rreo_balanco(rreo_current) if ok_rreo_current else {}
    rreo_vals = siconfi.extract_rreo_balanco(rreo_balanco) if ok_rreo else {}
    rgf_dtp_vals = siconfi.extract_rgf_dtp(rgf_dtp) if ok_rgf_dtp else {}
    rgf_caixa_vals = siconfi.extract_rgf_caixa(rgf_caixa) if ok_rgf_caixa else {}

    print("\nValores extraídos do SICONFI:")
    for label, vals in [("RREO atual", rreo_current_vals), ("RREO fechamento", rreo_vals),
                         ("RGF DTP", rgf_dtp_vals), ("RGF Caixa", rgf_caixa_vals)]:
        for k, v in vals.items():
            if v is not None:
                unit = "" if k.startswith("pct") else " R$" if isinstance(v, (int, float)) and abs(v) > 1e6 else ""
                print(f"  [{label}] {k} = {v}{unit}")

    # Overlay on KPIs and pessoal sheet
    kpis = sheets.get("kpis", [])
    # Orçamento DF: usar TOTAL DAS DESPESAS (XII) do RREO atual (2026/1)
    if rreo_current_vals.get("orcamento_total_dotacao"):
        update_kpi(kpis, "orcamento_df",
                   valor_bilhoes=fmt_bi(rreo_current_vals["orcamento_total_dotacao"]),
                   sub=f"Dotação atualizada {RREO_CURRENT_YEAR} (RREO {RREO_CURRENT_BIM}º bim)")
        sources["kpi.orcamento_df"] = "siconfi-rreo-atual"

    rcl = rgf_dtp_vals.get("rcl")
    # Investimento e receita de impostos vêm do fechamento (2025/6º bim)
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
            "rreo_current_period": f"{RREO_CURRENT_YEAR}/{RREO_CURRENT_BIM}",
            "rreo_closed_period": f"{RREO_CLOSED_YEAR}/{RREO_CLOSED_BIM}",
            "rgf_period": f"{DEFAULT_RGF_YEAR}/{DEFAULT_RGF_QUAD}",
            "populacao_df_year": DEFAULT_POP_YEAR,
            "populacao_df": populacao_df,
            "capag_nota_consolidada": capag_nota,
            "raw_siconfi": {
                "rreo_current": rreo_current_vals,
                "rreo_closed": rreo_vals,
                "rgf_dtp": rgf_dtp_vals,
                "rgf_caixa": rgf_caixa_vals,
            },
            "fcdf_dotacao_atualizada": fcdf_dotacao,
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
