# Filtro de Repetidas — Instagram

Aplicativo desktop para filtrar publicações repetidas do Instagram antes do envio diário.
Desenvolvido para operações de marketing digital que reciclam conteúdo do próprio perfil.

---

## O que o app faz

1. Recebe o link de uma publicação do Instagram (carrossel ou imagem única)
2. Baixa as mídias via [SnapInsta.to](https://snapinsta.to/pt) usando um navegador Chrome automatizado
3. Compara as imagens com todas as publicações já enviadas usando hash perceptual
4. Se não for repetida, salva automaticamente na pasta do dia de hoje (criando-a se necessário)
5. Registra curtidas, comentários e thumbnail no histórico interno do app

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
2. Cole o link de uma publicação do Instagram no campo de texto (ou use o botão **Colar**)
3. Clique em **Iniciar**
4. Acompanhe o progresso na barra e nos LOGs
5. Um popup verde indica sucesso; vermelho indica erro ou publicação repetida

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

O **preview** na aba de Configurações mostra em tempo real como ficará o nome da pasta.

---

## Como funciona a detecção de duplicatas

O app usa **hash perceptual** (`pHash` via biblioteca `imagehash`) para comparar imagens visualmente, não byte a byte. Isso garante que variações de compressão, redimensionamento ou metadados não causem falsos negativos.

**Parâmetros relevantes:**

- **COMPARE_FIRST_N = 4** — apenas as 4 primeiras imagens do carrossel são comparadas. As últimas costumam ser cards de CTA que se repetem entre publicações diferentes, o que geraria falsos positivos.
- **Limiar de similaridade (threshold)** — distância máxima entre hashes para considerar duas imagens iguais:
  - `0` = pixel-perfect idêntico
  - `5` (padrão) = tolera compressão JPEG e pequenas diferenças
  - `10+` = mais tolerante, pode gerar falsos positivos
- **Melhor alinhamento** — cada imagem nova é comparada com *todas* as imagens do post histórico (não apenas a da mesma posição), garantindo detecção mesmo se um post antigo tiver sido salvo fora de ordem

---

## Histórico de envios

O painel **Histórico de Envios** na aba principal exibe todos os posts processados com:

- Thumbnail da primeira imagem
- Nome da pasta de envio
- Data e hora do processamento
- Curtidas e comentários coletados do Instagram
- Link original (com botão de copiar)

Para apagar o histórico, clique em **Resetar** (um diálogo de confirmação será exibido).  
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
│   │   ├── config.json        ← configurações salvas
│   │   ├── history.json       ← histórico de envios
│   │   └── browser_profile/   ← sessão persistente do Chrome (login Instagram)
│   ├── config.py              ← leitura e escrita de configurações
│   ├── dedup.py               ← detecção de duplicatas por hash perceptual
│   ├── downloader.py          ← automação do SnapInsta.to + coleta de métricas do Instagram
│   ├── gui.py                 ← interface gráfica (Tkinter)
│   ├── main.py                ← ponto de entrada
│   ├── organizer.py           ← criação e gestão das pastas de envio
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

### Coleta de curtidas/comentários

Após baixar as mídias, o app navega para a URL original do Instagram para capturar métricas do DOM. Isso requer login no Instagram naquele perfil de browser.

**Detalhe crítico de implementação:** o Instagram renderiza os botões de "curtir" dos comentários *antes* da barra de ações no DOM. Por isso o seletor usa `querySelectorAll('svg[aria-label="Curtir"]')[length-1]` (o *último* SVG) para garantir que está lendo o like da barra de ações, não de um comentário. O SVG de comentar aparece apenas uma vez, então `querySelector` basta.

### Compatibilidade script vs. executável (paths.py)

O módulo `paths.py` resolve onde ficam os arquivos dependendo do contexto de execução:

| Contexto | `DATA_DIR` | `ASSETS_DIR` |
|---|---|---|
| Script Python (`python main.py`) | `instabot/data/` | `instabot/assets/` |
| Executável PyInstaller | `data/` ao lado do `.exe` | `_internal/assets/` dentro do bundle |

`DATA_DIR` fica fora do bundle porque é gravável (histórico, config, sessão do Chrome).  
`ASSETS_DIR` fica dentro do bundle porque é somente leitura (ícones).
