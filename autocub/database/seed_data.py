from sqlalchemy.orm import Session
from autocub.database.models import PadraoProjeto, Sinduscon
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
        "descricao": "Residência unifamiliar térrea, 1 pavimento, padrão de acabamento baixo."
    },
    {
        "codigo": "PP-4-B",
        "codigo_base": "PP-4",
        "nome": "Prédio Popular - Padrão Baixo",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "BAIXO",
        "pavimentos": 4,
        "descricao": "Prédio residencial multifamiliar de 4 pavimentos, padrão baixo."
    },
    {
        "codigo": "R8-B",
        "codigo_base": "R-8",
        "nome": "Residencial Multifamiliar - Padrão Baixo",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "BAIXO",
        "pavimentos": 8,
        "descricao": "Prédio residencial multifamiliar de 8 pavimentos, padrão baixo."
    },
    {
        "codigo": "PIS",
        "codigo_base": "PIS",
        "nome": "Projeto de Interesse Social",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "BAIXO",
        "pavimentos": 1,
        "descricao": "Habitação popular unifamiliar de interesse social."
    },
    # Residencial Normal
    {
        "codigo": "R1-N",
        "codigo_base": "R-1",
        "nome": "Residência Unifamiliar - Padrão Normal",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 1,
        "descricao": "Residência unifamiliar térrea, 1 pavimento, padrão normal de acabamento."
    },
    {
        "codigo": "PP-4-N",
        "codigo_base": "PP-4",
        "nome": "Prédio Popular - Padrão Normal",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 4,
        "descricao": "Prédio residencial multifamiliar de 4 pavimentos, padrão normal."
    },
    {
        "codigo": "R8-N",
        "codigo_base": "R-8",
        "nome": "Residencial Multifamiliar - Padrão Normal",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 8,
        "descricao": "Prédio residencial multifamiliar de 8 pavimentos, padrão normal."
    },
    {
        "codigo": "R16-N",
        "codigo_base": "R-16",
        "nome": "Residencial Multifamiliar - Padrão Normal (16 pav.)",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 16,
        "descricao": "Prédio residencial multifamiliar de 16 pavimentos, padrão normal."
    },
    # Residencial Alto
    {
        "codigo": "R1-A",
        "codigo_base": "R-1",
        "nome": "Residência Unifamiliar - Padrão Alto",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 1,
        "descricao": "Residência unifamiliar térrea, 1 pavimento, padrão alto de acabamento."
    },
    {
        "codigo": "R8-A",
        "codigo_base": "R-8",
        "nome": "Residencial Multifamiliar - Padrão Alto",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 8,
        "descricao": "Prédio residencial multifamiliar de 8 pavimentos, padrão alto."
    },
    {
        "codigo": "R16-A",
        "codigo_base": "R-16",
        "nome": "Residencial Multifamiliar - Padrão Alto (16 pav.)",
        "categoria": "RESIDENCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 16,
        "descricao": "Prédio residencial multifamiliar de 16 pavimentos, padrão alto."
    },
    # Comercial Normal
    {
        "codigo": "CAL-8-N",
        "codigo_base": "CAL-8",
        "nome": "Comercial Andar Livre - Padrão Normal",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 8,
        "descricao": "Edifício comercial com pavimentos de andar livre (vãos abertos), padrão normal."
    },
    {
        "codigo": "CSL-8-N",
        "codigo_base": "CSL-8",
        "nome": "Comercial Salas e Lojas - Padrão Normal (8 pav.)",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 8,
        "descricao": "Edifício comercial com lojas no térreo e salas nos pavimentos tipo, padrão normal."
    },
    {
        "codigo": "CSL-16-N",
        "codigo_base": "CSL-16",
        "nome": "Comercial Salas e Lojas - Padrão Normal (16 pav.)",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "NORMAL",
        "pavimentos": 16,
        "descricao": "Edifício comercial com lojas e salas, 16 pavimentos, padrão normal."
    },
    # Comercial Alto
    {
        "codigo": "CAL-8-A",
        "codigo_base": "CAL-8",
        "nome": "Comercial Andar Livre - Padrão Alto",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 8,
        "descricao": "Edifício comercial com pavimentos de andar livre, padrão alto."
    },
    {
        "codigo": "CSL-8-A",
        "codigo_base": "CSL-8",
        "nome": "Comercial Salas e Lojas - Padrão Alto (8 pav.)",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 8,
        "descricao": "Edifício comercial com lojas e salas, 8 pavimentos, padrão alto."
    },
    {
        "codigo": "CSL-16-A",
        "codigo_base": "CSL-16",
        "nome": "Comercial Salas e Lojas - Padrão Alto (16 pav.)",
        "categoria": "COMERCIAL",
        "padrao_acabamento": "ALTO",
        "pavimentos": 16,
        "descricao": "Edifício comercial com lojas e salas, 16 pavimentos, padrão alto."
    },
    # Especial / Galpão & Residência Popular
    {
        "codigo": "RP1Q",
        "codigo_base": "RP1Q",
        "nome": "Residência Popular (1 Quarto)",
        "categoria": "ESPECIAL",
        "padrao_acabamento": "UNICO",
        "pavimentos": 1,
        "descricao": "Residência popular unifamiliar compacta composta por 1 dormitório, sala, banheiro e cozinha."
    },
    {
        "codigo": "GI",
        "codigo_base": "GI",
        "nome": "Galpão Industrial",
        "categoria": "ESPECIAL",
        "padrao_acabamento": "UNICO",
        "pavimentos": 1,
        "descricao": "Galpão industrial com área livre de piso e estrutura metálica/concreto pré-moldado."
    }
]

SINDUSCONS_INICIAIS = [
    {"id": 10, "uf": "GO", "nome": "Sinduscon-GO", "regiao": "CENTRO-OESTE"},
    {"id": 8, "uf": "DF", "nome": "Sinduscon-DF", "regiao": "CENTRO-OESTE"},
    {"id": 1, "uf": "MG", "nome": "Sinduscon-MG", "regiao": "SUDESTE"},
    {"id": 32, "uf": "MG", "nome": "Sinduscon-Juiz de Fora", "regiao": "SUDESTE"},
    {"id": 33, "uf": "MG", "nome": "Sinduscon-Vale do Piranga", "regiao": "SUDESTE"},
    {"id": 34, "uf": "MG", "nome": "Sinduscon-Lagos", "regiao": "SUDESTE"},
    {"id": 36, "uf": "MG", "nome": "Sinduscon Norte", "regiao": "SUDESTE"},
    {"id": 39, "uf": "MG", "nome": "Sinduscon-GV", "regiao": "SUDESTE"},
    {"id": 20, "uf": "RJ", "nome": "Sinduscon-Rio", "regiao": "SUDESTE"},
    {"id": 18, "uf": "PR", "nome": "Sinduscon-PR", "regiao": "SUL"},
    {"id": 19, "uf": "PR", "nome": "Sinduscon-Noroeste-PR", "regiao": "SUL"},
    {"id": 38, "uf": "PR", "nome": "Sinduscon-Oeste-PR", "regiao": "SUL"},
    {"id": 26, "uf": "SC", "nome": "Sinduscon Grande Florianópolis-SC", "regiao": "SUL"},
    {"id": 3, "uf": "BA", "nome": "Sinduscon-BA", "regiao": "NORDESTE"},
    {"id": 4, "uf": "CE", "nome": "Sinduscon-CE", "regiao": "NORDESTE"},
    {"id": 6, "uf": "ES", "nome": "Sinduscon-ES", "regiao": "SUDESTE"},
    {"id": 13, "uf": "MT", "nome": "Sinduscon-MT", "regiao": "CENTRO-OESTE"},
    {"id": 16, "uf": "PE", "nome": "Sinduscon-PE", "regiao": "NORDESTE"},
]


def seed_initial_data(db: Session) -> None:
    logger.info("Populando sementes dos 19 Padrões NBR 12.721:2006...")
    for p_data in PADROES_NBR12721:
        exists = db.query(PadraoProjeto).filter_by(codigo=p_data["codigo"]).first()
        if not exists:
            db.add(PadraoProjeto(**p_data))

    logger.info("Populando sementes dos Sinduscons conhecidos...")
    for s_data in SINDUSCONS_INICIAIS:
        exists = db.query(Sinduscon).filter_by(id=s_data["id"]).first()
        if not exists:
            db.add(Sinduscon(**s_data))

    db.commit()
    logger.info("Sementes iniciais salvas com sucesso.")
