# Acervo oficial ENADE: inventário e ingestão

## Recorte atual

O manifesto `data/manifest.csv` contém dois cursos da área da Saúde, ambos da edição 2023:

- Enfermagem.
- Fisioterapia.

Para cada curso foram catalogados quatro documentos: prova, gabarito definitivo, padrão de resposta discursiva e diretriz de prova. O recorte permite iniciar a ingestão e testar a recuperação de questões entre cursos, mas não representa o acervo histórico completo do ENADE.

## Manifesto

O manifesto possui nove colunas:

| Coluna | Descrição |
|---|---|
| `ano` | Edição do ENADE. |
| `curso` | Nome do curso avaliado. |
| `area` | Área de conhecimento do curso. |
| `tipo_documento` | Tipo de documento: `prova`, `gabarito`, `padrao_resposta` ou `diretriz`. |
| `formato` | Formato esperado do documento, como `pdf` ou `html`. |
| `url_oficial` | URL do documento na fonte oficial. |
| `nome_arquivo` | Nome local esperado para o documento. |
| `status_link` | Estado da última verificação da URL oficial. |
| `status_local` | Estado de presença e validação do arquivo no ambiente local. |

Os valores de `status_link` são:

- `disponivel`: URL respondeu com HTTP 2xx/3xx na última checagem.
- `ausente`: documento esperado não foi localizado na página oficial; URL e nome ficam vazios.
- `quebrado`: servidor respondeu HTTP 404 ou 410.
- `nao_verificado`: link listado por fonte oficial, mas ainda não confirmado por resposta HTTP conclusiva, incluindo timeout, erro de rede e HTTP 5xx.

Os valores de `status_local` são:

- `baixado`: arquivo presente no diretório local e aprovado pelas verificações locais executadas.
- `nao_baixado`: arquivo não encontrado no diretório local esperado.

A URL do documento é preservada, sem substituição pelo endereço da página de catálogo. A coluna `nome_arquivo` define o nome local esperado, mas, isoladamente, não comprova que o download ocorreu.

Nos itens do Repositório Institucional do INEP (RIEP), `url_oficial` aponta para o **download direto do PDF** (endereço `/bitstreams/.../download`), não para a página HTML `/items/...`. A Portaria nº 287/2023 de Fisioterapia é distribuída nesse repositório como **PDF**, com nome local `portaria_287_2023_fisioterapia.pdf`. Diretrizes podem ser distribuídas como HTML ou PDF; o campo `formato` deve refletir o arquivo real.

## Contagem e estado observado (28/11/2026)

O inventário local identificou oito documentos no manifesto. Cinco PDFs estão presentes em `data/raw/`: prova e gabarito de Enfermagem 2023, prova, gabarito e padrão de resposta de Fisioterapia 2023.

Os arquivos locais ficam em `data/raw/`, diretório ignorado pelo Git, e não são versionados no repositório.

Resultado observado de `python -m scripts.inventory_enade`:

- Documentos identificados: 8.
- Links disponíveis: 8.
- Links ausentes: 0.
- Links quebrados: 0.
- Links não verificados: 0.
- Arquivos baixados: 5.
- Documentos não baixados: 3.
- Arquivos inválidos: 0.
- Documentos processados: 0.

Os três documentos ainda não obtidos localmente são o padrão de resposta de Enfermagem 2023, a diretriz de Enfermagem 2023 e a diretriz de Fisioterapia 2023.

O resultado do inventário representa o estado observado no ambiente local. A classificação de links disponíveis corresponde ao estado registrado no manifesto e não deve ser interpretada como uma nova checagem HTTP realizada durante cada execução do inventário.

### Arquivos locais

Os cinco PDFs presentes em `data/raw/` são:

| Arquivo | Curso | Documento |
|---|---|---|
| `2023_PV_enfermagem.pdf` | Enfermagem | Prova |
| `2023_GB_enfermagem.pdf` | Enfermagem | Gabarito definitivo |
| `2023_PV_fisioterapia.pdf` | Fisioterapia | Prova |
| `2023_GB_fisioterapia.pdf` | Fisioterapia | Gabarito definitivo |
| `2023_fisioterapia.pdf` | Fisioterapia | Padrão de resposta |

Os arquivos de Sistemas de Informação 2021 ainda podem existir localmente em `data/raw/`, mas não fazem parte do recorte atual nem dos oito registros do manifesto.

Os arquivos locais não são disponibilizados automaticamente no CI. A aprovação dos testes de CI não comprova que os PDFs locais foram enviados ou examinados pelo ambiente de integração contínua.

### Amostra real revisada

`sample/real_questions.jsonl` contém duas questões objetivas, uma de cada curso:

- Fisioterapia 2023, questão 04, página física 6, gabarito A. Aborda inteligência artificial generativa e menciona questões éticas.
- Enfermagem 2023, questão 15, página física 18, gabarito A. Aborda autonomia da paciente e princípios éticos/bioéticos.

As questões foram selecionadas como candidatas para testar uma busca textual por `ética` entre cursos diferentes. A existência de vocabulário relacionado nos textos não comprova, por si só, que o mecanismo de busca recupera ambas. Essa demonstração depende da execução e do registro de uma consulta real.

As páginas das duas questões da amostra e suas respectivas respostas foram conferidas nos PDFs originais e nos gabaritos oficiais, conforme os resultados apresentados na seção "Verificação de integridade e gabaritos". Não se deve alterar o texto das questões para forçar correspondência temática.

O extrator heurístico existente não deve ser considerado uma solução de segmentação integral sem avaliação adicional. Questões em colunas, alternativas lado a lado e itens de questionário de percepção podem produzir associações incorretas. A amostra manual não representa uma avaliação de qualidade com 50 questões.

## Execução

Na raiz do repositório:

```bash
python -m pip install -r requirements.txt
python -m scripts.inventory_enade
python -m scripts.inventory_enade --check-links
python -m scripts.inventory_enade --check-local
python -m pytest -q tests/test_inventory_enade.py
```

Os PDFs locais devem ficar em `data/raw/`. Os artefatos efetivamente processados ficam em `data/output/`. Esses diretórios são locais de trabalho e não devem ser versionados como PDFs grandes ou saídas geradas.

O resumo do inventário diferencia documentos identificados, links disponíveis, ausentes, quebrados e não verificados, arquivos baixados e documentos processados. A presença de um arquivo local não altera, por si só, o estado da URL oficial.

O contador `processados` verifica a existência dos arquivos JSONL esperados em `data/output/`. Essa contagem não valida, por si só, a qualidade ou a completude do conteúdo extraído.

## Limitações e próximos passos

- O recorte contempla somente dois cursos da edição 2023; não representa o universo completo do acervo ENADE.
- Três documentos do manifesto ainda não foram obtidos localmente.
- A extração automática integral e a publicação de todas as questões ainda precisam ser implementadas e validadas.
- A amostra atual possui duas questões revisadas e não substitui a avaliação manual de pelo menos 50 questões exigida para medir a qualidade da extração.
- A busca interdisciplinar entre Fisioterapia e Enfermagem ainda precisa ser demonstrada com uma consulta real no mecanismo de busca.
- O inventário não comprova que os documentos já foram processados, publicados no Kafka ou indexados no Elasticsearch.

## Fontes oficiais

- [ENADE — Provas e Gabaritos 2023](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos/2023).
- [Prova de Enfermagem 2023](https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_enfermagem.pdf).
- [Gabarito de Enfermagem 2023](https://download.inep.gov.br/enade/provas_e_gabaritos/2023_GB_enfermagem.pdf).
- [Prova de Fisioterapia 2023](https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_fisioterapia.pdf).
- [Gabarito de Fisioterapia 2023](https://download.inep.gov.br/enade/provas_e_gabaritos/2023_GB_fisioterapia.pdf).
- [Padrão de resposta de Fisioterapia 2023 (PDF)](https://riep.inep.gov.br/bitstreams/d4b82b3d-f1f5-4a66-99ff-fd5cfee5bd45/download).
- [Portaria INEP nº 275/2023 — Enfermagem](https://www.in.gov.br/web/dou/-/portaria-n-275-de-26-de-junho-de-2023-492247182).
- [Portaria INEP nº 287/2023 — Fisioterapia (PDF)](https://riep.inep.gov.br/bitstreams/97432eb4-616e-4a7c-b5cd-0fc693fa1c76/download).
- [Padrão de resposta de Enfermagem 2023 (PDF)](https://riep.inep.gov.br/bitstreams/f7b687b4-2997-4a72-b8a2-82bd476e0dac/download).

### Verificação de integridade e gabaritos

Os cinco PDFs classificados como baixados no recorte ENADE 2023 de Enfermagem e Fisioterapia foram verificados localmente. Os hashes SHA-256 foram recalculados e coincidiram com os valores registrados durante a conferência.

| Arquivo | Tamanho (bytes) | SHA-256 |
|---|---:|---|
| `2023_PV_enfermagem.pdf` | 9117323 | `41d267263ed395bda17ac07543fe54cb2a76dfbbdb3777f0da3d1a057176d0cc` |
| `2023_GB_enfermagem.pdf` | 177471 | `74a39b14cc72ee9456da68849b37071018ae14a50d1e6b444b076dc1e1f43793` |
| `2023_PV_fisioterapia.pdf` | 8932646 | `de34c0f531379814a7bb771041d430327756962af152cd71bf7336dffd3f3ec4` |
| `2023_GB_fisioterapia.pdf` | 178658 | `cb1f83ca8a6d77aea19ad592ceb406fad7e66a85aa90171ea4767852da1cec99` |
| `2023_fisioterapia.pdf` | 335552 | `a2214a6d237c787bd7825f0921133d70fabca55c2a5b814f44177048faf03e32` |

Os gabaritos oficiais foram conferidos com as provas originais e com as respostas registradas na amostra JSONL:

| Curso | Questão | Página da prova | Resposta oficial | Resposta JSONL |
|---|---:|---:|---|---|
| Enfermagem 2023 | 15 | 18 | A | A |
| Fisioterapia 2023 | 4 | 6 | A | A |

As duas respostas da amostra coincidem com os respectivos gabaritos oficiais. Os PDFs permanecem fora do versionamento Git.

As verificações de integridade e dos gabaritos foram realizadas localmente. A CI não verifica a presença nem a integridade desses arquivos, pois os PDFs não são versionados no repositório.
