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
import re
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

from loaders import siconfi, ibge, capag, manual, transparencia, beneficios  # noqa: E402
import transforms  # noqa: E402

MANUAL_XLSX = os.path.join(ROOT, "manual", "panorama_manual.xlsx")
CAPAG_DIR = os.path.join(ROOT, "capag")
BENEFICIOMETRO_DIR = os.path.join(ROOT, "beneficiometro")
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


def _build_riscos_fiscais(rows, top_n=10):
    """Agrega a aba 'riscos_fiscais' (Anexo XII da LDO) em totais + top N.

    Retorna dict com:
      total           : soma geral (R$)
      por_bloco       : [{bloco, valor}] (Passivos Contingentes / Demais Riscos Fiscais)
      por_dependencia : [{tipo, valor}]  (STF, Câmbio, Operacional, Contratual, etc.)
      top_n           : [{nome_curto, descricao, valor, pct, dependencia, bloco}] ordem desc
      conc_top2_pct   : % representado pelos 2 maiores itens (mostra concentração)
    """
    if not rows:
        return None
    total = sum(float(r.get("valor") or 0) for r in rows) or 1.0

    from collections import defaultdict as _d
    bloco_d = _d(float); dep_d = _d(float)
    for r in rows:
        v = float(r.get("valor") or 0)
        bloco_d[str(r.get("bloco") or "").strip()] += v
        dep_d[str(r.get("dependencia") or "").strip()] += v

    por_bloco = [{"bloco": k, "valor": v} for k, v in sorted(bloco_d.items(), key=lambda x: -x[1])]
    por_dep = [{"tipo": k, "valor": v} for k, v in sorted(dep_d.items(), key=lambda x: -x[1])]

    sorted_rows = sorted(rows, key=lambda r: -float(r.get("valor") or 0))
    top = sorted_rows[:top_n]
    top_out = [{
        "nome_curto": str(r.get("nome_curto") or "").strip(),
        "descricao": str(r.get("descricao") or "").strip(),
        "valor": float(r.get("valor") or 0),
        "pct": float(r.get("valor") or 0) / total * 100,
        "dependencia": str(r.get("dependencia") or "").strip(),
        "bloco": str(r.get("bloco") or "").strip(),
    } for r in top]

    conc_top2 = sum(r["valor"] for r in top_out[:2]) / total * 100 if len(top_out) >= 2 else 0
    return {
        "total": total,
        "por_bloco": por_bloco,
        "por_dependencia": por_dep,
        "top_n": top_out,
        "conc_top2_pct": conc_top2,
    }


def load_all_manual_sheets():
    """Read every sheet from manual.xlsx, normalizing the `chave` column.

    Strips parenthetical suffixes from `chave` values (e.g. 'beneficios (R$ 1,00)'
    becomes 'beneficios') so the user can document units inline without breaking
    the chave→label mapping in index.html.
    """
    import openpyxl
    wb = openpyxl.load_workbook(MANUAL_XLSX, data_only=True)
    sheets = {sheet: manual.read_sheet(wb, sheet) for sheet in wb.sheetnames}
    for rows in sheets.values():
        for row in rows:
            ch = row.get("chave")
            if isinstance(ch, str):
                row["chave"] = re.sub(r"\s*\([^)]*\)\s*$", "", ch).strip()
    return sheets


def fmt_bi(reais, decimals=1):
    return f"R$ {reais/1e9:.{decimals}f} bi".replace(".", ",")


def _coerce_to_reais(value):
    """Accept either a numeric value (in reais) or a string like 'R$ 11,3 bi' and
    return a float in reais. Returns None if the input isn't parseable."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip()
    m = re.search(r"([\d.,]+)\s*bi", s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(".", "").replace(",", ".")) * 1e9
        except ValueError:
            return None
    # Try parsing plain BR number (e.g. "13400000000" or "13.400.000.000")
    s_clean = s.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s_clean)
    except ValueError:
        return None


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
    """Upsert: atualiza a linha existente pelo `chave`; se não existir, cria.
    Permite que o manual.xlsx tenha apenas os limites legais (alerta/prudencial/máximo),
    enquanto atual_pct e rcl_bi são adicionados em runtime a partir da API."""
    for row in pessoal_rows:
        if row.get("chave") == chave:
            row["valor"] = value
            return True
    pessoal_rows.append({"chave": chave, "valor": value})
    return True


def build():
    print(f"Building data.json (root={ROOT})\n")
    sources = {}

    # ---- 1. Manual baseline ----
    print("[1/4] Loading manual XLSX baseline...")
    sheets = load_all_manual_sheets()
    print(f"  sheets: {list(sheets.keys())}")
    for k in sheets:
        sources[k] = "manual"

    # ---- 2. CAPAG (CSV local + obs/conceito do manual) ----
    print("\n[2/4] Loading CAPAG (CSVs)...")
    capag_history, ok = safely("CAPAG", lambda: capag.load_history(CAPAG_DIR), {})
    if ok:
        # Indicators (notas + valores) vêm do CSV; mas obs e conceito ficam no
        # manual.xlsx para ser editável (mensagens de "Para nota A: < 60%..." e
        # as explicações longas). Faz merge por `indicador`.
        manual_capag = sheets.get("capag", [])
        manual_by_indicador = {str(r.get("indicador") or "").strip(): r for r in manual_capag}
        csv_capag = transforms.build_capag_current(capag_history, RREO_CLOSED_YEAR)
        for row in csv_capag:
            m = manual_by_indicador.get(row.get("indicador", ""))
            if m:
                if m.get("obs"):
                    row["obs"] = m["obs"]
                if m.get("conceito"):
                    row["conceito"] = m["conceito"]
        sheets["capag"] = csv_capag
        sheets["capag_historico"] = transforms.build_capag_history(capag_history)
        sources["capag"] = "csv-local+manual(obs)"
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
        # Sub: posição do DF no ranking nacional (vem da aba `investimentos`)
        invest_rows = sheets.get("investimentos", [])
        df_row = next((r for r in invest_rows if str(r.get("estado", "")).strip() == "DF"), None)
        sub_invest = ""
        if df_row and df_row.get("ranking"):
            sub_invest = f"{int(df_row['ranking'])}º lugar no Brasil"
        update_kpi(kpis, "investimento_rcl",
                   valor_bilhoes=f"{pct:.1f}%".replace(".", ","),
                   sub=sub_invest)
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

    # KPI beneficios: total vem do manual (Beneficiômetro é Qlik sem API).
    # Aceita valor_bilhoes como número (em reais) ou string já formatada.
    #
    # Denominador do sub "% da receita de impostos":
    # Preferimos a aba `kpis` linha auxiliar `receita de impostos` (manual —
    # extraída do RREO Anexo 8, que inclui receitas intra-orçamentárias e NÃO
    # está disponível no SICONFI/API).
    # Se a linha manual estiver vazia, caímos no SICONFI (Anexo 01, linha Impostos
    # da coluna "Até o Bimestre (c)"), que é uma proxy levemente subestimada.
    receita_impostos_manual = None
    for row in kpis:
        if str(row.get("chave", "")).startswith("receita de impostos"):
            receita_impostos_manual = _coerce_to_reais(row.get("valor_bilhoes"))
            break
    receita_impostos = receita_impostos_manual or rreo_vals.get("receita_impostos_realizada")

    if receita_impostos:
        for row in kpis:
            if row.get("chave") != "beneficios":
                continue
            beneficios_reais = _coerce_to_reais(row.get("valor_bilhoes"))
            if beneficios_reais is None:
                break
            pct = beneficios_reais / receita_impostos * 100
            row["sub"] = f"{pct:.0f}% da receita de impostos"
            sources["kpi.beneficios.sub"] = (
                "manual-rreo-anexo08" if receita_impostos_manual else "siconfi-rreo-calc"
            )
            break

    # Remove a linha auxiliar `receita de impostos` antes de gerar data.json —
    # é dado de entrada, não vira KPI card.
    kpis[:] = [r for r in kpis if not str(r.get("chave", "")).startswith("receita de impostos")]

    # ---- Beneficiômetro detalhado (dados.df.gov.br) ----
    # Lê o TXT publicado em beneficiometro/renuncias-{ano}.txt e gera:
    #   - 3 agregações para a nova seção do painel (tributo / top benefício / top beneficiário)
    #   - O valor total substitui o KPI beneficios (mais autoritativo que o número do XLSX)
    beneficiometro_ano = RREO_CLOSED_YEAR  # ex: 2025 (mesmo ano de fechamento do RREO)
    beneficios_agg = None
    try:
        beneficios_agg = beneficios.load_and_aggregate(BENEFICIOMETRO_DIR, beneficiometro_ano)
        print(f"\n[Beneficiometro] {beneficiometro_ano}: R$ {beneficios_agg['total']/1e9:.3f} bi"
              f" / {len(beneficios_agg['top_beneficiarios'])-1} top beneficiários + Demais")
        # Substitui o valor do KPI beneficios pelo total exato do dataset
        for row in kpis:
            if row.get("chave") == "beneficios":
                row["valor_bilhoes"] = fmt_bi(beneficios_agg["total"])
                # recalcula o sub usando o novo total
                if receita_impostos:
                    pct = beneficios_agg["total"] / receita_impostos * 100
                    row["sub"] = f"{pct:.0f}% da receita de impostos"
                sources["kpi.beneficios"] = "dados-df-beneficiometro"
                break
    except FileNotFoundError as e:
        print(f"\n[Beneficiometro] arquivo não encontrado: {e} — KPI usa fallback do manual")

    # Normalize KPI valor_bilhoes coming from the manual XLSX to the dashboard's
    # "R$ X,Y bi" display format:
    #   - numbers (int/float in reais) → fmt_bi
    #   - strings already in "R$ X,Y bi" → kept as-is
    #   - strings that look like raw BR-formatted numbers ("13447362101,71") → fmt_bi
    #   - non-monetary strings ("C", "4,7%", "R$ 570 mi") → kept as-is
    for row in kpis:
        v = row.get("valor_bilhoes")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            row["valor_bilhoes"] = fmt_bi(v)
        elif isinstance(v, str):
            s = v.strip()
            # Skip strings that already look formatted or are non-monetary
            if re.search(r"\bbi\b", s, re.IGNORECASE) or re.search(r"\bmi\b", s, re.IGNORECASE):
                continue
            if "%" in s or len(s) <= 2:
                continue
            # Try to coerce — if parseable to a meaningful reais value, reformat
            n = _coerce_to_reais(s)
            if n is not None and abs(n) >= 1e6:  # ≥ 1 milhão = monetary, not a small number
                row["valor_bilhoes"] = fmt_bi(n)

    # KPI caixa: TOTAL (IV) do RGF atual
    caixa_total = rgf_caixa_vals.get("caixa_liquido_total")
    if caixa_total is not None:
        # display as "R$ X mi" when below 10 bi (more readable for small values)
        if abs(caixa_total) < 10e9:
            label = f"R$ {caixa_total/1e6:.0f} mi"
        else:
            label = fmt_bi(caixa_total)
        cor = "red" if caixa_total < 1e9 else "amber" if caixa_total < 3e9 else "green"
        update_kpi(kpis, "caixa",
                   valor_bilhoes=label,
                   sub=f"Disponibilidade líquida — dez/{DEFAULT_RGF_YEAR}",
                   cor=cor)
        sources["kpi.caixa"] = "siconfi-rgf-anexo05"

    # Tabela histórica de caixa — busca RGF Anexo 05 para cada ano de 2021 até DEFAULT_RGF_YEAR
    print(f"\nFetching caixa history {2021}..{DEFAULT_RGF_YEAR}")
    caixa_history = safely(
        "caixa history",
        lambda: siconfi.fetch_caixa_history(range(2021, DEFAULT_RGF_YEAR + 1)),
        [],
    )
    if isinstance(caixa_history, tuple):
        caixa_history, _ok = caixa_history
    if caixa_history:
        sheets["caixa"] = caixa_history
        sources["caixa"] = "siconfi-rgf-anexo05"
        print(f"  caixa history: {len(caixa_history)} anos")

    # Posição geral do DF no ranking de competitividade CLP (texto livre vindo
    # do manual.xlsx, aba 'clp_meta' linha 'pos_geral').
    clp_meta_rows = sheets.get("clp_meta", [])
    clp_pos_geral = ""
    for r in clp_meta_rows:
        if str(r.get("chave", "")).strip() == "pos_geral":
            clp_pos_geral = str(r.get("valor", "")).strip()
            break

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
            "clp_pos_geral": clp_pos_geral,
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
        "agenda": sheets.get("agenda", []),
        "beneficios_detalhado": beneficios_agg,  # None se o arquivo não existir
        "riscos_fiscais": _build_riscos_fiscais(sheets.get("riscos_fiscais", [])),
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
