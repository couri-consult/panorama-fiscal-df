# Referência Visual — Estilo "Donezo Dashboard"

Documento de referência extraído de um painel de produtividade. Use como base
para prompts de redesign, briefings ou design tokens. Os valores são
aproximações fiéis ao original, prontas para reuso.

---

## 1. Princípios gerais

- **Cards flutuantes sobre fundo cinza-claro.** Toda a interface vive em
  "ilhas" brancas separadas por gaps, em vez de um layout edge-to-edge.
- **Cor é informação, não decoração.** O verde aparece em poucos momentos
  pontuais (brand, item ativo, KPI âncora, CTA). O resto é tons de cinza.
- **Hierarquia por preenchimento, não por tamanho.** Botões primários e
  secundários têm a mesma forma — só mudam de sólido para outline.
- **Sombras mínimas.** A profundidade vem do contraste fundo cinza /
  superfície branca, não de drop shadows dramáticos.
- **Tudo respira.** Padding generoso, gaps consistentes, nenhum elemento
  colado em outro.

---

## 2. Estrutura de layout

- **3 zonas:** sidebar fixa à esquerda + topbar horizontal + área de
  conteúdo principal.
- **Wrapper externo** com padding `~14-20px` em todas as bordas, criando
  o efeito de cards flutuantes.
- **Gap entre blocos:** `~14px`.
- Topbar e conteúdo principal podem ser dois cards separados ou unificados
  numa mesma "ilha" branca.

---

## 3. Paleta de cores

```css
:root{
  /* Neutros */
  --bg:        #ececea;  /* fundo da página */
  --surface:   #ffffff;  /* superfície de cards */
  --border:    #ebebe6;  /* bordas muito sutis */

  /* Texto */
  --text:      #1a1f1a;  /* texto principal */
  --text-2:    #5b605b;  /* texto secundário */
  --text-3:    #9a9e9a;  /* placeholders, subs */

  /* Accent */
  --accent:        #1f8a4d;  /* verde principal */
  --accent-dark:   #176a3a;  /* texto sobre soft */
  --accent-soft:   #e3f2ea;  /* background de item ativo */

  /* Status (pílulas suaves) */
  --pos-soft:  #e3f2ea;  /* "Completed" — texto em var(--accent-dark) */
  --warn-soft: #fef3e2;  /* "In Progress" — texto em #b45309 */
  --neg-soft:  #fde8e8;  /* "Pending" / alerta — texto em #c63838 */
}
```

**Regra de ouro:** o verde aparece em **3-4 lugares no máximo** por tela
(brand mark, item ativo da sidebar, KPI âncora, botão primário).

---

## 4. Tipografia

- **Família:** sans-serif neutra e levemente arredondada — Inter, Plus
  Jakarta Sans, Manrope. Evitar Helvetica/Arial.
- **Peso:** o design usa principalmente 500 (medium), 600 (semibold) e
  700 (bold). Pouco texto em 400.

### Hierarquia

| Uso | Tamanho | Peso | Tracking |
|---|---|---|---|
| Page title ("Dashboard") | 28-32px | 700 | -0.02em |
| KPI value (números grandes) | 30-36px | 700 | -0.02em |
| Card title ("Project Analytics") | 15-16px | 600-700 | -0.01em |
| KPI label ("Total Projects") | 13px | 600 | normal |
| Body / descrições | 13-14px | 400-500 | normal |
| Sidebar section label ("MENU") | 10-11px | 600 | 0.12em + UPPERCASE |
| Trend pill / badge | 11-12px | 500-600 | normal |

**Importante:** os números são apresentados em sans-serif normal, não em
mono. Isso é adequado para apps de produtividade. **Para dashboards
analíticos densos (finanças, séries temporais, comparações precisas),
trocar por uma fonte mono com tabular-nums** (JetBrains Mono, IBM Plex
Mono) — caso contrário os números não alinham na vírgula decimal.

---

## 5. Cantos e sombras

### Border-radius em camadas

| Elemento | Radius |
|---|---|
| Cards externos (KPIs, blocos de conteúdo) | 18-20px |
| Search bar, ícones em círculo, botões retangulares | 10-12px |
| Pílulas (badges, status, "+ New") | 999px (total) |
| Avatares e ícones de ação circulares | 50% |
| Brand mark / ícones em quadrado | ~10px |

### Sombras

```css
--shadow-sm: 0 1px 2px rgba(20,30,20,.04);
--shadow-md: 0 4px 16px rgba(20,30,20,.05), 0 1px 3px rgba(20,30,20,.04);
```

Use `--shadow-sm` em cards estáticos e `--shadow-md` apenas em hover ou
em elementos elevados. **Nunca use sombras pesadas** — quebra a estética.

---

## 6. Espaçamento

| Onde | Valor |
|---|---|
| Padding interno de cards | 20-24px |
| Gap entre cards | 14-16px |
| Gap entre seções verticais | 24-32px |
| Padding do wrapper externo | 14-20px |

---

## 7. Sidebar

**Estrutura:**

1. **Brand no topo:** ícone colorido em quadrado arredondado (radius ~10px)
   + nome em peso 700 ao lado. Pode ter subtítulo cinza pequeno embaixo.
2. **Items agrupados por seção** com label em uppercase, tracking aberto
   e cinza claro (ex: "MENU", "GERAL").
3. **Items inativos:** ícone outline + texto cinza médio, sem fundo.
4. **Item ativo:** fundo `--accent-soft` + texto `--accent-dark` + uma
   barra vertical fina (3px) à esquerda do item, em verde sólido.
5. **Badges numéricas inline** (ex: contador de tarefas "12+") em pílula
   cinza suave à direita do label do item.

**Detalhes técnicos:**

- Ícones em estilo **outline (line icons)**, stroke 1.5-2px. Nunca filled.
- Padding de cada item: ~10px vertical, 12px horizontal.
- Border-radius do item: 10px.
- Gap entre ícone e texto: ~11px.

---

## 8. Topbar

- **Search bar com fundo `--bg`** (mesmo cinza do app, não branco) —
  funciona como "afundamento" visual.
- Atalho de teclado (⌘ F, Ctrl K) à direita do placeholder, em pílula
  branca com borda sutil.
- **Ícones de ação** (notificação, mensagens) em círculos `--bg` do mesmo
  tom da search bar. Tamanho ~36-40px.
- **Avatar + nome + email** num "chip" lado a lado, sem fundo. Avatar
  circular ~36px.

---

## 9. KPI cards (padrão central do design)

Esse é o componente mais distintivo. Anatomia de cada card:

```
┌─────────────────────────────┐
│  Total Projects        ↗   │  ← label + arrow icon (canto sup. dir.)
│                             │
│  24                         │  ← número grande, bold
│                             │
│  ▢ Increased from last mo.  │  ← trend pill (rodapé)
└─────────────────────────────┘
```

**Componentes:**

1. **Label** (canto sup. esq.): peso 600, tamanho 13px.
2. **Arrow icon** (canto sup. dir.): círculo cinza claro (`--bg`) com
   seta diagonal (↗). Tamanho ~30px. Sugere "expandir/detalhar" sem
   precisar de texto.
3. **Número grande:** 28-36px, peso 700, tracking apertado.
4. **Trend pill** (rodapé): pílula cinza com ícone (quadradinho ou seta)
   + texto curto descritivo. Substitui subtexto solto.

**Estado destacado (KPI âncora):**

- Fundo `--accent` sólido, texto branco.
- Arrow icon vira branco com seta verde escura.
- Trend pill com fundo branco semi-transparente.

**Variantes para alertas (em dashboards informativos):**

- Card permanece branco.
- **Apenas o número** muda de cor (vermelho para crítico, âmbar para
  atenção). Não pintar a borda inteira.

---

## 10. Botões

**Primário (CTA principal):**

- Verde sólido `--accent` + texto branco
- Arredondamento total (pílula, `border-radius: 999px`)
- Ícone à esquerda do texto (ex: "+", check, etc.)
- Padding: ~10px vertical, 18-20px horizontal
- Sombra muito sutil ou ausente

**Secundário:**

- Branco + borda 1px `--border` + texto `--text`
- Mesma forma de pílula
- Mesmo padding

**Princípio:** dois botões lado a lado, **mesma forma e tamanho**.
Hierarquia se dá apenas pelo preenchimento (sólido vs outline).

---

## 11. Status badges

Pílulas pequenas com **fundo colorido suave + texto da mesma cor escura**:

| Status | Fundo | Texto |
|---|---|---|
| Completed / sucesso | `--pos-soft` (#e3f2ea) | `--accent-dark` (#176a3a) |
| In Progress / atenção | `--warn-soft` (#fef3e2) | #b45309 |
| Pending / negativo | `--neg-soft` (#fde8e8) | #c63838 |

- Sem bordas.
- Padding apertado (~3px vertical, 10px horizontal).
- Tamanho de fonte: 11-12px, peso 500-600.
- Border-radius: total (pílula).

---

## 12. Visualizações de dados (cuidado!)

O painel original usa gráficos **decorativos**, não informativos:

- Barras vazias com hatching diagonal (linhas inclinadas).
- Barras preenchidas em verde sólido com cantos muito arredondados
  (forma de cápsula).
- Apenas a barra de destaque tem label numérica.
- Donut chart com hatching também — mais ilustração que gráfico.

**O que NÃO reusar para dashboards sérios:**

- Hatching diagonal vira ruído visual quando há muitas barras.
- Forma cápsula impede comparação precisa entre valores.
- Falta de gridlines e ticks numéricos compromete leitura.

**O que reusar com segurança:**

- Border-radius nas barras (~6-8px, não cápsula total).
- Paleta: barras na cor `--accent` ou em cinza neutro, com a barra
  destacada em outra cor (vermelho para alertas).
- Tooltip em fundo escuro (`#1a1f1a`) com cantos arredondados (8px).
- Gridlines muito sutis (`--border-soft`) e sem borda no eixo.
- Ticks em cinza claro (`--text-3`).

---

## 13. Ilustrações decorativas (atenção)

O painel tem cards com fundos escuros e ondulações verdes decorativas
("Time Tracker", footer da sidebar). Esses ornamentos:

- **Funcionam** em apps de produtividade leves, marketing, lifestyle.
- **Quebram credibilidade** em dashboards financeiros, jurídicos,
  médicos, fiscais ou qualquer contexto onde a seriedade do dado
  importa mais que o apelo visual.

Decida explicitamente se o seu contexto comporta esse tipo de elemento
ou não.

---

## 14. Resumo executivo (1 linha)

> Cards brancos arredondados sobre fundo cinza-claro, verde vibrante
> usado com parcimônia (3 momentos por tela), tipografia sans bold em
> hierarquia clara, KPI âncora em verde sólido, e tudo respira.
> **Atenção:** as visualizações de dados originais são decorativas
> demais para dashboards analíticos sérios.

---

## 15. Tokens prontos (copiar e colar)

```css
:root{
  /* Cores */
  --bg:#ececea;
  --surface:#ffffff;
  --border:#ebebe6;
  --border-soft:#f1f1ec;

  --text:#1a1f1a;
  --text-2:#5b605b;
  --text-3:#9a9e9a;

  --accent:#1f8a4d;
  --accent-dark:#176a3a;
  --accent-soft:#e3f2ea;

  --pos:#1f8a4d;       --pos-soft:#e3f2ea;
  --warn:#b45309;      --warn-soft:#fef3e2;
  --neg:#c63838;       --neg-soft:#fde8e8;
  --info:#2563a8;      --info-soft:#e6eef8;

  /* Sombras */
  --shadow-sm:0 1px 2px rgba(20,30,20,.04);
  --shadow-md:0 4px 16px rgba(20,30,20,.05),0 1px 3px rgba(20,30,20,.04);

  /* Cantos */
  --radius:18px;       /* cards externos */
  --radius-sm:12px;    /* search, botões retangulares, brand mark */
  --radius-pill:999px; /* pílulas, badges, botões CTA */

  /* Espaçamento */
  --pad-card:22px;
  --gap:14px;
  --gap-section:28px;
}

body{
  font-family:'Inter',system-ui,sans-serif;
  background:var(--bg);
  color:var(--text);
  font-size:14px;
  line-height:1.5;
  -webkit-font-smoothing:antialiased;
}
```
