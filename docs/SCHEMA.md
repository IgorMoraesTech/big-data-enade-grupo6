# Contrato de dados (versão 1)

Todos os componentes devem adotar este contrato. Campos ausentes não devem ser
inventados para simular enriquecimento real.

## Evento Kafka / documento Elasticsearch

```json
{
  "id": "sha256-hex-64-caracteres",
  "year": 2023,
  "area": "Ciências Exatas",
  "course": "Sistemas de Informação",
  "section": "CE",
  "number": 1,
  "question_type": "objective",
  "statement": "Texto integral da questão",
  "context": null,
  "alternatives": {"A": "Alternativa A", "B": "Alternativa B"},
  "answer": null,
  "annulled": false,
  "competencies": [],
  "knowledge_objects": [],
  "source_pdf": "https://dominio.gov.br/prova.pdf",
  "source_pages": [2]
}
```

- `id`: hash SHA-256 de **source_pdf | year | course | section | number**;
  estável para reprocessamento.
- `section`: `FG` (formação geral) ou `CE` (componente específico).
- `question_type`: `objective` ou `discursive`.
- `answer` null = desconhecido. Questão anulada tem `annulled=true`.
- `competencies` e `knowledge_objects`: listas vazias quando não identificadas.
- `source_pages` usa numeração física do arquivo a partir de 1.
- Fórmulas podem aparecer como `$...$` no texto; renderização e extração
  avançada de mídia ainda não estão garantidas.

## HTTP API (versão 1)

- `GET /health`: processo ativo.
- `GET /ready`: conexões com Elastic e Redis, ou erro 503.
- `GET /api/questions?q=&year=&course=&area=&section=&question_type=&competency=&page=1&page_size=10`
  retorna `{total,page,page_size,items,cache_hit}`.
- `GET /api/stats/courses` agrega questões por curso.
- `GET /api/stats/competencies` agrega por competência e ano.
- `POST /api/questions/{id}/cart`, `GET /api/cart`, `DELETE /api/questions/{id}/cart`
  serão adicionados em outra etapa.
- `GET /docs`: documentação OpenAPI do FastAPI.

**Aviso:** enquanto não houver LDAP, não há perfis reais nem bloqueio de gabaritos.
Não publicar respostas restritas em API pública.
