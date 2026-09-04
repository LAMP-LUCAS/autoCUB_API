# 📚 Guia Completo de Endpoints, Regras de Negócio e "Dores que Resolve" — AutoCUB API

> **Versão da API:** `v1.1.0`  
> **Norma Regulamentadora:** ABNT NBR 12.721:2006  
> **Fundamento Jurídico:** Lei Federal nº 4.591/1964 (Arts. 53 a 55)  
> **Ecossistema:** [Mundo AEC](https://mundoaec.com) / [AutoSINAPI](https://autosinapi.mundoaec.com)

---

## 🧭 Sumário Executivo

A **AutoCUB API** foi projetada para resolver a fragmentação histórica de dados do Custo Unitário Básico da Construção Civil no Brasil. O portal central da CBIC disponibiliza dados descentralizados em relatórios PDF fechados por sindicato estadual, sem uma interface programática unificada, sem rastreabilidade automatizada e sem correlações normativas diretas.

A API introduz três pilares fundamentais:
1. **Inteligência Normativa Canônica:** Implementa as diretrizes matemáticas da NBR 12.721:2006 (áreas equivalentes, lote de 29 insumos, 8 itens excluídos).
2. **Eficiência de Bytes e Cache Redis:** Rotas duplas (rotas curtas para economia de largura de banda e aliases descritivos) com caching em memória (TTL de 24h a 7 dias, latência `< 1ms`).
3. **Resolução Territorial Segura:** Tratamento rigoroso de IDs canônicos da CBIC, separação por sindicatos e sanitização temporal contra períodos futuros inválidos.

---

## 📑 Índice de Grupos de Endpoints

- [1. Calculadoras Paramétricas Normativas](#1-calculadoras-paramétricas-normativas)
- [2. CUB / Custo Unitário Básico](#2-cub--custo-unitário-básico)
- [3. Base de Conhecimento Perene & Normas](#3-base-de-conhecimento-perene--normas)
- [4. Metadados & Padrões Construtivos](#4-metadados--padrões-construtivos)
- [5. Administração & Auditoria Forense do ETL](#5-administração--auditoria-forense-do-etl)
- [6. Health Check & Monitoramento](#6-health-check--monitoramento)

---

## 1. Calculadoras Paramétricas Normativas

### `POST /v1/calc/area`
- **Nome:** Calculadora de Área Equivalente e Orçamento Estimativo Preliminar
- **Norma de Referência:** ABNT NBR 12.721:2006 (Quadro II)

#### 🎯 Dor de Negócio que Resolve
Multiplicar o custo do CUB/m² diretamente pela **Área Real física construída** de uma edificação gera distorções financeiras gravíssimas. Garagens descobertas, pilotis, terraços e varandas custam significativamente menos por metro quadrado do que os apartamentos tipo. Se um incorporador aplicar o CUB sobre a área real total, ele superavalia a obra (tornando o produto inviável no mercado) ou subavalia itens nobres.  
A legislação brasileira exige que todo memorial de incorporação calcule a **Área Equivalente de Construção**. Este endpoint resolve esse cálculo de forma 100% automatizada, aplicando fatores canônicos da norma ou customizados pelo orçamentista, e opcionalmente já entrega a **estimativa de custo global em R$**.

#### 📥 Parâmetros de Entrada
Aceita tanto o objeto estruturado `CalculoAreaRequest` quanto uma lista direta `[AreaItemInput]` para máxima retrocompatibilidade:

```json
{
  "cub_m2": 2623.20,
  "uf": "GO",
  "codigo_padrao": "R8-N",
  "itens": [
    {
      "ambiente": "Apartamento Privativo Tipo",
      "area_real_m2": 120.00,
      "fator_ponderacao": 1.00
    },
    {
      "ambiente": "Garagem Coberta (Subsolo)",
      "area_real_m2": 25.00,
      "fator_ponderacao": 0.65
    },
    {
      "ambiente": "Varanda Gourmet",
      "area_real_m2": 15.00,
      "fator_ponderacao": 0.50
    },
    {
      "ambiente": "Estacionamento Descoberto",
      "area_real_m2": 12.50,
      "fator_ponderacao": 0.12
    }
  ]
}
```

> **Nota de automação:** Se o campo `cub_m2` for omitido, mas forem fornecidos `uf` e `codigo_padrao`, a API consulta automaticamente o banco PostgreSQL para obter a cotação mais recente do CUB naquela praça e efetuar o cálculo. Se `fator_ponderacao` for omitido (`null`), o sistema resolve textualmente pelo nome do ambiente.

#### 📤 Exemplo de Resposta
```json
{
  "area_real_total_m2": 172.50,
  "area_equivalente_total_m2": 145.25,
  "fator_equivalente_medio": 0.8420,
  "cub_m2_aplicado": 2623.20,
  "custo_estimado_total": 381019.80,
  "itens": [
    {
      "ambiente": "Apartamento Privativo Tipo",
      "area_real_m2": 120.00,
      "fator_utilizado": 1.00,
      "area_equivalente_m2": 120.00
    },
    {
      "ambiente": "Garagem Coberta (Subsolo)",
      "area_real_m2": 25.00,
      "fator_utilizado": 0.65,
      "area_equivalente_m2": 16.25
    },
    {
      "ambiente": "Varanda Gourmet",
      "area_real_m2": 15.00,
      "fator_utilizado": 0.50,
      "area_equivalente_m2": 7.50
    },
    {
      "ambiente": "Estacionamento Descoberto",
      "area_real_m2": 12.50,
      "fator_utilizado": 0.12,
      "area_equivalente_m2": 1.50
    }
  ],
  "nota_normativa": "Conforme a ABNT NBR 12.721:2006 (Quadro II), a multiplicação do CUB/m² deve ser efetuada sempre sobre a Área Equivalente Total, e jamais sobre a Área Real física. O CUB não contempla fundações especiais, elevadores, urbanização e BDI."
}
```

---

### `GET /v1/calc/fatores`
- **Nome:** Catálogo Normativo de Coeficientes de Equivalência de Custo

#### 🎯 Dor de Negócio que Resolve
Engenheiros orçamentistas e desenvolvedores de sistemas de ERP muitas vezes não têm acesso fácil aos coeficientes tabelados pela ABNT ou usam valores empíricos arbitrários que podem ser contestados em juízo ou pelo cartório de registro de imóveis. Este endpoint entrega a tabela oficial com o coeficiente padrão e a faixa recomendada pela norma para cada tipologia de ambiente.

#### 📤 Exemplo de Resposta
```json
{
  "norma": "ABNT NBR 12.721:2006 — Quadro II",
  "descricao": "Coeficientes canônicos para cálculo da Área Equivalente de Construção.",
  "fatores": [
    {
      "tipo_ambiente": "Área Privativa Principal (Apartamento / Sala / Casa)",
      "fator_padrao": 1.00,
      "faixa_recomendada": "1.00",
      "descricao": "Área de vivência principal coberta com padrão de acabamento integral da unidade."
    },
    {
      "tipo_ambiente": "Garagem Coberta (Subsolo)",
      "fator_padrao": 0.65,
      "faixa_recomendada": "0.50 a 0.75",
      "descricao": "Estrutura e alvenaria simples, pisos industriais ou cimentados, sem acabamentos nobres."
    },
    {
      "tipo_ambiente": "Garagem Descoberta / Estacionamento",
      "fator_padrao": 0.12,
      "faixa_recomendada": "0.10 a 0.20",
      "descricao": "Pavimentação asfáltica, blocos intertravados ou brita sobre solo natural."
    },
    {
      "tipo_ambiente": "Varanda / Sacada Coberta",
      "fator_padrao": 0.50,
      "faixa_recomendada": "0.50 a 0.75",
      "descricao": "Área com fechamento parcial de alvenaria e guarda-corpo."
    },
    {
      "tipo_ambiente": "Terraço / Lazer Descoberto",
      "fator_padrao": 0.30,
      "faixa_recomendada": "0.30 a 0.60",
      "descricao": "Impermeabilização e pisos resistentes a intempéries sem cobertura."
    },
    {
      "tipo_ambiente": "Pilotis / Área de Recreação Coberta",
      "fator_padrao": 0.40,
      "faixa_recomendada": "0.30 a 0.50",
      "descricao": "Pavimento aberto sob pilotis com pilares e pisos comuns."
    }
  ]
}
```

---

## 2. CUB / Custo Unitário Básico

### `GET /v1/cub/br`
- **Nome:** CUB Médio Brasil Oficial Ponderado (21 Capitais)
- **Metodologia:** Fórmula Oficial CBIC / Quadro I e II da Cartilha "Saiba Mais CUB"

#### 🎯 Dor de Negócio que Resolve
O Brasil não tem um custo unitário básico simples nacional. Cada estado tem seu CUB calculado pelo respectivo sindicato. A CBIC sintetiza o indicador nacional calculando uma média ponderada das 21 capitais participantes, ponderadas pelo peso econômico de cada praça (baseado no número de empregados da construção e consumo de cimento).  
Calcular isso manualmente exigia baixar 21 relatórios todo mês, encontrar os projetos representativos e cruzar com os pesos. Este endpoint faz todo esse processamento instantaneamente e com cache de 24h.

#### 📥 Parâmetros Query
- `ano` (int, opcional): Ano de referência (ex: `2026`).
- `mes` (int, opcional): Mês de referência (ex: `8`).
- `desoneracao` (str, opcional, default: `SEM_DESONERACAO`): Regime tributário.

#### 📤 Exemplo de Resposta
```json
{
  "data_referencia": "2026-08-01",
  "desoneracao": "SEM_DESONERACAO",
  "cub_medio_brasil": 2247.85,
  "total_estados_ponderados": 21,
  "soma_pesos": 100.00,
  "por_regiao": {
    "SUDESTE": 2315.40,
    "SUL": 2290.15,
    "CENTRO-OESTE": 2185.30,
    "NORDESTE": 2045.60,
    "NORTE": 2110.20
  },
  "estados": [
    {
      "uf": "SP",
      "sinduscon_nome": "SindusCon-SP",
      "regiao": "SUDESTE",
      "projeto_representativo": "R8-N",
      "peso_relativo": 32.50,
      "valor_m2": 2380.50,
      "participacao_efetiva_pct": 32.50
    },
    {
      "uf": "GO",
      "sinduscon_nome": "SINDUSCON-GO",
      "regiao": "CENTRO-OESTE",
      "projeto_representativo": "R8-N",
      "peso_relativo": 3.40,
      "valor_m2": 2623.20,
      "participacao_efetiva_pct": 3.40
    }
  ]
}
```

---

### `GET /v1/cub/latest`
- **Nome:** Cotações Mais Recentes Consolidadas com Origem Territorial

#### 🎯 Dor de Negócio que Resolve
Muitos sistemas exibem apenas o valor financeiro do CUB sem vincular à UF ou à entidade de origem, gerando erros onde o CUB de uma capital é aplicado a outro estado. Este endpoint retorna o lote vigente mais recente com identificação explícita de `uf`, `sinduscon_id`, `sinduscon_nome` e `regiao`.

#### 📥 Parâmetros Query
- `uf` (str, opcional): Filtrar por sigla da UF (ex: `GO`). Se omitido, lista todas as UFs ativas do país.
- `desoneracao` (str, opcional): `SEM_DESONERACAO` ou `COM_DESONERACAO`.

---

### `GET /v1/cub/{uf}/dash` *(alias `/panorama`)*
- **Nome:** Painel Analítico Consolidado e Agrupamentos NBR da UF

#### 🎯 Dor de Negócio que Resolve
Em vez de um frontend ou aplicativo cliente disparar 19 requisições diferentes para entender os custos de um estado, o `/dash` pré-calcula em lote as médias por categoria (Residencial, Comercial, Especial), identifica os extremos (projeto mais caro e mais barato da praça, maior alta mensal e maior queda) e entrega a árvore estruturada por padrão de acabamento (Baixo, Normal, Alto). Com cache Redis, a resposta é entregue em menos de 1 milissegundo.

#### 📥 Parâmetros Path & Query
- `uf` (path, obrigatório): Sigla do estado (ex: `GO`, `MG`, `RJ`).
- `ano` (int, opcional), `mes` (int, opcional), `desoneracao` (str, opcional), `sinduscon_id` (int, opcional).

---

### `GET /v1/cub/{uf}/deson` *(alias `/impacto-desoneracao`)*
- **Nome:** Análise de Impacto Tributário da CPRB (Economia Real em R$/m²)

#### 🎯 Dor de Negócio que Resolve
A Lei Federal nº 12.546/2011 instituiu a Desoneração da Folha de Pagamento (CPRB), que reduz a contribuição previdenciária patronal sobre os trabalhadores da construção civil. No entanto, o benefício financeiro varia de acordo com o padrão construtivo: obras de padrão baixo (que usam mão de obra mais intensiva) têm uma economia percentual diferente de obras de padrão alto.  
Este endpoint cruza as séries **COM** e **SEM** desoneração no mesmo mês e entrega a **economia real em R$/m²** e a **economia percentual** para cada um dos 19 projetos, permitindo avaliar se a opção tributária da construtora é vantajosa.

---

### `GET /v1/cub/rank` *(alias `/ranking`)*
- **Nome:** Ranking Nacional de Estados por Projeto-Padrão

#### 🎯 Dor de Negócio que Resolve
Permite benchmarking geográfico instantâneo. Mostra quais estados estão acima ou abaixo da média nacional para um determinado projeto (ex: `R8-N`), indicando o desvio relativo (`desvio_media_pct`). Útil para investidores decidirem onde alocar capital imobiliário com menor custo de construção.

#### 📥 Parâmetros Query
- `codigo_padrao` (str, default: `R1-N`): Código normativo (ex: `R8-N`, `GI`, `CSL-8-N`).
- `ano`, `mes`, `desoneracao`.

---

### `GET /v1/cub/{uf}/hist/{codigo_padrao}` *(alias `/historico`)*
- **Nome:** Série Histórica e Inflação Setorial Acumulada

#### 🎯 Dor de Negócio que Resolve
Contratos de construção civil utilizam o CUB como indexador oficial durante a fase de obras (súmula pacificada pelo STJ). Calcular a inflação acumulada de 12 ou 24 meses manualmente para emitir notas fiscais ou reajustar parcelas de financiamento direto gera erros humanos frequentes.  
Este endpoint devolve a série cronológica completa e calcula a **variação acumulada total no período** (`variacao_acumulada_periodo_pct`), além da variação média mensal e dos valores extremos (mínimo e máximo).

---

### `GET /v1/cub/comp` *(alias `/comparativo`)*
- **Nome:** Comparativo Regional de Custos Entre Múltiplos Estados

#### 🎯 Dor de Negócio que Resolve
Permite a incorporadoras multinacionais e orçamentistas corporativos comparar simultaneamente até 27 estados para o mesmo projeto-padrão (ex: `ufs=GO,DF,MG,SP,PR&codigo_padrao=R8-N`) em uma única chamada de rede, calculando a média do grupo e o desvio relativo de cada praça.

---

### `GET /v1/cub/{uf}`
- **Nome:** Consulta Bruta das Cotações de um Estado

#### 🎯 Dor de Negócio que Resolve
Ponto de entrada flexível e sem agregação analítica, retornando a lista dos 19 projetos da UF especificada no mês/ano e regime tributário selecionados.

---

## 3. Base de Conhecimento Perene & Normas

A NBR 12.721:2006 e a Lei 4.591/1964 possuem regras imutáveis que não mudam a cada mês. Em vez de onerar o banco relacional, essas informações são servidas por adapters documentais (`cbic_booklet_v1`) com cache de 7 dias:

### `GET /v1/kb/faq`
- **Dor que resolve:** Disputas orçamentárias e jurídicas sobre o que o CUB cobre. Lista os **8 itens expressamente excluídos do CUB** pelo Item 8.3.5 da NBR 12.721:
  1. Fundações especiais e obras de terraplenagem;
  2. Elevadores e escadas rolantes;
  3. Instalações de ar condicionado, calefação e ventilação mecânica;
  4. Obras de urbanização, ajardinamento e áreas de lazer;
  5. Projetos arquitetônicos e de engenharia;
  6. Terreno e despesas de escritura/registro;
  7. Impostos e taxas públicas;
  8. Lucro da construtora e BDI (Benefícios e Despesas Indiretas).

### `GET /v1/kb/insumos`
- **Dor que resolve:** Transparência sobre como o índice é formado. Retorna a cesta dos **29 insumos-padrão** da NBR 12.721:2006 (25 materiais de construção, 2 categorias de mão de obra — pedreiro e servente, 1 despesa administrativa — engenheiro civil, e 1 equipamento — betoneira) com suas respectivas participações percentuais médias.

### `GET /v1/kb/lei`
- **Dor que resolve:** Segurança jurídica em contratos de compra e venda na planta. Explica a base legal dos Artigos 53, 54 e 55 da Lei Federal 4.591/1964, a obrigatoriedade dos sindicatos divulgarem o índice até o 5º dia do mês subsequente, e a **jurisprudência vinculante do STJ** que veda a incidência de reajuste pelo CUB após o habite-se e entrega das chaves da obra.

### `GET /v1/kb/nbr`
- **Dor que resolve:** Consulta canônica aos fatores normativos de equivalência de custo e instruções de cálculo segundo o Quadro II da norma.

---

## 4. Metadados & Padrões Construtivos

### `GET /v1/sinduscons`
- **Dor que resolve:** Identificação exata da autoridade patronal regional competente. Lista os 28 sindicatos cadastrados com seu ID oficial adotado pelo portal central da CBIC.
- **Filtros:** `uf`, `regiao`, `ativo_apenas`.

### `GET /v1/padroes`
- **Dor que resolve:** Dúvidas sobre o enquadramento de projetos na norma. Lista os 19 projetos-padrão normatizados divididos em:
  - **Residenciais:** Casa Unifamiliar (`R1-B`, `R1-N`, `R1-A`), Prédio Popular (`PP-4-B`, `PP-4-N`), Residência Multifamiliar (`R8-B`, `R8-N`, `R8-A`, `R16-N`, `R16-A`), Projeto de Interesse Social (`PIS`).
  - **Comerciais:** Comercial Andar Livre (`CAL-8-N`, `CAL-8-A`), Comercial Salas e Lojas (`CSL-8-N`, `CSL-8-A`, `CSL-16-N`, `CSL-16-A`).
  - **Especiais:** Galpão Industrial (`GI`), Residência Popular Unifamiliar (`RP1Q`).

### `GET /v1/padroes/{codigo}`
- **Dor que resolve:** Consulta detalhada à ficha técnica arquitetônica de um projeto (número de pavimentos, quantidade de dormitórios, vagas de garagem, área real e área equivalente de projeto).

---

## 5. Administração & Auditoria Forense do ETL

### `POST /v1/admin/etl/trigger`
- **Dor que resolve:** Automatiza a coleta descentralizada de dezenas de relatórios PDF com governança ética.
- **Mecanismos de Segurança:**
  - **Sanitização Temporal Estrita:** Rejeita requisições de anos futuros ou meses além do último período publicado pela CBIC (regra do 5º dia útil / Lei 4.591/64).
  - **Descoberta Dinâmica de IDs:** Valida se a UF solicitada é suportada pela CBIC central e resolve dinamicamente IDs com suporte a federações descentralizadas.
  - **Execução Híbrida:** Em produção, enfileira tarefas no Celery/Redis; em ambiente de desenvolvimento, opera via `BackgroundTasks` assíncronas do FastAPI.

### `GET /v1/admin/etl/logs`
- **Dor que resolve:** Falta de rastreabilidade sobre a integridade dos dados históricos. Permite que administradores auditem cada execução, identificando duração em milissegundos, quantidade de registros gravados, status (`SUCESSO`, `FALHA`, `CACHE_LOCAL`, `NAO_SUPORTADO_CBIC`) e eventuais mensagens de erro de rede ou de parser.

---

## 6. Health Check & Monitoramento

### `GET /health` e `GET /v1/health`
- **Dor que resolve:** Monitoramento de integridade e readiness probes para orquestradores (Kubernetes, Docker Compose, Traefik). Verifica ativamente a conectividade com o banco de dados PostgreSQL e informa o status operacional do serviço.

---

## 💡 Resumo das Rotas e Aliases Byte-Saving

| Rota Canônica (Curta / Byte-Saving) | Alias Descritivo (Retrocompatibilidade) | Objetivo Principal |
|---|---|---|
| `POST /v1/calc/area` | — | Cálculo de Área Equivalente e Orçamento Estimativo (NBR 12.721) |
| `GET /v1/calc/fatores` | — | Coeficientes normativos do Quadro II da NBR 12.721 |
| `GET /v1/cub/br` | — | CUB Médio Brasil Oficial ponderado (21 capitais) |
| `GET /v1/cub/latest` | — | Cotações vigentes com identificação territorial de origem |
| `GET /v1/cub/{uf}/dash` | `GET /v1/cub/{uf}/panorama` | Painel analítico consolidado e agrupamentos NBR por categoria |
| `GET /v1/cub/{uf}/deson` | `GET /v1/cub/{uf}/impacto-desoneracao` | Economia em R$/m² da desoneração da folha de pagamento |
| `GET /v1/cub/rank` | `GET /v1/cub/ranking` | Ranking nacional de estados por projeto-padrão |
| `GET /v1/cub/{uf}/hist/{cod}` | `GET /v1/cub/{uf}/historico/{cod}` | Série temporal e inflação acumulada do período |
| `GET /v1/cub/comp` | `GET /v1/cub/comparativo` | Comparativo regional de custos entre múltiplos estados |
| `GET /v1/cub/{uf}` | — | Cotações brutas de uma UF por período e regime |
| `GET /v1/kb/faq` | — | FAQ oficial e lista dos 8 itens excluídos do CUB |
| `GET /v1/kb/insumos` | — | Cesta dos 29 insumos-padrão e 4 famílias da NBR 12.721 |
| `GET /v1/kb/lei` | — | Lei Federal 4.591/1964 e súmulas vinculantes do STJ |
| `GET /v1/kb/nbr` | — | Fatores canônicos de ponderação de custo e instruções de uso |
| `GET /v1/sinduscons` | — | Catálogo dos 28 sindicatos com IDs canônicos da CBIC |
| `GET /v1/padroes` | — | Catálogo dos 19 projetos-padrão normalizados |
| `GET /v1/padroes/{codigo}` | — | Ficha técnica detalhada de um projeto específico |
| `POST /v1/admin/etl/trigger` | — | Disparo assíncrono do pipeline ETL ético e progressivo |
| `GET /v1/admin/etl/logs` | — | Logs de auditoria forense das execuções do ETL |
| `GET /health` | `GET /v1/health` | Verificação de integridade da API e do banco PostgreSQL |
