from decimal import Decimal
from sqlalchemy.orm import Session
from autocub.database.models import PadraoProjeto, Sinduscon, PesoCubBrasil
from autocub.core.logging import logger

PADROES_NBR12721 = [
    # Residencial Baixo
    {
        "codigo": "R1-B",
        "codigo_base": "R-1",
        "nome": "Residência Unifamiliar - Padrão Baixo",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "BAIXO",
        "pavimentos": 1,
        "area_real": Decimal("58.64"),
        "area_equivalente": Decimal("51.94"),
        "dormitorios": 2,
        "vagas_garagem": 0,
        "elevadores": 0,
        "descricao": "1 pavimento, com 2 dormitórios, sala, banheiro, cozinha e área para tanque."
    },
    {
        "codigo": "PP-4-B",
        "codigo_base": "PP-4",
        "nome": "Prédio Popular - Padrão Baixo",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "BAIXO",
        "pavimentos": 4,
        "area_real": Decimal("1415.07"),
        "area_equivalente": Decimal("927.08"),
        "dormitorios": 2,
        "vagas_garagem": 16,
        "elevadores": 0,
        "descricao": "Térreo e 3 pavimentos-tipo com 4 aptos/andar (2 dorms, sala, banho, cozinha, serviço). 16 vagas descobertas."
    },
    {
        "codigo": "R8-B",
        "codigo_base": "R-8",
        "nome": "Residencial Multifamiliar - Padrão Baixo",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "BAIXO",
        "pavimentos": 8,
        "area_real": Decimal("2801.64"),
        "area_equivalente": Decimal("1885.51"),
        "dormitorios": 2,
        "vagas_garagem": 32,
        "elevadores": 1,
        "descricao": "Térreo e 7 pavimentos-tipo com 4 aptos/andar (2 dorms, sala, banho, cozinha, tanque). Elevador e 32 vagas descobertas."
    },
    {
        "codigo": "PIS",
        "codigo_base": "PIS",
        "nome": "Projeto de Interesse Social",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "BAIXO",
        "pavimentos": 5,
        "area_real": Decimal("991.45"),
        "area_equivalente": Decimal("978.09"),
        "dormitorios": 2,
        "vagas_garagem": 0,
        "elevadores": 0,
        "descricao": "Térreo e 4 pavimentos-tipo com 4 aptos/andar (2 dormitórios, sala, banheiro, cozinha e área de serviço)."
    },
    # Residencial Normal
    {
        "codigo": "R1-N",
        "codigo_base": "R-1",
        "nome": "Residência Unifamiliar - Padrão Normal",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 1,
        "area_real": Decimal("106.44"),
        "area_equivalente": Decimal("99.47"),
        "dormitorios": 3,
        "vagas_garagem": 1,
        "elevadores": 0,
        "descricao": "1 pavimento, 3 dormitórios (1 suíte), banheiro social, sala, cozinha, serviço com banheiro e varanda/abrigo."
    },
    {
        "codigo": "PP-4-N",
        "codigo_base": "PP-4",
        "nome": "Prédio Popular - Padrão Normal",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 5,
        "area_real": Decimal("2590.35"),
        "area_equivalente": Decimal("1840.45"),
        "dormitorios": 3,
        "vagas_garagem": 32,
        "elevadores": 1,
        "descricao": "Pilotis e 4 pavimentos-tipo (4 aptos/andar com 3 dorms/1 suíte, sala estar/jantar, varanda). 32 vagas cobertas, elevador e salão."
    },
    {
        "codigo": "R8-N",
        "codigo_base": "R-8",
        "nome": "Residencial Multifamiliar - Padrão Normal",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 10,
        "area_real": Decimal("5998.73"),
        "area_equivalente": Decimal("4135.22"),
        "dormitorios": 3,
        "vagas_garagem": 64,
        "elevadores": 2,
        "descricao": "Garagem (64 vagas), pilotis (salão de festas) e 8 pavimentos-tipo (4 aptos/andar com 3 dorms/1 suíte). 2 elevadores."
    },
    {
        "codigo": "R16-N",
        "codigo_base": "R-16",
        "nome": "Residencial Multifamiliar - Padrão Normal (16 pav.)",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 18,
        "area_real": Decimal("10562.07"),
        "area_equivalente": Decimal("8224.50"),
        "dormitorios": 3,
        "vagas_garagem": 128,
        "elevadores": 3,
        "descricao": "Garagem (128 vagas), pilotis e 16 pavimentos-tipo (4 aptos/andar com 3 dorms/1 suíte, sala estar/jantar). Elevadores."
    },
    # Residencial Alto
    {
        "codigo": "R1-A",
        "codigo_base": "R-1",
        "nome": "Residência Unifamiliar - Padrão Alto",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 1,
        "area_real": Decimal("224.82"),
        "area_equivalente": Decimal("210.44"),
        "dormitorios": 4,
        "vagas_garagem": 2,
        "elevadores": 0,
        "descricao": "1 pavimento, 4 dormitórios (2 suítes, closet), sala de estar, jantar e íntima, cozinha, serviço completa e varanda/abrigo."
    },
    {
        "codigo": "R8-A",
        "codigo_base": "R-8",
        "nome": "Residencial Multifamiliar - Padrão Alto",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 10,
        "area_real": Decimal("5917.79"),
        "area_equivalente": Decimal("4644.79"),
        "dormitorios": 4,
        "vagas_garagem": 48,
        "elevadores": 2,
        "descricao": "Garagem (48 vagas), pilotis (festas, jogos) e 8 pavimentos-tipo (2 aptos/andar com 4 dorms/2 suítes). Padrão Alto."
    },
    {
        "codigo": "R16-A",
        "codigo_base": "R-16",
        "nome": "Residencial Multifamiliar - Padrão Alto (16 pav.)",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 18,
        "area_real": Decimal("10461.85"),
        "area_equivalente": Decimal("8371.40"),
        "dormitorios": 4,
        "vagas_garagem": 96,
        "elevadores": 3,
        "descricao": "Garagem (96 vagas), pilotis (festas, jogos) e 16 pavimentos-tipo (2 aptos/andar com 4 dorms/2 suítes). Padrão Alto."
    },
    # Comercial Normal
    {
        "codigo": "CAL-8-N",
        "codigo_base": "CAL-8",
        "nome": "Comercial Andar Livre - Padrão Normal",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 10,
        "area_real": Decimal("5290.62"),
        "area_equivalente": Decimal("3096.09"),
        "dormitorios": 0,
        "vagas_garagem": 64,
        "elevadores": 2,
        "descricao": "Garagem (64 vagas), pavimento térreo com lojas e 8 pavimentos-tipo com andares livres corridos. Padrão Normal."
    },
    {
        "codigo": "CSL-8-N",
        "codigo_base": "CSL-8",
        "nome": "Comercial Salas e Lojas - Padrão Normal (8 pav.)",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 10,
        "area_real": Decimal("5942.94"),
        "area_equivalente": Decimal("3921.55"),
        "dormitorios": 0,
        "vagas_garagem": 64,
        "elevadores": 2,
        "descricao": "Garagem (64 vagas), pavimento térreo com lojas e 8 pavimentos-tipo com 8 salas comerciais por andar. Padrão Normal."
    },
    {
        "codigo": "CSL-16-N",
        "codigo_base": "CSL-16",
        "nome": "Comercial Salas e Lojas - Padrão Normal (16 pav.)",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 18,
        "area_real": Decimal("9140.57"),
        "area_equivalente": Decimal("5734.46"),
        "dormitorios": 0,
        "vagas_garagem": 128,
        "elevadores": 3,
        "descricao": "Garagem (128 vagas), pavimento térreo com lojas e 16 pavimentos-tipo com 8 salas comerciais por andar. Padrão Normal."
    },
    # Comercial Alto
    {
        "codigo": "CAL-8-A",
        "codigo_base": "CAL-8",
        "nome": "Comercial Andar Livre - Padrão Alto",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 10,
        "area_real": Decimal("5290.62"),
        "area_equivalente": Decimal("3096.09"),
        "dormitorios": 0,
        "vagas_garagem": 64,
        "elevadores": 2,
        "descricao": "Garagem (64 vagas), térreo com lojas e 8 pavimentos-tipo com andares livres corridos. Acabamento Padrão Alto."
    },
    {
        "codigo": "CSL-8-A",
        "codigo_base": "CSL-8",
        "nome": "Comercial Salas e Lojas - Padrão Alto (8 pav.)",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 10,
        "area_real": Decimal("5942.94"),
        "area_equivalente": Decimal("3921.55"),
        "dormitorios": 0,
        "vagas_garagem": 64,
        "elevadores": 2,
        "descricao": "Garagem (64 vagas), térreo com lojas e 8 pavimentos-tipo com 8 salas com sanitário privativo. Padrão Alto."
    },
    {
        "codigo": "CSL-16-A",
        "codigo_base": "CSL-16",
        "nome": "Comercial Salas e Lojas - Padrão Alto (16 pav.)",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 18,
        "area_real": Decimal("9140.57"),
        "area_equivalente": Decimal("5734.46"),
        "dormitorios": 0,
        "vagas_garagem": 128,
        "elevadores": 3,
        "descricao": "Garagem (128 vagas), térreo com lojas e 16 pavimentos-tipo com 8 salas com sanitário privativo. Padrão Alto."
    },
    # Projetos Especiais
    {
        "codigo": "RP1Q",
        "codigo_base": "RP1Q",
        "nome": "Residência Popular (1 Quarto)",
        "categoria": "ESPECIAL",
        "padrao_acabamento": "UNICO",
        "pavimentos": 1,
        "area_real": Decimal("39.56"),
        "area_equivalente": Decimal("39.56"),
        "dormitorios": 1,
        "vagas_garagem": 0,
        "elevadores": 0,
        "descricao": "Residência unifamiliar popular térrea: 1 dormitório, sala, banheiro e cozinha."
    },
    {
        "codigo": "GI",
        "codigo_base": "GI",
        "nome": "Galpão Industrial",
        "categoria": "ESPECIAL",
        "padrao_acabamento": "UNICO",
        "pavimentos": 1,
        "area_real": Decimal("1000.00"),
        "area_equivalente": Decimal("1000.00"),
        "dormitorios": 0,
        "vagas_garagem": 0,
        "elevadores": 0,
        "descricao": "Galpão industrial com área fabril, área administrativa, 2 banheiros, vestiário e depósito."
    }
]

SINDUSCONS_CATALOGO = [
    # Centro-Oeste
    {"id": 8, "uf": "DF", "nome": "Sinduscon-DF", "regiao": "CENTRO-OESTE"},
    {"id": 10, "uf": "GO", "nome": "Sinduscon-GO", "regiao": "CENTRO-OESTE"},
    {"id": 13, "uf": "MT", "nome": "Sinduscon-MT", "regiao": "CENTRO-OESTE"},
    # Sudeste
    {"id": 1, "uf": "MG", "nome": "Sinduscon-MG", "regiao": "SUDESTE"},
    {"id": 32, "uf": "MG", "nome": "Sinduscon-Juiz de Fora", "regiao": "SUDESTE"},
    {"id": 33, "uf": "MG", "nome": "Sinduscon-Vale do Piranga", "regiao": "SUDESTE"},
    {"id": 34, "uf": "MG", "nome": "Sinduscon-Lagos", "regiao": "SUDESTE"},
    {"id": 36, "uf": "MG", "nome": "Sinduscon Norte", "regiao": "SUDESTE"},
    {"id": 39, "uf": "MG", "nome": "Sinduscon-GV", "regiao": "SUDESTE"},
    {"id": 9, "uf": "ES", "nome": "Sinduscon-ES", "regiao": "SUDESTE"},
    {"id": 20, "uf": "RJ", "nome": "Sinduscon-Rio", "regiao": "SUDESTE"},
    # Sul
    {"id": 18, "uf": "PR", "nome": "Sinduscon-PR", "regiao": "SUL"},
    {"id": 19, "uf": "PR", "nome": "Sinduscon-Noroeste-PR", "regiao": "SUL"},
    {"id": 38, "uf": "PR", "nome": "Sinduscon-Oeste-PR", "regiao": "SUL"},
    {"id": 26, "uf": "SC", "nome": "Sinduscon Grande Florianópolis-SC", "regiao": "SUL"},
    # Nordeste
    {"id": 6, "uf": "BA", "nome": "Sinduscon-BA", "regiao": "NORDESTE"},
    {"id": 7, "uf": "CE", "nome": "Sinduscon-CE", "regiao": "NORDESTE"},
    {"id": 11, "uf": "MA", "nome": "Sinduscon-MA", "regiao": "NORDESTE"},
    {"id": 15, "uf": "PB", "nome": "Sinduscon-João Pessoa", "regiao": "NORDESTE"},
    {"id": 16, "uf": "PE", "nome": "Sinduscon-PE", "regiao": "NORDESTE"},
    {"id": 17, "uf": "PI", "nome": "Sinduscon-Teresina", "regiao": "NORDESTE"},
    {"id": 21, "uf": "RN", "nome": "Sinduscon-RN", "regiao": "NORDESTE"},
    {"id": 22, "uf": "SE", "nome": "Sinduscon-SE", "regiao": "NORDESTE"},
    # Norte
    {"id": 4, "uf": "AC", "nome": "Sinduscon-AC", "regiao": "NORTE"},
    {"id": 5, "uf": "AM", "nome": "Sinduscon-AM", "regiao": "NORTE"},
    {"id": 14, "uf": "PA", "nome": "Sinduscon-PA", "regiao": "NORTE"},
    {"id": 25, "uf": "RO", "nome": "Sinduscon-RO", "regiao": "NORTE"},
    {"id": 30, "uf": "RR", "nome": "Sinduscon-RR", "regiao": "NORTE"},
]


# Ponderações Oficiais do CUB Médio Brasil (CBIC / Quadro I e II)
PESOS_CUB_BRASIL = [
    {"uf": "SP", "sinduscon_nome": "Sinduscon São Paulo", "regiao": "SUDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("25.3184")},
    {"uf": "PR", "sinduscon_nome": "Sinduscon Paraná", "regiao": "SUL", "projeto_representativo": "R8-N", "peso_relativo": Decimal("6.9763")},
    {"uf": "MG", "sinduscon_nome": "Sinduscon Minas Gerais", "regiao": "SUDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("6.5100")},
    {"uf": "RS", "sinduscon_nome": "Sinduscon Rio Grande do Sul", "regiao": "SUL", "projeto_representativo": "R8-N", "peso_relativo": Decimal("6.3787")},
    {"uf": "DF", "sinduscon_nome": "Sinduscon Distrito Federal", "regiao": "CENTRO-OESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("5.5426")},
    {"uf": "RJ", "sinduscon_nome": "Sinduscon Rio de Janeiro", "regiao": "SUDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("5.4616")},
    {"uf": "BA", "sinduscon_nome": "Sinduscon Bahia", "regiao": "NORDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("5.4549")},
    {"uf": "GO", "sinduscon_nome": "Sinduscon Goiás", "regiao": "CENTRO-OESTE", "projeto_representativo": "R16-A", "peso_relativo": Decimal("3.7331")},
    {"uf": "CE", "sinduscon_nome": "Sinduscon Ceará", "regiao": "NORDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("3.3455")},
    {"uf": "MS", "sinduscon_nome": "Sinduscon Mato Grosso do Sul", "regiao": "CENTRO-OESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("3.0031")},
    {"uf": "AM", "sinduscon_nome": "Sinduscon Amazonas", "regiao": "NORTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("2.0515")},
    {"uf": "MT", "sinduscon_nome": "Sinduscon Mato Grosso", "regiao": "CENTRO-OESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("2.0378")},
    {"uf": "SC", "sinduscon_nome": "Sinduscon Grande Florianópolis-SC", "regiao": "SUL", "projeto_representativo": "R8-N", "peso_relativo": Decimal("2.0378")},
    {"uf": "RO", "sinduscon_nome": "Sinduscon Rondônia", "regiao": "NORTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("2.0378")},
    {"uf": "MA", "sinduscon_nome": "Sinduscon Maranhão", "regiao": "NORDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("2.0378")},
    {"uf": "PE", "sinduscon_nome": "Sinduscon Pernambuco", "regiao": "NORDESTE", "projeto_representativo": "R16-N", "peso_relativo": Decimal("1.9903")},
    {"uf": "AL", "sinduscon_nome": "Sinduscon Alagoas", "regiao": "NORDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("1.8991")},
    {"uf": "PB", "sinduscon_nome": "Sinduscon João Pessoa-PB", "regiao": "NORDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("1.4549")},
    {"uf": "SE", "sinduscon_nome": "Sinduscon Sergipe", "regiao": "NORDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("1.4493")},
    {"uf": "ES", "sinduscon_nome": "Sinduscon Espírito Santo", "regiao": "SUDESTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("0.9668")},
    {"uf": "PA", "sinduscon_nome": "Sinduscon Pará", "regiao": "NORTE", "projeto_representativo": "R8-N", "peso_relativo": Decimal("0.8791")},
]


def seed_database(db: Session) -> None:
    """Popula os metadados perenes no banco de dados com idempotência total."""
    # 1. Padrões NBR 12.721:2006
    for item in PADROES_NBR12721:
        padrao = db.query(PadraoProjeto).filter(PadraoProjeto.codigo == item["codigo"]).first()
        if not padrao:
            db.add(PadraoProjeto(**item))
        else:
            for k, v in item.items():
                setattr(padrao, k, v)

    # 2. Sinduscons
    for item in SINDUSCONS_CATALOGO:
        sind = db.query(Sinduscon).filter(Sinduscon.id == item["id"]).first()
        if not sind:
            db.add(Sinduscon(**item))
        else:
            for k, v in item.items():
                setattr(sind, k, v)

    # 3. Ponderações Oficiais CUB Brasil
    for item in PESOS_CUB_BRASIL:
        peso = db.query(PesoCubBrasil).filter(PesoCubBrasil.uf == item["uf"]).first()
        if not peso:
            db.add(PesoCubBrasil(**item))
        else:
            for k, v in item.items():
                setattr(peso, k, v)

    db.commit()
    logger.info("Sementes de Padrões NBR, Sinduscons e Pesos CUB Brasil sincronizadas com sucesso.")

seed_initial_data = seed_database

