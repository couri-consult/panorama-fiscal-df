"""Portal da Transparência loader.

Endpoint usado:
    GET https://api.portaldatransparencia.gov.br/api-de-dados/despesas/por-orgao
        ?ano=AAAA&orgao=25915          (25915 = Fundo Constitucional do DF)

Autenticação: header `chave-api-dados: <TOKEN>`.
O token é obtido em https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email
e lido daqui via variável de ambiente TRANSPARENCIA_TOKEN.

Como configurar o token localmente:
    1. Criar um arquivo `.env` na raiz do projeto (já está no .gitignore) com:
           TRANSPARENCIA_TOKEN=<seu_token>
    2. Antes de rodar o build, exportar:
           export TRANSPARENCIA_TOKEN=<seu_token>          (bash)
           $env:TRANSPARENCIA_TOKEN="<seu_token>"          (PowerShell)
    3. Ou usar python-dotenv (não adicionei dependência ainda).

Limites: 90 req/min (06h–23h59), 300 req/min (00h–05h59). Para o build atual
fazemos 1 chamada por execução, sem preocupação.
"""
import os
import time
import requests

BASE = "https://api.portaldatransparencia.gov.br"
FCDF_ORGAO = "25915"  # código SIAFI do Fundo Constitucional do DF
UA = "panorama-fiscal-df/1.0"


def _get_token():
    """Read token from env. Returns None if not set (loader stays disabled)."""
    return os.environ.get("TRANSPARENCIA_TOKEN")


def _get(path, params=None, retries=3, backoff=4):
    """Authenticated GET against the Portal da Transparência API."""
    token = _get_token()
    if not token:
        return None
    url = f"{BASE}{path}"
    headers = {"chave-api-dados": token, "Accept": "application/json", "User-Agent": UA}
    last = None
    delay = backoff
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
            else:
                # 401/403/etc — won't recover with retry, raise immediately
                raise RuntimeError(f"HTTP {r.status_code} — {r.text[:200]}")
        except requests.RequestException as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < retries:
            print(f"  retry {attempt}/{retries} in {delay}s ({last})")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"GET failed after {retries} attempts: {url} — {last}")


def fetch_fcdf_execution(year):
    """Fetch FCDF annual expense aggregates (empenho/liquidação/pagamento).

    Returns a dict with the raw response if API call succeeds, or None if no token
    is configured. The shape of the response is `DespesaAnualPorOrgaoDTO` — a list
    with one element (the order itself) containing fields like `empenhado`,
    `liquidado`, `pago`.
    """
    if not _get_token():
        print("[Transparência] TRANSPARENCIA_TOKEN não configurado — pulando (fallback manual)")
        return None
    print(f"[Transparência] Despesas FCDF (órgão {FCDF_ORGAO}) — ano {year}")
    data = _get("/api-de-dados/despesas/por-orgao", params={"ano": year, "orgao": FCDF_ORGAO})
    if not data:
        return None
    print(f"  {len(data)} registros")
    return data


def extract_fcdf_total(response, fase="empenhado"):
    """Pull a single numeric value from the response.

    `fase` can be 'empenhado', 'liquidado', or 'pago'. The dashboard's "Orçamento
    FCDF" KPI is usually shown as the empenhado total (LOA executada).
    Returns the value as float (BRL), or None if the response is empty/unexpected.
    """
    if not response:
        return None
    # The endpoint returns an array; first entry is the order aggregate
    item = response[0] if isinstance(response, list) else response
    # field names per swagger: `orgaoSuperior`, `orgao`, `empenhado`, `liquidado`, `pago`
    raw = item.get(fase)
    if raw is None:
        return None
    # Portal da Transparência returns BR-formatted strings like "23.371.555.913,88".
    # Strip thousands separator (.) first, then swap decimal (,) for (.).
    try:
        s = str(raw).replace(".", "").replace(",", ".")
        return float(s)
    except (TypeError, ValueError):
        return None
