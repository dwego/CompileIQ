# ⚡ CompileIQ

**Do log à solução, inovando em compilação.**

> Este projeto open source foi criado para ajudar desenvolvedores e equipes de engenharia a identificar gargalos de performance com base em **tracelogs**, **análise estática** e um **XML detalhado** com as etapas de execução do seu código.

---

## 📌 Problema

Imagine o cenário:  
Um **banco digital** precisa processar **1 milhão de requisições por minuto**. Porém, uma das **tasks internas** roda com **500ms de execução** — isso gera um **grande gargalo** no tráfego de dados e pode derrubar toda a aplicação.

Hoje, identificar esses gargalos exige:

- Ler logs complexos manualmente.
- Rastrear etapas de execução.
- Entender o comportamento do algoritmo.
- Ajustar otimizações **no escuro**.

Isso consome tempo, aumenta custos e impacta diretamente o negócio.

---

## 🚀 Nossa Solução

O **CompileIQ** nasceu para **automatizar a análise de performance** e **sugerir otimizações** de forma inteligente.  
Através de uma combinação de:

- **Tracelogs completos** da execução.
- **Análise estática** detalhada do código.
- **XML com etapas de execução** e métricas.

A **IA** consegue:

1. Entender **como** seu código foi executado.
2. Identificar **onde** estão os gargalos de performance.
3. Otimizar automaticamente as tasks quando possível.
4. **Recomendar ajustes** quando a otimização não atinge o tempo solicitado.

---

## 👤 Perfil do Usuário

O projeto foi desenhado para:

- Desenvolvedores que precisam **garantir performance crítica**.
- Times que trabalham com **aplicações de alta disponibilidade**.
- Empresas que lidam com **grandes volumes de tráfego**.
- Projetos com **SLA rigoroso** onde cada milissegundo importa.

Exemplos de uso:

- Bancos processando **milhões de requisições** por minuto.
- Plataformas SaaS com **tasks de alta concorrência**.
- Sistemas IoT que precisam de **respostas quase em tempo real**.

---

## 🧠 Como Funciona

O sistema recebe:

- **Tracelogs** do algoritmo.
- Um **XML detalhado** com todas as etapas da execução.
- Os **limites de tempo** definidos pelo usuário.

Em seguida:

1. A IA **analisa os dados** e entende o comportamento do código.
2. Identifica **pontos críticos** com base no consumo de tempo e recursos.
3. Caso seja possível, **otimiza** automaticamente os gargalos.
4. Se a otimização não for suficiente, gera **recomendações práticas**.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.12+**
- **FastAPI** – Interface para upload e processamento de arquivos.
- **LLMs Otimizados** – Modelos de IA para análise de performance.
- **XML Parsing** – Para leitura detalhada do fluxo de execução.
- **Logging Avançado** – Geração de logs claros e rastreáveis.

---

## 📂 Estrutura do Projeto

```bash
.
├── app/
│   ├── client.py          # Cliente principal para rodar a análise
│   ├── core/              # Núcleo da lógica da aplicação
│   ├── utils/             # Funções auxiliares e helpers
│   └── models/            # Modelos e interfaces para IA
├── data/
│   ├── traces/            # Tracelogs originais
│   ├── xml/               # XMLs de execução
│   └── logs/              # Logs gerados pelo sistema
├── README.md
└── requirements.txt
```

---

## ⚙️ Instalação

Clone o repositório:

```bash
git clone https://github.com/seu-usuario/compileiq.git
cd compileiq
```

Crie e ative um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate    # Linux / MacOS
.venv\Scripts\activate      # Windows
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## ▶️ Como Usar

O cliente principal do sistema está localizado em `app/client.py`.  
Ele será responsável por processar o XML, analisar os tracelogs e gerar recomendações.

```bash
python app/client.py --xml caminho/do/arquivo.xml --trace caminho/do/tracelog.log --timeout 200
```

Exemplo:

```bash
python app/client.py --xml data/xml/output.xml --trace data/traces/app.log --timeout 300
```

---

## 📊 Saídas Geradas

Após a execução, o sistema gera:

- **Logs detalhados** → `data/logs/optimization.log`
- **Sugestões de otimização** → `data/logs/recommendations.log`
- **Resumo da execução** → Exibido no terminal

---

## 🧩 Exemplo de Uso Real

```bash
python app/client.py --xml ./data/xml/execucao.xml --trace ./data/traces/prod.log --timeout 150
```

**Saída esperada:**

```
[INFO] Iniciando análise...
[INFO] Executando IA de otimização...
[OK] 4 tasks foram otimizadas com sucesso.
[WARN] 2 tasks não atingiram o limite de 150ms.
[INFO] Recomendações foram salvas em: data/logs/recommendations.log
```

---

## 🧑‍💻 Contribuindo

Este projeto é **open source**!  
Sinta-se livre para abrir **issues** e enviar **pull requests**.

1. Faça um **fork** do projeto.
2. Crie uma nova branch: `git checkout -b feature/sua-feature`
3. Commit suas mudanças: `git commit -m 'feat: adiciona nova feature'`
4. Envie para o repositório: `git push origin feature/sua-feature`
5. Abra um **Pull Request** 🎉

---

## 📜 Licença

Este projeto está sob a licença **MIT**.  
Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
