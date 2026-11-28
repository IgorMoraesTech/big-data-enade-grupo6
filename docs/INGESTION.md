# Acervo oficial ENADE: inventário e ingestão

## Recorte inicial

O manifesto `data/manifest.csv` contém dois cursos de áreas distintas:

- Sistemas de Informação (bacharelado), edição 2021.
- Enfermagem (bacharelado), edição 2023.

Para cada curso foram catalogados prova, gabarito definitivo, padrão de resposta discursiva e portaria de diretrizes. O recorte serve para iniciar a ingestão e demonstrar pesquisa interdisciplinar; não representa o acervo histórico completo.

## Manifesto

Colunas: `ano,curso,area,tipo_documento,url_oficial,nome_arquivo,status`.

- `disponivel`: URL respondeu com HTTP 2xx/3xx na última checagem.
- `ausente`: documento esperado não foi localizado na página oficial; URL e nome ficam vazios.
- `quebrado`: servidor respondeu HTTP 404 ou 410.
- `nao_verificado`: link listado por fonte oficial, mas ainda não confirmado por resposta HTTP conclusiva (inclui timeout, erro de rede e HTTP 5xx).

A URL do documento é preservada, sem substituir pelo endereço da página de catálogo. As páginas de catálogo do INEP estão listadas nas fontes abaixo. A coluna `nome_arquivo` define o nome local esperado, não comprova que o download ocorreu.

## Contagem e estado observado (28/11/2026)

Foram recebidos e validados localmente quatro PDFs oficiais, dois por curso:
provas e gabaritos definitivos de Sistemas de Informação (2021) e Enfermagem
(2023). Os quatro arquivos ficam em `data/raw/`, ignorado pelo Git.

- Documentos identificados no manifesto: 8.
- Arquivos PDF obtidos e validados localmente: 4.
- Provas com extração manual de ao menos uma questão revisada: 2.
- Questões reais revisadas e validadas pelo schema: 2 (uma por curso).
- Diretrizes e padrões de resposta: 4 registros ainda não obtidos localmente.
- URLs não foram submetidas a nova checagem HTTP neste ambiente; o recebimento
  dos PDFs confirma a disponibilidade dos arquivos, não uma resposta HTTP atual.

Os PDFs foram conferidos quanto à assinatura `%PDF`, páginas e identificação
visual/textual do ENADE/INEP. SHA-256 dos arquivos recebidos:

| Arquivo | Bytes | SHA-256 |
|---|---:|---|
| `2021_PV_bacharelado_sistema_informacao.pdf` | 6.921.221 | `13d81a46488d93fb66836e7c704f9de1ba722c3b130ccb4f0aa9d3522c855ba7` |
| `2021_GB_bacharelado_sistema_informacao.pdf` | 522.400 | `aba7bbc12f549710bf0553ed2ac642423de22076418ff9ff06c810cd86092d85` |
| `2023_PV_enfermagem.pdf` | 9.117.323 | `41d267263ed395bda17ac07543fe54cb2a76dfbbdb3777f0da3d1a057176d0cc` |
| `2023_GB_enfermagem.pdf` | 177.471 | `74a39b14cc72ee9456da68849b37071018ae14a50d1e6b444b076dc1e1f43793` |

### Amostra real revisada

`sample/real_questions.jsonl` contém duas questões objetivas, uma de cada curso,
com `source_pdf`, página física, ID determinístico e gabarito definitivo:

- Sistemas de Informação 2021, questão 12, página física 19, gabarito B.
  Aborda confidencialidade e permissões de acesso a dados.
- Enfermagem 2023, questão 15, página física 18, gabarito A.
  Aborda autonomia da paciente e princípios éticos/bioéticos.

As páginas foram confrontadas manualmente com os PDFs recebidos. A amostra
permite demonstrar busca interdisciplinar por ética, autonomia e proteção de
informações, sem afirmar equivalência conceitual perfeita entre as questões.
Os arquivos JSONL individuais estão em `data/output/` (ignorado pelo Git).

O extrator heurístico existente foi executado experimentalmente, mas sua
segmentação não foi considerada confiável para publicação: alternativas em
colunas e questões lado a lado podem ser associadas incorretamente, e ele pode
capturar itens do questionário de percepção. Por isso, as duas questões da
amostra foram transcritas/revisadas a partir das páginas originais e validadas
com `Question.model_validate_json`; não se declara extração automática integral.

## Execução

Na raiz do repositório:

```bash
python -m pip install -r requirements.txt
python -m scripts.inventory_enade
python -m scripts.inventory_enade --check-links
python -m pytest -q tests/test_inventory_enade.py
```

Os arquivos baixados devem ficar em `data/raw/` e os artefatos efetivamente processados em `data/processed/`. Ambos são locais de trabalho e não devem ser versionados como PDFs grandes. O resumo diferencia identificados, disponíveis, ausentes, quebrados, não verificados, baixados e processados.

## Fontes oficiais verificadas no catálogo do INEP

- [ENADE — Provas e Gabaritos 2021](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos/2021): lista Sistemas de Informação (bacharelado), prova, gabarito e padrão de resposta.
- [ENADE — Provas e Gabaritos 2023](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos/2023): lista Enfermagem, prova, gabarito e padrão de resposta.
- [Legislação ENADE 2021](https://www.gov.br/inep/pt-br/centrais-de-conteudo/legislacao/enade/2021): lista Portaria nº 387/2021 para Sistemas de Informação.
- [Legislação ENADE 2023](https://www.gov.br/inep/pt-br/centrais-de-conteudo/legislacao/enade/2023): lista Portaria nº 275/2023 para Enfermagem.

## Tema transversal para demonstração

Há base documental para uma demonstração temática inicial sobre ética/bioética: a Portaria nº 386/2021 define “Ética, democracia e cidadania” como tema de Formação Geral; a Portaria nº 275/2023 inclui “Bioética e dilemas éticos” entre os objetos de conhecimento de Enfermagem. A prova de Enfermagem 2023 contém questão de componente específico sobre autonomia e princípios bioéticos. A busca interdisciplinar deverá usar questões efetivamente extraídas dos PDFs e não somente as diretrizes. Ainda é necessário revisar a prova de Sistemas de Informação para selecionar uma questão real equivalente antes de afirmar que a demonstração está pronta.

## Limitações

O recorte contempla uma edição de cada curso, não todas as edições disponíveis. As URLs foram obtidas nas páginas oficiais do INEP; por falha de DNS no ambiente desta execução, o download binário e a confirmação HTTP não puderam ser realizados aqui. Não afirmar que os PDFs foram baixados, processados ou que o acervo está completo. A próxima etapa operacional é baixar os seis PDFs/documentos de prova, gabarito e padrão de resposta, validar assinatura `%PDF` e SHA-256, depois extrair e revisar questões reais.
