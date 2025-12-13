"""
Tools de Calculo - Custos de Aquisicao e Venda de Imoveis em Leilao
"""

# Removido decorador @tool para permitir chamada direta
# from crewai_tools import tool
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class Cidade(Enum):
    SAO_PAULO = "SAO PAULO"
    SANTOS = "SANTOS"
    GUARUJA = "GUARUJA"
    PRAIA_GRANDE = "PRAIA GRANDE"
    SAO_VICENTE = "SAO VICENTE"
    BERTIOGA = "BERTIOGA"
    UBATUBA = "UBATUBA"
    CARAGUATATUBA = "CARAGUATATUBA"
    OUTROS = "OUTROS"


# Aliquotas ITBI por cidade
ITBI_ALIQUOTAS = {
    "SAO PAULO": 0.03,      # 3%
    "SANTOS": 0.02,         # 2%
    "GUARUJA": 0.02,
    "PRAIA GRANDE": 0.02,
    "SAO VICENTE": 0.02,
    "BERTIOGA": 0.02,
    "UBATUBA": 0.02,
    "CARAGUATATUBA": 0.02,
    "DEFAULT": 0.03
}

# Tabela de emolumentos SP (aproximada)
TABELA_ESCRITURA_SP = [
    (30000, 600),
    (50000, 900),
    (100000, 1500),
    (150000, 2200),
    (200000, 2800),
    (300000, 3500),
    (500000, 4500),
    (float('inf'), 5500)
]

TABELA_REGISTRO_SP = [
    (30000, 500),
    (50000, 800),
    (100000, 1200),
    (150000, 1800),
    (200000, 2200),
    (300000, 2800),
    (500000, 3500),
    (float('inf'), 4500)
]

# IRPF Ganho de Capital - Tabela Progressiva
IRPF_FAIXAS = [
    (5000000, 0.15),      # Ate 5M: 15%
    (10000000, 0.175),    # 5M a 10M: 17.5%
    (30000000, 0.20),     # 10M a 30M: 20%
    (float('inf'), 0.225) # Acima 30M: 22.5%
]


def calc_itbi(valor_arrematacao: float, cidade: str) -> Dict:
    """
    Calcula o ITBI (Imposto de Transmissao de Bens Imoveis) baseado na cidade.

    Args:
        valor_arrematacao: Valor do lance/arrematacao em reais
        cidade: Nome da cidade (ex: SAO PAULO, SANTOS)

    Returns:
        Dict com valor do ITBI e aliquota aplicada
    """
    cidade_upper = cidade.upper().strip()
    aliquota = ITBI_ALIQUOTAS.get(cidade_upper, ITBI_ALIQUOTAS["DEFAULT"])
    valor_itbi = valor_arrematacao * aliquota

    return {
        "valor_itbi": round(valor_itbi, 2),
        "aliquota_percentual": aliquota * 100,
        "cidade": cidade_upper,
        "base_calculo": valor_arrematacao
    }


def calc_cartorio(valor_imovel: float) -> Dict:
    """
    Calcula custos de cartorio (escritura e registro) baseado na tabela de emolumentos SP.

    Args:
        valor_imovel: Valor do imovel para calculo

    Returns:
        Dict com valores de escritura, registro, certidoes e total
    """
    # Calcula escritura
    valor_escritura = 0
    for limite, valor in TABELA_ESCRITURA_SP:
        if valor_imovel <= limite:
            valor_escritura = valor
            break

    # Calcula registro
    valor_registro = 0
    for limite, valor in TABELA_REGISTRO_SP:
        if valor_imovel <= limite:
            valor_registro = valor
            break

    # Certidoes (valor fixo estimado)
    valor_certidoes = 800.0

    return {
        "escritura": round(valor_escritura, 2),
        "registro": round(valor_registro, 2),
        "certidoes": round(valor_certidoes, 2),
        "total_cartorio": round(valor_escritura + valor_registro + valor_certidoes, 2),
        "base_calculo": valor_imovel
    }


def calc_irpf(lucro_bruto: float) -> Dict:
    """
    Calcula IRPF sobre ganho de capital na venda do imovel.

    Args:
        lucro_bruto: Lucro bruto da venda (preco_venda - custo_aquisicao)

    Returns:
        Dict com valor do IRPF, aliquota e lucro liquido
    """
    if lucro_bruto <= 0:
        return {
            "valor_irpf": 0,
            "aliquota_percentual": 0,
            "lucro_bruto": lucro_bruto,
            "lucro_liquido": lucro_bruto
        }

    # Determina aliquota
    aliquota = 0.15
    for limite, taxa in IRPF_FAIXAS:
        if lucro_bruto <= limite:
            aliquota = taxa
            break

    valor_irpf = lucro_bruto * aliquota
    lucro_liquido = lucro_bruto - valor_irpf

    return {
        "valor_irpf": round(valor_irpf, 2),
        "aliquota_percentual": aliquota * 100,
        "lucro_bruto": round(lucro_bruto, 2),
        "lucro_liquido": round(lucro_liquido, 2)
    }


def calc_custos_totais(
    valor_arrematacao: float,
    cidade: str,
    ocupado: bool = False,
    debitos_edital: float = 0,
    gravames_matricula: float = 0,
    area_m2: float = 50,
    custo_reforma_m2: float = 300,
    comissao_leiloeiro_pct: float = 5.0,
    honorarios_advogado: float = 4000,
    preco_venda_estimado: float = 0,
    condominio_mensal: float = 0,
    iptu_mensal: float = 0,
    meses_manutencao: int = 6
) -> Dict:
    """
    Calcula todos os custos de aquisicao, manutencao e venda de um imovel de leilao.

    Args:
        valor_arrematacao: Valor do lance
        cidade: Cidade do imovel
        ocupado: Se o imovel esta ocupado
        debitos_edital: Total de debitos no edital (IPTU + Condominio)
        gravames_matricula: Valor dos gravames transferidos
        area_m2: Area do imovel em m2
        custo_reforma_m2: Custo de reforma por m2
        comissao_leiloeiro_pct: Percentual da comissao do leiloeiro
        honorarios_advogado: Valor dos honorarios advocaticios
        preco_venda_estimado: Preco de venda estimado
        condominio_mensal: Valor do condominio mensal
        iptu_mensal: Valor do IPTU mensal
        meses_manutencao: Meses de manutencao ate venda

    Returns:
        Dict completo com todos os custos detalhados
    """
    # 1. CUSTOS DE AQUISICAO
    comissao_leiloeiro = valor_arrematacao * (comissao_leiloeiro_pct / 100)

    itbi_calc = calc_itbi(valor_arrematacao, cidade)
    cartorio_calc = calc_cartorio(valor_arrematacao)

    custo_desocupacao = 10000 if ocupado else 0
    custo_reforma = area_m2 * custo_reforma_m2

    custos_aquisicao = {
        "valor_arrematacao": round(valor_arrematacao, 2),
        "comissao_leiloeiro": round(comissao_leiloeiro, 2),
        "itbi": itbi_calc["valor_itbi"],
        "escritura": cartorio_calc["escritura"],
        "registro": cartorio_calc["registro"],
        "certidoes": cartorio_calc["certidoes"],
        "honorarios_advogado": round(honorarios_advogado, 2),
        "custo_desocupacao": round(custo_desocupacao, 2),
        "debitos_edital": round(debitos_edital, 2),
        "gravames_matricula": round(gravames_matricula, 2),
        "custo_reforma": round(custo_reforma, 2)
    }

    total_custos_aquisicao = sum([
        comissao_leiloeiro,
        itbi_calc["valor_itbi"],
        cartorio_calc["total_cartorio"],
        honorarios_advogado,
        custo_desocupacao,
        debitos_edital,
        gravames_matricula,
        custo_reforma
    ])

    investimento_total = valor_arrematacao + total_custos_aquisicao

    # 2. CUSTOS DE MANUTENCAO
    manutencao_condominio = condominio_mensal * meses_manutencao
    manutencao_iptu = iptu_mensal * meses_manutencao
    manutencao_luz_agua = 100 * meses_manutencao  # Estimado
    manutencao_seguro = 50 * meses_manutencao     # Estimado

    custos_manutencao = {
        "condominio": round(manutencao_condominio, 2),
        "iptu": round(manutencao_iptu, 2),
        "luz_agua": round(manutencao_luz_agua, 2),
        "seguro": round(manutencao_seguro, 2),
        "meses": meses_manutencao
    }

    total_manutencao = sum([
        manutencao_condominio,
        manutencao_iptu,
        manutencao_luz_agua,
        manutencao_seguro
    ])

    investimento_total_com_manutencao = investimento_total + total_manutencao

    # 3. CUSTOS DE VENDA (se preco_venda informado)
    custos_venda = {}
    resultado_venda = {}

    if preco_venda_estimado > 0:
        comissao_corretor = preco_venda_estimado * 0.06  # 6%

        lucro_bruto = preco_venda_estimado - investimento_total_com_manutencao - comissao_corretor
        irpf_calc = calc_irpf(lucro_bruto)

        custos_venda = {
            "comissao_corretor": round(comissao_corretor, 2),
            "irpf": irpf_calc["valor_irpf"],
            "total_custos_venda": round(comissao_corretor + irpf_calc["valor_irpf"], 2)
        }

        lucro_liquido = lucro_bruto - irpf_calc["valor_irpf"]
        roi_total = (lucro_liquido / investimento_total_com_manutencao) * 100 if investimento_total_com_manutencao > 0 else 0
        roi_mensal = roi_total / meses_manutencao if meses_manutencao > 0 else 0
        margem_seguranca = ((preco_venda_estimado - investimento_total_com_manutencao) / preco_venda_estimado) * 100 if preco_venda_estimado > 0 else 0

        # Comparativo CDI (aproximado 13% a.a.)
        rendimento_cdi = investimento_total_com_manutencao * (0.13 * meses_manutencao / 12)

        resultado_venda = {
            "preco_venda": round(preco_venda_estimado, 2),
            "lucro_bruto": round(lucro_bruto, 2),
            "lucro_liquido": round(lucro_liquido, 2),
            "roi_total_percentual": round(roi_total, 2),
            "roi_mensal_percentual": round(roi_mensal, 2),
            "margem_seguranca_percentual": round(margem_seguranca, 2),
            "comparativo_cdi": round(rendimento_cdi, 2),
            "diferenca_vs_cdi": round(lucro_liquido - rendimento_cdi, 2)
        }

    return {
        "custos_aquisicao": custos_aquisicao,
        "total_custos_aquisicao": round(total_custos_aquisicao, 2),
        "investimento_total": round(investimento_total, 2),
        "custos_manutencao": custos_manutencao,
        "total_manutencao": round(total_manutencao, 2),
        "investimento_total_com_manutencao": round(investimento_total_com_manutencao, 2),
        "custos_venda": custos_venda,
        "resultado_venda": resultado_venda,
        "resumo": {
            "valor_arrematacao": round(valor_arrematacao, 2),
            "total_custos": round(total_custos_aquisicao + total_manutencao, 2),
            "investimento_final": round(investimento_total_com_manutencao, 2),
            "cidade": cidade,
            "ocupado": ocupado,
            "meses_cenario": meses_manutencao
        }
    }


# Exemplo de uso
if __name__ == "__main__":
    resultado = calc_custos_totais(
        valor_arrematacao=120000,
        cidade="SAO PAULO",
        ocupado=True,
        debitos_edital=17000,
        gravames_matricula=8000,
        area_m2=65,
        custo_reforma_m2=300,
        preco_venda_estimado=525000,
        condominio_mensal=650,
        iptu_mensal=180,
        meses_manutencao=6
    )

    import json
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
