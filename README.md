![Python](https://img.shields.io/badge/-Python-05122A?style=flat&logo=python)
![Pandas](https://img.shields.io/badge/-Pandas-05122A?style=flat&logo=pandas)
![Plotly](https://img.shields.io/badge/-Plotly-05122A?style=flat&logo=plotly)
![Dash](https://img.shields.io/badge/-Dash-05122A?style=flat&logo=plotly)
![Flask](https://img.shields.io/badge/-Flask-05122A?style=flat&logo=flask)
![Redis](https://img.shields.io/badge/-Redis-05122A?style=flat&logo=redis)
![SQLite](https://img.shields.io/badge/-SQLite-05122A?style=flat&logo=sqlite)

# Synapsi
Hub de projetos analíticos: SegurAI/FinDash

**Synapsi** é um portfólio de projetos analíticos com foco em soluções aplicáveis a negócios. A plataforma reúne demonstrações interativas de modelos e dashboards desenvolvidos em Python, com foco em análise de dados, visualização e suporte à tomada de decisão.

### Projetos

### 📊 FinDash
MVP de análise de portfólio de ações. Principais recursos:
- Comparação de performance com benchmarks
- Análise de correlação entre ativos
- Visualização de distribuição setorial
- Métricas de retorno e risco

### 🛡️ SegurAI
Painel de análise de risco para seguradoras e clientes:
- Score de risco com base em dados individuais, demográficos e geográficos
- Apoio à precificação e gestão de risco

## Tecnologias Utilizadas
- Python (Dash, Flask, Pandas, Plotly)
- SQLite (persistência de dados local)
- Redis (cache de dados temporários)
- Flask/HTML/JS (integração com Dash)
- Estrutura modular para expansão futura

## Observação sobre Submódulos

Este repositório utiliza um **submódulo Git** para isolar a lógica de negócios (camada de serviços) que é mantida em um repositório privado.

Se você clonar este repositório e quiser executá-lo localmente, será necessário também ter acesso ao repositório do submódulo. Após o clone, inicialize os submódulos com:

```bash
git submodule update --init --recursive
