# Matriz de evidências e pendências — TP2 ENADE

**Data da consolidação: 28/11/2026.** Base: `main` após PRs #43–47, incluindo inventário, busca com questões oficiais e ensaio de consumer lag Kafka. Este documento é apoio ao relatório e à demonstração; não implica conclusão automática das issues.

## Resultados mensurados e rastreáveis

**Execução:** [Actions run #46103160249](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46103160249) — job `docker-e2e`; artifact `docker-integration-evidence`.

| Evidência | Resultado observado | Fonte | Restrição |
|---|---|---|---|
| Entrega Kafka ao Elasticsearch | `kafka_to_elasticsearch: true` | `scripts/smoke_e2e.py`, workflow E2E | Questão fictícia |
| Busca interdisciplinar em duas questões ENADE 2023 | Busca por `ética` recuperou as duas questões de Enfermagem e Fisioterapia; filtros por curso e gabaritos ocultos verificados | [Actions #46114404693](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46114404693); `scripts/smoke_real_questions.py` | Apenas duas questões transcritas/manualizadas; não valida extração nem conjunto de 50 |
| Endpoint de pesquisa e ocultação de gabarito | `search: true`, `public_answer_hidden: true` | Smoke E2E | Dados de teste |
| Redis carrinho e exportações PDF/JSON | `redis_cart`, `pdf_export`, `json_export` = true | Smoke E2E; download JSON confirmado também em Codespaces | Sessão anônima |
| Autenticação LDAP | `LDAP OpenLDAP REAL: login + 401/403 + professor: OK` | `scripts/smoke_ldap.py` | LDAP sem TLS no laboratório |
| Indexação idempotente | Documentos antes=1; depois=1 | `scripts/smoke_recovery.py` | Reentrega da mesma questão fictícia |
| Recuperação após parada do indexer | Passou | `scripts/smoke_recovery.py` | Reinício de processo; não HA |
| DLQ e continuidade do consumidor | Passou | `scripts/smoke_recovery.py` | Payload inválido demonstrativo |
| Consumer lag Kafka com indexador parado | 0 → 80 mensagens pendentes → 0 depois do reinício | [Actions #46115937123](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46115937123); `scripts/benchmark_ingestion.py` | Lote de 80 mensagens sintéticas |
| Indexação observada na recuperação | 80/80 documentos indexados em 6,332 s; **12,634 docs/s** | [Actions #46115937123](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46115937123); artifact `docker-integration-evidence` | Inclui tempo de reinício do container, polling e verificação ES; não é capacidade máxima nem extração de PDF |
| Benchmark cache repetido | 30 sucessos; 29 hits; p50=1,512 ms; p95=2,699 ms; p99=11,452 ms; 377,009 req/s | `scripts/benchmark_search.py` | 30 consultas HTTP sequenciais no runner |
| Benchmark sem reutilização | 30 sucessos; 0 hits; p50=9,359 ms; p95=11,859 ms; p99=17,041 ms; 96,237 req/s | `scripts/benchmark_search.py --cache-bust` | Termo de pesquisa muda a cada requisição |

**Nota sobre ingestão:** o benchmark de 80 registros usa documentos **sintéticos**, tempo desde o reinício do consumidor até a drenagem total e visibilidade de todos os registros no Elasticsearch. A taxa 12,634 docs/s é derivada de 80 / 6,332 s, **não** é throughput máximo em regime permanente. É uma execução isolada no runner do CI; o lote não testa extração ou cobertura de provas oficiais.

**Atenção metodológica:** `--cache-bust` altera a string pesquisada acrescentando `0..29`; os cenários não consultam dados idênticos, então as diferenças não são exclusivamente atribuíveis ao cache. `requests_per_second` é taxa de respostas HTTP, **não é docs/s de indexação**. Latências p99 estimadas com 30 amostras são instáveis.

## Estado por requisito ou entrega

| Bloco | Implementação | Validação exigida / status |
|---|---|---|
| Infraestrutura local Kafka/Elastic/Redis/FastAPI/LDAP | Implementada | CI Docker e teste Codespaces confirmados |
| Modelo JSON, produtor e consumidor Kafka | Implementados | E2E fictício, reinício e DLQ verificados |
| Mapeamento PT-BR e filtros/highlight | Implementados | Testes de lógica e integração com dado fictício |
| Cache e carrinho Redis, exportações | Implementados | CI e teste manual de uso |
| LDAP, perfis e rotas 403 | Implementados no backend de laboratório | CI 401/403/200; interface de login também integrada; falta segurança de produção |
| Kerberos entre serviços | **Não implementado** | Não alegar conformidade |
| Inventário de acervo oficial | **Integrado no PR #43**, ajustado no PR #44 | 8 entradas, Enfermagem e Fisioterapia de 2023; 5 PDFs reportados no ambiente do colaborador, fora do Git |
| Questões reais em JSONL | **Integradas no PR #43** | 2 questões em `sample/real_questions.jsonl`; busca, filtros e ocultação de respostas confirmados pelo PR #45 no CI |
| Extração de PDF em escala | Heurística experimental | Colunas e mídia complexa não resolvidas |
| Avaliação de qualidade de 50 questões | **Pendente** | Necessário medir campos e erros |
| Kafka lag e vazão docs/s | **Medição inicial integrada no PR #47** | CI: 80 mensagens sintéticas, lag 80→0 e 12,634 docs/s na recuperação; falta medição com corpus oficial e repetições |
| Relatório SBC e vídeo | Em produção | PDF de até 12 páginas e vídeo de até 5 minutos ainda não concluídos |

## Ações de fechamento

1. Acervo: preservar a autoria do Álvaro no [PR #43](https://github.com/IgorMoraesTech/big-data-enade-grupo6/pull/43); URLs oficiais corrigidas no [PR #44](https://github.com/IgorMoraesTech/big-data-enade-grupo6/pull/44). Ampliar extração e avaliar 50 questões separadamente.
2. Busca real: o CI do [PR #45](https://github.com/IgorMoraesTech/big-data-enade-grupo6/pull/45) já demonstrou Kafka→Elasticsearch para duas questões. Para reproduzir localmente após `git pull origin main` e os serviços Docker iniciarem, executar `docker compose run --rm api python -m scripts.produce sample/real_questions.jsonl`, aguardar o indexador e pesquisar `ética` na interface.
3. Engenharia: ensaio inicial de lag e vazão sintética concluído no [PR #47](https://github.com/IgorMoraesTech/big-data-enade-grupo6/pull/47). Repetir com múltiplos tamanhos de lote e dados oficiais quando disponíveis, sem apresentar o resultado de laboratório como capacidade máxima.
4. Segurança: registrar claramente Kerberos pendente; não tratar LDAP como substituto.
5. Coordenação: preencher autoria/divisão de tarefas e declaração de IA; converter rascunho em PDF SBC, revisar e gravar vídeo final.
