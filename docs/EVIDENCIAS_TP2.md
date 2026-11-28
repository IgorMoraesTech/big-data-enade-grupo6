# Matriz de evidências e pendências — TP2 ENADE

**Data da consolidação: 28/11/2026.** Base: `main` após PR #34 e PR #35 em revisão. Este documento é apoio ao relatório e à demonstração; não implica conclusão automática das issues.

## Resultados mensurados e rastreáveis

**Execução:** [Actions run #46103160249](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46103160249) — job `docker-e2e`; artifact `docker-integration-evidence`.

| Evidência | Resultado observado | Fonte | Restrição |
|---|---|---|---|
| Entrega Kafka ao Elasticsearch | `kafka_to_elasticsearch: true` | `scripts/smoke_e2e.py`, workflow E2E | Questão fictícia |
| Endpoint de pesquisa e ocultação de gabarito | `search: true`, `public_answer_hidden: true` | Smoke E2E | Dados de teste |
| Redis carrinho e exportações PDF/JSON | `redis_cart`, `pdf_export`, `json_export` = true | Smoke E2E; download JSON confirmado também em Codespaces | Sessão anônima |
| Autenticação LDAP | `LDAP OpenLDAP REAL: login + 401/403 + professor: OK` | `scripts/smoke_ldap.py` | LDAP sem TLS no laboratório |
| Indexação idempotente | Documentos antes=1; depois=1 | `scripts/smoke_recovery.py` | Reentrega da mesma questão fictícia |
| Recuperação após parada do indexer | Passou | `scripts/smoke_recovery.py` | Reinício de processo; não HA |
| DLQ e continuidade do consumidor | Passou | `scripts/smoke_recovery.py` | Payload inválido demonstrativo |
| Benchmark cache repetido | 30 sucessos; 29 hits; p50=1,512 ms; p95=2,699 ms; p99=11,452 ms; 377,009 req/s | `scripts/benchmark_search.py` | 30 consultas HTTP sequenciais no runner |
| Benchmark sem reutilização | 30 sucessos; 0 hits; p50=9,359 ms; p95=11,859 ms; p99=17,041 ms; 96,237 req/s | `scripts/benchmark_search.py --cache-bust` | Termo de pesquisa muda a cada requisição |

**Atenção metodológica:** `--cache-bust` altera a string pesquisada acrescentando `0..29`; os cenários não consultam dados idênticos, então as diferenças não são exclusivamente atribuíveis ao cache. `requests_per_second` é taxa de respostas HTTP, **não é docs/s de indexação**. Latências p99 estimadas com 30 amostras são instáveis.

## Estado por requisito ou entrega

| Bloco | Implementação | Validação exigida / status |
|---|---|---|
| Infraestrutura local Kafka/Elastic/Redis/FastAPI/LDAP | Implementada | CI Docker e teste Codespaces confirmados |
| Modelo JSON, produtor e consumidor Kafka | Implementados | E2E fictício, reinício e DLQ verificados |
| Mapeamento PT-BR e filtros/highlight | Implementados | Testes de lógica e integração com dado fictício |
| Cache e carrinho Redis, exportações | Implementados | CI e teste manual de uso |
| LDAP, perfis e rotas 403 | Implementados no backend de laboratório | CI 401/403/200; falta login visual e segurança de produção |
| Kerberos entre serviços | **Não implementado** | Não alegar conformidade |
| Inventário de acervo oficial | **PR #35 aberto** | 8 entradas, dois cursos/anos; revisão pendente |
| Questões reais em JSONL | **PR #35 aberto** | 2 exemplos manuais; ainda não integrados ao fluxo da main |
| Extração de PDF em escala | Heurística experimental | Colunas e mídia complexa não resolvidas |
| Avaliação de qualidade de 50 questões | **Pendente** | Necessário medir campos e erros |
| Kafka lag e vazão docs/s | **Pendente** | Não confundir com HTTP req/s |
| Relatório SBC e vídeo | Em produção | PDF de até 12 páginas e vídeo de até 5 minutos ainda não concluídos |

## Ações de fechamento

1. Álvaro: responder aos comentários no [PR #35](https://github.com/IgorMoraesTech/big-data-enade-grupo6/pull/35), corrigir contradições de `docs/INGESTION.md`; fornecer evidências e ampliar validação para 50 questões.
2. Após aprovação do PR #35: integrar amostra oficial à main, rodar `docker compose run --rm api python -m scripts.produce sample/real_questions.jsonl`, aguardar indexador e validar busca interdisciplinar. **Este comando só será válido após merge e atualização do Codespaces.**
3. Engenharia: obter `docs/s` e lag Kafka com prova reproduzível, ou registrar impossibilidade e justificar no relatório.
4. Segurança: registrar claramente Kerberos pendente; não tratar LDAP como substituto.
5. Coordenação: preencher autoria/divisão de tarefas e declaração de IA; converter rascunho em PDF SBC, revisar e gravar vídeo final.
