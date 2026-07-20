# 🧭 ESTRATÉGIAS — Registro por Feature (o que cada uma usa e o status dos testes)

Registro vivo das estratégias de cada feature: o que está em uso, o que está em
teste e o que já foi validado. **As estratégias não se substituem: são tentadas
em ordem/combinadas, e qualquer uma que funcionar vale.** Atualizar o status
(✅ validada / 🧪 em teste) conforme os ciclos de teste-reteste.

_Atualizado em: 17/07/2026_

---

# 🔁 FEATURE: Detecção de Repetidas (Filtro por Link E Filtro Entre Contas)

> Os dois filtros usam a MESMA engine (`dedup.find_duplicate_post`): "jogo da
> memória" bijetivo — matching bipartido máximo entre os hashes perceptuais
> (pHash 64 bits) dos cards, cada card só pode parear uma vez.

## Regras de decisão (por candidato — QUALQUER uma marca REPETIDA)

| # | Regra | Como funciona | Pega o quê | Status |
|---|---|---|---|---|
| 1 | **Clássica** (tolerância 1) | Limiar estrito (padrão 5): todos os cards menos 1 encontram par | Cópias idênticas · troca de 1 card final | ✅ validada |
| 2 | **MIOLO tolerante** | Ignora os últimos *N cards de CTA* (padrão 2) **de cada lado** e exige o miolo INTEIRO pareado com limiar tolerante (padrão 16); mínimo de 3 cards no miolo | CTA de 1–2 cards refeita/redesenhada · recompressão entre downloads | 🧪 quase-validada: consistência TRIPLA em 19/07 (referência × app-João × app-Valter = 100% de acordo, 153/158 conferem com os 156 grupos); falta só a amostragem visual do usuário p/ ✅ |

## Evidência medida (caso real: mesma publicação em João Dia1 × Valter Dia10 × João Dia55\2)

- Mesma arte baixada em épocas diferentes: distância pHash **6–14 bits** (recompressão) → estourava o limiar 5 → NENHUM card casava → furo.
- CTAs trocadas (padrão antigo → novo, 2 cards): distância **24–28**.
- Cards de publicações DIFERENTES: distância **20+**.
- → Limiar do miolo **16** = no meio do vão entre 14 (mesma arte) e 20 (outra arte).
- Resultado: os 3 vazamentos reais viram REPETIDA (miolo 7/7@t16); publicações diferentes seguem limpas.

## Configurações (aba Configurações → Detecção de Duplicatas)

- **Limiar de similaridade** (padrão 5) — regra clássica
- **Cards de CTA no final** (padrão 2) — quantos cards do fim são ignorados pelo miolo
- **Limiar do miolo** (padrão 16) — tolerância da regra 2
- Cache `.hashes.json` com assinatura (nome/tamanho/mtime): troca de card invalida sozinho
- **Base de comparação**: TODA subpasta (2º nível) da Pasta de Destino com imagens
  numeradas — incluindo slots renomeados ("7 - Vitrine", "10 - Híbrido") e pastas de
  coleção. ⚠ Antes só entravam nomes puramente numéricos: slots nomeados ficavam FORA
  da base e não bloqueavam repetidas (corrigido em 17/07/2026).

## Localização das repetidas (por item)

- `find_all_duplicates`: cada publicação do Entre Contas guarda **TODAS** as pastas
  onde já existe (`dup_locations`, sem parar na primeira) — alimenta o "⚠ REPETIDAS: X ▾"
  do cartão (passar o mouse abre um botão 📁 por pasta).

# 🤖 FEATURE: Edição CARDs Finais (automação chatgpt.com)

> Automação do **chatgpt.com via navegador** (perfil próprio `chatgpt_profile`, login
> pela seção Logins). Frágil por natureza — o DOM do ChatGPT muda muito. Refinar com
> LOGs reais (mesmo método do feedbot). Storage dos perfis: `card_scripts.json`.

## Estratégias de seletor (chatgpt.py) — todas 🧪 em teste

| Alvo | Estratégia (em camadas) |
|---|---|
| Login | existe `#prompt-textarea` OU `div[contenteditable]`/`textarea` → logado |
| Anexar imagens | `input[type=file]` → `set_input_files` (até 30) |
| Caixa de texto | `#prompt-textarea` → `div[contenteditable]` → `textarea[data-testid]` → `textarea` |
| Enviar | `keyboard.insert_text` + Enter |
| Fim da geração | some `button[data-testid=stop-button]` / aria "Parar"/"Stop" |
| Ler resposta | último `[data-message-author-role="assistant"]` → innerText |
| Imagens geradas | `<img>` http do último bloco assistant → download p/ `cards_gerados/` |

- **Fluxo**: script + exemplos-base fixos → gera Card Final; depois Legenda (base numa
  legenda-exemplo). Cartões da "Lista de Publicações do Dia" (aba, read-only) têm
  **Editar CTA** que anexa as imagens da publicação como contexto.

# 📅 FEATURE: Postagem/Programação (poster.py — AGUARDANDO PRINTS)

> Automação do modal de criação do Instagram por navegador, **conta EXCLUSIVA de
> postagem** (`poster_profile`, separada por segurança). `IMPLEMENTED=False` até os
> seletores entrarem — não posta nada real por enquanto.

Passos do modal a mapear com os prints (cada um vira um TODO já marcado no poster.py):
1. Abrir "Criar" (＋) / Nova publicação
2. `set_input_files` com as imagens na ORDEM numérica (1,2,3…)
3. Recorte/proporção → "Avançar"; efeitos → "Avançar"
4. Escrever a legenda (= conteúdo do Legenda.txt)
5. Marcar pessoas: abrir, digitar cada @ salvo, confirmar (multi)
6. **Música em alta**: abrir painel, filtrar itens com a flecha ↗ (tendência),
   escolher UMA ao acaso (usuário troca depois na mão → menos suspeita de bot)
7. "Compartilhar" e aguardar a confirmação de publicado

Motor (postplan.py — ✅ testado): 8 horários-base × 5 variantes, variância 0/20/30/40,
sorteio sem 3 variantes iguais seguidas, imediata×agendada, vigia 24h via due_posts().

## Ferramenta de verificação

- **🔎 Auditar Repetidas** (Configurações → Detecção de Duplicatas): roda as mesmas 2
  regras da Pasta de Destino contra ela mesma e agrupa por união-busca (grupos de 2,
  3, N cópias — se A==B e B==C, o grupo é {A,B,C}). Relatório .txt em `data/`,
  aberto ao terminar. Use após mudar limiares para medir o efeito.

## LOG de diagnóstico

Toda análise "não repetida" loga o candidato mais próximo:
`mais proximo: Dia10.../4 (0/8 pares · dist max 0) · sem par: dist 6 · miolo 7/7@t16`
→ se aparecer `miolo N/N` completo mas não marcou, o limiar do miolo está baixo demais; se `sem par: dist ~6-14`, é recompressão.

---

# 🌱 FEATURE: Coletor do Feed Especial (leitura do Instagram)

## 1. Leitura de curtidas/comentários (nesta ordem)

| # | Estratégia | Exemplo que ela entende | Status |
|---|---|---|---|
| 1 | Número + palavra (pt/es/en) | "24,3 mil curtidas" · "1.234 Me gusta" · "2.4K likes" · "Ver todos os 987 comentários" | ✅ validada |
| 2 | "e outras N pessoas" | "Curtido por fulano e outras 24.301 pessoas" · "y N personas más" · "and N others" | ✅ validada |
| 3 | Sequência de números soltos | "Seguir \| 6,6 mil \| 436 \| 185" → curtidas, comentários, compartilhamentos (layout novo) | 🧪 em teste |

- Sufixos entendidos: `mil`/`k` (milhar) e `mi`/`m` (milhão); separadores `.` e `,` nos dois papéis.
- A estratégia 3 só entra quando a 1 e a 2 não acharam nada — nada foi removido.

## 2. Visibilidade (quando um post pode ser julgado)

| # | Estratégia | O que resolve | Status |
|---|---|---|---|
| A | Julgar só com **≥60% do post na tela** | Post "espiando" na borda ainda não tem contadores/carrossel montados pelo Instagram — não queima como "já visto" | 🧪 em teste |
| B | **Resgate pelo rodapé de dados** | Post subindo com o topo cortado, mas com os contadores ainda visíveis embaixo — captura antes de o scroll "comer estrada" | 🧪 em teste |

## 3. Detecção de carrossel (qualquer uma basta)

1. Botão de avançar (`aria-label` Próximo / Avançar / Siguiente / Next)
2. Mais de 1 slide (`ul li img` / listas de apresentação)
3. Link com `img_index`

## 4. Comportamento do scroll ("jardineiro do algoritmo")

- Publicação **aprovada** no filtro → pausa de 2,5–5 s (ensina o algoritmo da conta-isca)
- **Reprovada** → passa em 0,6–1,4 s
- Rolagem de 500–900 px por ciclo, aleatória; reiniciar a sessão entre coletas renova a entrega

## 5. Blindagem da janela do robô

| # | Estratégia | O que resolve | Status |
|---|---|---|---|
| A | `Input.setIgnoreInputEvents` (CDP) | Mouse/teclado MANUAIS sobre a janela do robô são ignorados (rolagem acidental não atrapalha) | 🧪 em teste |
| B | Troca automática p/ rolagem via JS | Se o escudo também travar a roda do PRÓPRIO bot (scrollY parado 3 ciclos), rola via `window.scrollBy` | 🧪 em teste |
| C | Flags anti-throttling (`--disable-backgrounding-occluded-windows`, `--disable-renderer-backgrounding`) | Janelas por cima NÃO pausam o render/lazy-load — melhor que pausar a coleta: não perde publicações nem tempo | 🧪 em teste |

## 5b. Janela do navegador do robô ao ÚLTIMO PLANO

| # | Estratégia | Detalhe | Status |
|---|---|---|---|
| A | `winutil.send_chrome_windows_to_back` | ctypes/EnumWindows → `SetWindowPos(HWND_BOTTOM, NOACTIVATE)` em toda janela cujo título termina em "Google Chrome". Chamado 4× nos primeiros 6 s (a janela surge async). Só afeta Chrome; o app Tk fica na frente | 🧪 em teste (SnapInsta + Feed) |
| — | Fallback (minimizar tudo/restaurar) | NÃO implementado — a estratégia A resolve sem mexer nas outras janelas | 📋 reserva |

## 5c. Legenda do post (Filtro por Link, opcional)

| # | Estratégia | Detalhe | Status |
|---|---|---|---|
| 1 | `<h1>` do article | Novo layout: a legenda costuma estar no primeiro `<h1>` | 🧪 em teste |
| 2 | `og:description` | Fallback: extrai o trecho entre aspas da meta description | 🧪 em teste |
- Só roda com a caixa "Baixar Carrossel com Legenda?" marcada; requer login no Instagram.

## 6. Capa das publicações no Feed Especial (nesta ordem)

| # | Estratégia | Detalhe | Status |
|---|---|---|---|
| 1 | Maior `<img>` renderizado do post (`currentSrc`) | Qualidade CDN original (~1080px). O 1º `<img>` do card é o AVATAR do autor — era o bug das capas erradas | 🧪 em teste |
| 2 | Print full-HD do 1º card | Fallback se a capa vier distorcida/errada | 📋 reserva |
| 3 | Download do 1º card via SnapInsta | Último recurso (mais lento) | 📋 reserva |

---

> **Ao mudar/adicionar uma estratégia:** registrar aqui, rodar uma coleta e conferir o
> **Resumo do LOG** (vistas · aprovadas · recusas por motivo) antes de marcar ✅ validada.
