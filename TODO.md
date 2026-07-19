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

## 🖥 App

- [ ] Refinar o envio "Coleção → pasta própria" (nomenclatura/sequências) conforme o uso
- [ ] Modo tolerante "suspeitas de repetida" no Entre Contas (ideia nº 1 do IDEIAS.md)
- [ ] Sugestão automática da pasta mais parecida no "É Repetida" (ideia nº 2 do IDEIAS.md)
- [ ] Login de "Programar Publicações" (3º slot, hoje inativo) quando a função nascer
