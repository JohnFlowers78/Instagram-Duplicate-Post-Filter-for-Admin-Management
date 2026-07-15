# Filtro de Repetidas — Instagram

Aplicativo desktop para filtrar publicações repetidas do Instagram antes do envio diário.
Desenvolvido para operações de marketing digital que reciclam conteúdo do próprio perfil.

---

## O que o app faz

O app tem **dois filtros**, cada um numa aba (mais a aba de Configurações):

### 🔗 Filtro por Link
1. Recebe o link de uma publicação do Instagram (carrossel ou imagem única)
2. Baixa as mídias via [SnapInsta.to](https://snapinsta.to/pt) usando um navegador Chrome automatizado
3. Compara as imagens com a **Pasta de Destino** (seus envios) **e** com a Fila de Espera, usando hash perceptual
4. Se não for repetida, **usa agora** (salva na próxima pasta livre do dia) ou **adiciona à Fila de Espera** — você escolhe na chave seletora
5. Registra curtidas, comentários, data de publicação e thumbnail no histórico

### 🔁 Filtro Entre Contas
Analisa a pasta **inteira de outra conta** e monta listas reutilizáveis: cada publicação é comparada com a sua Pasta de Destino (as repetidas ficam em cinza), e você reaproveita conteúdo entre diferentes clientes. Detecta ainda o tipo de **CTA** de cada publicação por OCR (Comentar / Seguir / Guardar).

Tem também **tema claro/escuro**, **Fila de Espera** reordenável por arraste, **Histórico** navegável por dia (timeline) e painéis redimensionáveis.

> 💡 Observações de operação e ideias futuras ficam registradas no [IDEIAS.md](IDEIAS.md) — documento vivo que acompanha o desenvolvimento.

---

## Pré-requisitos

| Requisito | Versão mínima | Observação |
|---|---|---|
| Windows | 10 ou 11 | Testado no Windows 11 Pro |
| Google Chrome | qualquer versão recente | Obrigatório mesmo no executável |
| Python | 3.12 | Apenas para rodar via código-fonte |
| Tesseract OCR | 5.x | **Opcional** — só para detectar o CTA no "Filtro Entre Contas" (veja abaixo) |

### Tesseract (opcional — detecção de CTA)

A leitura do CTA dos cards finais usa OCR via **Tesseract**. Sem ele o app funciona normalmente; só a linha de CTA mostra *"OCR indisponível"*.

1. Baixe o instalador do Windows: **https://github.com/UB-Mannheim/tesseract/wiki**
2. Instale em `C:\Program Files\Tesseract-OCR\` (ou deixe no PATH). Na tela de idiomas, marque **Português** e **Espanhol**.
3. O app localiza o `tesseract.exe` sozinho (PATH → `C:\Program Files\Tesseract-OCR\` → AppData). Vale tanto para o código-fonte quanto para o executável (o Tesseract é uma instalação do sistema, não vem no `.exe`).

---

## Opção 1 — Usar o executável (sem Python)

O executável portátil fica em `dist\FiltroDeRepetidas\` após o build.

**Para distribuir:** zipar a pasta `dist\FiltroDeRepetidas\` inteira e copiar para outro computador.  
**Para rodar:** abrir `FiltroDeRepetidas.exe`. Não precisa de Python instalado, apenas Chrome.

> A pasta `data\` (histórico, configurações e sessão do Instagram) é criada automaticamente ao lado do `.exe` na primeira execução. **Não inclua a pasta `data\` ao distribuir** — cada usuário cria a sua.

---

## Opção 2 — Rodar via código-fonte

### 1. Clonar o repositório

```
git clone https://github.com/JohnFlowers78/Instagram-Duplicate-Post-Filter-for-Admin-Management.git
cd Instagram-Duplicate-Post-Filter-for-Admin-Management
```

### 2. Criar o ambiente virtual

```powershell
python -m venv instabot/venv
```

### 3. Ativar o venv e instalar dependências

```powershell
instabot\venv\Scripts\activate
pip install -r instabot/requirements.txt
```

### 4. Instalar os navegadores do Playwright

```powershell
playwright install chrome
```

> Este passo não tem equivalente no JS/Node — o Playwright precisa baixar o binário do Chrome para automação.

### 5. Rodar o app

```powershell
python instabot/main.py
```

---

## Gerar o executável (build)

Execute o arquivo `build.bat` na raiz do projeto:

```
build.bat
```

O script instala o PyInstaller no venv e gera a pasta `dist\FiltroDeRepetidas\` automaticamente.  
O build leva alguns minutos e gera em torno de 175 MB de arquivos.

---

## Como usar o app

### Primeiro uso — login no Instagram

O navegador Chrome que o app abre é um perfil persistente. Na primeira vez:

1. Inicie qualquer pipeline (cole um link e clique em Iniciar)
2. O Chrome abrirá o SnapInsta.to. Após o download, o app navega para o Instagram
3. Sem sessão logada, o app **pausa e avisa** (balão "🔐 Login necessário" + tela de login aberta no Chrome): faça login nessa janela e o processo **continua sozinho** assim que a sessão for detectada (aguarda até 5 minutos; sem login, segue sem curtidas/comentários)
4. A sessão fica salva — nas próximas vezes o login é automático

### Fluxo de uso normal (aba "Filtro por Link")

1. Em **Configurações → Pasta de Destino**, escolha a pasta raiz onde ficam todas as pastas de envio (é a sua base de comparação)
2. Na aba **Filtro por Link**, escolha o modo na chave seletora: **Utilizar agora** ou **Adicionar à Fila de Espera**
3. Cole o link de uma publicação do Instagram no campo de texto (ou use o botão **Colar**)
4. Clique em **Iniciar** (ou **Adicionar à Fila**)
5. Acompanhe o progresso na barra e nos LOGs
6. Um popup verde indica sucesso; vermelho indica erro ou publicação repetida

### Salvos (Fila de Espera) e Coleções

Publicações adicionadas são **baixadas e estacionadas** para uso posterior, na lista principal **Salvos**. O painel é aberto pela seta **❯** no canto superior direito e fica à direita da tela. Um alternador no topo troca entre a lista **Salvos** e a grade de **Coleções**.

- **Utilizar de Próxima** (verde): manda a publicação para a próxima pasta livre do dia e a remove dos Salvos. Se não houver pasta livre, um aviso flutuante aparece por alguns segundos.
- **Remover da Espera** (vermelho): tira dos Salvos e apaga as imagens estacionadas (libera espaço).
- **🔖 Salvar em Coleções**: adiciona a publicação a uma ou mais coleções (pode criar coleção nova ali mesmo). Por padrão ela fica **nos dois lugares** (Salvos + coleção); marcando **"Tirar dos Salvos"** ela aparece **só nas coleções** marcadas — mas continua valendo para a detecção de repetidas e o Utilizar de Próxima.
- **Reordenar**: arraste pela alça **⠿** (canto superior direito de cada item) para mudar a ordem — só na lista principal, movimento suave estilo playlist.
- **↻ Métricas** (topo do painel): o bot abre o navegador e visita cada link, um por um, atualizando curtidas e comentários. Pede confirmação antes (o sistema fica ocupado durante o processo) e os cartões atualizam em tempo real; se uma captura falhar, os valores antigos são mantidos.
- **Esvaziar** (topo do painel): remove todas as publicações dos Salvos e apaga as imagens estacionadas (com confirmação).
- O painel é **redimensionável** (puxe a alça **⋮** na borda esquerda dele), respeitando as larguras mínimas do painel e da área principal.

**Coleções** (grade estilo "Salvos" do Instagram): cada coleção vira um quadrado com **mosaico 2×2** das capas de até 4 publicações, com nome e contagem. Botões para **criar** (+ Nova Coleção), **renomear** (✏) e **apagar** (🗑). Apagar uma coleção **não apaga publicações** — as que estavam só nela voltam para os Salvos.

Ao **Adicionar à Fila** por link, o campo **"Salvar em:"** permite mandar a publicação direto para **Salvos (geral)** ou **Salvos + uma coleção** (ou criar a coleção na hora), sem precisar abrir o 🔖 depois.

Só entram nos Salvos publicações **não repetidas** (o filtro roda antes). Se você tentar **Utilizar agora** uma publicação que já está salva, o app avisa — e, se você confirmar o uso, a cópia é removida automaticamente.

### Filtro Entre Contas

Serve para **reaproveitar conteúdo de outra conta** (por exemplo, entre clientes diferentes). Na aba **Filtro Entre Contas**:

1. Selecione a **Pasta de Publicações da Conta de Origem** (as pastas seguem o mesmo padrão `Dia..._X`, a inicial no fim pode ser diferente)
2. Dê um **nome à lista** e clique em **Analisar Conta**
3. O app varre **todas** as publicações da pasta, compara cada uma com a sua Pasta de Destino e cria uma lista na fila da direita

As listas ficam no painel da direita, com um **seletor (dropdown)** para alternar entre as contas/clientes, um botão **↻ Recarregar** (re-checa quais ainda estão disponíveis) e um botão **🗑 Apagar Lista** (remove a lista ativa com confirmação — as imagens da conta de origem ficam intactas).

- **Repetida** (já existe no destino) → aparece **em cinza**, mostrando em qual pasta já existe
- **Disponível** → item colorido, com **Utilizar de Próxima** (vai pra próxima pasta livre + histórico) e fica cinza depois de usada
- **CTA**: em segundo plano, o OCR lê os últimos cards e mostra o tipo de chamada — ex. `CTA: Comentar QUIERO · Seguir` (prioriza COMENTAR). Só roda nos itens disponíveis primeiro; se não achar, mostra "não detectada"
- A **legenda** viaja junto: ao usar um item, o texto do `Legenda.txt` da origem é gravado na pasta de destino
- A lista é **virtualizada** — abre leve mesmo com centenas de publicações (renderiza só o que aparece na tela)
- **Filtros e ordenação**: barra no painel para ordenar (dia ↑↓, disponíveis primeiro, repetidas/utilizadas primeiro, CTA) e filtrar **combinando** status, tipo de CTA, palavra-gatilho e faixa de dias — ex.: só publicações *Comentar RECETAS*, *disponíveis*, *a partir do dia 20*. Um contador mostra "X de Y" e o botão **Limpar filtros** zera tudo
- **Marcação manual**: botões **É Repetida** / **Não é Repetida** em cada item, para quando o filtro não reconhece sozinho (ex.: Card Final refeito). Ao marcar, dá para indicar a pasta/dia onde ela já existe (opcional). O **Recarregar preserva** as marcações manuais
- Os **LOGs** mostram o andamento do OCR de CTA: quantas já foram analisadas, qual está sendo analisada agora (disponíveis primeiro, depois repetidas/já utilizadas) e o resultado de cada uma
- Ao usar um item, a pasta de destino **não recebe cache de hash** — ele é recriado depois, a partir das imagens reais (afinal o Card Final ainda vai ser refeito)

O **Histórico de Envios** é compartilhado entre as duas abas — funciona como a *timeline do dia*, para você montar a rotina misturando publicações do Filtro por Link e do Filtro Entre Contas.

### Tema claro/escuro

Em **Configurações → Aparência**, alterne entre **☀ Claro** e **☾ Escuro**. A troca é aplicada na hora e fica salva para as próximas aberturas.

### Painéis redimensionáveis

A divisória **• • •** entre os LOGs e o Histórico pode ser arrastada para dar mais espaço a um ou outro.

### O que acontece na pasta selecionada

O app cria automaticamente uma pasta para o dia de hoje com subpastas numeradas para cada envio:

```
Pasta raiz selecionada/
├── Dia1_15_06_26_V/
│   ├── 1/
│   │   ├── 1.jpg
│   │   ├── 2.jpg
│   │   └── Legenda.txt
│   ├── 2/
│   │   └── Legenda.txt   ← vazia, aguardando próximo envio
│   └── ...
└── Dia2_16_06_26_V/
    └── ...
```

Cada subpasta numerada (1, 2, 3...) corresponde a um slot de envio do dia.  
As pastas de slot abrem automaticamente em modo **Ícones Grandes** no Explorer do Windows.

---

## Configurações (aba Configurações)

| Configuração | Padrão | Descrição |
|---|---|---|
| Pasta de Destino | — | Pasta base dos seus envios (comparação) e onde as pastas dos dias são criadas |
| Incluir contador de dias | Ativado | Adiciona `Dia1`, `Dia2`... no nome da pasta |
| Incluir inicial da pessoa | Ativado | Adiciona a inicial do responsável pelo envio |
| Inicial da pessoa | `Z` | Letra que identifica o responsável |
| Publicações por dia | `4` | Quantos slots são criados na pasta do dia |
| Limiar de similaridade | `5` | Sensibilidade do filtro de duplicatas (veja abaixo) |
| Aparência (tema) | `Claro` | Alterna entre tema claro e escuro (aplica na hora) |

O **preview** na aba de Configurações mostra em tempo real como ficará o nome da pasta.

---

## Como funciona a detecção de duplicatas

O app usa **hash perceptual** (`pHash` via biblioteca `imagehash`) para comparar imagens visualmente, não byte a byte. Isso garante que variações de compressão, redimensionamento ou metadados não causem falsos negativos.

A comparação funciona como um **jogo da memória bijetivo** entre o carrossel novo e cada publicação já registrada:

- **Todos os cards são comparados** (não apenas os primeiros) — um card único no meio ou no fim do carrossel é suficiente para distinguir duas publicações diferentes.
- **Matching bipartido máximo** (algoritmo de *augmenting paths*) — cada imagem só pode ser pareada uma vez, e o resultado é sempre o ótimo, independente da ordem dos cards. Isso evita tanto o falso positivo (cards de template compartilhados) quanto o falso negativo (cards reordenados).
- **Tolerância do card final (CTA)** — o último card costuma mudar entre publicações (data, oferta, chamada). Por isso o algoritmo **ignora 1 card de diferença**: se todas as imagens menos uma encontram par, é tratado como repetida (e você confere visualmente no balão lado a lado).
- **Checa histórico + Fila de Espera** — a publicação nova é comparada com o histórico de envios **e** com o que está aguardando na Fila de Espera.

**Limiar de similaridade (threshold)** — distância máxima entre hashes para considerar duas imagens iguais:
- `0` = pixel-perfect idêntico
- `5` (padrão) = tolera compressão JPEG e pequenas diferenças
- `10+` = mais tolerante, pode gerar falsos positivos

Quando uma repetida é detectada, aparece um **balão lado a lado** com a imagem inicial da nova publicação e da já existente, com a opção de **confirmar** ou **salvar mesmo assim** (caso seja um falso positivo).

**Cache de hashes** — cada pasta de envio guarda um `.hashes.json` com os hashes já calculados, carregado instantaneamente nas próximas comparações. O cache guarda a **assinatura** de cada imagem (nome, tamanho e data de modificação): trocar qualquer card — ex.: Card Final refeito por IA — invalida e recalcula sozinho, só daquela pasta. Para forçar um recálculo geral, use **Configurações → Apagar caches de hash**.

---

## Histórico de envios

O painel **Histórico de Envios** é a *timeline do dia*, compartilhado entre as abas. Cada item mostra:

- Thumbnail da primeira imagem, nome da pasta de envio
- **Salva em:** data/hora do processamento · **Postado em:** data de publicação no Instagram · curtidas e comentários
- Vindas do Filtro Entre Contas mostram a origem: **↪ De outra conta (R): Dia.../N** (dia e inicial da conta de origem)
- Link clicável com botão de copiar (mini balão **"Copiado!"**) e botão **📁** para abrir a pasta
- No **dia atual**: botões **↩ Retornar para a Fila** (devolve a publicação para a origem) e **×** (apaga o registro)

**Navegação por dia:** a página inicial é **sempre o dia de HOJE** (pela data da máquina) — se hoje ainda não teve envios, aparece uma lista em branco e os dias anteriores ficam atrás da seta **◀** (mostrando o nome da pasta do dia). Os novos envios entram **no fim** da lista. Dias passados são **somente leitura** (sem botões de ação). O arquivo fica em `data/history.json`.

O botão **Resetar** (com confirmação) só aparece na lista de **hoje** com envios: devolve cada publicação à sua origem — itens do Filtro Entre Contas voltam coloridos para a lista, itens que vieram da Fila de Espera voltam para a fila, e itens de link direto apenas liberam a pasta do dia (o link precisa ser colado de novo).

---

## Estrutura do projeto

```
/
├── instabot/
│   ├── assets/
│   │   ├── icon.ico           ← ícone da janela e taskbar do Windows
│   │   └── logo_header.png    ← logo exibida no header da GUI
│   ├── venv/                  ← ambiente virtual Python (não commitado)
│   ├── data/                  ← dados do usuário (não commitados)
│   │   ├── config.json        ← configurações salvas (inclui o tema)
│   │   ├── history.json       ← histórico de envios
│   │   ├── waiting_queue.json ← metadados da Fila de Espera
│   │   ├── waiting_queue/     ← imagens estacionadas na Fila de Espera
│   │   ├── cross_lists.json   ← listas do Filtro Entre Contas
│   │   └── browser_profile/   ← sessão persistente do Chrome (login Instagram)
│   ├── config.py              ← leitura e escrita de configurações
│   ├── crossaccount.py        ← listas nomeadas do Filtro Entre Contas
│   ├── cta.py                 ← detecção do tipo de CTA por OCR (Tesseract)
│   ├── dedup.py               ← detecção de duplicatas por hash perceptual
│   ├── downloader.py          ← automação do SnapInsta.to + coleta de métricas do Instagram
│   ├── gui.py                 ← interface gráfica (Tkinter)
│   ├── main.py                ← ponto de entrada
│   ├── organizer.py           ← criação e gestão das pastas de envio
│   ├── waitqueue.py           ← persistência e imagens da Fila de Espera
│   ├── paths.py               ← resolução de caminhos (script vs. executável)
│   └── requirements.txt       ← dependências Python
├── build.bat                  ← script para gerar o executável
├── filtro.spec                ← configuração do PyInstaller
├── IDEIAS.md                  ← observações de operação e ideias futuras (documento vivo)
└── README.md
```

---

## Dependências

| Biblioteca | Uso |
|---|---|
| `playwright` | Automação do Chrome (SnapInsta.to + Instagram) |
| `playwright-stealth` | Contorna detecção de bot do Instagram |
| `Pillow` | Abertura e processamento de imagens |
| `imagehash` | Hash perceptual para comparação de imagens |
| `pytesseract` | Ponte para o Tesseract OCR (detecção de CTA) — precisa do Tesseract instalado no sistema |
| `requests` | Download das mídias via HTTP direto |

---

## Detalhes técnicos relevantes para manutenção

### Por que o app usa Chrome real (não headless)?

O Instagram e o SnapInsta.to detectam e bloqueiam browsers headless convencionais. O app usa `channel="chrome"` do Playwright para controlar o Chrome do usuário com um perfil persistente, tornando o tráfego indistinguível de uso humano.

### Coleta de curtidas/comentários/data

Após baixar as mídias, o app navega para a URL original do Instagram para capturar métricas do DOM. Isso requer login no Instagram naquele perfil de browser.

A **data de publicação** é lida do elemento `<time>` da postagem (o `title`, que sempre traz o ano completo em pt-BR), identificado pelo permalink `/p/<shortcode>/` para não confundir com as datas dos comentários.

**Detalhe crítico de implementação:** o Instagram renderiza os botões de "curtir" dos comentários *antes* da barra de ações no DOM. Por isso o seletor usa `querySelectorAll('svg[aria-label="Curtir"]')[length-1]` (o *último* SVG) para garantir que está lendo o like da barra de ações, não de um comentário. O SVG de comentar aparece apenas uma vez, então `querySelector` basta.

### Detecção de CTA (cta.py)

O tipo de CTA é lido por **OCR (Tesseract via `pytesseract`, `por+spa`)** nos últimos cards de cada publicação, seguido de classificação por palavras-chave. Roda **em segundo plano** (a lista abre na hora e os CTAs preenchem aos poucos), priorizando os itens **disponíveis**. A atualização é **reativa** — só o rótulo do item que mudou é reconfigurado, sem re-renderizar a lista (sem "piscar"). Se o Tesseract não estiver instalado, `cta.available()` retorna `False` e o app segue normal.

### Filtro Entre Contas (crossaccount.py)

Cada lista referencia as imagens **direto na pasta de origem** (não copia — uma conta pode ter centenas de publicações), guardando os hashes já calculados para o Recarregar. A lista na UI é **virtualizada**: só os cartões visíveis (+ uma margem) são criados de fato, então abrir uma lista de 600 itens é instantâneo.

### Compatibilidade script vs. executável (paths.py)

O módulo `paths.py` resolve onde ficam os arquivos dependendo do contexto de execução:

| Contexto | `DATA_DIR` | `ASSETS_DIR` |
|---|---|---|
| Script Python (`python main.py`) | `instabot/data/` | `instabot/assets/` |
| Executável PyInstaller | `data/` ao lado do `.exe` | `_internal/assets/` dentro do bundle |

`DATA_DIR` fica fora do bundle porque é gravável (histórico, config, sessão do Chrome).  
`ASSETS_DIR` fica dentro do bundle porque é somente leitura (ícones).
