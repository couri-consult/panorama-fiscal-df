"""Portal da Transparência loader: FCDF execution data (órgão 25915).

The Portal da Transparência has an open REST API at https://api.portaldatransparencia.gov.br
but most endpoints require an API token (free, registered).

If a token is available via env var TRANSPARENCIA_TOKEN, this module fetches FCDF execution.
Otherwise it returns None and the caller should fall back to manual data.
"""
import os
from ._http import get_json


def fetch_fcdf_execution(year):
    """Fetch FCDF total executed expense for a given year. Returns float or None if no token."""
    token = os.environ.get("TRANSPARENCIA_TOKEN")
    if not token:
        print("[Transparência] TRANSPARENCIA_TOKEN not set — skipping FCDF fetch (use manual value)")
        return None

    # Endpoint TBC: empenho/orgao/25915 with year filter
    # Token goes in 'chave-api-dados' header (per Portal da Transparência docs).
    # Stub: uses despesas/items endpoint as placeholder; adjust once the exact endpoint is confirmed.
    print(f"[Transparência] FCDF execution {year} (TODO: confirm endpoint)")
    # When confirmed, call: get_json(url, params=..., headers={'chave-api-dados': token})
    return None
