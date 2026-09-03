from pathlib import Path
from typing import Any, Dict, List
from autocub.adapters.base import BaseEtlAdapter, StandardEtlResult


class CbicBookletAdapter(BaseEtlAdapter):
    """
    Adaptador para ingestão e estruturação dos dados perenes das Cartilhas Oficiais da CBIC/Sinduscon-MG
    e da ABNT NBR 12.721:2006 (Lote básico de insumos, itens inclusos/exclusos, FAQ e Lei 4.591/64).
    """
    adapter_id = "cbic_booklet_v1"
    version = "1.0.0"

    def can_handle(self, source_type: str, source_reference: Any) -> bool:
        return source_type.lower() in ("booklet", "cartilha", "knowledge_base", "kb")

    def extract(self, source_reference: Any, **kwargs) -> Dict[str, Any]:
        """Retorna o repositório estruturado de conhecimentos normativos das cartilhas."""
        return {
            "lote_insumos": self.get_lote_insumos(),
            "itens_excluidos": self.get_itens_excluidos_cub(),
            "faq": self.get_faq(),
            "lei_4591": self.get_fundamentacao_legal(),
            "fatores_area_equivalente": self.get_fatores_area_equivalente()
        }

    def transform(self, raw_content: Any, **kwargs) -> StandardEtlResult:
        return StandardEtlResult(
            adapter_id=self.adapter_id,
            source_identifier="docs/cartilhas",
            status="SUCCESS",
            records_count=len(raw_content),
            data=raw_content,
            metadata={"fonte": "Sinduscon-MG / CBIC / ABNT NBR 12.721:2006"}
        )

    @staticmethod
    def get_lote_insumos() -> Dict[str, Any]:
        """Os 29 insumos do lote básico da NBR 12.721:2006 e suas 4 famílias macro."""
        return {
            "familias_macro_percentuais": {
                "materiais": {"peso_medio_pct": 48.0, "descricao": "Materiais de construção civis e acabamentos"},
                "mao_de_obra": {"peso_medio_pct": 47.0, "descricao": "Mão de obra direta com encargos sociais plenos"},
                "despesas_administrativas": {"peso_medio_pct": 4.5, "descricao": "Honorários de Engenheiro residente"},
                "equipamentos": {"peso_medio_pct": 0.5, "descricao": "Locação de betoneira e maquinário básico"}
            },
            "total_insumos": 29,
            "insumos": [
                {"item": 1, "familia": "MATERIAIS", "nome": "Chapa compensado plastificado 18mm", "unidade": "m²"},
                {"item": 2, "familia": "MATERIAIS", "nome": "Aço CA-50 Ø 10mm", "unidade": "kg"},
                {"item": 3, "familia": "MATERIAIS", "nome": "Concreto fck=25 MPa pré-dosado", "unidade": "m³"},
                {"item": 4, "familia": "MATERIAIS", "nome": "Cimento CP-32 II", "unidade": "kg"},
                {"item": 5, "familia": "MATERIAIS", "nome": "Areia média", "unidade": "m³"},
                {"item": 6, "familia": "MATERIAIS", "nome": "Brita nº 02", "unidade": "m³"},
                {"item": 7, "familia": "MATERIAIS", "nome": "Bloco cerâmico 9x19x19 cm", "unidade": "un"},
                {"item": 8, "familia": "MATERIAIS", "nome": "Bloco de concreto vedação 19x19x39 cm", "unidade": "un"},
                {"item": 9, "familia": "MATERIAIS", "nome": "Telha fibrocimento ondulada 6mm", "unidade": "m²"},
                {"item": 10, "familia": "MATERIAIS", "nome": "Porta interna semi-oca 0,60x2,10m", "unidade": "un"},
                {"item": 11, "familia": "MATERIAIS", "nome": "Esquadria de correr em alumínio anodizado", "unidade": "m²"},
                {"item": 12, "familia": "MATERIAIS", "nome": "Janela de correr em ferro 1,20x1,20m", "unidade": "m²"},
                {"item": 13, "familia": "MATERIAIS", "nome": "Fechadura para porta interna tipo IV", "unidade": "un"},
                {"item": 14, "familia": "MATERIAIS", "nome": "Placa cerâmica azulejo PEI II", "unidade": "m²"},
                {"item": 15, "familia": "MATERIAIS", "nome": "Bancada de pia em mármore branco 2,00x0,60m", "unidade": "un"},
                {"item": 16, "familia": "MATERIAIS", "nome": "Placa de gesso liso 0,60x0,60m", "unidade": "m²"},
                {"item": 17, "familia": "MATERIAIS", "nome": "Vidro liso transparente 4mm com massa", "unidade": "m²"},
                {"item": 18, "familia": "MATERIAIS", "nome": "Tinta látex PVA", "unidade": "l"},
                {"item": 19, "familia": "MATERIAIS", "nome": "Emulsão asfáltica impermeabilizante", "unidade": "kg"},
                {"item": 20, "familia": "MATERIAIS", "nome": "Fio de cobre antichama 750V # 2,5mm²", "unidade": "m"},
                {"item": 21, "familia": "MATERIAIS", "nome": "Disjuntor tripolar 70A", "unidade": "un"},
                {"item": 22, "familia": "MATERIAIS", "nome": "Bacia sanitária branca com caixa acoplada", "unidade": "un"},
                {"item": 23, "familia": "MATERIAIS", "nome": "Registro de pressão cromado Ø 1/2\"", "unidade": "un"},
                {"item": 24, "familia": "MATERIAIS", "nome": "Tubo de ferro galvanizado Ø 2 1/2\"", "unidade": "m"},
                {"item": 25, "familia": "MATERIAIS", "nome": "Tubo PVC-R rígido para esgoto Ø 150mm", "unidade": "m"},
                {"item": 26, "familia": "MAO_DE_OBRA", "nome": "Pedreiro (com encargos sociais)", "unidade": "h"},
                {"item": 27, "familia": "MAO_DE_OBRA", "nome": "Servente (com encargos sociais)", "unidade": "h"},
                {"item": 28, "familia": "ADMINISTRATIVO", "nome": "Engenheiro (honorários de supervisão)", "unidade": "h"},
                {"item": 29, "familia": "EQUIPAMENTOS", "nome": "Locação de betoneira 320 litros", "unidade": "dia"}
            ]
        }

    @staticmethod
    def get_itens_excluidos_cub() -> List[Dict[str, str]]:
        """Itens que NÃO estão incluídos no CUB segundo o Item 8.3.5 da ABNT NBR 12.721 e Cartilha 1."""
        return [
            {"item": "Fundações Especiais", "impacto": "+5% a +10%", "descricao": "Fundações profundas (estacas, tubulões), submuramentos, paredes-diafragma, rebaixamento de lençol freático."},
            {"item": "Elevadores", "impacto": "+3% a +6%", "descricao": "Elevadores de passageiros, monta-cargas e escadas rolantes."},
            {"item": "Equipamentos e Instalações Especiais", "impacto": "+4% a +8%", "descricao": "Ar-condicionado, geradores de emergência, subestação transformadora, bombas de recalque, aquecedor solar."},
            {"item": "Urbanização e Lazer", "impacto": "+3% a +7%", "descricao": "Piscinas, quadras esportivas, paisagismo, playgrounds externos, ajardinamento e pavimentação externa."},
            {"item": "Projetos de Engenharia e Arquitetura", "impacto": "+3% a +5%", "descricao": "Projeto arquitetônico, estrutural, instalações hidrossanitárias, elétricas, combate a incêndio e maquetes."},
            {"item": "Impostos, Taxas e Emolumentos", "impacto": "+4% a +6%", "descricao": "Alvará de construção, taxas de ligação definitiva de água/luz, certidões de Habite-se, registros em cartório."},
            {"item": "Remuneração do Construtor e Incorporador (BDI e Lucro)", "impacto": "+15% a +25%", "descricao": "Bonificação e Despesas Indiretas (BDI), lucro da construtora, riscos do empreendimento e custos de comercialização."},
            {"item": "Terreno", "impacto": "+15% a +35%", "descricao": "Custo de aquisição do lote/gleba urbana e comissões imobiliárias."}
        ]

    @staticmethod
    def get_faq() -> List[Dict[str, str]]:
        """Perguntas e respostas essenciais da Cartilha CBIC."""
        return [
            {
                "pergunta": "Os projetos entram no cálculo do CUB/m²?",
                "resposta": "Não. De acordo com a ABNT NBR 12.721:2006, não estão incluídos os custos de projetos arquitetônicos, complementares ou especiais."
            },
            {
                "pergunta": "O que é Área Equivalente de Construção?",
                "resposta": "É a área virtual cujo custo de construção é equivalente ao custo da respectiva área real, utilizada para ponderar áreas cobertas/descobertas (Quadro II da NBR 12.721)."
            },
            {
                "pergunta": "O custo do terreno entra no cálculo do CUB?",
                "resposta": "Não. O CUB/m² calcula exclusivamente o custo unitário básico da edificação padrão, desconsiderando lote, fundações, projetos e BDI."
            },
            {
                "pergunta": "Qual a diferença entre a série Com e Sem Desoneração?",
                "resposta": "A desoneração (Lei 12.546/11 alterada pela Lei 12.844/13) substitui a contribuição patronal de 20% sobre a folha pela CPRB (receita bruta). O impacto no CUB reflete exclusivamente a redução nos encargos sociais da mão de obra direta (de ~125% para ~85%), mantendo materiais inalterados."
            }
        ]

    @staticmethod
    def get_fundamentacao_legal() -> Dict[str, Any]:
        """Fundamentação legal na Lei Federal 4.591/1964 e jurisprudência consolidada."""
        return {
            "lei": "Lei Federal 4.591 de 16 de dezembro de 1964",
            "artigos": {
                "art_53": "Incumbe à ABNT fixar critérios e normas técnicas para cálculo de custos unitários de construção e padronização de projetos (origem da NBR 12.721).",
                "art_54": "Determina a obrigatoriedade dos sindicatos estaduais (Sinduscons) divulgarem mensalmente até o dia 5 de cada mês os custos unitários de construção.",
                "art_54_par_1": "Exige que o incorporador arquive no Cartório de Registro de Imóveis (R.I.) o Memorial de Incorporação com o orçamento do custo global da obra indexado aos quadros da NBR e ao CUB."
            },
            "jurisprudencia_stj": "O Superior Tribunal de Justiça (STJ) firmou jurisprudência reconhecendo o CUB como indexador financeiro válido para contratos imobiliários EXCLUSIVAMENTE durante a fase de construção. Após a concessão do Habite-se, o saldo devedor deve migrar para índices gerais de preços (ex: IPCA ou INPC)."
        }

    @staticmethod
    def get_fatores_area_equivalente() -> List[Dict[str, Any]]:
        """Coeficientes de equivalência de custo normatizados (NBR 12.721 Quadro II)."""
        return [
            {"ambiente": "Área privativa principal padrão", "fator_padrao": 1.00, "faixa_min_max": [1.00, 1.00]},
            {"ambiente": "Garagem coberta / subsolo", "fator_padrao": 0.65, "faixa_min_max": [0.50, 0.75]},
            {"ambiente": "Garagem descoberta / estacionamento", "fator_padrao": 0.12, "faixa_min_max": [0.10, 0.20]},
            {"ambiente": "Varanda coberta / sacada", "fator_padrao": 0.50, "faixa_min_max": [0.40, 0.60]},
            {"ambiente": "Área de serviço descoberta / terraço aberto", "fator_padrao": 0.30, "faixa_min_max": [0.20, 0.40]},
            {"ambiente": "Pilotis de uso comum", "fator_padrao": 0.40, "faixa_min_max": [0.30, 0.50]}
        ]
