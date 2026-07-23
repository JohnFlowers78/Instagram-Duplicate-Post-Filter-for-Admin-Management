# ✅ TODO — Filtro de Repetidas / Feed Especial

Lista viva de pendências para **nunca esquecer nada**. Riscar (`[x]`) ao concluir.
Detalhes de design ficam no [IDEIAS.md](IDEIAS.md); aqui é só o "o que falta fazer".

_Atualizado em: 16/07/2026_

---

## 🎯 Feed Especial

- [ ] **Estratégia de definição e manutenção do algoritmo da conta-isca** — definir a rotina:
  o que curtir/salvar/seguir, quanto tempo parar em cada tipo, quando resetar a sessão,
  como NÃO "sujar" o contexto (o bot já faz o dwell básico; falta a metodologia completa)
- [ ] **Carrosséis de exemplo / "Perfis de Gosto" (Fase 2)** — CLIP local + OCR + idioma;
  conjuntos nomeados de exemplos (10–30 por perfil), cada um com seu centroide;
  ver a proposta na seção 🎯 do IDEIAS.md
- [ ] Estética do Feed (deixar mais parecido com o Instagram de verdade)
- [ ] Rodízio/intercalação (após 500 vistas, repete intercalado; 5× sem salvar → negativos)
- [ ] Coleta agendada contínua (rodar sozinha de tempos em tempos)
- [ ] Fase 3: deploy do coletor em VM/cloud (mesmo contrato de inbox; atenção ao IP de datacenter)

## 📋 Tipos de publicação a captar (rascunho — EDITAR JUNTOS)

> Metodologia: cada tipo vira um "Perfil de Gosto" com seus exemplos; o bot prioriza os
> tipos marcados como ativos. Marcar prioridade (🔥 alta / 🙂 média / 💤 baixa) ao editar.

- [ ] Frases inspiradoras/estoicas em card único bem tipografado
- [ ] Carrossel de listas: "X hábitos / X regras / X lições de..."
- [ ] Quadrinhos/tirinhas de mentalidade e autodesenvolvimento
- [ ] Foto de pessoa famosa + história/frase (storytelling de referência)
- [ ] Educação financeira ilustrada
- [ ] Comparações visuais (antes/depois, mentalidade fraca × forte)
- [ ] _(adicionar mais tipos e definir a prioridade de cada um)_

## 🤖 Módulo "Edição CARDs Finais" — IMPLEMENTADO (19/07), refinar automação

> ✅ Feito: aba nova + storage de perfis (cardscripts.py) + login ChatGPT nas Configurações
> + "Lista de Publicações do Dia" read-only com "Editar CTA" + chatgpt.py (automação
> best-effort). 🧪 A automação do chatgpt.com precisa de refino com LOGs reais (DOM muda).
> Pendências finas do módulo:
- [ ] Testar a automação real do chatgpt.com e ajustar seletores (ESTRATEGIAS.md tem a tabela)
- [ ] Confirmar o fluxo card→legenda com legenda-exemplo (hoje é um prompt único por vez)
- [ ] Miniatura da imagem gerada direto na área de resposta (hoje: botão abre a pasta/arquivo)

### (design original, mantido para referência)

**Arquitetura decidida:**
- Nova aba **"Edição CARDs Finais"**. Automação do **chatgpt.com via navegador** (perfil
  próprio de Chrome, como o Instagram) — SEM pagar API. Login: botão nas Configurações
  ("Logins" ganha um 4º: ChatGPT) que abre o navegador para logar/deslogar (mesmo padrão).
- **Perfis de script reutilizáveis** (`data/card_scripts.json`): cada perfil = {nome, título
  de capa (livre, ex.: "CTA Comentar", "Cliente Valter", "Troca de Gatilho", "Edição
  Completa"), texto do script (caixa média), imagem de exemplo}. Salvar → vira botão
  (nome + miniatura). CRUD completo (criar/editar/renomear/apagar). Testável isolado.
- **Requisição**: caixa de texto do script + anexar até **30 imagens** de contexto/corte.
  Gera **card final E** depois a **legenda** (com base numa legenda-exemplo fornecida).
  2 cards finais fixos como exemplo-base default (editáveis).
- **Resposta**: área que mostra o texto/reposta do chat + **botão para baixar a imagem
  gerada** (salvar em `data/cards_gerados/` com data no nome).

**Ordem de implementação sugerida (fatiar p/ testar):**
1. Storage + UI dos perfis de script (CRUD, botões com miniatura) — 100% testável isolado
2. Login ChatGPT nas Configurações + navegador próprio
3. Envio do script + imagens ao chatgpt.com e leitura da resposta (a parte frágil)
4. Download da imagem gerada
- Registrar as estratégias de seletor no ESTRATEGIAS.md (chatgpt.com muda muito)

## 🎨 Produção de conteúdo

- [ ] Criar conta no **GROK** e avaliar custo — gerar imagens de animações/desenhos e
  recortes de imagens reais com efeitos/texturas/cores diferentes, mantendo a resolução
  e traduzindo para espanhol quando preciso
- [ ] **Módulo ChatGPT p/ cards finais + LEGENDAS** (via assinatura, sem API paga):
  - Listas de scripts salvos como **botões** (nome + imagem de exemplo); 5 títulos de capa que identificam o tipo
  - As caixas de texto dos scripts geram o **card final E a legenda** correspondente
  - Inserção de até **30 imagens** de contexto por requisição (cortes/uso para o card e para a legenda)
  - Fluxo: gerar o card final e, na sequência, a legenda **com base numa legenda-exemplo** fornecida
  - 2 imagens fixas como exemplo-base de tudo
- [ ] **Varredura de contas parecidas** (250k–20M seguidores, contexto similar aos
  exemplos) → separar os achados em coleções diferentes

## 🚀 Era do DEPLOY (sistema rodando FULL TIME)

> Visão: o sistema roda sozinho numa máquina ligada direto (VM/cloud ou um PC dedicado),
> com uma **sessão do Claude gerenciando um clone deste repositório** — rodando, analisando
> e decidindo o que fazer — enquanto o usuário gerencia tudo pelo celular.

- [ ] **Consertar/estabilizar a internet** antes de decidir onde o deploy vive
- [ ] Escolher onde rodar: VPS/cloud (~US$5–10/mês) × PC dedicado em casa —
  lembrar do alerta do IDEIAS.md: **IP de datacenter é mais visado pelo Instagram** que IP residencial
- [ ] Mover o `feedbot` para a máquina de deploy usando o **mesmo contrato de inbox**
  (Fase 3 do IDEIAS.md) — o CLI `python feedbot.py --minutes N` já está pronto
- [ ] Definir a **sincronização do inbox** entre a máquina de deploy e a máquina do app
  (arquivo em nuvem simples ou mini endpoint HTTP)
- [ ] **Criar o CLAUDE.md na raiz** — instruções de bordo para a sessão nova do Claude
  acordar sabendo as regras do projeto (testes isolados, padrão de commits, docs vivas,
  ler TODO/IDEIAS/ESTRATEGIAS antes de agir)
- [ ] Preparar o kit da máquina nova: Chrome + Tesseract instalados, logins refeitos pela
  seção **Logins** (o `data/` não viaja no Git, de propósito)
- [ ] Rotina do Claude-gestor: coletar, analisar Resumos dos LOGs, ajustar estratégias,
  reportar pendências — e o usuário comandando pelo app Claude do celular
- [ ] **Programar publicações no Instagram** (bot human-like; 3º login já reservado nas
  Configurações — o usuário está montando o raciocínio anti-detecção)

## 📱 Era do CELULAR (app próprio de controle remoto)

> Visão: front-end próprio para celulares (estilo RESTful: a parte cliente roda no
> dispositivo do usuário), consumindo o backend Python — junto da migração FastAPI + TS
> já planejada no IDEIAS.md.

- [ ] Migrar a UI para web (backend FastAPI servindo os módulos atuais; front TypeScript)
- [ ] Expor as ações do app via **API** (filas, coleções, feed, histórico, coletas)
- [ ] **App/front mobile**: rolar o Feed Especial no celular, salvar em coleções,
  disparar coletas e acompanhar métricas de qualquer lugar
- [ ] Autenticação/segurança da API (o celular vira o controle remoto oficial)
- [ ] Notificações do sistema no celular (hoje: lembretes agendados via app Claude;
  no futuro: notificações do nosso próprio app)

## 🎯 ENGATILHADO para a próxima sessão (análise tripla de 19/07/2026)

> Contexto: os 3 relatórios (lista de referência do Claude + relatório do app no DB do
> João + relatório do app no DB do Valter) bateram 100% — 153 e 158 repetidas cruzadas
> conferem EXATAMENTE com a matemática dos 156 grupos da referência. Filtro consistente
> e determinístico entre máquinas. Pendências finas:

- [ ] **Validação visual por amostragem** (usuário): conferir ~10 grupos no olho (os 9 de
  3+ cópias primeiro) → se zero erro, promover a regra do MIOLO de 🧪 para ✅ no ESTRATEGIAS.md
- [ ] **Marcar no relatório qual regra pegou cada repetida** — "(clássica)" ou "(miolo)" ao
  lado de cada linha: essencial para calibrar limiares com dados
- [ ] **Nome do arquivo do Relatório Geral incluir a base comparada** (ex.:
  `relatorio_geral_VALTER_...txt`) — o usuário hoje renomeia na mão
- [ ] **Revisar CTAs vazias/não detectadas** nas disponíveis (ex.: Dia22_13_06_26_V\6,
  Dia2_24_05_26_V\3, Dia9_31_05_26_V\1) — reprocessar OCR ou melhorar classificação

## 📅 Postagem/Programação — EM ANDAMENTO (motor pronto 19/07)

> ✅ Feito: `postplan.py` (motor de horários + storage, TESTADO) — 8 bases × 5 variantes
> (−10/−5/0/+5/+10), variância 0/20/30/40, sorteio aleatório sem 3 iguais seguidas,
> imediata vs agendada, contas @ salvas, due_posts/mark. `poster.py` (esqueleto:
> perfil próprio `poster_profile`, ordem das imagens, Legenda.txt, marcações) com o
> modal do Instagram STUBBED (`IMPLEMENTED=False`, nunca posta de verdade ainda).
> Login "Instagram — Postagem/Programação" ATIVADO nas Configurações (conta separada).

### 🟢 ATUALIZAÇÃO 22/07 — ambiente Android pronto + FLUXO MAPEADO
- ✅ **Emulador AVD instalado** (JDK/SDK/adb/emulador/AVD 'postador'/Android14+PlayStore, sem admin em %LOCALAPPDATA%\Android). `androidenv.py` vincula (start/wait_boot/push_images/detecta IG).
- ✅ **uiautomator2** instalado e conectando (automação por identidade de elemento — celular físico Galaxy S21 Ultra também detectado via ADB).
- ✅ **FLUXO DE POSTAGEM/AGENDAMENTO 100% MAPEADO** (contas pequenas) em **POSTFLOW_INSTAGRAM.md** — os 8 passos com todos os seletores (Criar→Post→seleção na ordem via data→Taxa/Retrato→Música em alta ↗ (IMAGE RECOGNITION)→Avançar→Legenda→Colaboradores→Programar toggle→data/hora→Concluir→Programar).
- Decisões: **3 estratégias** que o usuário escolhe na aba (API Graph="Método Seguro" padrão; Emulador e Celular="Risco Existente"→uiautomator2). Bot põe 1ª música em alta (↗). Ordem das imagens via timestamps no adb push. Setup: fazer 1 post MANUAL antes (limpar permissões).

### 🟢 ATUALIZAÇÃO — navegação/troca de conta capturadas + androidposter.py (bring-up TESTADO)
- ✅ **Barra inferior mapeada** (nav): `feed_tab`(Página inicial), `profile_tab`(Perfil), clips/direct/search.
- ✅ **Troca de conta CAPTURADA**: clique-LONGO em `profile_tab` → bottom sheet onde cada
  linha é `ViewGroup` com `content-desc == @` da conta (sem resource-id). Bot casa pelo @.
- ✅ **DESCOBERTA**: o estilo do seletor de data/hora é do **APARELHO, não da conta** — a
  MESMA `@mentedespierta.es` (196k) mostra **RODA no emulador** e RELÓGIO no físico. Logo o
  **fluxo do EMULADOR (roda) está COMPLETO**; o relógio vira ramo defensivo (mapear no físico, reaproveitável).
- ✅ **`androidposter.py` criado** (uiautomator2, por serial): `IGDriver` com open_app(fresh),
  go_to_profile, active_account, switch_account, ensure_account, open_create_post + `navtest()`.
  **TESTADO no emulador**: abre Feed → Perfil → lê @mentedespierta.es → abre compositor de Post (sem publicar). ✅

Pendências desta feature:
- ✅ **Estilo RELÓGIO CAPTURADO no emulador** (contas grandes ALTERNAM A/B roda×relógio no
  mesmo aparelho/conta!). POSTFLOW TELA 7-ALT: overlay 'Programar post' (linhas Data/Horário) →
  DatePicker (dias por content-desc 'DD mês AAAA', `next` p/ mês, OK=`android:id/button1`) →
  TimePicker MODO TECLADO (`toggle_mode`→`input_hour`/`input_minute` 24h→OK). Bot DETECTA o estilo em runtime.
- [ ] **Continuar o `poster.py`/androidposter.py**: seleção de imagens NA ORDEM (timestamps no push + ler "criação em HH:MM" do desc), Taxa=Retrato→Concluir, Avançar, legenda, colaboradores, Mais opções→toggle Programar, setar data/hora (RODA=3× numberpicker OU RELÓGIO=Data/Horário), Compartilhar→Programar.
- [ ] (conferência) re-verificar o RELÓGIO no **Galaxy físico** (mesmos componentes Material → deve bater).
- [ ] **Configurar a API Graph da Meta** (o "Método Seguro" — publica sem música/sem agendar-nativo; via nosso vigia 24h)
- [ ] Seletor das 3 estratégias na aba Postagem + fallback "continuar com emulador" se celular desconectado
- [ ] (autonomia) `androidenv` ciente de SERIAL (2 aparelhos ligados quebram adb "solto") + helper open_instagram; ligar navtest ao botão de teste da aba

Pendências (print-INDEPENDENTES — dá pra fazer sem os prints):
- [ ] **Aba "Postagem/Programações"**: a Lista de Publicações do Dia como tela principal,
  cada cartão com: horário-base (dropdown 00–21h), imediata×agendada, contas @ (multi,
  salvas), música (definir depois manualmente). Linha de topo com variância 0/20/30/40.
  Reordenar por arraste (mesmo mecanismo da Fila/Coleções). Botão **PROGRAMAR** abaixo do
  último card → sorteia horários (postplan.program_day), fixa balão "Publicação Programada".
- [ ] **Vigia 24h** (relógio da máquina): `_start_post_watch` checa `postplan.due_posts()`
  e dispara o poster quando chega a hora (roda com o app aberto — avisar o usuário).
- [ ] LOGs publicação por publicação.

⚠️ VIRADA DE ESTRATÉGIA (19/07): a postagem pelo NAVEGADOR (Instagram web no Windows)
NÃO serve — a web só permite "Compartilhar" na hora, **sem aplicar música e sem
programar horário**. Caminho futuro decidido pelo usuário: **emulador Android (AVD)**
rodando o app do Instagram, onde dá para escolher música em alta e a data/hora de
publicação. O `poster.py` (browser) fica como referência mas provavelmente será
substituído por automação do emulador. `postplan.py` (motor de horários) e a futura
aba/vigia continuam VÁLIDOS — muda só a "mão" que posta.
- [ ] Reavaliar poster: automação via emulador Android (AVD) em vez de navegador
  (escolher música em alta + programar data/hora nativamente no app do IG).
- [ ] Aba "Postagem/Programações" + vigia 24h (print-independente, ainda vale).

## 🖥 App

- [ ] Refinar o envio "Coleção → pasta própria" (nomenclatura/sequências) conforme o uso
- [ ] Modo tolerante "suspeitas de repetida" no Entre Contas (ideia nº 1 do IDEIAS.md)
- [ ] Sugestão automática da pasta mais parecida no "É Repetida" (ideia nº 2 do IDEIAS.md)
- [ ] Login de "Programar Publicações" (3º slot, hoje inativo) quando a função nascer
