# Mapa de seletores — fluxo de Postagem/Programação do Instagram (Android)

Capturado ao vivo no emulador (uiautomator2), app com.instagram.android.
Cada passo lista o seletor que o poster.py vai usar (id / text / desc).

---

## CHECAGEM DE CONTA (sempre antes de postar)
- Username ativo no topo do perfil: `id=action_bar_title` → text = @ da conta
  (ex.: "mentalityfilter"). O bot confere se bate com a conta de destino.
- Abrir o menu Criar: action bar do perfil, ImageView `desc='Criar novo'`.

## NAVEGAÇÃO — Barra inferior (presente em todas as telas principais) ✅
O app abre no FEED. O bot navega pela barra de baixo (todos com `content-desc`):
- 🏠 **Feed / Página inicial:** `id=feed_tab` (desc='Página inicial')
- 🎬 Reels: `id=clips_tab` (desc='Reels')
- ✉️ Mensagens: `id=direct_tab` (desc='Mensagem')
- 🔍 Pesquisar: `id=search_tab` (desc='Pesquisar e explorar')
- 👤 **Perfil:** `id=profile_tab` (desc='Perfil')  ← a foto de perfil na barra
- FLUXO padrão do bot: abre no Feed → toca `profile_tab` → lê `action_bar_title`
  (@ ativo) → confere se == conta de destino.

## TROCA DE CONTA (se a conta ativa != conta de destino) ✅ CAPTURADO
Gatilho: **CLIQUE LONGO (long_click) na foto de Perfil da barra inferior** = `id=profile_tab`.
→ abre um bottom sheet com a lista de contas logadas.
- **Cada conta é uma linha `ViewGroup` cujo `content-desc` = o @ da conta** (SEM resource-id):
  - conta ATIVA: desc == exatamente o @ (ex.: desc='mentedespierta.es')
  - outras contas: desc pode ter sufixo (ex.: desc='mentalityfilter, 1 conversa e mais 1')
  - `desc='Adicionar conta do Instagram'` (Button) — add novo login
  - `desc='Acessar a Central de Contas'` (Button) — Meta
- **ESTRATÉGIA do bot:** long_click `profile_tab` → achar a ViewGroup cujo content-desc
  == @destino OU startswith(@destino) → tocar → o app troca e recarrega o perfil →
  re-ler `action_bar_title` pra CONFIRMAR a troca. Fechar sem trocar = `press('back')`.
- REQUISITO: as contas de destino precisam estar TODAS logadas no mesmo IG do robô
  (multi-login). O bot nunca digita senha — só alterna entre contas já logadas.
- SELETOR u2: `d(resourceId='...:id/profile_tab').long_click()` →
  `d(descriptionStartsWith='<@destino>').click()`

## TELA 1 — Menu "Criar" (bottom sheet)
- Título do painel: `id=title_text_view` text='Criar'
- **Post (carrossel/foto):** Button `desc='Criar novo post'` (rótulo `text='Post'`)  ← o bot toca aqui
- Outros: `desc='Criar novo reel'`, `desc='Criar novo story'`, 'Edits', 'Destaques', 'Live'

## TELA 2 — Seleção de imagens do carrossel (MediaCaptureActivity)
- Cancelar: `id=action_bar_cancel`
- Título: `id=new_post_title` text='Novo post'
- **Avançar:** `id=next_button_textview` text='Avançar'  ← toca ao terminar
- **Múltipla seleção (carrossel):** `id=multi_select_slide_button_alt` desc='Botão Selecionar vários'
- **Proporção/corte:** `id=croptype_toggle_button` desc='Alterar corte' → escolher "Original"
- Miniaturas: `id=gallery_grid_item_thumbnail` (desc começa com "Selecionado"/"Não selecionado")
- Pasta/álbum: `id=gallery_folder_menu_tv` text='Recentes'
- Miniaturas: `id=gallery_grid_item_thumbnail`; desc SELECIONADA = "Número da mídia
  selecionada N Miniatura de foto com criação em <DATA> <HORA>" (o 'selecionada' com
  'a' marca selecionado); NÃO selecionada = "Não selecionado ... com criação em ...".
- Célula câmera = 1ª sem "criação em". Círculo: `gallery_grid_item_selection_circle`.

### ✅ SOLUÇÃO DA ORDEM — TESTADA E APROVADA (5 imgs, selos 1..5 corretos)
**Descobertas dos testes (NÃO funcionam):** o "criação em" do IG = **date_added**
(momento da INDEXAÇÃO no MediaStore). NÃO é o mtime (touch -t IGNORADO) nem a EXIF
DateTimeOriginal (IGNORADA). Indexar tudo de uma vez → mesmo minuto pra todas.
**O que FUNCIONA (implementado em androidposter.push_carousel + select_carousel):**
1. Álbum DEDICADO `/sdcard/Pictures/postador` (rm -rf antes).
2. `adb push` + `MEDIA_SCANNER_SCAN_FILE` **UMA imagem por vez**, em **ORDEM REVERSA**
   (N, N-1, …, 1) com `sleep ~1.6s` entre elas → cada uma ganha `date_added` distinto
   (segundos); a imagem **1 é a ÚLTIMA indexada = a MAIS NOVA = 1ª célula da grade**.
3. No compositor: `multi_select_slide_button_alt` → LIMPAR seleção automática (tocar
   as células com 'selecionada' até zerar) → tocar as **N primeiras células de foto
   em ordem de leitura** (esquerda→direita, cima→baixo) → carrossel 1..N. ✅
- Robustez: como as N minhas são as mais novas (push imediatamente antes), são as N
  primeiras da grade — não depende de ler timestamp nenhum. (Endurecer no futuro:
  abrir só o álbum 'postador' via `gallery_folder_menu_tv` p/ isolar de outras fotos.)

## ⚙️ REQUISITO DE SETUP (adendo do usuário — IMPORTANTE)
Na PRIMEIRA publicação num emulador/aparelho novo, o Android/IG mostra VÁRIOS
diálogos de permissão (fotos, etc.) no meio da tela. O usuário DEVE fazer UMA
publicação MANUAL antes de usar o bot, pra limpar essas permissões — senão elas
aparecem pro bot e travam o fluxo. Avisar isso no botão de Login/Setup do app.

## TELA 3 — Edição (tools: Áudio/Texto/Sobreposição/Filtros/Editar/Taxa)
- Pílula de áudio sugerido: `id=audio_pill_empty_background` → **BOT PULA** (música manual depois)
- Tabs (sem id, achar por text/desc): 'Áudio', 'Texto', 'Sobreposição', 'Filtros', 'Editar', **'Taxa'**
- **Taxa (proporção):** elemento text/desc='Taxa' → o bot toca e escolhe **"RETRATO"** (em TODOS os casos)
- Miniaturas do carrossel: `id=thumbnail_image` (desc='Foto selecionada')
- Adicionar mais: `id=plus_image`
- **Avançar:** `id=media_thumbnail_tray_button` (text='Avançar')
- Voltar: `id=button_back`
- NOTA música/ban: no lado do usuário, ADICIONAR = ALTERAR (mesmo risco, atividade
  humana). Decisão: BOT NÃO define música (menos ação do bot + evita o seletor
  frágil de música em alta); usuário adiciona a ↗ manualmente depois.

## TELA 3b — Submenu da "Taxa" (opções de proporção)
- Título do submenu: `id=bottom_sheet_title` text='Taxa'
- Opções (sem id, por texto/desc): **'Retrato'** ← o bot toca aqui, 'Quadrado' (e prob. Original/Paisagem)
- Bot: abrir tab 'Taxa' → tocar **'Retrato'** → tocar **'Concluir'** (salva a alteração) → depois 'Avançar'
- **Concluir (salva a Taxa):** `id=bottom_sheet_done_button` (text='Concluir') ✅
- Cancelar bottom-sheet: `id=bottom_sheet_cancel_button` (genéricos — reusados em outros bottom sheets)

## TELA 3c — Áudio / Música (bottom sheet) — DECISÃO: bot põe a 1ª "Em alta"
- Abrir: tab 'Áudio' (na tela de edição)
- Busca: `id=row_search_edit_text` (text='Pesquisar…')
- **Abas (por texto, sem id):** 'Para você', **'Em alta'** ← TRENDING, 'Salvos', 'Áudio original'
- **ESTRATÉGIA:** tocar a aba **'Em alta'** → tocar a 1ª faixa `id=track_container`
  (mais robusto que caçar o ícone ↗ item por item)
- Faixa: `id=track_container` (desc="Selecionar faixa <titulo> de <artista>,<duracao>")
  título `id=song_title`, artista `id=artist_name`; salvar `desc="Salvar <titulo>..."`
- _(a capturar: a tela que abre APÓS escolher a faixa — trecho/clip, e como confirma p/ carrossel)_

### ⚠️ FLECHA "EM ALTA" (↗) NÃO É ELEMENTO — precisa de IMAGE RECOGNITION
- Dump profundo confirmou: track_container → album_art + song_title + artist_name.
  A flecha ↗ NÃO tem nó/crachá — é ícone puramente VISUAL (compound drawable/canvas).
- Usuário QUER: 1ª faixa COM flecha na aba "Para você" (rolar até achar). NÃO quer a aba "Em alta".
- PLANO: como cada `track_container` tem `bounds` conhecidos, o bot tira screenshot,
  recorta cada linha e detecta o ícone da flecha (template match / pixel) → seleciona
  a 1ª que tiver. É a parte MAIS FRÁGIL (re-capturar o template se o ícone mudar).
- ALTERNATIVA robusta (rejeitada pelo usuário, mas guardada): aba "Em alta" → 1ª faixa
  `track_container` (100% por seletor, sem imagem).
- FALTA do usuário: posição/cor/tamanho da flecha na linha (pro template). ✅ RESOLVIDO
  (setinha ↗ cinza no início da 2ª linha/artista; template do screenshot ig_music.png).

### TELA 3d — Pop-up de confirmação da música (balão vinho embaixo)
- Ao tocar a faixa, sobe um balão embaixo: capa + título/artista + ▶ + →
- ▶ ouvir prévia: `id=play_pause_button` (desc='Reproduzir faixa') — o bot NÃO usa
- **→ CONFIRMAR música: `id=select_button_tap_target`** ← o bot toca aqui
- (a cor do balão varia com a música; o botão é sempre `select_button_tap_target`)

## TELA 5 — Legenda / Compartilhar (action_bar 'Novo post')
- **Legenda:** tocar `id=caption_input_text_view` na tela de compartilhar ABRE UMA
  TELA DEDICADA 'Legenda' (action_bar_textview_title='Legenda'). Lá o bot escreve em
  `id=caption_input_text_view` e CONFIRMA no botão **`id=next_button_textview`
  (text/desc='OK')** → volta à tela de compartilhar. ✅ (sem o OK, fica preso na Legenda)
- **Marcar pessoas/COLABORADOR:** `id=metadata_row_people` (contém `tag_people_string`='Marcar pessoas')
- Música aplicada (confirma): `id=music_track_title`/`music_track_subtitle`; remover `id=music_track_cross`
- Localização: `id=metadata_location_row`
- Preview: `id=photo_media_preview_image_view` (miniaturas do carrossel)
- **Compartilhar (postar direto):** `id=share_footer_button`
- Voltar: `id=button_back`
- ⚠️ "... Mais opções" (Config. avançadas → PROGRAMAR) fica ABAIXO da dobra — rolar p/ achar.
- NOTA: conta de destino (@) não aparece aqui. O bot GARANTE a conta certa ANTES
  de entrar no fluxo de criação — ver seção "TROCA DE CONTA" (checa @ no perfil e
  alterna via multi-login se necessário).

## TELA 6 — "Mais opções" (action_bar_title='Mais opções')
- ⚠️ Na tela de compartilhar, a linha '... Mais opções' (`id=title` text='Mais opções')
  fica ABAIXO da dobra → ROLAR (swipe up ~1x) até achar e tocar. ✅ TESTADO.
- Seção 'Preferências de compartilhamento' com VÁRIAS chaves, cada uma: `id=title` (texto) + `id=toggle` (ToggleButton)
- Linhas: **'Programar esse post'** (1ª), 'Desativar comentários', 'Ocultar nº de curtidas',
  'Ocultar nº de compartilhamentos', 'Compartilhamento automático'
- ⚠️ TODAS as chaves têm `id=toggle` IGUAL (sem id único)! Estratégia: achar o TextView
  `text='Programar esse post'` → subir ao container da linha → tocar o ToggleButton daquela linha.
  (xpath: //*[@text="Programar esse post"]/../..//*[@class="android.widget.ToggleButton"] ou similar)
- Ao ATIVAR a chave → abre overlay de DATA/HORA (de 5 em 5 min). No FÍSICO o seletor de
  hora é diferente (relógio circular) — RE-VERIFICAR no Android físico depois.

## TELA 7 — Overlay "Programar post" estilo RODA ✅ TESTADO (Galaxy S21U/And.15/IG 438)
### ⚠️ ARMADILHAS DESCOBERTAS NO TESTE REAL (custaram tempo — leia antes de mexer)
1. **`numberpicker_input` é do FRAMEWORK: `android:id/numberpicker_input`** — NÃO
   `com.instagram.android:id/...`. Usar o prefixo errado faz a detecção falhar.
2. **O título 'Programar post' aparece nos DOIS estilos** → NUNCA usar como sinal de
   detecção. Correto: existe `android:id/numberpicker_input`? → RODA. Existe linha
   `descriptionStartsWith='Data,'`? → RELÓGIO.
3. **CLICAR nos botões de valor anterior/seguinte NÃO FUNCIONA** (de ~180 cliques,
   1 registrou). O NumberPicker só responde a **GESTO**.
4. **Calibração do gesto:** swipe vertical de **1 altura de item** (o `numberpicker_input`
   mede ~135px) com `duration=0.25` = **exatamente 1 passo**. Para cima = próximo valor,
   para baixo = anterior. Dormir ~0.55s entre gestos (animação).
5. **Tocar na LINHA do agendamento (quando já ligada) DESLIGA a chave** — não reabre o
   seletor. Para reabrir, acionar a chave de novo (`toggle_schedule`).

### Estrutura (3 colunas)
- Folha: `id=date_picker_sheet` → `date_picker_hint_text` → `date_picker_container` → `time_picker_view`
- Cada coluna: `Button`(valor anterior) / `EditText android:id/numberpicker_input`(ATUAL) / `Button`(valor seguinte)
  - [0] DATA (ex.: 'qui., 23 de jul.') — sem botão "anterior" quando está em HOJE (mínimo)
  - [1] HORA ('13') · [2] MINUTO ('55', de 5 em 5)
- **CONCLUIR:** `id=bb_primary_action_container` (desc='Concluir')
- ESTRATÉGIA (androidposter): DATA = contar dias (`delta = alvo - hoje`, 1 gesto/dia) em vez
  de interpretar o texto localizado; HORA/MINUTO = caminho circular mais curto (módulo 24 / 60 passo 5).

## TELA 7 (nota antiga) — Overlay "Programar post" (data + hora) — EMULADOR
- Título: `id=title_text_view` text='Programar post'
- Container: `id=date_picker_sheet`; dica: `id=date_picker_hint_text`
- **3 NumberPickers, todos `id=numberpicker_input` (EditText), por ÍNDICE:**
  - [0] DATA (ex.: 'qua., 22 de jul.')  [1] HORA (ex.: '19')  [2] MINUTO (ex.: '50', de 5 em 5)
- **CONCLUIR (ativa a programação E a chave toggle): `id=bb_primary_action_container`** (desc='Concluir')
- ⚠️ Sem o Concluir, a chave NÃO ativa (Voltar/clicar fora = cancela).
- Minutos de 5 em 5 → batem exatamente com postplan.py (±10/±5/0). 
- SETAR os pickers: ler valor atual do `numberpicker_input` e rolar (swipe) até o alvo,
  OU tentar set_text. Distinguir os 3 por índice/posição. FISICO tem picker diferente
  (relógio circular) — RE-VERIFICAR e mapear à parte.

### TELA 7-ALT — Overlay data/hora estilo RELÓGIO ✅ CAPTURADO (emulador)
**O QUE ALTERNA O ESTILO (medido):** é um teste A/B do IG que parece ser **POR CONTA**,
NÃO por aparelho. No MESMO Galaxy S21U: `@mentalityfilter` mostrou SEMPRE **RODA** e
`@mentedespierta.es` mostrou SEMPRE **RELÓGIO** (5x seguidas cada). Portanto o estilo é
estável por conta, mas **TRATAR OS DOIS COMO POSSÍVEIS** e SEMPRE DETECTAR em runtime:
existe `android:id/numberpicker_input` → RODA; existe linha `descriptionStartsWith='Data,'`
→ RELÓGIO. (⚠ o título 'Programar post' aparece nos DOIS — nunca usar como sinal.)
✅ AMBOS os estilos testados no FÍSICO: roda="Sat, Jul 25, 4:40PM"; relógio="Sun, Jul 26, 2:20PM".

**Overlay "Programar post" (folha IG):**
- Título: `id=title_text_view` text='Programar post'; subtítulo de fuso `id=subtitle_text_view`
- **Linha DATA:** `Button` `descriptionStartsWith='Data,'` (desc completo ex.: 'Data, qua., jul. 22, 2026')
  → dentro: `id=igds_textcell_title`='Data', `id=igds_textcell_subtitle`=data atual, `igds_textcell_chevron`
- **Linha HORÁRIO:** `Button` `descriptionStartsWith='Horário,'` (ex.: 'Horário, 10:35 PM')
  → `id=igds_textcell_title`='Horário', `id=igds_textcell_subtitle`=hora atual
- **CONCLUIR (fecha o overlay e ativa a programação):** `id=bb_primary_action_container` desc='Concluir'

**Diálogo DATA = Material DatePicker (ids no namespace `android:`):**
- `id=datePicker`; cabeçalho `id=date_picker_header_year`(ex.'2026') + `id=date_picker_header_date`('Qua., 22 de jul.')
- **Dias:** `View` clicável com `text`=número do dia E **`content-desc`='DD <mês> AAAA'** (ex.: desc='25 julho 2026')
  → bot seleciona por content-desc (mês por extenso, minúsculo, em pt).
- **Próximo mês:** `id=next` (desc='Próximo mês'); mês anterior fica OCULTO p/ datas passadas.
- **CANCELAR:** `id=button2` · **OK:** `id=button1`  (namespace `android:id/...`)
- ESTRATÉGIA: se o mês alvo != mês exibido, tocar `next` N vezes; depois tocar o `View`
  cujo content-desc == "DD <mês> AAAA"; OK.

**Diálogo HORÁRIO = Material TimePicker (24h) — USAR O MODO TECLADO (robusto):**
- Modo dial (padrão): `id=timePicker`; `id=hours`(ex.'22') `id=separator`(':') `id=minutes`('35');
  `id=radial_picker` com números = `content-desc` '0'..'23'. (frágil: exige acertar ângulo)
- **`id=toggle_mode`** (desc='Alterne para o modo de entrada') → vira MODO TECLADO ↓↓
- **MODO TECLADO (o bot usa este):**
  - `id=input_header`='Definir horário'; `id=input_hour` (EditText, HH 24h) ; `id=input_minute` (EditText, MM)
  - labels `id=label_hour`='hora', `id=label_minute`='minuto'; volta ao dial por `id=toggle_mode`
  - **CANCELAR:** `id=button2` · **OK:** `id=button1`
- ESTRATÉGIA: tocar linha Horário → tocar `toggle_mode` → set_text `input_hour`=HH, `input_minute`=MM (24h) → OK.

**FLUXO do bot no estilo RELÓGIO:**
1. tocar linha DATA (`descriptionStartsWith='Data,'`) → (next N vezes p/ mês) → `View` desc="DD mês AAAA" → OK (`android:id/button1`)
2. tocar linha HORÁRIO (`descriptionStartsWith='Horário,'`) → `toggle_mode` → set input_hour/input_minute → OK
3. `bb_primary_action_container`(Concluir) → fecha overlay, chave Programar ativa
4. `share_footer_button` (vira 'Programar')

## TELA 8 — Submit final ✅
- **Botão final: `id=share_footer_button`** — MESMO componente; desc/text muda:
  'Compartilhar' (imediato) ↔ **'Programar'** (agendado). Container: `id=footer_button_container`.
- Também aparece 'Compartilhar também no…' (crosspost Facebook) — bot ignora.

## TELA 9 — "Marcar pessoas" (aberta por `metadata_row_people` da legenda)
- Título: `id=action_bar_title` text='Marcar pessoas'; Voltar: `id=action_bar_button_back`
- **"V" (visto, canto sup. direito) = CONFIRMA/SALVA colaboradores+marcações: ImageView `desc='Concluir'`**
  → o bot toca aqui DEPOIS de adicionar os colaboradores; volta à tela da legenda
- Quando há colaborador add: aparece a seção `id=row_header_textview` text='Colaboradores'
- Marcar pessoas na foto: `id=tag_image_view` — o bot NÃO usa
- **COLABORADOR: `id=invite_collaborator_button`** (desc='Convidar colaboradores') ← o bot toca aqui
### TELA 9b — Busca de colaboradores (abre ao tocar Convidar colaboradores)
- **Busca:** `id=search_edit_text` (desc='Procurar um usuário') → o bot digita o @
- **Linha de resultado:** `id=row_search_user_container` (Button), contém
  `id=row_search_user_username` (o @, ex.: 'mentedespierta.es') e `row_search_user_fullname`
- Bot: digita o @ → acha a `row_search_user_container` cujo `row_search_user_username` == @ alvo → toca
- Pode repetir (Convidar colaboradores de novo) p/ 2-3 colaboradores. Concluir: ImageView `desc='Concluir'`

---

## ✅ FLUXO COMPLETO (contas pequenas) — pronto para montar o poster.py
ORDEM do bot:
1. Checar conta ativa (`action_bar_title` == @destino)
2. Menu Criar (`desc='Criar novo'`) → 'Criar novo post'
3. Seleção: `multi_select_slide_button_alt` → tocar miniaturas na ordem (via data no desc) → `next_button_textview`
4. Edição: 'Taxa' → 'Retrato' → `bottom_sheet_done_button`(Concluir); Áudio → aba/lista → IMAGE RECOG. da ↗ → faixa → `select_button_tap_target`
5. `media_thumbnail_tray_button`(Avançar)
6. Legenda: `caption_input_text_view`(escreve); colaboradores: `metadata_row_people` → `invite_collaborator_button` → `search_edit_text`(@) → `row_search_user_container` → Concluir
7. Programar: rolar → toggle da linha 'Programar esse post' → overlay data/hora
   (roda: 3x `numberpicker_input` por índice; OU relógio nas contas grandes) → `bb_primary_action_container`(Concluir)
8. Submit: `share_footer_button` (vira 'Programar')

✅ Estilo RODA e estilo RELÓGIO AMBOS mapeados (ver TELA 7 e TELA 7-ALT). O bot
detecta em runtime qual apareceu (contas grandes alternam A/B). Re-verificar no
FÍSICO fica como conferência final (mesmos componentes Material → deve bater).

## TELA 6 — Configurações avançadas → Programar publicação (rolar p/ achar)
_(a capturar)_

## TELA 7 — Confirmação do agendamento
_(a capturar)_

---
NOTA: scroll é suportado (uiautomator2 rola até achar o elemento por texto/id).
