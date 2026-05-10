# CLAUDE.md — Redesign Cosmético: ID Visual "Arruda"

> **Leia este arquivo antes de qualquer ação. Ele define o escopo do trabalho.**

## 🎯 Objetivo

Aplicar a identidade visual **"Arruda"** ao Panorama Fiscal do DF. Trata-se de um **redesign exclusivamente cosmético**.

## 🚫 ESCOPO — O que você NÃO PODE fazer

Estas restrições são **invioláveis**:

1. **Não edite arquivos `.html`.** Nenhum elemento pode ser adicionado, removido ou ter sua estrutura alterada. Classes existentes não devem ser renomeadas.
2. **Não edite arquivos `.js`.** Nenhuma lógica, fonte de dados, cálculo, pipeline ou interação pode ser modificada.
3. **Não edite arquivos de dados** (`.json`, `.csv`, `.xlsx`, ou qualquer fonte).
4. **Não crie novos componentes.** Não adicione novos cards, seções, gráficos, modais, ou qualquer elemento visual que não exista hoje.
5. **Não remova componentes existentes.** Mesmo que pareçam visualmente desnecessários.
6. **Não instale dependências novas** (npm, CDN, fontes externas além das definidas em `tokens.css`).
7. **Não altere a estrutura de pastas do projeto.**

## ✅ ESCOPO — O que você PODE (e DEVE) fazer

1. **Editar arquivos `.css` existentes.** Reescrever regras de estilo para aplicar a nova identidade.
2. **Importar `tokens.css`** no topo do CSS principal e refatorar valores hardcoded (cores, fontes, espaçamentos) para usar as variáveis CSS.
3. **Adicionar `tokens.css`** à pasta de estilos do projeto.
4. **Adicionar a `<link>` das Google Fonts** no `<head>` do HTML — esta é a **única** alteração permitida em arquivos HTML, e somente se as fontes ainda não estiverem carregadas.

## 📋 Processo recomendado

Trabalhe nesta ordem:

1. **Mapeie o projeto.** Liste todos os arquivos `.css`, `.html`, `.js`. Identifique qual CSS é o principal (provavelmente `style.css`, `main.css` ou similar).
2. **Copie `tokens.css`** para a mesma pasta dos outros estilos.
3. **Adicione `@import` ou `<link>`** do `tokens.css` no CSS principal ou no HTML (preferência: `@import` no CSS, pra não tocar no HTML).
4. **Refatore o CSS por seção**, na ordem:
   - Body, tipografia base, cores globais
   - Header / hero
   - Cards (KPIs)
   - Tabelas e rankings
   - Gráficos (apenas wrapper, cores e bordas — não tocar em config de Chart.js/Plotly)
   - Footer e elementos secundários
5. **Após cada seção**, peça ao usuário para revisar visualmente antes de prosseguir.
6. **Não faça commit.** Deixe o usuário revisar e commitar.

## 🎨 Direção visual (resumo)

Detalhes completos em `REDESIGN_BRIEFING.md`. Resumo:

- **Paleta:** verdes profundos (`#0E3B1F`, `#1A5A2E`) como base, **verde-limão `#A8E830`** como acento de assinatura (use com parcimônia — apenas em destaques, CTAs e variações positivas).
- **Tipografia:** **Playfair Display** (serifa) para títulos de seção e hero. **Inter** para corpo. **JetBrains Mono** para números fiscais (alinhamento decimal).
- **Cards:** cantos arredondados (`16px`), sombra suave verde-tonalizada, fundo branco sobre `--color-surface-alt` (off-white esverdeado).
- **Header:** gradiente verde `--gradient-hero` com padrão de folhagem em `opacity: 0.06` (já incluído como SVG inline em `tokens.css`).
- **Pills/badges:** totalmente arredondados (`9999px`), seguindo o padrão do tag "Sudoeste" da peça original.
- **Vermelho semântico:** `#E84545` para variações negativas/déficit — calibrado para ter peso visual equivalente ao verde-limão.

## ⚠️ Regras de aplicação dos tokens

- **Nunca** use cores hexadecimais hardcoded no CSS. Sempre use `var(--color-*)`.
- **Nunca** use `px` para fontes de título. Use as variáveis `--text-*`.
- **Use o verde-limão `--color-accent` com escassez.** Regra prática: no máximo **um elemento limão por viewport visível**. Se virar fundo de tudo, perde o impacto e descaracteriza a id.
- **Para gráficos** (Chart.js / Plotly), edite apenas as cores via tokens. Se a config estiver no `.js`, **pare e pergunte ao usuário** como prefere expor as cores (ex.: criar um arquivo `chart-theme.js` mínimo, ou aceitar a alteração pontual).

## 🛑 Quando parar e perguntar

- Se encontrar cores ou estilos hardcoded dentro de arquivos `.js` (ex.: cores de gráficos).
- Se uma regra CSS depender de estrutura HTML que você acha que deveria mudar.
- Se houver conflito entre duas regras CSS e não estiver claro qual prevalece.
- Se o `tokens.css` não cobrir um caso de uso que apareça no projeto (ex.: cor de hover específica).

**Regra geral:** na dúvida, pergunte. É preferível pausar a alterar fora de escopo.

## 📦 Arquivos desta entrega

- `CLAUDE.md` — este arquivo (instruções operacionais).
- `tokens.css` — todas as variáveis CSS da id Arruda.
- `REDESIGN_BRIEFING.md` — descrição visual detalhada da id, com exemplos de "antes/depois" de regras CSS.
