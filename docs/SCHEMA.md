# Contrato de dados (versão 1)

Todos os componentes devem adotar este contrato. Campos ausentes não devem ser inventados para simular enriquecimento real.

## Evento Kafka / documento Elasticsearch

O exemplo abaixo ilustra a estrutura e os metadados de uma questão da amostra. Os textos de enunciado e alternativas são ilustrativos, não uma transcrição integral da prova.

```json
{
  "id": "sha256-hex-64-caracteres",
  "year": 2023,
  "area": "Saúde",
  "course": "Fisioterapia",
  "section": "FG",
  "number": 4,
  "question_type": "objective",
  "statement": "Texto integral da questão",
  "context": null,
  "alternatives": {"A": "Alternativa A", "B": "Alternativa B"},
  "answer": "A",
  "annulled": false,
  "competencies": [],
  "knowledge_objects": [],
  "source_pdf": "https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_fisioterapia.pdf",
  "source_pages": [6]
}
```

- `id`: hash SHA-256 de **source_pdf | year | course | section | number**; estável para reprocessamento.
- `section`: `FG` (formação geral) ou `CE` (componente específico).
- `question_type`: `objective` ou `discursive`.
- `answer` null = desconhecido. Questão anulada tem `annulled=true`.
- `competencies` e `knowledge_objects`: listas vazias quando não identificadas.
- `source_pages` usa numeração física do arquivo a partir de 1.
- Fórmulas podem aparecer como `$...$` no texto; renderização e extração avançada de mídia ainda não estão garantidas.

## HTTP API (versão 1)

- `GET /health`: processo ativo.
- `GET /ready`: conexões com Elastic e Redis, ou erro 503.
- `GET /api/questions?q=&year=&course=&area=&section=&question_type=&competency=&page=1&page_size=10` retorna `{total,page,page_size,items,cache_hit}`.
- `GET /api/stats/courses` agrega questões por curso.
- `GET /api/stats/competencies` agrega por competência e ano.
- `POST /api/questions/{id}/cart`: adiciona à sessão anônima Redis, máximo de 30.
- `GET /api/cart`: lista da sessão; `DELETE /api/questions/{id}/cart`: remove.
- `GET /api/cart/export.json` e `GET /api/cart/export.pdf`: exportação pública **sem gabaritos**.
- Sessão: cookie HttpOnly aleatório, SameSite=Lax, expiração 24h; não é login LDAP.
- Mudanças de sessão não exigem autenticação real nesta versão de laboratório.
- Exportações completas com gabaritos/professor exigem LDAP e autorização no backend.
- `GET /docs`: documentação OpenAPI do FastAPI.

**Aviso:** enquanto não houver LDAP, não há perfis reais nem bloqueio de gabaritos. Não publicar respostas restritas em API pública.
