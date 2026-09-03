# 📋 Modelo Padronizado de Release Notes (CI/CD)

Utilize este modelo para as releases subsequentes (`v1.x.x`, `v2.x.x`) geradas automaticamente pelo pipeline de CI/CD via GitHub Actions.
O objetivo é fornecer uma leitura rápida, técnica e transparente das mudanças introduzidas.

---

```markdown
# 🏷️ AutoCUB API — Release [vX.Y.Z] (YYYY-MM-DD)

## 📌 Resumo da Versão
[Breve resumo em 1 ou 2 parágrafos destacando o principal foco desta release: nova funcionalidade, novo adapter estadual, otimização de performance ou correção crítica].

---

## 🚀 Novidades & Funcionalidades (Features)
- **[Componente/Rota]**: Descrição objetiva da funcionalidade adicionada (#PR).
- **[Adapters]**: Suporte a nova fonte ou estado adicionado (ex: `SindusconSpAdapter`).
- **[API]**: Novo parâmetro ou novo endpoint introduzido.

---

## 🐛 Correções de Bugs (Bug Fixes)
- **[ETL/Downloader]**: Correção de tratamento de resposta ou timeout (#Issue).
- **[Parser]**: Ajuste no parsing de tabelas ou formatos específicos de UFs.
- **[Database]**: Correção em queries, relacionamentos ou integridade referencial.

---

## ⚡ Performance & Otimizações
- **[Redis Cache]**: Redução de tempo de resposta ou ajustes de TTL.
- **[Celery Worker]**: Melhoria na taxa de processamento concorrente do ETL.
- **[Consultas SQL]**: Criação de índices ou otimização de joins no PostgreSQL.

---

## 📦 Infraestrutura, Dependências & CI/CD
- Atualização de pacotes no `requirements.txt` (ex: FastAPI, SQLAlchemy, pdfplumber).
- Melhorias na imagem Docker ou nos healthchecks do Docker Compose.
- Novos testes automatizados adicionados à suíte de regressão.

---

## ⚠️ Quebras de Compatibilidade (Breaking Changes)
> *[Caso não haja, indique: "Nenhuma quebra de compatibilidade nesta versão."]*
- **[Rota/Schema]**: Descrição da alteração que exige atualização no cliente consumidor.

---

## 📝 Lista de Commits
- `abc1234` feat: adiciona suporte ao sinduscon X
- `def5678` fix: corrige validação de períodos passados
- `ghi9012` docs: atualiza documentação dos endpoints

**Autores e Colaboradores:** @LAMP-LUCAS
```
