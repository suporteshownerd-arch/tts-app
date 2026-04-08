# PRD — TTS App

## Visão Geral

Aplicativo desktop para Linux que converte texto em fala (Text-to-Speech) usando a engine Microsoft Edge TTS. Interface gráfica simples e moderna, sem necessidade de conta ou API key.

---

## Problema

Usuários Linux que precisam ouvir textos (acessibilidade, revisão de conteúdo, estudo) não têm uma ferramenta TTS desktop simples, com vozes de qualidade e controle de velocidade, que funcione offline via CLI ou com GUI intuitiva.

---

## Objetivos

- Converter texto em fala com vozes neurais de alta qualidade
- Permitir salvar o áudio gerado como arquivo MP3
- Funcionar inteiramente no Linux sem dependência de conta ou serviço pago
- Ser fácil de instalar e rodar

---

## Usuários-Alvo

| Perfil                         | Necessidade                             |
| ------------------------------ | --------------------------------------- |
| Usuário com deficiência visual | Ouvir textos sem configuração complexa  |
| Estudante / leitor             | Ouvir conteúdo enquanto faz outra coisa |
| Criador de conteúdo            | Gerar áudio narrado rapidamente         |
| Desenvolvedor                  | Integrar TTS em scripts via `tts_utils` |

---

## Funcionalidades

### Existentes (v1.0)

| #   | Funcionalidade           | Descrição                                                      |
| --- | ------------------------ | -------------------------------------------------------------- |
| F1  | Entrada de texto         | Área de texto multilinha para colar ou digitar conteúdo        |
| F2  | Seleção de voz           | Dropdown com 5 vozes neurais (pt-BR, en-US, es-ES)             |
| F3  | Controle de velocidade   | Slider de -50% a +50%                                          |
| F4  | Reprodução direta        | Botão "Falar" gera e reproduz o áudio imediatamente            |
| F5  | Salvar MP3               | Exporta o áudio gerado para arquivo `.mp3`                     |
| F6  | Limpar texto             | Limpa a área de entrada                                        |
| F7  | Feedback de status       | Indicador visual do estado atual (gerando, reproduzindo, erro) |
| F8  | Checagem de dependências | Verifica `edge-tts` e `ffplay` antes de executar               |

### Planejadas (backlog)

| #   | Funcionalidade                                       | Prioridade |
| --- | ---------------------------------------------------- | ---------- |
| B1  | Mais vozes disponíveis (listar via API edge_tts)     | Alta       |
| B2  | Histórico de textos recentes                         | Média      |
| B3  | Suporte a arquivos de texto (.txt) via drag-and-drop | Média      |
| B4  | Botão de parar reprodução em andamento               | Alta       |
| B5  | Tema claro / escuro configurável                     | Baixa      |
| B6  | Empacotamento como `.deb` ou AppImage                | Alta       |

---

## Arquitetura

```
tts-app/
├── main.py              # Interface gráfica (Tkinter)
├── tts_utils.py         # Lógica de TTS: comandos, API, checagem
├── requirements.txt     # Dependências Python (edge-tts)
├── Makefile             # Atalhos: install, run, test, clean
├── scripts/
│   └── check_deps.py    # Verifica dependências do sistema
├── tests/
│   └── test_tts_utils.py # Testes unitários (pytest)
└── .github/workflows/
    └── ci.yml           # CI automático no GitHub Actions
```

### Dependências

| Dependência         | Tipo          | Função                     |
| ------------------- | ------------- | -------------------------- |
| `edge-tts`          | Python (pipx) | Engine TTS — gera o áudio  |
| `ffmpeg` / `ffplay` | Sistema (apt) | Reprodução do áudio gerado |
| `tkinter`           | Python stdlib | Interface gráfica          |

### Fluxo principal (Falar)

```
Usuário digita texto
  → Clica "Falar"
  → check_executables()
  → generate_audio(voz, velocidade, texto, /tmp/tts_saida.mp3)
      → API edge_tts.Communicate (preferencial)
      → fallback: CLI edge-tts
  → ffplay reproduz o arquivo
  → Status atualizado na UI
```

---

## Requisitos Não-Funcionais

| Requisito      | Critério                                                    |
| -------------- | ----------------------------------------------------------- |
| Plataforma     | Linux (Ubuntu/Debian e derivados)                           |
| Performance    | Áudio gerado em menos de 3s para textos curtos (<200 chars) |
| Confiabilidade | Fallback CLI quando API Python não disponível               |
| Testabilidade  | Cobertura de testes em `tts_utils.py` via pytest + CI       |
| Instalação     | Funcional com `make install && make run`                    |

---

## Critérios de Aceite (v1.0)

- [ ] Usuário consegue ouvir um texto em menos de 5 segundos após clicar "Falar"
- [ ] Usuário consegue salvar o áudio em MP3 em qualquer pasta
- [ ] App exibe mensagem de erro clara se `edge-tts` ou `ffplay` não estiver instalado
- [ ] Testes passam no CI (GitHub Actions)
- [ ] Funciona em Ubuntu 22.04+ com Python 3.10+

---

## Fora do Escopo (v1.0)

- Suporte a Windows ou macOS
- Síntese de voz offline (sem internet)
- Integração com clipboard automático
- Player com controles (pausar, retroceder)
