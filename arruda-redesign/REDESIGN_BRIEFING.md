# REDESIGN_BRIEFING.md — ID Visual "Arruda"

Referência visual e exemplos práticos de aplicação. Use junto com `CLAUDE.md` (regras de escopo) e `tokens.css` (variáveis).

---

## 🎨 A vibe da id Arruda

**Institucional + orgânica.** Combina autoridade (verdes profundos) com vivacidade (verde-limão). A peça original equilibra três elementos:

1. **Gradiente verde profundo** como base — transmite seriedade fiscal/governamental.
2. **Padrão de folhagem sutil** no fundo — evoca natureza, sustentabilidade, regionalismo.
3. **Verde-limão como pontuação** — energia, modernidade, ação.

A tradução para dashboard fiscal preserva esses três elementos mas **ajusta as proporções**: muito mais espaço branco/off-white (legibilidade de números), folhagem só no header, e limão exclusivo para destaques semânticos.

---

## 🎯 Princípios de aplicação

### 1. Hierarquia tipográfica clara
- **Títulos (h1, h2):** sempre Playfair Display (serifa).
- **Corpo, labels, navegação:** Inter (sans-serif).
- **Números fiscais (KPI, tabelas, valores monetários):** JetBrains Mono.

A regra do número monoespaçado é não-negociável: comparações fiscais exigem alinhamento decimal correto.

### 2. Escassez do verde-limão
**Regra prática:** no máximo um elemento limão por viewport visível. Lugares aceitáveis:
- KPI principal de destaque (1 por seção)
- Badge de variação positiva
- Botão CTA primário
- Pin de localização (header)

**Lugares proibidos:**
- Background de cards múltiplos
- Cor de fundo de tabelas
- Bordas genéricas
- Texto corrido

### 3. Folhagem só no hero
O padrão de folhagem (`--pattern-foliage`) deve aparecer **apenas** no header principal, com `opacity: 0.06`. Em qualquer outra seção, polui e dificulta leitura de dados.

### 4. Cores semânticas com peso equivalente
Verde-limão (`--color-positive`) e vermelho (`--color-negative`) foram calibrados para ter peso visual equivalente. Use sempre o par — nunca destaque positivo sem o negativo correspondente.

---

## 📐 Exemplos de "antes/depois"

> Estes exemplos são **direções de refatoração**, não código para colar. Adapte aos seletores reais do projeto.

### Body e tipografia base

```css
/* ANTES (provável) */
body {
  font-family: Arial, sans-serif;
  background: #f4f4f4;
  color: #333;
}

/* DEPOIS */
body {
  font-family: var(--font-body);
  background: var(--color-surface-alt);
  color: var(--color-text-on-light);
  line-height: 1.5;
}

h1, h2, h3 {
  font-family: var(--font-display);
  color: var(--color-text-on-light);
}

/* Números em tabelas e KPIs */
.kpi-value, .table-numeric, td.numeric {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
```

### Header / Hero

```css
/* DEPOIS */
.header, .hero, header {
  background: var(--gradient-hero);
  color: var(--color-text-on-dark);
  padding: var(--space-12) var(--space-16);
  position: relative;
  overflow: hidden;
}

.header::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: var(--pattern-foliage);
  opacity: 0.06;
  pointer-events: none;
}

.header h1, .hero h1 {
  font-family: var(--font-display);
  font-size: var(--text-display);
  font-weight: var(--weight-bold);
}
```

### KPI Cards

```css
/* DEPOIS */
.kpi-card, .card, .indicator {
  background: var(--color-surface);
  border-radius: var(--radius-card);
  padding: var(--space-6);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}

.kpi-label {
  font-size: var(--text-label);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.kpi-value {
  font-family: var(--font-mono);
  font-size: var(--text-kpi);
  font-weight: var(--weight-bold);
  color: var(--color-text-on-light);
}
```

### Badges de variação (delta)

```css
.delta-positive, .badge-positive {
  background: var(--color-positive-bg);
  color: var(--color-accent-dark);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  font-weight: var(--weight-semibold);
  font-size: var(--text-small);
}

.delta-negative, .badge-negative {
  background: var(--color-negative-bg);
  color: var(--color-negative);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  font-weight: var(--weight-semibold);
  font-size: var(--text-small);
}
```

### Tabelas / Rankings

```css
.ranking-table, table {
  width: 100%;
  border-collapse: collapse;
}

.ranking-table th {
  text-align: left;
  font-size: var(--text-label);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border-strong);
}

.ranking-table td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.ranking-table td.numeric {
  font-family: var(--font-mono);
  text-align: right;
}

.ranking-table tr:hover {
  background: var(--color-surface-alt);
}

/* Destaque do DF (se houver) */
.ranking-table tr.highlight {
  background: var(--color-positive-bg);
}
```

### Gráficos (wrappers)

> ⚠️ **Importante:** edite apenas o wrapper e a paleta (via tokens). **Não edite a config interna do Chart.js/Plotly em arquivos `.js`.** Se a paleta atual estiver hardcoded em `.js`, pare e pergunte ao usuário.

```css
.chart-container, .chart-wrapper {
  background: var(--color-surface);
  border-radius: var(--radius-card);
  padding: var(--space-6);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border);
}

.chart-title {
  font-family: var(--font-display);
  font-size: var(--text-h3);
  color: var(--color-text-on-light);
  margin-bottom: var(--space-4);
}
```

**Paleta sugerida para gráficos** (passar para Chart.js/Plotly via JS apenas se o usuário autorizar):
```js
const arrudaPalette = [
  '#1A5A2E', '#A8E830', '#2D7A42', '#F2B90C',
  '#E84545', '#6B8276', '#0E3B1F', '#BFF055'
];
```

### Botões

```css
.btn-primary {
  background: var(--color-accent);
  color: var(--color-bg-deep);
  font-weight: var(--weight-bold);
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-btn);
  border: none;
  cursor: pointer;
  box-shadow: var(--shadow-pill-accent);
  transition: background var(--transition-fast);
}

.btn-primary:hover {
  background: var(--color-accent-hover);
}

.btn-secondary {
  background: transparent;
  color: var(--color-text-on-light);
  border: 1px solid var(--color-border-strong);
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-btn);
  cursor: pointer;
}
```

### Pills / Tags (estilo "Sudoeste")

```css
.tag-location, .pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-accent);
  color: var(--color-bg-deep);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-pill);
  font-weight: var(--weight-bold);
  font-size: var(--text-small);
  box-shadow: var(--shadow-pill-accent);
}
```

---

## ✅ Checklist final de revisão

Antes de considerar o redesign completo, verifique:

- [ ] Nenhum `.html` ou `.js` foi modificado (exceto a `<link>` das Google Fonts, se necessária).
- [ ] Nenhuma cor hexadecimal hardcoded permanece no CSS (tudo via `var(--color-*)`).
- [ ] Playfair Display em todos os títulos (h1, h2, h3).
- [ ] Inter no corpo e navegação.
- [ ] JetBrains Mono em todos os números fiscais (KPIs e células numéricas de tabelas).
- [ ] Padrão de folhagem aparece **apenas** no header.
- [ ] Verde-limão usado com escassez (≤ 1 elemento por viewport).
- [ ] Variações positivas e negativas usam o par `--color-positive` / `--color-negative`.
- [ ] Cards têm `border-radius: var(--radius-card)` e `box-shadow: var(--shadow-card)`.
- [ ] Pills/tags usam `border-radius: var(--radius-pill)`.
- [ ] Gráficos foram revisados — se cores estavam em `.js`, foi feita pergunta ao usuário.
