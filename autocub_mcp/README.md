# AutoCUB MCP Server

Adapter MCP para consultas CUB/NBR 12.721. O transporte público usa
Streamable HTTP em `/sse` e SSE legado; o callback é `/messages/`.

## Credencial

Em HTTP, a `X-API-KEY` é lida do contexto da requisição pelo FastMCP e
repassada somente em memória ao cliente interno. A credencial não é campo de
tool, não aparece no schema e o cache é particionado por digest. Em stdio, a
chamada local pode usar uma chave explícita; chamadas HTTP sem header falham
fechadas.

O upstream padrão é o gateway autorizado (`AUTOCUB_BASE_URL`). O servidor não
deve apontar para um upstream interno para contornar tier ou quota.

## Testes

```bash
PYTHONPATH=src pytest -q
```
