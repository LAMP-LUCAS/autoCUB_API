"""LIM-38 — espelho da nota de cobertura da API (auditoria MCP de custo).

O texto canônico vive em ``autocub/api/lim38.py`` (API). O contexto de build
deste pacote é apenas ``autocub_mcp/`` (Dockerfile da stack), então o MCP
não pode importar o módulo da API — o espelho aqui é proposital e está
documentado: mantido em sincronia pelo claim ``claim_lim38`` do gate da
casa, que exige as chaves do texto (CBIC / equipe / solução) na resposta
ao vivo.

Uso: ``cub_get_uf`` converte o 404 de UF brasileira sem adapter em
*resposta* com a nota (decisão 2026-09-30: responder > erro/``[]`` vazio).
A detecção é pelo marcador ``LIM-38`` no ``detail`` repassado pelo client.
"""

NOTA_LIM38 = (
    "Dado de CUB ainda não disponibilizado pelo CBIC para esta UF "
    "(limitação de roadmap LIM-38: alguns estados não publicam o índice e "
    "adapters de outros ainda não foram implementados); a equipe de "
    "desenvolvimento está procurando solução."
)
