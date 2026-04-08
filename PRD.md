# PRD — TTS App

## Visão Geral

Aplicativo desktop para Linux que converte texto em fala (Text-to-Speech) usando a engine Microsoft Edge TTS. Interface gráfica moderna com suporte a múltiplos idiomas, tema claro/escuro, histórico, fila de exportação em lote e tray icon. Não requer conta ou API key, porém requer conexão com a internet para acessar o serviço online.

---

## Problema

Usuários Linux que precisam ouvir textos (acessibilidade, revisão de conteúdo, estudo) não têm uma ferramenta TTS desktop simples, com vozes de qualidade e controle de velocidade, que funcione com GUI intuitiva e integre bem ao ambiente de trabalho.

---

## Objetivos

- Converter texto em fala com vozes neurais de alta qualidade
- Permitir salvar o áudio gerado como arquivo MP3
- Funcionar inteiramente no Linux sem dependência de conta ou serviço pago
- Ser fácil de instalar e integrar ao sistema (launcher GNOME, tray, notificações)

---

## Usuários-Alvo

| Perfil                         | Necessidade                                       |
| ------------------------------ | ------------------------------------------------- |
| Usuário com deficiência visual | Ouvir textos sem configuração complexa            |
| Estudante / leitor             | Ouvir conteúdo enquanto faz outra coisa           |
| Criador de conteúdo            | Gerar áudio narrado rapidamente, exportar em lote |
| Desenvolvedor                  | Integrar TTS em scripts via `tts_utils`           |

---

## Funcionalidades

### Implementadas (v1.x)

| #   | Funcionalidade            | Descrição                                                                             |
| --- | ------------------------- | ------------------------------------------------------------------------------------- |
| F1  | Entrada de texto          | Área multilinha com undo/redo (Ctrl+Z/Y), contador de caracteres                      |
| F2  | Seleção de voz            | Dropdown com vozes neurais carregadas dinamicamente via API                           |
| F3  | Controle de velocidade    | Slider de -50% a +50%                                                                 |
| F4  | Controle de volume        | Slider de 0% a 100%                                                                   |
| F5  | Reprodução direta         | Botão "Falar" gera e reproduz; vira "■ Parar" durante reprodução                      |
| F6  | Salvar MP3                | Exporta o áudio para arquivo `.mp3`                                                   |
| F7  | Limpar texto              | Com confirmação quando há conteúdo                                                    |
| F8  | Checagem de dependências  | Verifica `edge-tts` e `ffplay` uma vez na inicialização                               |
| F9  | Abrir arquivo .txt        | Botão 📂 e atalho `Ctrl+O`                                                            |
| F10 | Colar clipboard           | Botão 📋 para colar diretamente                                                       |
| F11 | Histórico de textos       | Últimos 20 textos salvos em `~/.config/tts-app/history.json`                          |
| F12 | Fila de exportação        | Botão 📤 para exportar múltiplos textos em lote                                       |
| F13 | Tema claro/escuro         | Toggle ☀️/🌙 com preferência persistente                                              |
| F14 | Tamanho de fonte          | Botões A- / A+ no textarea                                                            |
| F15 | Filtro de vozes           | Campo de busca + abas de idioma (ALL PT EN ES FR DE JA ZH)                            |
| F16 | Vozes recentes            | Últimas 3 vozes usadas fixadas no topo do dropdown                                    |
| F17 | Indicador de carregamento | "⏳ carregando..." no seletor enquanto API busca vozes                                |
| F18 | Barra de progresso        | Progressbar indeterminada durante geração/salvamento                                  |
| F19 | Detecção de idioma        | Sugere voz automaticamente após 1s digitando (langdetect)                             |
| F20 | Texto longo               | Divide em chunks (>4500 chars) e concatena com ffmpeg                                 |
| F21 | Retry automático          | Tenta até 4x com backoff para erro 529 (serviço sobrecarregado)                       |
| F22 | Notificação desktop       | `notify-send` ao terminar reprodução e salvamento                                     |
| F23 | Tray icon                 | Minimiza para bandeja do sistema (pystray)                                            |
| F24 | Auto-update check         | Verifica atualizações via git ao iniciar (background)                                 |
| F25 | Preferências persistentes | Voz, velocidade, volume, tema e fonte salvos em `~/.config/tts-app/prefs.json`        |
| F26 | Atalhos de teclado        | `Ctrl+Enter` falar · `Ctrl+S` salvar · `Ctrl+O` abrir · `Esc` parar                   |
| F27 | Instalação no sistema     | `make install-system` instala em `/opt/tts-app` com entrada GNOME e comando `tts-app` |
| F28 | CI/CD                     | GitHub Actions roda testes em cada push/PR                                            |

### Backlog

| #   | Funcionalidade                      | Prioridade |
| --- | ----------------------------------- | ---------- |
| B1  | Drag & drop de arquivos .txt        | Média      |
| B2  | Player com pausa e retrocesso       | Média      |
| B3  | Empacotamento `.deb` / AppImage     | Alta       |
| B4  | Suporte a múltiplos idiomas na UI   | Baixa      |
| B5  | Integração com clipboard automático | Baixa      |

---

## Arquitetura

```
tts-app/
├── main.py                    # Interface gráfica (Tkinter)
├── tts_utils.py               # Lógica TTS: API, CLI, split, retry, volume
├── requirements.txt           # edge-tts, pystray, Pillow, langdetect
├── Makefile                   # install, run, test, install-system, uninstall-system
├── install.sh                 # Instala em /opt/tts-app + entrada GNOME
├── uninstall.sh               # Remove instalação do sistema
├── tts-app.desktop            # Entrada para launcher GNOME
├── assets/
│   └── tts-app.svg            # Ícone do app
├── scripts/
│   └── check_deps.py          # Verificação de dependências
├── tests/
│   ├── test_tts_utils.py      # Testes unitários
│   └── test_integration.py   # Testes de integração
└── .github/workflows/
    └── ci.yml                 # CI automático
```

### Dependências

| Dependência         | Tipo          | Função                             |
| ------------------- | ------------- | ---------------------------------- |
| `edge-tts`          | Python (pip)  | Engine TTS — gera o áudio          |
| `ffmpeg` / `ffplay` | Sistema (apt) | Reprodução e concatenação de áudio |
| `tkinter`           | Python stdlib | Interface gráfica                  |
| `pystray`           | Python (pip)  | Tray icon no sistema               |
| `Pillow`            | Python (pip)  | Imagem do tray icon                |
| `langdetect`        | Python (pip)  | Detecção automática de idioma      |

### Fluxo principal (Falar)

```
Usuário digita texto
  → Clica "Falar" (ou Ctrl+Enter)
  → check_executables() [feito na inicialização]
  → split_text() — divide se >4500 chars
  → generate_audio / generate_audio_long
      → API edge_tts.Communicate com retry 529
      → fallback: CLI edge-tts
  → ffplay reproduz com volume configurado
  → notify-send ao concluir
  → Status e botão atualizados na UI
```

---

## Requisitos Não-Funcionais

| Requisito      | Critério                                                                       |
| -------------- | ------------------------------------------------------------------------------ |
| Plataforma     | Linux (Ubuntu/Debian e derivados, Pop!\_OS)                                    |
| Performance    | Áudio gerado em menos de 5s para textos curtos (<200 chars) com conexão padrão |
| Confiabilidade | Retry automático (529), fallback CLI, checagem de deps na inicialização        |
| Testabilidade  | 12+ testes unitários e de integração via pytest + CI GitHub Actions            |
| Instalação     | Funcional com `make install-system`                                            |
| Configuração   | Preferências persistidas em `~/.config/tts-app/`                               |

---

## Critérios de Aceite

- [x] Usuário ouve texto em menos de 5s após clicar "Falar" (<200 chars)
- [x] Usuário salva áudio em MP3 em qualquer pasta
- [x] App exibe erro claro se `edge-tts` ou `ffplay` não estiver instalado
- [x] Testes passam no CI (GitHub Actions)
- [x] Funciona em Ubuntu 22.04+ / Pop!\_OS com Python 3.10+
- [x] App aparece no launcher GNOME após `make install-system`
- [x] Texto longo é dividido e concatenado automaticamente
- [x] Preferências são restauradas ao reabrir o app

---

## Fora do Escopo

- Suporte a Windows ou macOS
- Síntese de voz offline (sem internet)
- Player com controles de pausa e retrocesso
- Integração com leitores de tela (AT-SPI)
