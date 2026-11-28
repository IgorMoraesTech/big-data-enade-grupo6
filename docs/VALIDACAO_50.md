# Protocolo de avaliação: 50 questões ENADE 2023

**Estado da evidência: 0/50 revisões humanas registradas.** Este arquivo e o CSV são um plano, **não resultados medidos**.

## Amostra e fontes

- 25 questões objetivas de Enfermagem 2023 e 25 de Fisioterapia 2023 (50 registros).
- Provas oficiais: [Enfermagem](https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_enfermagem.pdf) e [Fisioterapia](https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_fisioterapia.pdf).
- Intervalos: questões objetivas 01–09 (FG) e 10–38 (CE). D1/D2 (discursivas) estão excluídas, assim como o questionário de percepção, que reutiliza números de 01 a 09.
- Seleção sistemática e não aleatória de 25 números por curso, espalhada ao longo da prova; não extrapolar resultados para outras edições/cursos.
- **Páginas físicas não foram preenchidas** porque exigem verificação nos PDFs originais.

## Procedimento para obter dados válidos

1. Obter os PDFs oficiais e armazenar sem versioná-los em `data/raw/2023_PV_enfermagem.pdf` e `data/raw/2023_PV_fisioterapia.pdf`.
2. Copiar `evidence/validation_50_template.csv` para `evidence/validation_50_reviewed.csv` ou gerar novo template com `python -m scripts.validation_50 prepare --output evidence/validation_50_template.csv`.
3. Executar o extrator existente para os PDFs com `python -m scripts.extract_pdf --help` e guardar os JSONL em `data/output/`. **Não corrigir o JSONL automaticamente antes da avaliação.** O extrator atual recebe uma seção fixa (`--section FG/CE`), pode misturar o questionário de percepção, perder colunas, alternativas e páginas. Esses defeitos são candidatos a erros observáveis e não devem ser encobertos.
4. Para cada uma das 50 linhas, **localizar a questão no PDF**, registrar a página física e o caminho do JSONL e comparar os seis campos: número, seção, tipo, enunciado, alternativas e páginas. Marcar cada campo como `certo` ou `errado`. Se não houver extração, marcar os campos prejudicados como `errado` e `categoria_erro=nao_extraida`.
5. Informar revisor, `data_revisao` no padrão `AAAA-MM-DD`, observações, categoria de erro quando aplicável e `status_revisao=verificado` **somente depois da comparação humana real**.
6. Gerar o resultado com `python -m scripts.validation_50 report --input evidence/validation_50_reviewed.csv --output evidence/validation_50_results.json`. O script rejeita 50 itens incompletos, duplicados, sem revisor/data/páginas, ou sem marcação de cada campo.

## Como interpretar

A taxa por campo = registros corretos para o campo ÷ 50; a taxa de registro integral = registros com os seis campos corretos ÷ 50. A classificação precisa ser feita por alguém que confronte a extração com o PDF original; testes com dados fictícios provam apenas a lógica do cálculo.

- **Número**: excluir falsos positivos de questionário de percepção.
- **Seção**: FG (01–09) ou CE (10–38).
- **Tipo**: questão objetiva.
- **Enunciado**: integridade, ordem e associação de texto/contexto.
- **Alternativas**: A–E alinhadas ao item certo, sem trocas/truncamentos.
- **Páginas**: todas as páginas físicas que contêm o item.

O protocolo **não** valida gabaritos, figuras, tabelas, questões discursivas, processamento completo dos documentos ou qualidade estatística do corpus inteiro. O arquivo de relatório prova apenas consistência da planilha preenchida, não a autenticidade de uma revisão humana — guardar evidência visual e assinatura/identificação dos revisores.

## Conclusão atual

**Nenhuma taxa de acerto pode ser declarada ainda.** O formulário e os testes são infraestrutura para cumprir o requisito de avaliação manual; a revisão de 50 questões continua pendente.
