# Roteiro de validação (somente resultados reais contam)

## Passo 1 — infraestrutura
```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 indexer
curl http://localhost:8000/ready
```
Se `ready` retornar 503, investigar logs e serviços.

## Passo 2 — índice e produtor
```bash
docker compose run --rm api python -m scripts.create_index
docker compose run --rm api python -m scripts.produce sample/example_question.json
docker compose logs --tail=50 indexer
curl "http://localhost:8000/api/questions?q=etica"
curl "http://localhost:8000/api/questions?q=etica"
```
Verificar `total`, `cache_hit` (false/true) e o índice no Elasticsearch.
O exemplo é **fictício** e apenas valida integração.

## Passo 3 — idempotência e falha
- Publicar o mesmo JSON duas vezes e verificar `_count` do índice.
- Interromper indexador, produzir novas mensagens, reiniciar e medir progresso.
- Publicar documento inválido (usando produtor separado) e verificar DLQ.
- Inspecionar offsets e lag de consumidor Kafka.
- Registrar comandos, timestamps, prints e saídas observadas.

## Passo 4 — acervo oficial
- Obter PDFs oficiais e construir manifesto.
- Rodar extrator em cada PDF com referência à URL oficial.
- Validar pelo menos 50 questões manualmente, incluindo metadados e gabaritos.
- Comparar cobertura com inventário completo, sem inferir 100% por amostra.
- Medir taxa de acerto, vazão docs/s e p50/p95/p99 de latências.

## Segurança (BLOQUEANTE para RF22–RF25)
- Configurar e testar LDAP e Kerberos de fato.
- Demonstrar 403 no backend com usuário estudante em rota restrita.
- O front atual não possui login; não alegar segurança plena.

**Este arquivo é roteiro, não relatório de resultados executados.**
