# 🏛️ Consórcio CBIC, Federação do CUB e Especificação de Futuros Adapters

Este documento registra a radiografia federativa da apuração do **Custo Unitário Básico de Construção (CUB/m²)** no Brasil, discriminando os estados formalmente integrados ao portal nacional da **CBIC (`cub.org.br`)**, os estados que operam sistemas próprios e o blueprint arquitetural para desenvolvimento de futuros adapters.

---

## 1. Contexto Legal e Institucional

A publicação do CUB/m² é regida pela **Lei Federal nº 4.591 de 16 de dezembro de 1964** (Art. 54) e padronizada pela **ABNT NBR 12.721:2006**.
A lei estabelece que:
1. Cabe aos sindicatos regionais da indústria da construção civil (**Sinduscons**) calcular e divulgar mensalmente os custos unitários até o **5º dia útil do mês subsequente**.
2. A **CBIC (Câmara Brasileira da Indústria da Construção)** mantém o portal centralizador nacional (`cub.org.br`), onde congrega a emissão padronizada dos relatórios mensais em PDF e calcula o **CUB Médio Brasil ponderado**.

Contudo, a adesão ao sistema unificado da CBIC é federativa e voluntária. Determinados estados optam por manter sistemas próprios de publicação ou não disponibilizam seus dados na plataforma nacional.

---

## 2. Mapa dos 27 Estados Brasileiros no Portal CBIC (`cub.org.br`)

O mapeamento abaixo foi validado por inspeção HTTP automatizada em setembro de 2026:

| UF | Sinduscon(s) Ativo(s) | ID Oficial CBIC | Status no Consórcio CBIC | Fonte Primária |
|:---|:---|:---:|:---:|:---|
| **AC** | Sinduscon-AC | `4` | ✅ Integrado | `cub.org.br/cub-m2-estadual/AC/` |
| **AL** | Sinduscon-AL | `17` | ⚠️ Intermitente / Local | `cub.org.br/cub-m2-estadual/AL/` / Portal Sinduscon-AL |
| **AM** | Sinduscon-AM | `5` | ✅ Integrado | `cub.org.br/cub-m2-estadual/AM/` |
| **AP** | — | `-1` | ❌ Não Integrado | Portal local / Federação das Indústrias AP |
| **BA** | Sinduscon-BA | `6` | ✅ Integrado | `cub.org.br/cub-m2-estadual/BA/` |
| **CE** | Sinduscon-CE | `7` | ✅ Integrado | `cub.org.br/cub-m2-estadual/CE/` |
| **DF** | Sinduscon-DF | `8` | ✅ Integrado | `cub.org.br/cub-m2-estadual/DF/` |
| **ES** | Sinduscon-ES | `9` | ✅ Integrado | `cub.org.br/cub-m2-estadual/ES/` |
| **GO** | Sinduscon-GO | `10` | ✅ Integrado | `cub.org.br/cub-m2-estadual/GO/` |
| **MA** | Sinduscon-MA | `11` | ✅ Integrado | `cub.org.br/cub-m2-estadual/MA/` |
| **MG** | Sinduscon-MG (BH)<br>Sinduscon-Juiz de Fora<br>Sinduscon-GV<br>Sinduscon-Vale do Piranga<br>Sinduscon-Lagos<br>Sinduscon Norte | `1`<br>`32`<br>`39`<br>`33`<br>`34`<br>`36` | ✅ Integrado (Multi-sindicatos) | `cub.org.br/cub-m2-estadual/MG/` |
| **MS** | Sinduscon-MS | `-1` | ⚠️ Intermitente / Local | Portal Sinduscon-MS |
| **MT** | Sinduscon-MT | `13` | ✅ Integrado | `cub.org.br/cub-m2-estadual/MT/` |
| **PA** | Sinduscon-PA | `14` | ✅ Integrado | `cub.org.br/cub-m2-estadual/PA/` |
| **PB** | Sinduscon-João Pessoa | `15` | ✅ Integrado | `cub.org.br/cub-m2-estadual/PB/` |
| **PE** | Sinduscon-PE | `16` | ✅ Integrado | `cub.org.br/cub-m2-estadual/PE/` |
| **PI** | Sinduscon-Teresina | `17` | ✅ Integrado | `cub.org.br/cub-m2-estadual/PI/` |
| **PR** | Sinduscon-PR (Curitiba)<br>Sinduscon-Noroeste (Maringá)<br>Sinduscon-Oeste (Cascavel) | `18`<br>`19`<br>`38` | ✅ Integrado (Multi-sindicatos) | `cub.org.br/cub-m2-estadual/PR/` |
| **RJ** | Sinduscon-Rio | `20` | ✅ Integrado | `cub.org.br/cub-m2-estadual/RJ/` |
| **RN** | Sinduscon-RN | `21` | ✅ Integrado | `cub.org.br/cub-m2-estadual/RN/` |
| **RO** | Sinduscon-RO | `25` | ✅ Integrado | `cub.org.br/cub-m2-estadual/RO/` |
| **RR** | Sinduscon-RR | `30` | ✅ Integrado | `cub.org.br/cub-m2-estadual/RR/` |
| **RS** | Sinduscon-RS | `-1` | ⚠️ Portal Próprio | `sinduscon-rs.com.br/banco-de-dados/cub/` |
| **SC** | Sinduscon Grande Florianópolis | `26` | ✅ Integrado | `cub.org.br/cub-m2-estadual/SC/` |
| **SE** | Sinduscon-SE | `22` | ✅ Integrado | `cub.org.br/cub-m2-estadual/SE/` |
| **SP** | Sinduscon-SP | `-1` | ❌ Portal Próprio Fechado | `sindusconsp.com.br/cub/` |
| **TO** | Sinduscon-TO | `-1` | ❌ Não Integrado | Portal local / FIETO |

---

## 3. Diagnóstico dos Estados "Outliers" (Necessidade de Adapters)

### 3.1 São Paulo (`SP`) — Sinduscon-SP
- **Situação:** São Paulo possui o maior peso econômico relativo no cálculo do CUB Brasil (25,32%), porém o **Sinduscon-SP não publica seus dados no formulário central da CBIC**.
- **Causa:** O sindicato paulista monetiza e restringe o acesso direto ao CUB em seu próprio portal corporativo (`https://sindusconsp.com.br/cub/`), disponibilizando apenas resumos ou acesso via login/intranet.
- **Solução Futura:** Criar o adapter `SindusconSpAdapter` implementando:
  1. Crawler específico para a página de releases do Sinduscon-SP.
  2. Parser HTML/JSON das tabelas estaduais publicadas pela imprensa ou boletins oficiais da construção civil paulista.

### 3.2 Rio Grande do Sul (`RS`) — Sinduscon-RS
- **Situação:** O Sinduscon-RS mantém um banco de dados independente e próprio com séries históricas extensas (`https://www.sinduscon-rs.com.br/banco-de-dados/cub/`).
- **Solução Futura:** Criar o adapter `SindusconRsAdapter` para consumir diretamente os dados estruturados do portal gaúcho.

### 3.3 Amapá (`AP`), Tocantins (`TO`) e Mato Grosso do Sul (`MS`)
- **Situação:** Pequenos sindicatos patronais que não transmitem sistematicamente a planilha padronizada da NBR 12.721 à CBIC.
- **Solução Futura:** Criação de adapters para feeds das Federações Estaduais de Indústria (FIEAP, FIETO, FIEMS) ou diários oficiais dos estados.

---

## 4. Blueprint Arquitetural para Novos Adapters

A arquitetura do AutoCUB API baseada em **Ports & Adapters (Hexagonal)** permite adicionar suporte a qualquer um desses estados sem alterar nenhuma linha da API ou do banco de dados.

### Como Implementar um Novo Adapter:

1. **Crie a classe herdeira de `BaseEtlAdapter`:**
```python
# autocub/adapters/sinduscon_sp_adapter.py
from autocub.adapters.base import BaseEtlAdapter, StandardEtlResult

class SindusconSpAdapter(BaseEtlAdapter):
    adapter_id = "sinduscon_sp_crawler_v1"
    version = "1.0.0"

    def can_handle(self, source_type: str, source_reference: Any) -> bool:
        return source_type.upper() == "SP_DIRECT" or source_reference == "SP"

    def extract(self, source_reference: Any, **kwargs) -> Any:
        # Lógica de scraping ou consumo da API do Sinduscon-SP
        ...

    def transform(self, raw_content: Any, **kwargs) -> StandardEtlResult:
        # Mapeamento para os 19 padrões canônicos da NBR 12.721
        ...
```

2. **Registre no `AdapterRegistry`:**
```python
# autocub/adapters/registry.py
from autocub.adapters.sinduscon_sp_adapter import SindusconSpAdapter

AdapterRegistry.register(SindusconSpAdapter())
```

3. **Pronto!** O pipeline de ETL resolverá o novo adapter automaticamente via polimorfismo quando a UF `SP` for solicitada.
