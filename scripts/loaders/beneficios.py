"""Beneficios tributários (Beneficiômetro DF) — loader e agregadores.

Fonte: dados.df.gov.br — dataset "renuncias-fiscais-beneficiometro"
Arquivo: beneficiometro/renuncias-{ano}.txt (download manual quando atualizar)

Layout (pipe-delimited, UTF-8 com BOM):
    Ano de competência | CNPJ | BENEFICIÁRIO | SETOR ICMS | SETOR ISS |
    TRIBUTO | TIPO BENEFÍCIO | BENEFICIO | CAPITULAÇÃO LEGAL | Vigência |
    Valor do benefício

Os campos SETOR ICMS / SETOR ISS são alternativos (um ou outro, raramente
ambos), no formato "<letter><N dígitos> - <descrição CNAE>".
O valor vem em formato BR (vírgula como decimal, ponto como milhar).
"""
import csv
import os
import re
from collections import defaultdict


def parse_br_number(s):
    """Converte '237186728,30737' → float. Aceita string ou número."""
    if s is None or s == "":
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


# Mapeamento por palavras-chave (case-insensitive) na descrição CNAE.
# Ordem importa: a primeira regra que casar ganha.
SECTOR_KEYWORDS = [
    # (rótulo curto, lista de palavras-chave que disparam)
    ("Saúde",            ["medicamento", "hospitalar", "farmac", "medicinai",
                          "produtos médicos", "ortopédic", "odontoló", "cirúrg",
                          "saúde", "clínic", "hospital"]),
    ("Abastecimento",    ["aliment", "carnes", "frutas", "verduras", "frigorífic",
                          "abate", "bebid", "laticín", "leite", "açúcar",
                          "supermercad", "hipermercad", "padar", "doces",
                          "mercadorias em geral", "atacadista de produtos"]),
    ("Combustíveis",     ["combustív", "petróleo", "lubrific", "gasol"]),
    ("Construção",       ["construç", "edifíc", "obras", "obras de",
                          "incorporaç", "engenh"]),
    ("Imobiliário",      ["imóvei", "imobiliár", "imóvel próprio", "imóvel residen",
                          "loteamen"]),
    ("Veículos",         ["automóv", "veícul", "motociclet", "camionet",
                          "caminhõ", "automotor", "peças e acessór"]),
    ("Móveis e decoração", ["mobiliári", "móvel", "móveis", "decoraç"]),
    ("Vestuário e calçados", ["vestuár", "tecidos", "roupas", "calçad",
                              "artigos do vestuário"]),
    ("Eletro / Tecnologia", ["instrumentos e materiais", "equipamento de informát",
                             "computador", "celular", "eletrodoméstic",
                             "eletrônic", "software", "tecnologia da informaç"]),
    ("Logística",        ["transport", "armazenag", "logístic", "courier",
                          "carga", "frete", "rodoviár"]),
    ("Hotelaria e turismo", ["hotel", "hospedag", "turism", "alojament"]),
    ("Restaurantes / Alimentação", ["restaurante", "lanchonet", "bar", "café"]),
    ("Cultura, esporte e lazer", ["cultur", "esport", "lazer", "entretenim",
                                  "espetácul", "exibição"]),
    ("Educação",         ["educaç", "ensino", "escola", "universid"]),
    ("Agropecuária",     ["agropecu", "pintos de um dia", "criação", "cultivo",
                          "agríc"]),
    ("Industrial",       ["fabricaç", "indústr", "produção de "]),
    ("Comércio (outros)", ["comércio "]),  # catch-all para G* que não casou acima
    ("Serviços (outros)", ["serviços", "ativid"]),
]


def infer_sector_short(setor_full):
    """Recebe 'G464510100 - Comércio atacadista de instrumentos e materiais para uso médico'
    e devolve um rótulo curto: 'Saúde'."""
    if not setor_full:
        return "Pessoa física" if False else "Sem setor"
    text = setor_full.lower()
    for label, kws in SECTOR_KEYWORDS:
        for kw in kws:
            if kw in text:
                return label
    return "Outros"


def _row_setor(r):
    """Devolve setor ICMS, caso vazio o ISS, ou vazio."""
    return (r.get("SETOR ICMS") or "").strip() or (r.get("SETOR ISS") or "").strip()


def load(path):
    """Lê o arquivo e devolve lista de dicts já com setor inferido e valor float."""
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="|")
        for r in reader:
            setor = _row_setor(r)
            beneficiario = (r.get("BENEFICIÁRIO") or "").strip()
            rows.append({
                "ano": r.get("Ano de competência", "").strip(),
                "cnpj": (r.get("CNPJ") or "").strip(),
                "beneficiario": beneficiario,
                "setor": setor,
                "setor_curto": "Pessoa física" if beneficiario == "Pessoa Física" else infer_sector_short(setor),
                "tributo": (r.get("TRIBUTO") or "").strip(),
                "tipo": (r.get("TIPO BENEFÍCIO") or "").strip(),
                "beneficio": (r.get("BENEFICIO") or "").strip(),
                "valor": parse_br_number(r.get("Valor do benefício")),
            })
    return rows


def aggregate(rows, top_n=10):
    """Produz as 3 agregações usadas no painel.

    Retorna dict com:
      total            : soma geral
      por_tributo      : [{nome, valor, pct}], ordenado desc
      top_beneficios   : [{nome, valor, pct}], top N + 1 linha "Demais"
      top_beneficiarios: [{nome, setor_curto, valor, pct}], top N + 1 linha "Demais"
    """
    total = sum(r["valor"] for r in rows) or 1.0  # evita /0 absurdo

    # Por tributo (todos)
    bt = defaultdict(float)
    for r in rows:
        bt[r["tributo"]] += r["valor"]
    por_tributo = [
        {"nome": k, "valor": v, "pct": v / total * 100}
        for k, v in sorted(bt.items(), key=lambda x: -x[1])
    ]

    # Top benefícios + Demais
    bb = defaultdict(float)
    for r in rows:
        bb[r["beneficio"]] += r["valor"]
    sorted_b = sorted(bb.items(), key=lambda x: -x[1])
    top_b = sorted_b[:top_n]
    rest_b = sorted_b[top_n:]
    top_beneficios = [
        {"nome": k, "valor": v, "pct": v / total * 100} for k, v in top_b
    ]
    if rest_b:
        rest_total = sum(v for _, v in rest_b)
        top_beneficios.append({
            "nome": f"Demais ({len(rest_b)})",
            "valor": rest_total,
            "pct": rest_total / total * 100,
        })

    # Top beneficiários + Demais (com setor)
    by = defaultdict(lambda: {"valor": 0.0, "setor_curto": ""})
    for r in rows:
        d = by[r["beneficiario"]]
        d["valor"] += r["valor"]
        # mantém o setor curto do primeiro registro com setor presente
        if not d["setor_curto"] and r["setor_curto"] not in ("", "Sem setor"):
            d["setor_curto"] = r["setor_curto"]
    sorted_y = sorted(by.items(), key=lambda x: -x[1]["valor"])
    top_y = sorted_y[:top_n]
    rest_y = sorted_y[top_n:]
    top_beneficiarios = [
        {
            "nome": nome,
            "setor_curto": info["setor_curto"] or "Sem setor",
            "valor": info["valor"],
            "pct": info["valor"] / total * 100,
        }
        for nome, info in top_y
    ]
    if rest_y:
        rest_total = sum(info["valor"] for _, info in rest_y)
        top_beneficiarios.append({
            "nome": f"Demais ({len(rest_y)})",
            "setor_curto": "",
            "valor": rest_total,
            "pct": rest_total / total * 100,
        })

    return {
        "total": total,
        "por_tributo": por_tributo,
        "top_beneficios": top_beneficios,
        "top_beneficiarios": top_beneficiarios,
    }


def load_and_aggregate(directory, year):
    """Conveniência: lê beneficiometro/renuncias-{year}.txt e devolve agregado."""
    path = os.path.join(directory, f"renuncias-{year}.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Beneficiometro file not found: {path}")
    rows = load(path)
    return aggregate(rows)
