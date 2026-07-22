# Mapa de seletores — fluxo de Postagem/Programação do Instagram (Android)

Capturado ao vivo no emulador (uiautomator2), app com.instagram.android.
Cada passo lista o seletor que o poster.py vai usar (id / text / desc).

---

## CHECAGEM DE CONTA (sempre antes de postar)
- Username ativo no topo do perfil: `id=action_bar_title` → text = @ da conta
  (ex.: "mentalityfilter"). O bot confere se bate com a conta de destino.
- Abrir o menu Criar: action bar do perfil, ImageView `desc='Criar novo'`.

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
- ⚠️ ORDEM DO CARROSSEL: as miniaturas NÃO têm o nome do arquivo no crachá; a
  galeria ordena por DATA (mais recente primeiro) e a ORDEM DE TOQUE = ordem do
  carrossel. SOLUÇÃO no poster.py: ao `adb push`, dar timestamps de forma que
  "1" seja o mais recente (aparece 1º) OU tocar as miniaturas na ordem inversa
  do grid. A VALIDAR no teste real.

### ✅ SOLUÇÃO DA ORDEM (descoberta na captura da tela selecionada)
- Miniatura SELECIONADA: `id=gallery_grid_item_thumbnail`, desc =
  "Número da mídia selecionada N Miniatura de foto com criação em <DATA> <HORA>"
  → expõe o número da ordem (N) E a data/hora de criação!
- Miniatura não selecionada: desc = "Não selecionado ... com criação em <DATA> <HORA>"
- Círculo de seleção: `id=gallery_grid_item_selection_circle`; desmarcar: `id=unselect_button`
- **ESTRATÉGIA ROBUSTA:** no adb push, dar a cada imagem um timestamp DISTINTO
  (>= 1 min de diferença). O bot lê a "criação em <HORA>" no desc de cada miniatura,
  mapeia hora→numero do arquivo, e toca na ordem 1..N. Não depende do sort da galeria.
  (granularidade do desc é minuto → espacar os timestamps em >= 1 min).

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
- **Legenda:** `id=caption_input_text_view` (AutoComplete; text placeholder 'Adicione uma legenda…')
  → o bot escreve o conteúdo do Legenda.txt
- **Marcar pessoas/COLABORADOR:** `id=metadata_row_people` (contém `tag_people_string`='Marcar pessoas')
- Música aplicada (confirma): `id=music_track_title`/`music_track_subtitle`; remover `id=music_track_cross`
- Localização: `id=metadata_location_row`
- Preview: `id=photo_media_preview_image_view` (miniaturas do carrossel)
- **Compartilhar (postar direto):** `id=share_footer_button`
- Voltar: `id=button_back`
- ⚠️ "... Mais opções" (Config. avançadas → PROGRAMAR) fica ABAIXO da dobra — rolar p/ achar.
- NOTA: conta de destino (@) não aparece aqui; troca de conta foi ADIADA pelo usuário
  (por ora o bot posta na conta ativa, confirmada por action_bar_title).

## TELA 6 — "Mais opções" (action_bar_title='Mais opções')
- Seção 'Preferências de compartilhamento' com VÁRIAS chaves, cada uma: `id=title` (texto) + `id=toggle` (ToggleButton)
- Linhas: **'Programar esse post'** (1ª), 'Desativar comentários', 'Ocultar nº de curtidas',
  'Ocultar nº de compartilhamentos', 'Compartilhamento automático'
- ⚠️ TODAS as chaves têm `id=toggle` IGUAL (sem id único)! Estratégia: achar o TextView
  `text='Programar esse post'` → subir ao container da linha → tocar o ToggleButton daquela linha.
  (xpath: //*[@text="Programar esse post"]/../..//*[@class="android.widget.ToggleButton"] ou similar)
- Ao ATIVAR a chave → abre overlay de DATA/HORA (de 5 em 5 min). No FÍSICO o seletor de
  hora é diferente (relógio circular) — RE-VERIFICAR no Android físico depois.

## TELA 7 — Overlay "Programar post" (data + hora) — EMULADOR
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

### TELA 7-ALT — Overlay data/hora estilo RELÓGIO (contas GRANDES: 200k/2M) — a mapear no emulador
- Variável que muda o estilo: provavelmente o Nº DE SEGUIDORES da conta.
- Estrutura (dos prints): a folha "Programar post" tem 2 LINHAS: **"Data"** e **"Horário"**,
  cada uma abre um diálogo separado (Material):
  - Data → calendário (grade de dias, mês, > ) + CANCELAR / OK
  - Horário → relógio de HORAS (00–23 em círculo) → ao escolher, abre relógio de MINUTOS
    (00,05,...55 em círculo) → CANCELAR / OK
- poster.py deve DETECTAR qual estilo apareceu (numberpicker_input? então roda; senão relógio)
  e agir conforme. RE-VERIFICAR logando conta grande no emulador (capturar os seletores).

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

FALTA: mapear estilo RELÓGIO (conta grande) + re-verificar no FÍSICO.

## TELA 6 — Configurações avançadas → Programar publicação (rolar p/ achar)
_(a capturar)_

## TELA 7 — Confirmação do agendamento
_(a capturar)_

---
NOTA: scroll é suportado (uiautomator2 rola até achar o elemento por texto/id).
