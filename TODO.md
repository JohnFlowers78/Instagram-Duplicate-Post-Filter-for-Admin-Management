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
- [ ] **Módulo ChatGPT p/ cards finais** (via assinatura, sem API paga): área de listas de
  scripts salvos como botões (nome + imagem de exemplo), caixa de texto com inserção de
  imagens de exemplo (2 fixas como base), 5 títulos de capa que identificam o tipo
- [ ] **Varredura de contas parecidas** (250k–20M seguidores, contexto similar aos
  exemplos) → separar os achados em coleções diferentes

## 🖥 App

- [ ] Refinar o envio "Coleção → pasta própria" (nomenclatura/sequências) conforme o uso
- [ ] Modo tolerante "suspeitas de repetida" no Entre Contas (ideia nº 1 do IDEIAS.md)
- [ ] Sugestão automática da pasta mais parecida no "É Repetida" (ideia nº 2 do IDEIAS.md)
- [ ] Login de "Programar Publicações" (3º slot, hoje inativo) quando a função nascer
