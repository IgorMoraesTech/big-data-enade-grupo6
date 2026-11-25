# Big Data — Buscador de Questões ENADE (Grupo 6)

Projeto acadêmico de processamento e pesquisa de questões do ENADE. **Em desenvolvimento.**

## Arquitetura e tecnologias

PDFs → Python (extração) → Kafka → Elasticsearch → FastAPI + Redis → Web.

O TP2 também exige LDAP e Kerberos: **ainda não implementados nesta base**.
O Compose existente é um *laboratório local inseguro*, não adequado à produção.

- [Arquitetura, decisões e limitações](docs/ARCHITECTURE.md)
- [Contrato de dados e API](docs/SCHEMA.md)
- [Colaboração em equipe](docs/TEAM.md)
- [Issues e tarefas](https://github.com/IgorMoraesTech/big-data-enade-grupo6/issues)

## Requisitos locais

- Docker Engine/Compose v2 com memória disponível para Kafka e Elasticsearch.
- Python 3.12+ para rodar scripts e testes no host (opcional).
- PDFs reais obtidos de fontes oficiais do INEP para avaliação do requisito RF01.

## Iniciar

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

No Windows PowerShell: `Copy-Item .env.example .env`.

A interface estará em `http://localhost:8000`; Swagger em `http://localhost:8000/docs`.
Para ver logs: `docker compose logs -f indexer`.

## Demonstração inicial

```bash
# Publicar um JSON de exemplo indicado como dado fictício
docker compose run --rm api python -m scripts.produce sample/example_question.json
# Consultar busca
curl "http://localhost:8000/api/questions?q=etica"
```

O exemplo fictício demonstra integração, **não comprova** extração do acervo.
Para extração real consultar `scripts/extract_pdf.py` e validar os resultados
antes de enviá-los ao Kafka.

## Testes locais

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

**Status dos requisitos:** verificar issues e `docs/ARCHITECTURE.md`.
Não relatar como concluídas autenticação, cobertura integral do acervo,
extração multimodal ou desempenho sem evidência de execução e medições.
