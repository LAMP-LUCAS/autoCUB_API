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

## Adaptador local em desenvolvimento

Pacote independente `autocub_mcp`, layout src/tools em dois tiers seguindo a referência Matryoshka. Contrato estático: revisão de produto `c08892b38f3035cbfe6a837a92eeb3f3285ee5c7`, routers montados em `/v1`; sem consulta ao OpenAPI runtime. Treze tools: as doze consultas solicitadas e `cub_calc_area` (POST `/v1/calc/area`, objeto ou lista). `/v1/calc/fatores` só possui GET: a tool POST solicitada é omitida. `/v1/cub/br` existe, mas não recebeu nome no catálogo solicitado e não é exposta implicitamente. Aliases panorama, impacto-desoneracao, ranking, historico e comparativo existem, embora ocultos no OpenAPI.

Configuração exclusivamente por ambiente: `AUTOCUB_BASE_URL` usa a constante `DEFAULT_GATEWAY_BASE_URL` (`http://api-gateway-kong:8000`), contrato interno de serviço; `AUTOCUB_CACHE_URL` é opcional, sem fallback de infraestrutura. `AUTOCUB_CACHE_TTL=300`, `AUTOCUB_TIMEOUT=30`, `AUTOCUB_RETRIES=3` (total de tentativas). `AUTOCUB_MCP_PORT=8080`, `AUTOCUB_MCP_HOST=0.0.0.0`, `AUTOCUB_MCP_TRANSPORT=streamable-http` (também SSE e stdio). GET `/sse` é SSE legado; POST `/sse` é Streamable HTTP; `/messages/` recebe mensagens SSE. Não há override de TransportSecuritySettings.

BYOK por chamada, sem chave global, sem leitura de dotenv. Chaves Redis usam `autocub:` + impressão SHA-256 truncada + argumentos canônicos. O cache-aside aceita callback confiável de autorização, executado antes da leitura; sem callback, não lê nem escreve cache e consulta o gateway em toda execução. As tools não instalam callback fictício: integração de `saas-gateway/MCP-Admission v1`, identidade/tenant/escopo, revogação e contabilização permanecem gates de exposição. Fingerprint não substitui admissão. Respostas REST são preservadas sem recalcular ou converter precisão monetária.

Entrega inclui testes isolados e Dockerfiles; sem build Docker, deployment, credenciais ou alterações de infraestrutura. O responsável pela integração deve configurar URL/rotas autorizadas do gateway, cache dedicado se habilitado, admissão antes de cache, rede/ingress, limites e compatibilidade de transporte. Testes locais não são aprovação de catálogo nem validação runtime.

### Evidências locais

Em 2026-09-17: `pytest -q` — 61 testes aprovados; `ruff check .` e `mypy src` aprovados (9 módulos). Ambiente isolado Python 3.12, MCP SDK 1.30.0; instalação via `pip install --no-deps .` construiu wheel e confirmou `autocub-mcp = autocub_mcp:main`. Testes bloqueiam sockets externos, simulam HTTP/Redis e verificam handshake Streamable HTTP, descoberta de 13 tools e lifespan. SSE legado tem roteamento verificado, não sessão ponta a ponta. Dockerfiles usam Python 3.11, ainda não testado em container. `/health` local verifica liveness do processo no modo combinado, não readiness de gateway/Redis; o healthcheck Docker pressupõe esse modo. `Dockerfile.dev` instala fonte antes do editable; não configura hot reload.

Nenhuma validação de API live, admissão operacional, build Docker ou deployment foi executada. Cache não serve hits nas tools até integração confiável de admissão; erros de autorização não são cacheados. `BLE001` é excetuado apenas em cache.py para fronteiras de degradação e negação segura. Schemas de resposta são preservados como JSON REST, não revalidados contra DTOs duplicados. Validações CUB de UF/período permanecem no produto REST; segmentos de path inseguros são rejeitados localmente.
