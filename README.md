# Panorama Fiscal do DF — Dashboard

Dashboard estático que apresenta indicadores fiscais do Distrito Federal. Os dados são gerados localmente por um script Python que consulta APIs públicas (Siconfi/Tesouro, IBGE, Portal da Transparência) e os consolida em um `data.json` consumido pelo navegador.

- **Painel ao vivo:** https://couri-consult.github.io/panorama-fiscal-df/
- **Repositório:** `couri-consult/panorama-fiscal-df` (GitHub Pages serve `main` na raiz)

---

## Estrutura do projeto

```
panorama-fiscal-df/
├── index.html               # Dashboard (HTML + CSS + JS inline). Carrega data.json.
├── data.json                # Gerado pelo build. Versionado no git.
├── styles/tokens.css        # Variáveis CSS (cores, sombras, raios).
├── manual/
│   └── panorama_manual.xlsx # Só dados editáveis manualmente (sem fallback redundante).
├── capag/                   # CSVs anuais da CAPAG (download manual do Tesouro).
├── scripts/
│   ├── build_data.py        # Orquestrador: lê .env, chama loaders, gera data.json.
│   ├── transforms.py        # Helpers de formatação.
│   └── loaders/
│       ├── _http.py         # Cliente HTTP com retry/backoff.
│       ├── siconfi.py       # RREO + RGF do DF (id_ente=53).
│       ├── ibge.py          # População via SIDRA.
│       ├── capag.py         # Leitura dos CSVs locais.
│       ├── transparencia.py # Portal da Transparência (FCDF).
│       └── manual.py        # Lê o XLSX manual.
├── docs/                    # Notas de arquitetura e roadmap.
├── .env                     # NÃO COMMITAR. Guarda TRANSPARENCIA_TOKEN.
└── .gitignore
```

---

## Como o dashboard funciona

1. O navegador abre `index.html` (servido pelo GitHub Pages).
2. O JavaScript faz `fetch('data.json')`.
3. Cada chave do JSON alimenta uma função `renderXxx` do `index.html` (Chart.js para gráficos).

O `data.json` é gerado **offline** por `python scripts/build_data.py` e versionado no git — não há requisição a APIs externas em tempo de execução, então o painel é rápido e não tem problemas de CORS.

---

## Atualizando os dados

### Pré-requisitos (uma vez só)

```bash
# Python 3.10+ com pip
pip install requests openpyxl pandas pypdf

# Token do Portal da Transparência (necessário para o FCDF):
#   1. Acesse https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email
#   2. Faça login com gov.br (selo Prata ou Ouro)
#   3. Receba o token por email
#   4. Salve em .env (na raiz do projeto):
echo "TRANSPARENCIA_TOKEN=seu_token_aqui" > .env
```

> ⚠️ Se você pedir o token mais de uma vez, o anterior é invalidado. Use o último recebido.

### Atualizar bimestralmente (quando o RREO/RGF for publicado)

```bash
# 1. Gerar data.json novo
python scripts/build_data.py

# 2. Ver localmente (opcional)
python -m http.server 3000
# → abrir http://localhost:3000 no navegador

# 3. Publicar
git add data.json
git commit -m "Atualiza dados — [mês]/[ano]"
git push
```

GitHub Pages republica em 30-90 segundos. Para forçar reload no navegador: **Ctrl+Shift+R**.

### O que cada execução do build faz

- Consulta **SICONFI** (RREO 2026/1 + 2025/6 fechamento, RGF 2025/3) para orçamento, investimento, receita de impostos, RCL, despesa com pessoal, caixa.
- Consulta **Portal da Transparência** (FCDF dotação atualizada via web scraping da página `/orgaos/25915`).
- Consulta **IBGE SIDRA** (população do DF).
- Lê os **CSVs da CAPAG** locais (`capag/capagdosestados{ano}.csv`) — atualização manual quando o Tesouro publica novo.
- Lê o **manual.xlsx** para dados sem API equivalente (Beneficiômetro, CLP, PPPs, agenda, ranking 27 UFs).

### Atualizando dados que continuam manuais

Cada aba do `manual/panorama_manual.xlsx` contém **só o que o painel realmente usa**. O que cada aba contribui:

| Aba | Colunas usadas | Quando atualizar |
|---|---|---|
| `kpis` | só a linha `beneficios (R$ 1,00)` tem valor real (em reais) — as 5 outras linhas são anchors para ordem dos cards | Quando o Beneficiômetro SEEC publica novo valor mensal/anual |
| `investimentos` | `estado`, `pct`, `ranking`, `destaque` | Quando o RREO do fechamento de exercício for analisado para todos os UFs |
| `capag` | `indicador`, `obs`, `conceito` (nota/valor vêm dos CSVs) | Raramente — textos descritivos do card |
| `pessoal` | só limites legais da LRF (`alerta_pct`, `prudencial_pct`, `maximo_pct`) — atual e RCL vêm da API | Só se a legislação mudar (raríssimo) |
| `clp_ranking` | `indicador`, `posicao`, `conceito` (9 indicadores do Pilar Solidez Fiscal) | Anual quando o CLP publica nova edição |
| `clp_meta` | `pos_geral`, `pos_geral_obs`, `ano_ranking` | Junto com o `clp_ranking` |
| `ppps` | `nome`, `status` | Quando houver novo contrato ou mudança de status |
| `ppps_projecao` | `ano`, `despesas_ppp`, `rcl`, `pct` | Quando o RREO Anexo 13 trouxer projeção atualizada |
| `agenda` | `eixo`, `cor`, `titulo`, `item` | Quando a agenda propositiva for revisada |
| `riscos_fiscais` | `bloco`, `categoria`, `descricao`, `nome_curto`, `valor`, `dependencia` | Anualmente quando sair o novo PLDO (Anexo XII) |

Para **CAPAG anual**: baixar o CSV do Tesouro Transparente e salvar em `capag/capagdosestados{ano}.csv` (não vai no manual.xlsx).

Para **Beneficiômetro detalhado** (3 gráficos da seção Benefícios): baixar o TXT publicado pela SEEC-DF em
`https://www.dados.df.gov.br/dataset/renuncias-fiscais-beneficiometro` e salvar em
`beneficiometro/renuncias-{ano}.txt`. O loader detecta setor automaticamente a partir do CNAE.

Após editar, rode `update.bat` (ou `python scripts/build_data.py && git add ... && git commit && git push`).

---

## Como o índice de seções está mapeado

Cada chave do `data.json` alimenta uma seção do painel:

| Chave | Seção do painel | Fonte hoje |
|---|---|---|
| `kpis` | Cartões da Visão Geral | API SICONFI/Transparência + manual (só `beneficios`) |
| `investimentos` | Ranking Investimento/RCL por estado | manual |
| `caixa` | Gráfico Disponibilidade de Caixa (5 anos) | API SICONFI RGF Anexo 05 |
| `capag` + `capag_historico` | Tabela CAPAG | CSVs locais (nota/valor) + manual (obs/conceito) |
| `pessoal` | Despesa com Pessoal / LRF | API SICONFI RGF (atual + RCL) + manual (limites LRF) |
| `clp_ranking` | Ranking CLP — Pilar Solidez Fiscal | manual |
| `ppps` + `ppps_projecao` | PPPs | manual |
| `agenda` | Agenda de Recuperação Fiscal | manual |

> ⚠️ **Não renomeie as chaves do JSON nem suas colunas** sem também atualizar o `index.html` — os nomes são referenciados como string literais nas funções `renderXxx`.

---

## Visualizar a procedência dos dados

O `data.json` tem uma seção `_meta.sources` que mostra de onde cada KPI/seção veio:

```json
"_meta": {
  "sources": {
    "kpi.orcamento_df": "siconfi-rreo-atual",
    "kpi.fcdf": "portal-transparencia-scrape",
    "kpi.caixa": "siconfi-rgf-anexo05",
    "kpi.capag": "csv-local",
    "kpis": "manual"
  }
}
```

Útil pra debugar: se um KPI vier errado, olha a fonte e investiga lá.

---

## Sistema de design

Tema visual definido em variáveis CSS em `styles/tokens.css`. **Não adicione hex codes diretos em regras CSS** — sempre use as variáveis.

### Tipografia

| Uso | Família | Pesos |
|---|---|---|
| Títulos, valores KPI, card-titles | Poppins | 600, 700 |
| Corpo, nav, legendas | Inter | 400, 500 |

### Cores principais

| Variável | Valor | Uso |
|---|---|---|
| `--g700` / `--g600` | Verde STN | Títulos, botões |
| `--red` | `#c0392b` | Indicadores negativos |
| `--amber` | `#c47a10` | Atenção |
| `--blue` | `#1a5fa6` | Informativo |

Lista completa: ver bloco `:root` em `styles/tokens.css` e fallback no topo de `<style>` em `index.html`.

---

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| Painel mostra "Erro ao carregar dados" | `data.json` faltando ou inválido — rodar `python scripts/build_data.py` |
| Card aparece com valor antigo após push | Cache do navegador — Ctrl+Shift+R |
| Build falha com "Chave de API inválida" | Token do Transparência invalidado (você pediu mais de uma vez?) — registrar de novo |
| SICONFI retorna HTTP 429 | Rate limit do Oracle ORDS — esperar alguns minutos, o retry/backoff resolve a maior parte |
| FCDF não atualiza após push | Layout da página do Transparência pode ter mudado — ajustar regex em `transparencia.py:_ORC_ATUALIZADO_RE` |
| Pages não republica | Aguardar 30-90s; verificar Settings → Pages no GitHub se houve erro de build |

---

## Fontes dos dados

- **Siconfi / Tesouro Nacional** — https://apidatalake.tesouro.gov.br/docs/siconfi/ (RREO + RGF do DF, id_ente=53)
- **CAPAG** — https://www.tesourotransparente.gov.br/temas/estados-e-municipios/capacidade-de-pagamento-capag (download anual)
- **IBGE SIDRA** — https://servicodados.ibge.gov.br/api/v3/agregados/6579 (população)
- **Portal da Transparência** — https://api.portaldatransparencia.gov.br + scraping de `/orgaos/25915` (FCDF)
- **CLP Ranking** — https://rankingdecompetitividade.org.br/estados/ (manual)
- **Beneficiômetro SEEC-DF** — https://paineis.fazenda.df.gov.br/beneficiometro/ (Qlik, manual)
