# 🏷️ AutoCUB API — Release v1.1.0 (2026-09-03)

## 📌 Resumo da Versão
A versão **v1.1.0** da **AutoCUB API** expande a capacidade analítica e de orquestração do ecossistema, introduzindo a decomposição do pipeline de ETL em sub-tarefas atômicas no Celery (*task chunking*), a desativação de sindicatos que não publicam no portal nacional da CBIC, o módulo de telemetria e auditoria forense com captura de recursos de hardware em tempo real, além de enriquecimento da documentação OpenAPI e do endpoint de fatores de ponderação da NBR 12.721:2006.

Esta release é 100% retrocompatível com a versão v1.0.0.

---

## 🚀 Novidades & Funcionalidades (Features)

- **[Cálculo & Engenharia]**: Novo endpoint `GET /v1/calc/fatores` retornando os fatores normativos canônicos da NBR 12.721:2006 para conversão de área real em área equivalente de construção.
- **[Cálculo & Engenharia]**: Refatoração do endpoint `POST /v1/calc/area-equivalente`, permitindo o cálculo conjugado paramétrico de custo total estimado baseado no CUB/m² de um estado/projeto específico.
- **[Auditoria & Observabilidade]**: Novo endpoint `GET /v1/admin/etl/report`, expondo em tempo real métricas consolidadas de eficiência, conciliação do PostgreSQL, armazenamento físico de PDFs e telemetria de hardware (CPU, RAM e tráfego de rede via `psutil`).
- **[OpenAPI & Swagger]**: Documentação completa e enriquecida em todas as rotas da API, com detalhamento das regras normativas da NBR 12.721:2006 e da Lei Federal 4.591/1964.

---

## ⚡ Performance & Otimizações

- **[Celery Task Chunking]**: Quebra do ETL monolítico em sub-tarefas atômicas e idempotentes `process_chunk_cub(sinduscon_id, ano)`. O tempo por tarefa caiu para 15s–45s, eliminando definitivamente o risco de estouro do limite de timeout padrão do Celery (`TimeLimitExceeded(3600)`).
- **[Desativação de Sindicatos Inativos]**: Marcação formal de `ativo = False` para os sindicatos regionais que não alimentam o portal central da CBIC (`cub.org.br`) (MG regionais, PR-Oeste, SE e RO), reduzindo centenas de chamadas desnecessárias na fila.
- **[Telemetria Automática]**: Ao final de cada ciclo de ingestão, o worker emite automaticamente o sumário consolidado no log formatado em Markdown e persiste os relatórios `etl_audit_latest.json` e `etl_audit_latest.md`.

---

## 🛡️ Segurança & Higienização de Repositório

- **[Expurgo do Histórico do Git]**: Reescrita cirúrgica de todo o histórico do Git via `git-filter-repo`, eliminando do rastreamento qualquer script auxiliar ou credencial de teste.
- **[Blindagem no .gitignore]**: Adição formal de pastas e arquivos de apoio (`scripts/`, `scratch/`, `*.bak`, `*.tmp`, `*.log`) no `.gitignore` para proteção permanente.

---

## 📦 Infraestrutura, Dependências & CI/CD

- Adição da biblioteca `psutil>=5.9.0` em `requirements.txt` para monitoramento de recursos do sistema.
- Suíte completa de 27 testes automatizados validada com 100% de sucesso.
- Imagens Docker `api` e `celery_worker` atualizadas e reconstruídas.

---

## ⚠️ Quebras de Compatibilidade (Breaking Changes)
> *Nenhuma quebra de compatibilidade nesta versão. Todos os contratos de dados e rotas anteriores permanecem 100% funcionais.*

---

## 📝 Commits Desta Versão
- `chore: bump version to v1.1.0 and add release notes`
- `chore: remove auxiliary scripts and audit reports from public repository`
- `feat(etl): implement task chunking, inactive sinduscon flags, and automated telemetry report`
- `feat(api): refactor area calc endpoint, add /calc/fatores, and enrich OpenAPI documentation across all routers`

**Autores e Colaboradores:** @LAMP-LUCAS
