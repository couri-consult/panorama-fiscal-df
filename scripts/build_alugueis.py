"""Gera alugueis.json a partir da planilha de locacao de imoveis em manual/.

Fonte: manual/planilha-de-locacao-de-imoveis-2-e-32025-para-processo-em-
cumprimento-a-lei-distrital.csv  (CSV ;-delimitado, encoding latin-1).

Consumido por dashboard_alugueis_gdf.html via fetch('alugueis.json').
Rode este script sempre que a planilha em manual/ for atualizada.
"""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "manual" / (
    "planilha-de-locacao-de-imoveis-2-e-32025-"
    "para-processo-em-cumprimento-a-lei-distrital.csv"
)
OUT_PATH = ROOT / "alugueis.json"

# --- Curadoria: nome curto do orgao ---------------------------------------
# A planilha traz o nome completo. Encurtamos para caber nos eixos dos graficos.


def short_org(nome: str) -> str:
    s = (nome or "").strip()
    if not s:
        return "Não informado"
    s = re.sub(r"\s+do Distrito Federal\b", "", s)
    s = re.sub(r"^Secretaria de Estado de ", "SE ", s)
    s = re.sub(r"^Administração Regional ", "RA ", s)
    s = re.sub(r"^Instituto de ", "Inst. ", s)
    return s.strip()


# --- Curadoria: agrupamento de familias empresariais ----------------------
# A planilha lista cada CNPJ separadamente; agrupamos variantes da mesma
# familia para que os graficos de proprietario consolidem a concentracao.
OWNER_GROUPS = [
    (("SARKIS",), "Sarkis (todas variantes)"),
    (("PAULO OCTAVIO", "PAULO OCTÁVIO", "PO 700"), "Grupo Paulo Octávio"),
    (("PHENICIA", "PHENÍCIA"), "Grupo Phenícia"),
    (("ESTRUTURAL EMPREENDIMENTOS",), "Estrutural Empreendimentos"),
    (("SERRA BONITA",), "Serra Bonita Imóveis"),
]


def owner_group(pn_clean: str) -> str:
    up = pn_clean.upper()
    for keys, label in OWNER_GROUPS:
        if any(k in up for k in keys):
            return label
    return pn_clean


# --- Parsers ---------------------------------------------------------------
def parse_money(s: str):
    """'R$ 744.861,43' -> 744861.43"""
    s = (s or "").replace("R$", "").replace(".", "").replace(",", ".").strip()
    if not s:
        return None
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def parse_num(s: str):
    """'54,07' ou '111' -> float"""
    s = (s or "").replace(".", "").replace(",", ".").strip()
    if not s:
        return None
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def parse_int(s: str):
    digits = re.sub(r"\D", "", s or "")
    return int(digits) if digits else None


_PRAZO_RE = re.compile(r"(\d+)\s*\(\s*(\d{2}/\d{2}/\d{4})\s*\)")


def parse_prazo(s: str):
    """'36 (12/07/2024)' -> (36, '12/07/2024')"""
    m = _PRAZO_RE.search(s or "")
    if not m:
        return None, None
    return int(m.group(1)), m.group(2)


_CNPJ_RE = re.compile(r"\s*\([\d./\-]+\)\s*$")


def clean_owner(pn: str) -> str:
    """'MULTI ... LTDA (38.044.723/0001-65)' -> 'MULTI ... LTDA'"""
    return _CNPJ_RE.sub("", (pn or "").strip()).strip()


# --- Build -----------------------------------------------------------------
def build():
    with CSV_PATH.open(encoding="latin-1", newline="") as fh:
        rows = list(csv.reader(fh, delimiter=";"))

    contratos = []
    for r in rows[1:]:
        if len(r) < 11:
            continue
        orgao = (r[0] or "").strip() or "Não informado"
        pm, da = parse_prazo(r[7])
        pn = clean_owner(r[10])
        contratos.append(
            {
                "o": orgao,
                "oc": short_org(orgao),
                "e": (r[1] or "").strip(),
                "vm": parse_money(r[4]),
                "m2t": parse_num(r[5]),
                "m2u": parse_num(r[6]),
                "pm": pm,
                "da": da,
                "gt": parse_money(r[8]),
                "p": parse_int(r[9]),
                "pn": pn,
                "gp": owner_group(pn),
            }
        )

    payload = {
        "_meta": {
            "updated_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "fonte": (
                "Planilha de Locação de Imóveis — 2º e 3º trimestres de 2025, "
                "publicada em cumprimento à legislação distrital de transparência"
            ),
            "csv_origem": str(CSV_PATH.relative_to(ROOT)).replace("\\", "/"),
            "total_contratos": len(contratos),
        },
        "contratos": contratos,
    }

    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"alugueis.json gerado: {len(contratos)} contratos -> {OUT_PATH}")


if __name__ == "__main__":
    build()
