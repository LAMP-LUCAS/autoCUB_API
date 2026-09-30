"""Envelope de resultado vazio — STORY-MCP-007/C-01 (ADR 010).

Antes, toda tool do AutoCUB que voltava sem linhas respondia ``content: []``
(zero blocos de texto) com ``isError: false`` e
``structuredContent: {"result": []}``. Qualquer cliente que lê ``content`` —
inclusive um agente — via um retorno **em branco**, sem "sem dados para AC em
2026-07"; e como ``isError`` era ``false``, nada indicava falha.

Decisão 2026-09-30 (usuário): a correção fica **no MCP** (não na API), para não
quebrar o contrato HTTP já consumido. O envelope só entra quando o resultado é
vazio — resultado com linhas continua sendo lista/envelope de antes (o claim
``claim_lim38`` exige que UF coberta continue lista plana).

Três estados, nunca misturados:

* **com dado** → a resposta de sempre;
* **sem dado** → envelope ``{items: [], sem_dados: true, motivo, ...}`` (aqui);
* **erro** → exceção nomeada com ``correlation_id`` (o do client.py).
"""

MOTIVO_SEM_COTACAO = "SEM_COTACAO_PARA_O_PERIODO"

# Marcas que o gate procura para reconhecer um envelope de "sem dado".
MARCAS = ("sem_dados", "motivo", "nota_lim38", "ultima_referencia_disponivel")


def vazio(motivo: str = MOTIVO_SEM_COTACAO, **extra: object) -> dict:
    """Envelope explícito de "sem dado".

    `items` é sempre lista (o consumidor lê `envelope["items"]`), e o motivo é
    nomeado — o agente consegue avisar o usuário em vez de somar vazio.
    """
    envelope = {
        "items": [],
        "total": 0,
        "sem_dados": True,
        "motivo": motivo,
    }
    envelope.update({k: v for k, v in extra.items() if v is not None})
    return envelope


def e_vazio(resultado: object) -> bool:
    """`True` quando a API devolveu lista vazia (o caso mudo que motivou C-01)."""
    return isinstance(resultado, list) and not resultado
