"""SICONFI loader: RREO and RGF for the Federal District (Governo do DF, id_ente=53).

Docs: http://apidatalake.tesouro.gov.br/docs/siconfi/

Each row has columns: exercicio, demonstrativo, periodo, periodicidade, instituicao,
cod_ibge, uf, populacao, anexo, esfera, rotulo, coluna, cod_conta, conta, valor.

We filter rows by `cod_conta` (machine-stable account code) + `coluna` (column header) +
sometimes `conta` (when same cod_conta groups multiple lines, like RGF Anexo 05 where
each cod_conta has rows for different "TOTAL DOS RECURSOS..." subtotals).
"""
import time
from ._http import get_json

BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
# DF as a state-level entity uses cod_ibge=53 (UF code).
# Note: 5300108 = Brasília as a municipality (Cod_instituicoes_siconfi.pdf p3 vs p1).
# For the executive government specifically the cod_siconfi is "53EX".
DF_ID_ENTE = 53

THROTTLE_SLEEP = 3  # SICONFI's ORDS pool rate-limits aggressively; pause between calls.


def _normalize(rows):
    return [{k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()} for r in rows]


def fetch_rreo(year, periodo, anexo):
    """Fetch a RREO annex for the DF at a given bimester."""
    print(f"[SICONFI] RREO {year}/{periodo}º bim — {anexo}")
    data = get_json(
        f"{BASE}/rreo",
        params={
            "an_exercicio": year,
            "nr_periodo": periodo,
            "co_tipo_demonstrativo": "RREO",
            "id_ente": DF_ID_ENTE,
            "no_anexo": anexo,
        },
    )
    items = _normalize(data.get("items", []))
    print(f"  {len(items)} rows")
    time.sleep(THROTTLE_SLEEP)
    return items


def fetch_rgf(year, quad, anexo, poder="E"):
    """Fetch a RGF annex for the DF at a given quarter (Q periodicity)."""
    print(f"[SICONFI] RGF {year}/{quad}º quad — {anexo} (poder={poder})")
    data = get_json(
        f"{BASE}/rgf",
        params={
            "an_exercicio": year,
            "in_periodicidade": "Q",
            "nr_periodo": quad,
            "co_tipo_demonstrativo": "RGF",
            "co_poder": poder,
            "id_ente": DF_ID_ENTE,
            "no_anexo": anexo,
        },
    )
    items = _normalize(data.get("items", []))
    print(f"  {len(items)} rows")
    time.sleep(THROTTLE_SLEEP)
    return items


def find_value(rows, *, cod_conta, coluna, conta=None):
    """Extract a single numeric value from a SICONFI dataset, filtering by cod_conta + coluna
    (and optionally `conta` to disambiguate when one cod_conta has multiple sub-rows)."""
    for r in rows:
        if r.get("cod_conta") != cod_conta:
            continue
        if r.get("coluna") != coluna:
            continue
        if conta is not None and r.get("conta") != conta:
            continue
        return r.get("valor")
    return None


# ── RREO Anexo 01 — Balanço Orçamentário ─────────────────────────
def extract_rreo_balanco(rows):
    """Extract budget figures from RREO Anexo 01 rows.

    Returns dict with:
      - orcamento_total_dotacao: linha TOTAL DAS DESPESAS (XII) = (X + XI), dotação atualizada
      - investimento_liquidado: linha INVESTIMENTOS, coluna despesas liquidadas até o bimestre
      - receita_impostos_realizada: linha Impostos, coluna receitas realizadas até o bimestre
    All values are in BRL.

    Note: SICONFI's RREO uses current MCASP layout. The line "(VIII)" in older RREO is
    now "DespesasExcetoIntraOrcamentarias"; the total *including intras* is `TotalDespesas`
    (XII = X + XI, where X = SUBTOTAL = VIII + IX and XI = amortização da dívida/refinanciamento).
    """
    return {
        "orcamento_total_dotacao": find_value(
            rows, cod_conta="TotalDespesas", coluna="DOTAÇÃO ATUALIZADA (e)"
        ),
        "investimento_liquidado": find_value(
            rows, cod_conta="Investimentos", coluna="DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)"
        ),
        "receita_impostos_realizada": find_value(
            rows, cod_conta="Impostos", coluna="Até o Bimestre (c)"
        ),
    }


# ── RGF Anexo 01 — DTP / Apuração do Limite Legal ────────────────
def extract_rgf_dtp(rows):
    """Extract personnel-expense indicators from RGF Anexo 01.

    Returns: rcl, despesa_pessoal_total, pct_pessoal_rcl_ajustada.
    """
    return {
        "rcl": find_value(rows, cod_conta="ReceitaCorrenteLiquidaLimiteLegal", coluna="Valor"),
        "rcl_ajustada": find_value(rows, cod_conta="ReceitaCorrenteLiquidaAjustada", coluna="Valor"),
        "despesa_pessoal_total": find_value(
            rows, cod_conta="DespesaComPessoalTotal", coluna="TOTAL (ÚLTIMOS 12 MESES) (a)"
        ),
        "pct_pessoal_rcl_ajustada": find_value(
            rows, cod_conta="DespesaComPessoalTotal", coluna="% sobre a RCL Ajustada"
        ),
    }


# ── RGF Anexo 05 — Disponibilidade de Caixa ──────────────────────
def extract_rgf_caixa(rows):
    """Extract cash-availability figures from RGF Anexo 05.

    The Anexo 05 is a matrix: each row groups multiple `conta` lines under one cod_conta.
    We want the "TOTAL DOS RECURSOS NÃO VINCULADOS (I)" line for "Disponibilidade líquida"
    (after RPNP inscription), plus the totalised liquid availability figure.
    """
    # Coluna name is very long; SICONFI keeps it verbatim.
    coluna_liq = "DISPONIBILIDADE DE CAIXA LÍQUIDA (APÓS A INSCRIÇÃO EM RESTOS A PAGAR NÃO PROCESSADOS DO EXERCÍCIO) (i) = (g - h)"
    return {
        "caixa_liquido_total_nao_vinculado": find_value(
            rows, cod_conta="DisponibilidadeDeCaixaLiquida",
            coluna=coluna_liq, conta="TOTAL DOS RECURSOS NÃO VINCULADOS (I)"
        ),
        # The "caixa líquido" headline number that the dashboard shows is the TOTAL across
        # all sources (vinculados + não vinculados). The cod_conta DisponibilidadeDeCaixaLiquida
        # exposes that as another `conta` value — we'll discover it once we run against real data.
    }
