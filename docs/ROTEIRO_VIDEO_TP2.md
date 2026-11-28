# Roteiro preliminar de vídeo TP2 — até 5 minutos

**Não gravado.** Use este roteiro somente depois de integrar pelo menos duas questões reais do ENADE; adapte se algum passo não funcionar. Os resultados mostrados devem ser da execução real, não imagens simuladas. Deixe o Codespaces com porta 8000 **Private**; não publicar a porta 9200 do Elasticsearch.

| Intervalo alvo | Tela e demonstração | Fala sugerida |
|---|---|---|
| 0:00–0:35 | GitHub, README, arquitetura (docs/ARCHITECTURE.md) e Compose | “Criamos um pipeline de questões do ENADE que recebe dados estruturados no Kafka, indexa no Elasticsearch e oferece busca pela interface web. O Redis faz cache e guarda a seleção de questões.” |
| 0:35–1:20 | Terminal: `docker compose ps`; produtor `docker compose run --rm api python -m scripts.produce sample/real_questions.jsonl` após merge; `docker compose logs --tail=30 indexer` | “As questões passam por validação do esquema, são publicadas no Kafka e o consumidor registra cada uma no Elasticsearch.” |
| 1:20–2:20 | Site na porta 8000. Pesquisar termo presente nas duas amostras oficiais; mostrar curso, ano, PDF e páginas; aplicar filtros | “As questões estão associadas à prova e página de origem. É possível pesquisar e filtrar por curso e ano.” |
| 2:20–3:00 | Repetir busca idêntica e mostrar indicação de cache Redis; selecionar questão e exportar PDF/JSON | “A busca repetida pode ser respondida pelo cache. A seleção por sessão é mantida no Redis e exportada nos dois formatos.” |
| 3:00–3:55 | Página `/docs`. Autenticar estudante com `POST /api/auth/login`; consultar `GET /api/professor/stats/courses` → 403. Autenticar professor → 200 | “O login é realizado por OpenLDAP no backend. Um estudante autenticado recebe HTTP 403 ao tentar acessar recurso reservado ao professor.” |
| 3:55–4:35 | GitHub Actions: execução Docker E2E, testes de DLQ/reinício e p50/p95/p99 | “Executamos testes automatizados de recuperação e medimos a latência HTTP em um ambiente temporário. Esses valores vêm de uma questão fictícia, não de um acervo em escala.” |
| 4:35–5:00 | README/relatório: limitações | “A extração automatizada dos PDFs ainda é limitada, o corpus oficial está em expansão e Kerberos não foi implementado. O projeto é um protótipo acadêmico.” |

**Antes de gravar:** ensaiar sem ultrapassar 5 minutos; confirmar link acessível, áudio, resolução e credenciais somente demonstrativas. **Não inventar resultados e não mostrar uma busca interdisciplinar que não retorne questões reais de dois cursos.** Se a integração real falhar, apresentar a limitação e a evidência do pipeline fictício com transparência.

**Requisito operacional:** depois que o Álvaro atualizar o PR #35 e ele for integrado, é necessário `git pull origin main` no Codespaces e `docker compose up --build -d` antes de indexar os dados reais.
