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

### Verificação automatizada disponível

O workflow `.github/workflows/docker-e2e.yml` executa, em runner descartável:

- Kafka + Elasticsearch + Redis + API + LDAP reais no Docker Compose
- Reenvio da mesma questão fictícia para verificar contagem inalterada (idempotência)
- Parada do indexador, envio de novo evento e recuperação após reinício
- Payload inválido enviado à DLQ e continuidade de consumo
- Benchmark de **30 buscas sequenciais** com cache e sem reutilizar a mesma chave
- Publicação de **duas questões ENADE 2023** e verificação da busca `ética` em Enfermagem e Fisioterapia
- Ensaio controlado com **80 registros sintéticos** para medir backlog de offsets Kafka e tempo de drenagem após reinício

O ensaio de ingestão interrompe o serviço `indexer`, publica 80 eventos com IDs únicos pelo Kafka, consulta o `consumer lag` por partição com `kafka-consumer-groups.sh --describe`, reinicia o serviço e aguarda lag zero **e** visibilidade de todos os registros no Elasticsearch. O tempo de drenagem **inclui partida do container, polling e atualização do índice**, portanto `docs/s` é taxa observada de recuperação com carga sintética, não capacidade máxima sustentável ou vazão de extração dos PDFs. Resultado: `evidence/kafka-ingestion-lag.json` (apenas após execução bem-sucedida).

Evidências JSON são anexadas à execução GitHub Actions como artefato
`docker-integration-evidence` quando o job termina com sucesso. **Esses números
são medições do ambiente efêmero do GitHub Actions e de uma questão fictícia,
não resultados de escala com acervo ENADE real.** Não confundir req/s HTTP
com docs/s de indexação Kafka e não extrapolar esses resultados para produção.

Para executar o mesmo fluxo localmente, depois de subir o Compose e executar
`python scripts/smoke_e2e.py`, use:

```bash
python scripts/smoke_ldap.py
python scripts/smoke_recovery.py
python scripts/benchmark_search.py --query tecnologia --requests 30 --output evidence/benchmark-search.json
python scripts/benchmark_search.py --query tecnologia --requests 30 --cache-bust --output evidence/benchmark-no-cache.json
python scripts/smoke_real_questions.py  # depois de publicar sample/real_questions.jsonl
python scripts/benchmark_ingestion.py --count 80 --output evidence/kafka-ingestion-lag.json
```

## Passo 4 — acervo oficial
- Obter PDFs oficiais e construir manifesto.
- Rodar extrator em cada PDF com referência à URL oficial.
- Validar pelo menos 50 questões manualmente, incluindo metadados e gabaritos.
- Comparar cobertura com inventário completo, sem inferir 100% por amostra.
- Medir taxa de acerto, vazão docs/s e p50/p95/p99 de latências.

## Segurança (BLOQUEANTE para RF22–RF25)
- Configurar e testar LDAP e Kerberos de fato.
- Demonstrar 403 no backend com usuário estudante em rota restrita.
- A interface possui login visual LDAP de laboratório; não alegar segurança plena, pois LDAP não usa TLS e Kerberos permanece não implementado.

**Este arquivo é roteiro, não relatório de resultados executados.**
