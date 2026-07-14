# 💡 Ideias e Observações — Filtro de Repetidas

Documento vivo, separado do README: aqui ficam as **observações de funcionamento** que valem ouro na operação e as **ideias futuras** discutidas durante o desenvolvimento — para nada se perder entre uma versão e outra. As observações mais importantes também vão para o README.

_Atualizado em: 14/07/2026_

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
5. **Feed raspador por engajamento** — "Apify própria" em Playwright: varrer perfis e ranquear publicações por curtidas/comentários para alimentar as filas. Sem APIs pagas.
6. **Bot de publicação desktop human-like** — Graph API está fora (não permite escolher música em alta); publicar via automação com comportamento humano.
7. **Geração de cards** — cards de troca de palavra por **template + código (PIL)**; artes novas via **bot no ChatGPT** (assinatura própria, sem pagar API).
8. **Celular como controle remoto** — depois da UI web, expor as ações via API para operar do celular.

---

## ✅ Ideias implementadas (saíram da lista acima)

_Nenhuma ainda — quando uma ideia da lista for implementada, ela migra para cá automaticamente, com a data._

---

> **Como manter este documento:**
> 1. Ideias novas são apresentadas **no chat primeiro**; entram aqui **a cada commit**, salvo veto.
> 2. Ideia da lista que for implementada **sai das futuras e entra em "Ideias implementadas"** (migração automática).
> 3. Critério de entrada: ideias **viáveis e palpáveis** — criatividade é bem-vinda, conto de fadas não. Toda ideia precisa sobreviver à releitura sóbria do dia seguinte.
> 4. As observações mais importantes vão também para o README.
