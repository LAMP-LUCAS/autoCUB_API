# PLAN: Fase 3.2 — desenvolvimento MCP do AutoCUB

> Dono: autocub_api. Revisão 2026-09-17; plano proposto, implementação e validação pendentes. Escopo exclusivamente de produto.

## Propriedade e contrato

O produto mantém dados CUB, regras normativas, schemas e calculadoras; tools são adaptadores dos casos de uso existentes, não um novo motor de cálculo. O guia [Endpoints e regras de negócio](GUIA_ENDPOINTS_E_REGRAS_DE_NEGOCIO.md) é contexto funcional, não prova da versão efetiva da API.

Entregável proposto: **`autocub/MCP-Catalog v1`**, autoridade única neste produto para catálogo, entradas/saídas, erros, protocolo negociado, transporte, path, health e configuração suportada. Deve identificar a revisão do OpenAPI usada. Consumir **`saas-gateway/MCP-Admission v1`** por nome e versão para autorização/contabilização; contrato de admissão ainda depende de aprovação e publicação pelo gateway. Não duplicar suas regras comerciais.

## Implementação planejada

1. Inventariar OpenAPI e código da revisão escolhida, incluindo consultas, metadados e calculadoras. Construir uma matriz tool → operationId → método/path → schemas → testes. Não fixar quantidade de tools.
2. Mapear `/calc/*` e aliases ao OpenAPI existente antes de criar qualquer rota. Não presumir GET para cálculo de área/fatores nem declarar endpoints novos por ausência em documentação antiga. Divergência exige decisão do produto e teste, não alteração implícita do contrato.
3. Definir catálogo aprovado com o gateway; separar rotas públicas de administração, ETL e auditoria operacional, que não viram tools públicas.
4. Manter camadas transporte → aplicação → portas de consulta/cálculo, com adapters injetáveis e bibliotecas confirmadas no projeto. Reutilizar schemas e regras; não copiar uma implementação de outro produto sem análise de dependências.
5. Autenticar por caller; pedir admissão conforme `MCP-Admission v1`. Contexto MCP deve ser confiável e vinculado à tool, tenant e identidade; header autodeclarado ou URL REST não concede `mcp_access`.
6. Falhar fechado na ausência de caller ou decisão válida, inclusive quando a autorização estiver indisponível. Não há API key privilegiada compartilhada de fallback.
7. Autorizar antes de cache hits; particionar por tenant, escopo e argumentos canônicos. Invalidar/reautorizar em revogação ou mudança de plano, seguindo a autoridade do gateway. Respeitar a semântica aprovada de quota/retry/fan-out.
8. Preservar unidades, referência temporal, fonte e limitações normativas em respostas; não inventar dado ausente ou confundir cálculo com persistência de projeto.

## Testes e entrega

- [ ] Schemas e métodos de cada tool conferem com OpenAPI da revisão declarada, especialmente calculadoras.
- [ ] Testes de casos válidos, unidades/UF/referência inválidas e limites de payload; consistência com os casos de uso existentes.
- [ ] Negação para caller inválido/revogado, sem admissão e contexto MCP forjado.
- [ ] Cache quente/frio, separação entre tenants, mudança de plano e indisponibilidade de autorização cobertos.
- [ ] Descoberta não concede execução; nenhuma tool administrativa/ETL publicada.
- [ ] Transporte, negociação, cancelamento e erros definidos e testados; catálogo versionado sem contagem presumida.
- [ ] Release publica contrato, configuração suportada e evidências de compatibilidade; exposição é gate separado.

Não houve validação runtime nesta revisão. Gaps estáticos não são exploits demonstrados nem evidência de invasão.
