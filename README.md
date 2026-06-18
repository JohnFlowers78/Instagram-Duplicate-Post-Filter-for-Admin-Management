# Filtro de Repetidas — Instagram

Aplicativo desktop para filtrar publicações repetidas do Instagram antes do envio diário.
Desenvolvido para operações de marketing digital que reciclam conteúdo do próprio perfil.

---

## O que o app faz

1. Recebe o link de uma publicação do Instagram (carrossel ou imagem única)
2. Baixa as mídias via [SnapInsta.to](https://snapinsta.to/pt) usando um navegador Chrome automatizado
3. Compara as imagens com todas as publicações já enviadas (histórico) **e** com as que estão na Fila de Espera, usando hash perceptual
4. Se não for repetida, **usa agora** (salva na próxima pasta livre do dia) ou **adiciona à Fila de Espera** para usar depois — você escolhe na chave seletora
5. Registra curtidas, comentários, data de publicação e thumbnail no histórico interno do app

Tem ainda **tema claro/escuro**, **Fila de Espera** reordenável por arraste e painéis redimensionáveis.

---

## Pré-requisitos

| Requisito | Versão mínima | Observação |
|---|---|---|
| Windows | 10 ou 11 | Testado no Windows 11 Pro |
| Google Chrome | qualquer versão recente | Obrigatório mesmo no executável |
| Python | 3.12 | Apenas para rodar via código-fonte |

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
3. Se ainda não estiver logado, faça login manualmente nesta janela do Chrome
4. A sessão fica salva — nas próximas vezes o login é automático

### Fluxo de uso normal

1. Clique em **Selecionar...** e escolha a pasta raiz onde ficam todas as pastas de envio
2. Escolha o modo na chave seletora: **Utilizar agora** ou **Adicionar à Fila de Espera**
3. Cole o link de uma publicação do Instagram no campo de texto (ou use o botão **Colar**)
4. Clique em **Iniciar** (ou **Adicionar à Fila**)
5. Acompanhe o progresso na barra e nos LOGs
6. Um popup verde indica sucesso; vermelho indica erro ou publicação repetida

### Fila de Espera

Publicações adicionadas à Fila de Espera são **baixadas e estacionadas** para uso posterior. O painel é aberto pela seta **❯** no canto superior direito e fica à direita da tela.

- **Utilizar de Próxima** (verde): manda a publicação para a próxima pasta livre do dia e a remove da fila. Se não houver pasta livre, um aviso flutuante aparece por alguns segundos.
- **Remover da Espera** (vermelho): tira da fila e apaga as imagens estacionadas (libera espaço).
- **Reordenar**: arraste pela alça **⠿** (canto superior direito de cada item) para mudar a ordem — o movimento é suave, estilo edição de playlist.
- O painel é **redimensionável** (puxe a alça **⋮** na borda esquerda dele).

Só entram na fila publicações **não repetidas** (o filtro roda antes). Se você tentar **Utilizar agora** uma publicação que já está na fila, o app avisa — e, se você confirmar o uso, a cópia da fila é removida automaticamente.

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
| Incluir contador de dias | Ativado | Adiciona `Dia1`, `Dia2`... no nome da pasta |
| Incluir inicial da pessoa | Ativado | Adiciona a inicial do responsável pelo envio |
| Inicial da pessoa | `V` | Letra que identifica o responsável |
| Publicações por dia | `6` | Quantos slots são criados na pasta do dia |
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

**Cache de hashes** — cada pasta de envio guarda um `.hashes.json` com os hashes já calculados, carregado instantaneamente nas próximas comparações. O cache é recalculado automaticamente se as imagens da pasta mudarem.

---

## Histórico de envios

O painel **Histórico de Envios** na aba principal exibe todos os posts processados com:

- Thumbnail da primeira imagem
- Nome da pasta de envio
- **Salva em:** data e hora do processamento
- Curtidas, comentários e **Postado em:** (data de publicação no Instagram)
- Link original clicável (abre no navegador) com botão de copiar — ao copiar, aparece um mini balão **"Copiado!"**
- Botão **×** para apagar um item específico do histórico

Para apagar tudo, clique em **Resetar** (um diálogo de confirmação será exibido).  
O arquivo de histórico fica em `data/history.json`.

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
│   │   └── browser_profile/   ← sessão persistente do Chrome (login Instagram)
│   ├── config.py              ← leitura e escrita de configurações
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
| `requests` | Download das mídias via HTTP direto |

---

## Detalhes técnicos relevantes para manutenção

### Por que o app usa Chrome real (não headless)?

O Instagram e o SnapInsta.to detectam e bloqueiam browsers headless convencionais. O app usa `channel="chrome"` do Playwright para controlar o Chrome do usuário com um perfil persistente, tornando o tráfego indistinguível de uso humano.

### Coleta de curtidas/comentários/data

Após baixar as mídias, o app navega para a URL original do Instagram para capturar métricas do DOM. Isso requer login no Instagram naquele perfil de browser.

A **data de publicação** é lida do elemento `<time>` da postagem (o `title`, que sempre traz o ano completo em pt-BR), identificado pelo permalink `/p/<shortcode>/` para não confundir com as datas dos comentários.

**Detalhe crítico de implementação:** o Instagram renderiza os botões de "curtir" dos comentários *antes* da barra de ações no DOM. Por isso o seletor usa `querySelectorAll('svg[aria-label="Curtir"]')[length-1]` (o *último* SVG) para garantir que está lendo o like da barra de ações, não de um comentário. O SVG de comentar aparece apenas uma vez, então `querySelector` basta.

### Compatibilidade script vs. executável (paths.py)

O módulo `paths.py` resolve onde ficam os arquivos dependendo do contexto de execução:

| Contexto | `DATA_DIR` | `ASSETS_DIR` |
|---|---|---|
| Script Python (`python main.py`) | `instabot/data/` | `instabot/assets/` |
| Executável PyInstaller | `data/` ao lado do `.exe` | `_internal/assets/` dentro do bundle |

`DATA_DIR` fica fora do bundle porque é gravável (histórico, config, sessão do Chrome).  
`ASSETS_DIR` fica dentro do bundle porque é somente leitura (ícones).
