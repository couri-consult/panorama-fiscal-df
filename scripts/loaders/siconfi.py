"""SICONFI loader: RREO and RGF for the Federal District (id_ente=5300108).

Docs: http://apidatalake.tesouro.gov.br/docs/siconfi/

Each call returns {'items': [row, ...]} where each row has columns like:
  exercicio, periodo, instituicao, anexo, conta, cod_conta, coluna, valor
We filter rows by `coluna` and `cod_conta`/`conta` to extract the indicators we want.
"""
import time
from ._http import get_json

BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
DF_ID_ENTE = 5300108  # IBGE code for the Federal District


def _normalize(rows):
    """Strip whitespace from string fields."""
    out = []
    for r in rows:
        out.append({k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
    return out


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
    print(f"  → {len(items)} rows")
    time.sleep(2)  # be gentle with the throttled ORDS pool
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
    print(f"  → {len(items)} rows")
    time.sleep(2)
    return items


def find_row(rows, *, coluna=None, cod_conta=None, conta_contains=None):
    """Find the first row matching the given filters. Useful for one-shot value extraction."""
    for r in rows:
        if coluna is not None and r.get("coluna") != coluna:
            continue
        if cod_conta is not None and r.get("cod_conta") != cod_conta:
            continue
        if conta_contains is not None and conta_contains.lower() not in (r.get("conta") or "").lower():
            continue
        return r
    return None
