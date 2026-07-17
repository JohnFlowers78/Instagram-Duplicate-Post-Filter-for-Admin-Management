# 💡 Ideias e Observações — Filtro de Repetidas

Documento vivo, separado do README: aqui ficam as **observações de funcionamento** que valem ouro na operação e as **ideias futuras** discutidas durante o desenvolvimento — para nada se perder entre uma versão e outra. As observações mais importantes também vão para o README.

_Atualizado em: 15/07/2026_

---

## 📌 Observações de operação

### Cards Finais trocados por IA × hashes
O `.hashes.json` de cada pasta guarda a **assinatura** de cada imagem (nome, tamanho e data de modificação). Trocar o Card Final — por IA ou na mão — **invalida o cache daquela pasta sozinho**: os hashes são recalculados das imagens reais na próxima comparação. O botão **Apagar caches de hash** (Configurações → Detecção de Duplicatas) fica como reforço para casos raros (ex.: restaurar um backup antigo que preserva as datas dos arquivos).

### Falsos "disponíveis" no Filtro Entre Contas
Publicações marcadas como disponíveis que na verdade já existem no destino provavelmente vêm de **comparações feitas com caches congelados** de antes das edições dos Cards Finais. Receita:

1. **Apagar caches de hash** (Configurações);
2. **↻ Recarregar** a lista;
3. Marcar manualmente (**É Repetida**) só as que sobrarem.

O Recarregar **preserva** as marcações manuais (É Repetida / Não é Repetida) — ele nunca sobrescreve o que foi decidido na mão.

### Regra do Card Final (CTA)
O último card muda em praticamente toda republicação. Por isso o detector **ignora 1 card de diferença** em qualquer comparação. Se a operação passar a trocar **2** cards por publicação (ex.: card de troca de palavra + CTA), o detector começará a deixar repetidas passarem — nesse caso, ver a ideia do "modo tolerante" abaixo.

### Tesseract nas máquinas
O OCR de CTA depende do **Tesseract instalado no sistema** (não vem no `.exe`). Ao montar/atualizar a máquina de trabalho: instalar o Tesseract com os idiomas **Português** e **Espanhol**, senão a linha de CTA mostra "OCR indisponível" (o resto funciona normal).

### Atualização de versão sem perder dados
Ao levar uma nova versão para a máquina de trabalho: trocar só o `FiltroDeRepetidas.exe` e a pasta `_internal\` — **manter a pasta `data\`** (histórico, filas, listas e sessão do Chrome ficam nela).

---

## 💡 Ideias futuras

### Curto prazo (dentro do app atual)

1. **Modo tolerante / "suspeitas de repetida"** — opção no Recarregar que ignora **2** cards em vez de 1 e pinta as quase-repetidas de **laranja** ("suspeita"), com botões É/Não é para revisar em um clique. Transforma a caça manual numa revisão de lista curta. Útil se os falsos "disponíveis" persistirem mesmo após purge + Recarregar.
2. **Sugerir a pasta mais parecida ao marcar "É Repetida"** — o app calcula o melhor candidato na Pasta de Destino e pré-preenche o campo de pasta/dia no dialog (hoje o campo é manual e opcional).
3. **Botão "Sair do Instagram do robô"** (Configurações) — limpa a sessão do perfil do Chrome do bot para trocar a conta logada sem mexer em pastas; o próximo uso cai na pausa de login normalmente.

### Médio/longo prazo (roadmap discutido)

4. **UI web** — backend continua Python (FastAPI servindo os módulos atuais), front em TypeScript. A lógica já está modular (`gui.py` é só um "chamador"); migrar apenas quando for a hora.
5. **Feed Especial ("Instagram Saudável")** — em desenho detalhado, ver a seção 🎯 abaixo.
6. **Bot de publicação desktop human-like** — Graph API está fora (não permite escolher música em alta); publicar via automação com comportamento humano.
7. **Geração de cards** — cards de troca de palavra por **template + código (PIL)**; artes novas via **bot no ChatGPT** (assinatura própria, sem pagar API).
8. **Celular como controle remoto** — depois da UI web, expor as ações via API para operar do celular.

---

## 🎯 Em desenho: Feed Especial ("Instagram Saudável")

Feed idêntico ao do Instagram DENTRO do app, alimentado por um bot que rola o feed de uma **conta-isca** (conta criada e "treinada" pelo usuário para o nicho desejado — o app é agnóstico de nicho: pode ser desenvolvimento pessoal/estoicismo/frases em ESPANHOL para uso pessoal, ou receitas na versão de trabalho). Objetivo: unir passatempo curado + trabalho, sem roubar tempo.

### Decisões de arquitetura (conversa de 15/07/2026)
1. **Separado desde o dia 1, rodando junto**: o coletor (`feedbot`) nasce como processo próprio com contrato simples de **"inbox"** (arquivo JSON/SQLite com links + metadados). Deploy futuro em VM = só mover o processo, sem reescrever. O app principal segue LEVE (só lê o inbox).
2. **Começar local, deploy depois**: além do custo (~US$5–10/mês de VPS), o risco maior é **IP de datacenter** (Instagram detecta e bloqueia); o IP residencial da máquina local é mais seguro. Reavaliar após estabilizar a internet.
3. **Copiar o link NÃO suja o algoritmo**: ler o shortcode no DOM é passivo. O que treina o algoritmo da conta-isca é dwell time, like, save, comment, follow. Logo, o bot deve ser o **"jardineiro" do algoritmo**: parar mais tempo (e ocasionalmente curtir/salvar) nas publicações DENTRO do gosto e pular rápido as de fora — coleta e manutenção do contexto no mesmo gesto.
4. **Restart de sessão** entre ciclos para "refresh" da entrega (comprovado nos testes do usuário).

### Filtro de gosto (sem APIs pagas)
- **Engajamento**: faixa configurável (ex.: likes 20k–1M). ⚠ 20k+ de comentários é raríssimo — propor limiar separado para comentários (ex.: ≥ 200). **A definir.**
- **Só carrosséis** (formato).
- **Carrosséis de exemplo**: área "Configurações do Feed" onde o usuário insere N carrosséis-referência. Similaridade semântica via **CLIP local** (modelo open-source, roda em CPU, grátis, download único) — o phash NÃO serve para isso (só pega quase-idênticas, não "mesma vibe"). Complementos: OCR dos cards (Tesseract, já temos) para palavras-chave + filtro de idioma (espanhol).
- **Ciclo fechado de treino**: salvas = exemplos positivos; expiradas do rodízio (5× vistas sem salvar) = **negativos** → a "10ª lista" não é lixo, é o dataset que refina o ranking.

### Comportamento do Feed no app
- Rolagem estilo Instagram; **salvar numa Coleção/Salvos → some do feed** e entra no fluxo já existente (pipeline em modo fila + coleção de destino — reuso total dos Salvos/Coleções).
- Buffer de **500–1000 links** por feed; "lista invisível" de próximas (prefetch); após 500 vistas, **intercala** repetidas com novas; 5× repetida sem salvar → lista de negativos.
- Injeção gradual configurável (ex.: janela de 8h).
- **Vários feeds** possíveis (um por conta-isca/nicho), cada um com sua config e seu inbox.

### Fases
1. ✅ **MVP local** (implementada em 16/07/2026): `feedbot` separado + conta-isca + filtro engajamento (E) / carrossel + inbox + aba Feed com salvar→Coleções + cronômetro + estratégias de leitura em camadas (ver ESTRATEGIAS.md).
2. **Gosto**: OCR + idioma + CLIP com exemplos ("Perfis de Gosto": conjuntos nomeados de 10–30 carrosséis, um centroide por perfil, nota = maior similaridade) + negativos refinando.
3. **Deploy do coletor** (VM/cloud) mantendo o mesmo contrato de inbox.
4. **Mobile/web** (junto da migração FastAPI já planejada).

---

## ✅ Ideias implementadas (saíram da lista acima)

- **14/07/2026 — Escolher a coleção já ao Adicionar à Fila**: dropdown "Salvar em:" no modo fila do Filtro por Link (Salvos geral, Salvos + coleção, ou criar coleção nova na hora). Proposta e implementada no mesmo dia — fazia parte da ideia original dos Salvos com Coleções.

---

> **Como manter este documento:**
> 1. Ideias novas são apresentadas **no chat primeiro**; entram aqui **a cada commit**, salvo veto.
> 2. Ideia da lista que for implementada **sai das futuras e entra em "Ideias implementadas"** (migração automática).
> 3. Critério de entrada: ideias **viáveis e palpáveis** — criatividade é bem-vinda, conto de fadas não. Toda ideia precisa sobreviver à releitura sóbria do dia seguinte.
> 4. As observações mais importantes vão também para o README.
