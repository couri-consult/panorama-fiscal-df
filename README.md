# Panorama Fiscal do DF — Dashboard

Dashboard estático (HTML + JS) que apresenta indicadores fiscais do Distrito Federal. Os dados ficam em uma planilha Excel publicada no GitHub Pages e são carregados pelo navegador em tempo de execução.

- **Painel ao vivo:** https://couri-consult.github.io/panorama-fiscal-df/
- **Fonte dos dados:** `panorama_fiscal_df.xlsx` (editado no Google Sheets e publicado no GitHub)

---

## Estrutura do projeto

```
dashboard/
├── index.html                 # Dashboard completo (HTML + CSS + JS inline)
├── panorama_fiscal_df.gsheet  # Atalho para a planilha no Google Drive (superfície de edição)
├── panorama_fiscal_df.xlsx    # Cópia local exportada da planilha do Google
├── dashboard_fiscal_df_v2.pdf # Referência de layout/design
├── CLAUDE.md                  # Instruções técnicas para o Claude Code
└── README.md                  # Este arquivo
```

### Como o dashboard funciona

1. O navegador abre `index.html` (servido pelo GitHub Pages).
2. O JavaScript faz `fetch` do arquivo `panorama_fiscal_df.xlsx` publicado no GitHub Pages.
3. A biblioteca **SheetJS** lê as abas da planilha e o **Chart.js** desenha os gráficos.
4. Cada aba da planilha alimenta uma seção específica do painel.

### Abas da planilha e seções do painel

| Aba da planilha      | Seção do painel                                 |
| -------------------- | ----------------------------------------------- |
| `kpis`               | Cartões da Visão Geral (topo)                   |
| `investimentos`      | Ranking Investimento/RCL por estado             |
| `caixa`              | Gráfico "Disponibilidade de caixa (R$ bi)"      |
| `capag`              | Tabela CAPAG — Nota Consolidada                 |
| `capag_historico`    | Histórico consolidado da CAPAG                  |
| `pessoal`            | Poder Executivo — % da RCL / LRF                |
| `clp_ranking`        | Ranking CLP — Solidez Fiscal                    |
| `ppps`               | Lista de PPPs contratadas e a contratar         |
| `ppps_projecao`      | Gráfico de comprometimento da RCL com PPPs      |

> ⚠️ **Não renomeie as abas nem as colunas** sem também atualizar o `index.html` — os nomes são referenciados como strings literais no código (função `renderXxx` correspondente).

---

## Atualização bimestral

A atualização é feita a cada **dois meses**, após a publicação do novo RREO (Relatório Resumido de Execução Orçamentária) e dos dados do Siconfi/Tesouro.

### Passo 1 — Coletar os dados novos

Fontes de referência (já citadas em cada caixa do painel):

- **Siconfi/Tesouro** — https://siconfi.tesouro.gov.br/siconfi/index.jsf
- **CAPAG** — https://www.tesourotransparente.gov.br/temas/estados-e-municipios/capacidade-de-pagamento-capag
- **Ranking CLP** — https://rankingdecompetitividade.org.br/estados/
- **RREO do DF** — publicado bimestralmente pela SEEC-DF

### Passo 2 — Editar a planilha no Google Sheets

1. Abra o arquivo `panorama_fiscal_df.gsheet` (clique duplo — abre no navegador).
2. Atualize cada aba com os novos valores, mantendo **os mesmos nomes de coluna**.
3. Para os KPIs (aba `kpis`), atualize `valor_bilhoes` e `sub` de cada linha.
4. Para gráficos históricos (`caixa`, `capag_historico`, `ppps_projecao`), **acrescente uma nova linha** com o ano/período novo — não sobrescreva anos antigos.
5. Revise se as tooltips / notas nas colunas `conceito` e `obs` continuam coerentes.

### Passo 3 — Exportar para `.xlsx`

No Google Sheets:

1. Menu **Arquivo → Fazer download → Microsoft Excel (.xlsx)**.
2. Salve o arquivo baixado com o nome exato **`panorama_fiscal_df.xlsx`** (substituindo a cópia local nesta pasta).

### Passo 4 — Publicar no GitHub

Veja a seção [Como subir arquivos no GitHub](#como-subir-arquivos-no-github) abaixo. Em resumo: faça upload do `panorama_fiscal_df.xlsx` atualizado para o repositório `couri-consult/panorama-fiscal-df`.

### Passo 5 — Validar

1. Aguarde ~1–2 minutos após o commit (tempo de build do GitHub Pages).
2. Abra https://couri-consult.github.io/panorama-fiscal-df/ em uma aba anônima (para evitar cache).
3. Confira:
   - Os cartões da Visão Geral mostram os valores novos.
   - Os gráficos (caixa, PPPs) têm o novo período.
   - Nenhuma seção aparece vazia (indicaria erro de leitura de aba/coluna).
4. Em caso de erro: abra o DevTools (F12) → aba **Console** para ver a mensagem.

---

## Como subir arquivos no GitHub

O repositório é **`couri-consult/panorama-fiscal-df`** e o GitHub Pages serve o conteúdo da branch `main` na raiz.

### Opção A — Pela interface web (mais simples, recomendado para atualização bimestral)

1. Acesse https://github.com/couri-consult/panorama-fiscal-df
2. Clique no arquivo que quer substituir (ex.: `panorama_fiscal_df.xlsx`).
3. Clique no ícone de **lápis** (Edit) ou no botão **Delete** para remover e depois subir a nova versão.
   - Para arquivos binários (`.xlsx`), use **Add file → Upload files** na raiz do repositório e arraste o arquivo novo — isso sobrescreve o existente.
4. Na caixa **Commit changes** embaixo da página:
   - Escreva uma mensagem curta, ex.: `Atualização bimestral — fev/2026`.
   - Marque **Commit directly to the main branch**.
   - Clique em **Commit changes**.
5. O GitHub Pages reconstrói automaticamente em 1–2 minutos.

### Opção B — Via linha de comando (Git)

Pré-requisitos: [Git instalado](https://git-scm.com/download/win) e repositório clonado localmente.

```bash
# Na primeira vez: clonar o repositório
git clone https://github.com/couri-consult/panorama-fiscal-df.git
cd panorama-fiscal-df

# Copie o .xlsx atualizado desta pasta para dentro do repositório local
# (substituindo o arquivo existente)

# Commit e push
git add panorama_fiscal_df.xlsx
git commit -m "Atualização bimestral — fev/2026"
git push origin main
```

### Opção C — Via GitHub Desktop

1. Abra o [GitHub Desktop](https://desktop.github.com/) com o repositório aberto.
2. Arraste o arquivo atualizado para a pasta do repositório local.
3. Confira as mudanças detectadas na janela do Desktop.
4. Escreva a mensagem de commit e clique **Commit to main** → **Push origin**.

---

## Sistema de design

O tema visual do painel segue as definições abaixo, todas centralizadas em variáveis CSS no bloco `:root` do `index.html`. Para alterar qualquer cor ou fonte, edite apenas as variáveis — não adicione valores hex ou nomes de fontes diretamente nas regras CSS.

### Tipografia

Fontes carregadas do Google Fonts (tags `<link>` antes do `<style>`):

| Uso | Família | Pesos |
| --- | ------- | ----- |
| Títulos, valores KPI, card-titles, seção | Poppins | 600, 700 |
| Corpo, nav, legendas | Inter | 400, 500 |

### Paleta de cores

| Variável | Valor | Uso |
| -------- | ----- | --- |
| `--g800` | `#1B5E20` | Header, fundo de tooltips, verde escuro |
| `--g700` | `#2E7D32` | Títulos de seção e card, links |
| `--g600` / `--g500` | `#4CAF50` | Verde principal — bordas de destaque, botões |
| `--g300` | `#66BB6A` | Hover, acentos verdes suaves |
| `--g200` | `#A5D6A7` | Borda de títulos de seção, texto secundário no header |
| `--g100` | `#E8F5E9` | Fundo de cabeçalho de tabela, badges positivos |
| `--red` | `#c0392b` | Indicadores negativos |
| `--amber` | `#c47a10` | Indicadores de atenção |
| `--blue` | `#1a5fa6` | Indicadores informativos |
| `--lgray` / `--muted` | `#6B7280` | Texto secundário, legendas, fontes |
| `--bg` | `#F5F5F5` | Fundo da página |
| `--card` | `#FFFFFF` | Fundo de cards e KPIs |
| `--border` | `#E5E7EB` | Bordas de cards e separadores de tabela |
| `--text` | `#1A1A1A` | Texto principal |

### Forma

| Variável | Valor | Uso |
| -------- | ----- | --- |
| `--radius` | `14px` | Border-radius de cards, KPIs, agenda-boxes e modal |
| `--shadow` | `0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)` | Sombra suave em cards, KPIs e nav |

---

## Alterações de código (layout, cores, novas seções)

Alterações no **`index.html`** (layout, textos fixos, cores, novas seções) seguem o mesmo fluxo de upload ao GitHub — substitua o `index.html` no repositório pela versão editada desta pasta.

Pontos importantes antes de mexer no HTML:

- Paleta de cores está em variáveis CSS no topo do `<style>` (`:root{...}`). Reutilize-as — não adicione novos valores hex diretamente nas regras.
- Adicionar uma **nova seção que puxa dados** exige três passos:
  1. Criar uma nova aba na planilha com as colunas necessárias.
  2. Adicionar o `<div>` / `<canvas>` na seção correspondente no HTML.
  3. Criar uma função `renderMinhaSeção(rows)` em JS e chamá-la dentro de `init()` com `readSheet(wb, 'nome_da_aba')`.
- Leia o `CLAUDE.md` para ver o mapeamento completo aba → função renderizadora.

---

## Problemas comuns

| Sintoma                                       | Causa provável                                                  |
| --------------------------------------------- | --------------------------------------------------------------- |
| Painel fica travado em "Carregando dados..."  | `.xlsx` não foi publicado / URL incorreta / erro de CORS        |
| Uma seção aparece vazia                       | Aba renomeada ou coluna com nome diferente do esperado          |
| Valores aparecem como "NaN" ou `R$ NaN bi`    | Célula com texto em vez de número; verificar `valor_bilhoes`    |
| Gráfico não atualiza após upload              | Cache do navegador — abrir aba anônima ou Ctrl+F5               |

---

## Fontes dos dados

- Siconfi / Tesouro Nacional
- Tesouro Transparente (CAPAG)
- Painel TCDF
- Beneficiômetro SEEC
- CLP — Ranking de Competitividade dos Estados
- RREO (Relatório Resumido de Execução Orçamentária) — SEEC-DF
