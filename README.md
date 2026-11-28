# Big Data — Buscador de Questões ENADE (Grupo 6)

Projeto acadêmico de processamento e pesquisa de questões do ENADE. **Protótipo em desenvolvimento — não é a entrega final.**

## Fluxo

PDF oficial → Python → JSON → Kafka → Elasticsearch → API FastAPI/Redis → Interface web.

O projeto inclui **login LDAP de laboratório** com estudantes e professores e proteção 403, mas **Kerberos SASL/GSSAPI ainda não está implementado**. As credenciais demonstrativas não são adequadas a produção.
A configuração local usa Kafka PLAINTEXT e Elasticsearch sem segurança, portanto
**não deve ser exposta à internet**.

Documentos:
- [Arquitetura e limitações](docs/ARCHITECTURE.md)
- [Contrato de dados](docs/SCHEMA.md)
- [Guia para colaborar](docs/TEAM.md)
- [Passos de validação](docs/VALIDATION.md)
- [Estrutura do relatório](docs/REPORT_OUTLINE.md)
- [Issues](https://github.com/IgorMoraesTech/big-data-enade-grupo6/issues)

## Pré-requisitos

Docker Engine + Compose v2, aproximadamente 4–6 GB de RAM livres para o
laboratório, e acesso à internet para obter imagens Docker e bibliotecas.
Para desenvolver fora do Docker: Python 3.12+.

## Iniciar a aplicação

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Windows PowerShell: `Copy-Item .env.example .env`.
O serviço `init-index` prepara mapping e analisador do Elasticsearch.
Aguarde a conclusão e confira seus logs: `docker compose logs init-index`.

- Web: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Ver logs: `docker compose logs -f indexer`

## Exemplo fictício (teste do pipeline, NÃO é questão real do INEP)

```bash
docker compose run --rm api python -m scripts.produce sample/example_question.json
docker compose logs --tail=50 indexer
curl "http://localhost:8000/api/questions?q=etica"
curl "http://localhost:8000/api/questions?q=etica"
```

A primeira busca tende a mostrar `cache_hit:false` e a seguinte,
`cache_hit:true` se o Redis estiver disponível e o TTL não tiver expirado.

## Extração de prova real (etapa exploratória)

Coloque o PDF localmente e rode (no host, com dependências instaladas):

```bash
python -m scripts.extract_pdf --pdf prova.pdf --year 2023 --course "Sistemas de Informação" --area "Tecnologia" --section CE --source-url "URL_OFICIAL_DO_PDF" --output data/output/questoes.jsonl
```

O extrator é heurístico, depende da diagramação e **não resolve** OCR,
gabaritos ou fórmulas complexas. Revise manualmente todos os registros antes
de publicar com `python -m scripts.produce data/output/questoes.jsonl`.

## Login LDAP no ambiente de demonstração

O Compose inclui um servidor OpenLDAP interno (sem exposição da porta 389 na máquina).
Essas credenciais são **somente demonstrativas** e não devem ser reutilizadas:

- Estudante: `estudante` / `demo123`
- Professor: `professor` / `demo123`

**Login pela interface web:** abra `http://localhost:8000`. No painel "Entrar no sistema" informe as credenciais de demonstração. O perfil autenticado aparece no topo e o botão **Testar acesso a estatísticas do professor** chama a rota real `GET /api/professor/stats/courses`:
- com estudante, o backend retorna **HTTP 403**, mostrado na tela;
- com professor, retorna **HTTP 200** e a contagem de questões por curso;
- sem login, a rota protegida retorna **HTTP 401**.

Use **Sair da conta** para encerrar a sessão no servidor. A busca pública, o carrinho e as exportações não exigem autenticação nesta versão. O formulário não armazena senha nem token no armazenamento do navegador; a sessão usa cookie HttpOnly. **Este login é apenas para um laboratório privado**, sem TLS no serviço LDAP; não publicar Codespaces/serviços publicamente.

Pelo Swagger em `http://localhost:8000/docs`, use `POST /api/auth/login`
com `{"username":"estudante","password":"demo123"}` e, na mesma sessão
de navegador, acesse `GET /api/professor/stats/courses`: recebe **403**.
Sem login, recebe **401**. Login com `professor` permite consulta de
`GET /api/professor/questions/{question_id}/answer` e painel de cursos.
O navegador mantém a sessão em cookie HttpOnly por até uma hora.
`POST /api/auth/logout` encerra a sessão.

**Atenção:** o laboratório LDAP usa rede Compose sem TLS, apenas para
demonstração local; não o exponha à rede pública. Proteção Kerberos do
Kafka/Elasticsearch permanece pendente, assim como endurecimento
de segurança necessário para produção.

## Testes unitários

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

## Estado e escopo

A integração Docker ponta a ponta com dados fictícios, a recuperação Kafka,
o login OpenLDAP com HTTP 403 e o cache Redis já possuem testes automatizados.
Os relatórios desses testes estão em GitHub Actions e em `docs/EVIDENCIAS_TP2.md`.
O corpus ENADE oficial, a avaliação manual de 50 questões, a vazão de ingestão,
o lag Kafka, Kerberos e o PDF/vídeo finais ainda não estão concluídos.
Não afirmar que RF01 (acervo integral), RF04 (conversão complexa de mídias),
RF22 (Kerberos) ou as metas não funcionais foram integralmente cumpridos.
Relatório e vídeo devem mostrar somente comportamento observado e limitações.
