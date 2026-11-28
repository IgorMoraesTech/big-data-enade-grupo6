# Relatório técnico TP2 — Buscador de questões ENADE (RASCUNHO)

**Grupo 6 · texto-base para diagramação no modelo SBC · 28/11/2026**

> **Status: rascunho, não é o PDF final.** É necessário revisar texto, referências, autoria e rubrica, diagramar no template SBC, checar limite máximo de 12 páginas e exportar PDF. Distinguir resultados de laboratório e resultados do corpus ENADE. Substituir os campos `[PENDENTE]` apenas após coletar a respectiva evidência. Não apresentar uma funcionalidade de laboratório como solução segura de produção.

## Título provisório

**Pipeline de ingestão e busca de questões do ENADE com Kafka, Elasticsearch, Redis e autenticação LDAP: construção e avaliação de um protótipo**

**Autores:** [PENDENTE — nomes completos e vínculos acadêmicos conforme grupo e modelo SBC].

### Resumo

Este trabalho apresenta um protótipo de plataforma de ingestão, indexação e pesquisa de questões do Exame Nacional de Desempenho dos Estudantes (ENADE). A arquitetura integra extração e normalização em Python, publicação de registros estruturados no Apache Kafka, indexação e consultas textuais no Elasticsearch, interface web e API FastAPI, além do Redis para cache e armazenamento de listas de questões por sessão. Um servidor OpenLDAP de laboratório permite autenticar usuários de demonstração com perfis de estudante e professor; rotas restritas retornam HTTP 403 quando acessadas por estudantes autenticados. A validação automatizada confirmou o envio Kafka→Elasticsearch, a exportação PDF/JSON, a idempotência por identificador estável, a retomada após reinício do consumidor e o uso de dead-letter queue (DLQ). Em 30 consultas sequenciais por cenário em um executor temporário do GitHub Actions, a mediana da latência HTTP foi de 1,512 ms com reaproveitamento do cache e 9,359 ms sem reaproveitamento de chaves. Essas métricas de latência foram obtidas com uma **questão fictícia de teste** e não representam desempenho em escala com acervo oficial. Separadamente, um teste de integração com duas questões oficiais transcritas de Enfermagem e Fisioterapia de 2023 comprovou busca textual interdisciplinar no laboratório, sem validar extração automática em larga escala. A avaliação manual de 50 questões, métricas de ingestão e o uso de Kerberos permanecem incompletos. O protótipo evidencia o funcionamento do fluxo integrado e explicita suas limitações de escala e segurança.

**Palavras-chave:** ENADE; Big Data; Apache Kafka; Elasticsearch; Redis; LDAP.

### Abstract

This paper presents a prototype for ingesting, indexing and searching Brazil's ENADE examination questions. The pipeline combines Python-based data normalization, Apache Kafka event publishing, Elasticsearch indexing and full-text retrieval, a FastAPI-based web interface, and Redis for query caching and session-scoped question collections. An experimental OpenLDAP deployment supports student/teacher authentication and HTTP 403 access-control tests. Automated integration tests verified Kafka-to-Elasticsearch delivery, PDF/JSON exports, idempotent indexing, consumer recovery after restart and dead-letter queue routing. In a temporary GitHub Actions environment, 30 sequential HTTP search requests per scenario yielded median response times of 1.512 ms with cache-key reuse and 9.359 ms without it. The latency measurements used a **synthetic question** and cannot establish performance at scale on an official ENADE corpus. Separately, an integration test using two manually transcribed official ENADE questions from Nursing and Physiotherapy (2023) verified cross-course text search in the laboratory. Broader PDF extraction, manual validation of 50 questions, ingestion-throughput measurements and Kerberos authentication remain pending. The study therefore reports verified integration capabilities and their technical limitations rather than claiming complete compliance.

**Keywords:** ENADE; Big Data; Apache Kafka; Elasticsearch; Redis; LDAP.

## 1. Introdução

As provas do ENADE são documentos relevantes para o estudo do desempenho e de conteúdos cobrados em diferentes cursos superiores. Entretanto, suas questões são disponibilizadas originalmente em documentos PDF, cuja diagramação, figuras, tabelas, alternativas e gabaritos variam conforme a edição. Pesquisar assuntos compartilhados por áreas diferentes exige transformar documentos heterogêneos em registros estruturados, preservando as fontes e páginas de origem.

O objetivo do projeto é construir e avaliar um pipeline que receba registros de questões, disponibilize busca textual com filtros e mantenha respostas de acesso rápido por cache. A avaliação considera tanto os mecanismos de recuperação e tratamento de falhas quanto a experiência de consulta em uma interface web. A proposta é um **protótipo acadêmico reproduzível**, não uma solução de produção ou um acervo completo.

Contribuições efetivamente verificadas até 28/11/2026: integração por Docker Compose; produtor e consumidor Kafka em Python; índice Elasticsearch com analisador de português brasileiro; API e interface com busca, paginação, marcação de termos e exportações; Redis para cache e carrinho; login LDAP e proteção de rotas de professor; testes automatizados de integração, falhas e latência. Duas questões oficiais transcritas e revisadas foram integradas no PR #43 e testadas em um ensaio E2E próprio no PR #45, separadamente dos benchmarks com dados fictícios.

## 2. Arquitetura e topologia

O caminho lógico dos dados é **PDF oficial → extração Python → JSON canônico → produtor Kafka → tópico `enade-questions` → consumidor Python → índice `enade-questions-v1` no Elasticsearch → API FastAPI → interface web**. As respostas de busca são armazenadas em Redis por chave derivada de consulta/filtros; a seleção de questões também é guardada em Redis, com sessão identificada por cookie. O controle de acesso a rotas administrativas usa OpenLDAP e sessões no Redis.

No Docker Compose de laboratório: um broker Kafka (modo KRaft), uma instância Elasticsearch, uma instância Redis, OpenLDAP, inicializador de índice, API e indexador. O Elasticsearch é configurado com **um shard primário e zero réplicas**; o Kafka usa fatores de replicação 1. A topologia minimiza consumo de recursos e simplifica reprodução, mas **não oferece alta disponibilidade**. Existem volumes persistentes para Kafka, Elasticsearch e Redis. A API é publicada no endereço loopback da máquina de desenvolvimento.

**Limitação de segurança:** Kafka usa PLAINTEXT, Elasticsearch está sem autenticação e o LDAP demonstrativo usa tráfego não cifrado na rede interna. O projeto não deve ser publicado em rede pública nessas condições. Kerberos SASL/GSSAPI e autenticação mútua entre serviços **não estão implementados**.

**Figura 1 — [PENDENTE]:** inserir diagrama derivado de `docs/ARCHITECTURE.md`, distinguindo componentes reais, componentes planejados e limites de rede.

## 3. Coleta e engenharia de dados

O contrato definido em `app/schema.py` e `docs/SCHEMA.md` inclui: ID determinístico, ano, área, curso, seção (FG/CE), número, tipo (objetiva/discursiva), enunciado, contexto, alternativas, gabarito opcional, indicador de anulação, competências, objetos de conhecimento, URL do PDF e páginas de origem. O identificador é um SHA-256 dos campos de identificação da questão e de sua origem; isso permite reprocessar o mesmo documento mantendo a identidade do registro. Valores não verificados, como competências inferidas, não devem ser preenchidos artificialmente.

O extrator inicial (`scripts/extract_pdf.py`) usa PyMuPDF para obter texto de páginas, expressão regular para localizar números das questões e heurísticas para alternativas. **Limitação observada:** diagramações em colunas e questões lado a lado podem produzir segmentação errada; não estão resolvidos OCR, tabelas, fórmulas nem diagramas complexos. Portanto, o extrator não demonstra cobertura integral e todo registro derivado dele requer revisão manual.

**Acervo oficial integrado (PR #43):** o inventário inicial registra oito documentos (provas, gabaritos, padrões de resposta e diretrizes) de **Enfermagem e Fisioterapia, edição 2023**. O colaborador documentou cinco PDFs obtidos e verificados localmente, sem incluí-los no Git, e duas questões estruturadas (uma por curso), incluindo páginas e gabaritos. O PR #44 corrigiu três URLs de download e o formato da diretriz de Fisioterapia. As verificações locais dos PDFs não são reproduzidas pela CI. O inventário não constitui o acervo histórico completo nem comprova extração automática integral.

**Avaliação de qualidade da extração:** [PENDENTE — amostra ≥50 questões, tabela campo a campo com referência PDF/página, contagem de acertos, taxa e categorias de erros]. Não atribuir uma taxa de acerto sem comparar as amostras com a fonte original.

## 4. Mensageria e indexação

O produtor `scripts/produce.py` lê arquivos JSON ou JSONL linha a linha, valida cada item pelo modelo Pydantic e publica com chave determinística no tópico `enade-questions`. Utiliza `acks=all` e espera as confirmações de entrega. O consumidor (`app/consumer.py`) lê mensagens por grupo, valida o contrato, indexa documentos com `_id` persistente e confirma offsets de forma síncrona **após** a indexação. Dados malformados são encaminhados ao tópico `enade-questions-dlq`; a confirmação do offset depende do envio durável à DLQ. Uma falha transitória não tratada do Elasticsearch interrompe o consumidor para que, após reinício, a mensagem possa ser reentregue.

A garantia implementada é **at-least-once** dentro das condições do laboratório, não exactly-once entre Kafka e Elasticsearch. A indexação por ID estável torna o reprocessamento idempotente quanto ao número de documentos. Os testes automatizados confirmaram que reenviar o exemplo fictício manteve a contagem de documentos inalterada (1 antes, 1 depois), que uma mensagem publicada durante a parada do consumidor foi recuperada após seu reinício e que uma mensagem inválida foi recebida pela DLQ sem impedir o processamento subsequente.

## 5. Elasticsearch e busca textual

O índice é criado por `scripts/create_index.py`, com campos estruturados `keyword` para filtros e campos `text` para enunciado e contexto. O analisador `enade_pt` combina normalização em minúsculas, asciifolding, remoção de stopwords brasileiras, stemming para português e um pequeno conjunto inicial de sinônimos. A consulta `multi_match` prioriza enunciado sobre contexto, aplica filtros combináveis e pagina resultados. Trechos encontrados recebem marcação `<mark>`. A API pública não retorna o gabarito.

A rota `GET /api/questions` suporta texto livre, ano, curso, área, seção, tipo, competência, página e tamanho da página. A interface oferece formulários para os filtros, navegação entre páginas, cartões de resultado, destaques e links para o documento de origem quando há URL oficial. Os endpoints `/health`, `/ready` e `/docs` auxiliam operação e consulta OpenAPI. Existem agregações por curso e por competência/ano.

**Busca interdisciplinar com questões oficiais:** no [GitHub Actions #46114404693](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46114404693), o CI publicou pelo Kafka duas questões transcritas das provas do ENADE 2023 (Enfermagem e Fisioterapia), confirmou sua recuperação no Elasticsearch por busca textual `ética`, verificou filtros por curso e a ausência do campo `answer` na API pública. Evidência: `scripts/smoke_real_questions.py` e PR #45. **Limite:** o experimento valida a integração e a recuperação dessas duas amostras, não a fidelidade de extração automática ou uma avaliação estatística de 50 questões.

## 6. Cache e seleção de questões com Redis

O Redis armazena respostas de consultas por chave derivada do corpo de busca (incluindo filtros e paginação) e versão do índice. O TTL padrão é de **60 segundos**; uma indexação bem-sucedida incrementa a versão global para que novas pesquisas não reutilizem entradas antigas. A disponibilidade do Redis não é condição para executar buscas diretamente no Elasticsearch: em caso de indisponibilidade do cache, a API procura responder pelo mecanismo de busca.

A lista selecionada utiliza uma sessão anônima distinta por cookie HttpOnly, expira após **24 horas**, permite adicionar/remover até 30 questões e exportar os itens para JSON e PDF sem revelar gabaritos. O download de JSON foi corrigido no PR #34 com cabeçalho HTTP de anexo, e o funcionamento foi verificado manualmente no Codespaces e no teste de integração.

## 7. Autenticação e autorização

O backend implementa autenticação contra OpenLDAP de laboratório. Os perfis demonstrativos estudante e professor são identificados por atributo LDAP `employeeType`, e não por uma política completa de grupos corporativos. Depois do login, a API cria sessão Redis, associada a cookie HttpOnly de até uma hora. O usuário não autenticado recebe HTTP **401** em recursos exclusivos; estudante autenticado recebe **403**; professor autenticado consegue acessar dados reservados, como gabaritos, conforme sua rota autorizada.

O workflow de integração `scripts/smoke_ldap.py` comprovou essas respostas contra contêineres reais. **Limites:** a tela visual de login existe no frontend, mas o LDAP demonstrativo não usa TLS; não foi implementado Kerberos nem endurecimento suficiente para produção. A interface pública não expõe gabaritos nem utiliza a sessão LDAP para o carrinho.

## 8. Avaliação experimental

### 8.1 Ambiente e método

Uma execução reproduzível do GitHub Actions em **28/11/2026** iniciou os serviços Docker em um executor temporário, indexou uma **questão fictícia** e rodou integração HTTP, Kafka, Elasticsearch, Redis, LDAP, recuperação do consumidor e benchmarks. O código de teste está em `.github/workflows/docker-e2e.yml`, `scripts/smoke_e2e.py`, `scripts/smoke_ldap.py`, `scripts/smoke_recovery.py` e `scripts/benchmark_search.py`.

Os benchmarks efetuaram **30 requisições sequenciais por cenário** com um único processo cliente e consulta inicial `tecnologia`. No cenário de cache reutilizado, repetiu-se a mesma expressão; no cenário “sem reaproveitamento”, modificou-se o termo da consulta em cada requisição (`tecnologia 0`, `tecnologia 1`, etc.), impedindo o reuso da mesma chave. **Isso também muda a consulta de busca**, portanto a comparação não isola rigorosamente apenas o efeito do cache: os resultados são indicativos, não uma medida causal controlada de aceleração.

### 8.2 Latências HTTP observadas

| Indicador | Consulta repetida, cache reutilizado | Termos distintos, sem reutilização |
|---|---:|---:|
| Requisições com sucesso / total | 30/30 | 30/30 |
| Acertos do cache Redis | 29/30 (96,67%) | 0/30 (0%) |
| Média (ms) | 2,050 | 9,807 |
| p50 (ms) | 1,512 | 9,359 |
| p95 (ms) | 2,699 | 11,859 |
| p99 (ms) | 11,452 | 17,041 |
| Vazão HTTP observada (req/s, sequencial) | 377,009 | 96,237 |

Fonte: logs da execução [GitHub Actions #46103160249](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46103160249), job `docker-e2e`, etapa “Medir latência HTTP p50 p95 p99 e cache real”; artefato `docker-integration-evidence`. Valores são medições de latência vistas pelo cliente, inclusive overhead do ambiente de execução. **req/s HTTP não é docs/s de ingestão.** O tamanho da amostra é pequeno e os percentis altos são sensíveis a variações, especialmente p99.

### 8.3 Recuperação, integridade e controle de acesso

Os testes automatizados verificaram: (i) idempotência, contagem 1→1 após reenvio; (ii) interrupção e retomada do consumidor, com registro pendente indexado ao voltar; (iii) DLQ para payload malformado; (iv) consumo posterior à mensagem inválida; (v) autenticação LDAP e respostas 401/403/200 conforme perfil; (vi) exportações JSON e PDF e ocultação de gabarito na API pública. São testes funcionais do protótipo, **não** provas de recuperação perante falha do host, perda do volume ou alta disponibilidade.

### 8.4 Busca com duas questões oficiais

O ensaio independente [GitHub Actions #46114404693](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46114404693), implementado no PR #45, confirmou a publicação de duas questões reais manualmente estruturadas pelo produtor Kafka, sua indexação e a recuperação por busca `ética` em dois cursos diferentes. Os filtros por curso foram testados e o campo de gabarito não foi exposto na resposta pública. Os PDFs oficiais não foram reprocessados automaticamente durante esse ensaio; portanto, o teste **não mede a qualidade da extração** nem a cobertura do acervo.

### 8.5 Métricas ainda não coletadas

- **docs/s do pipeline de ingestão** com carga de dados oficiais: [PENDENTE].
- **consumer lag** medido em Kafka sob carga e recuperação: [PENDENTE].
- **Medição de precisão da extração** com pelo menos 50 questões conferidas: [PENDENTE].
- **Carga com corpus oficial mais amplo, gráficos e repetição de experimentos:** [PENDENTE].

Não substituir essas medições por estimativas ou valores de benchmarks HTTP.

## 9. Gargalos, decisões e lições aprendidas

A transformação de PDF para questões é o principal risco de qualidade: ordem de leitura, colunas, elementos visuais e gabaritos dificultam identificação automática consistente. Uma abordagem de extração heurística com revisão manual é viável para um recorte demonstrativo, mas não garante escalabilidade de acervo. Outro limite é a topologia de nó único; Kafka e Elasticsearch não conseguem manter serviço diante de perda completa da instância ou do volume local. O cache reduz consultas repetitivas, mas exige invalidação e não resolve problemas de extração. O LDAP de laboratório demonstra autorização da API, porém não substitui autenticação forte entre serviços.

A disciplina de testes foi importante para distinguir componentes “iniciados” de um pipeline efetivamente funcional: o CI realizou publicações Kafka e verificou a recuperação de registros no Elasticsearch, além de HTTP 403 e exportações. Para um sistema de maior porte seriam necessários datasets oficiais maiores, controle experimental da comparação de cache, observabilidade de lag, tolerância a falhas por replicação e segurança por TLS/Kerberos.

## 10. Conclusão e trabalhos futuros

Foi implementado e verificado um protótipo de busca de questões com integração de mensageria, indexação, cache, sessão, API e autorização. A avaliação funcional comprova o fluxo Kafka→Elasticsearch, o tratamento de mensagens inválidas, a recuperação após reinício do consumidor e as rotas restritas por perfil LDAP. Os benchmarks revelam menores latências nas consultas repetidas que reutilizam o cache, nas condições pontuais medidas.

As limitações são significativas: **acervo oficial ainda incompleto, extração insuficientemente validada, métricas de ingestão/lag ausentes, não implementação de Kerberos e segurança de laboratório**. A continuidade inclui ampliação do acervo além das duas questões oficiais já indexadas e recuperadas no teste, revisão de 50 amostras, experimentos de ingestão, estabilização da extração e avaliação de autenticação forte entre serviços.

## 11. Divisão do trabalho e uso de IA

**Preencher e validar com os integrantes antes de submeter.** As evidências GitHub indicam que o usuário `IgorMoraesTech` integrou a maior parte da infraestrutura, backend, testes e interface com auxílio substancial do assistente de IA; `alvin-silvaM` entregou o inventário e duas questões oficiais no PR #43 (precedido pelo PR #35, revertido); `IgorMoraesTech` integrou as correções de links no PR #44 e o teste E2E no PR #45. **Não inferir automaticamente o trabalho de todos os cinco integrantes apenas por autoria dos commits.** Registrar os nomes completos, tarefas reais, validações, roteiro, redação e revisão feitos por cada pessoa.

**Declaração provisória de IA generativa:** “Ferramenta de IA generativa (ChatGPT, OpenAI) foi utilizada para auxiliar na arquitetura, elaboração/revisão de código, testes, organização das issues e redação inicial do relatório. Os integrantes são responsáveis pela revisão do material, execução das validações e correção de erros. Os resultados numéricos relatados provêm de logs reais dos testes, não foram gerados como simulação pela IA.” Complementar identificação da ferramenta/modelo quando exigida pelo enunciado, tarefas e custo estimado quando aplicável.

## Referências e fontes técnicas a verificar na versão final

1. **INEP** — portal oficial de provas e gabaritos do ENADE (links e anos no manifesto integrado no PR #43 e corrigido no PR #44; citar URLs oficiais consultadas na versão final).
2. **Apache Software Foundation** — documentação oficial do Apache Kafka, versão usada no laboratório 3.9.1.
3. **Elastic** — documentação do Elasticsearch 8.17, incluindo indexação e analisadores de texto.
4. **Redis** — documentação oficial de expiração e armazenamento chave-valor.
5. **FastAPI** — documentação oficial de API e OpenAPI.
6. **GitHub Actions** — [execução #46103160249](https://github.com/IgorMoraesTech/big-data-enade-grupo6/actions/runs/46103160249), logs e artefato de evidência.
7. **Repositório do Grupo 6** — [código-fonte, README e PRs #28–#35](https://github.com/IgorMoraesTech/big-data-enade-grupo6).

> **Não inserir referências bibliográficas inventadas.** Completar autoria, ano, título, URL, data de acesso e formato no padrão exigido pela SBC.
