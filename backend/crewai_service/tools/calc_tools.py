"""
Tools de Calculo - Custos de Aquisicao e Venda de Imoveis em Leilao
Atualizado: Dezembro 2024 - Baseado em ProLeilao, D1Lance, SuperBid
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class TipoLeilao(Enum):
    """Tipos de leilao com custos diferenciados"""
    JUDICIAL = "judicial"                    # 5% comissao leiloeiro
    EXTRAJUDICIAL = "extrajudicial"         # 5% comissao leiloeiro
    VENDA_ONLINE_CAIXA = "venda_online_caixa"  # 0% comissao (sem leiloeiro)


# ==============================================================================
# TABELA COMPLETA DE ITBI POR MUNICIPIO DE SP
# Fonte: Prefeituras municipais e ProLeilao (2024)
# ==============================================================================
ITBI_ALIQUOTAS = {
    # Capital
    "SAO PAULO": 0.03,        # 3%

    # Litoral Paulista
    "SANTOS": 0.02,           # 2%
    "GUARUJA": 0.02,
    "PRAIA GRANDE": 0.02,
    "SAO VICENTE": 0.02,
    "BERTIOGA": 0.02,
    "UBATUBA": 0.02,
    "CARAGUATATUBA": 0.02,
    "MONGAGUA": 0.02,
    "ITANHAEM": 0.02,
    "PERUIBE": 0.02,
    "ILHABELA": 0.02,
    "SAO SEBASTIAO": 0.02,
    "CUBATAO": 0.02,

    # Grande Sao Paulo - ABC
    "SANTO ANDRE": 0.03,      # 3%
    "SAO BERNARDO DO CAMPO": 0.03,
    "SAO CAETANO DO SUL": 0.02,
    "DIADEMA": 0.02,
    "MAUA": 0.02,
    "RIBEIRAO PIRES": 0.02,
    "RIO GRANDE DA SERRA": 0.02,

    # Grande Sao Paulo - Outros
    "GUARULHOS": 0.02,
    "OSASCO": 0.03,
    "BARUERI": 0.02,
    "SANTANA DE PARNAIBA": 0.02,
    "ALPHAVILLE": 0.02,       # Barueri/Santana de Parnaiba
    "COTIA": 0.02,
    "EMBU DAS ARTES": 0.02,
    "TABOAO DA SERRA": 0.02,
    "ITAPECERICA DA SERRA": 0.02,
    "CARAPICUIBA": 0.02,
    "JANDIRA": 0.02,
    "ITAPEVI": 0.02,
    "VARGEM GRANDE PAULISTA": 0.02,

    # Grande Sao Paulo - Zona Leste
    "MOGI DAS CRUZES": 0.02,
    "SUZANO": 0.02,
    "ITAQUAQUECETUBA": 0.02,
    "FERRAZ DE VASCONCELOS": 0.02,
    "POA": 0.02,
    "ARUJA": 0.02,
    "GUARAREMA": 0.02,
    "BIRITIBA MIRIM": 0.02,
    "SALESOPOLIS": 0.02,

    # Grande Sao Paulo - Zona Norte
    "CAIEIRAS": 0.02,
    "FRANCO DA ROCHA": 0.02,
    "FRANCISCO MORATO": 0.02,
    "MAIRIPORA": 0.02,

    # Interior - Principais Cidades
    "CAMPINAS": 0.03,         # 3%
    "RIBEIRAO PRETO": 0.02,
    "SOROCABA": 0.02,
    "SAO JOSE DOS CAMPOS": 0.02,
    "PIRACICABA": 0.02,
    "JUNDIAI": 0.02,
    "LIMEIRA": 0.02,
    "AMERICANA": 0.02,
    "PAULINIA": 0.02,
    "INDAIATUBA": 0.02,
    "HORTOLANDIA": 0.02,
    "SUMARE": 0.02,
    "VALINHOS": 0.02,
    "VINHEDO": 0.02,
    "ITATIBA": 0.02,
    "BRAGANCA PAULISTA": 0.02,
    "ATIBAIA": 0.02,
    "TAUBATE": 0.02,
    "JACAREI": 0.02,
    "PINDAMONHANGABA": 0.02,
    "CAMPOS DO JORDAO": 0.02,
    "BAURU": 0.02,
    "MARILIA": 0.02,
    "PRESIDENTE PRUDENTE": 0.02,
    "ARACATUBA": 0.02,
    "SAO JOSE DO RIO PRETO": 0.02,
    "FRANCA": 0.02,
    "ARARAQUARA": 0.02,
    "SAO CARLOS": 0.02,
    "BOTUCATU": 0.02,

    # Default para cidades nao listadas
    "DEFAULT": 0.03
}

# ==============================================================================
# CUSTOS POR TIPO DE LEILAO
# Fonte: D1Lance, SuperBid, blogs especializados
# ==============================================================================
CUSTOS_POR_TIPO_LEILAO = {
    "judicial": {
        "comissao_leiloeiro_pct": 5.0,       # 5% do valor arrematacao
        "taxa_administrativa_pct": 0.0,
        "custas_processuais": 2000,          # Custas judiciais estimadas
        "honorarios_advogado_pct": 10.0,     # 10% em judicial (mais complexo)
        "honorarios_minimo": 5000,
        "honorarios_maximo": 20000,
    },
    "extrajudicial": {
        "comissao_leiloeiro_pct": 5.0,       # 5% do valor arrematacao
        "taxa_administrativa_pct": 0.0,
        "custas_processuais": 0,
        "honorarios_advogado_pct": 5.0,      # 5% em extrajudicial
        "honorarios_minimo": 3000,
        "honorarios_maximo": 15000,
    },
    "venda_online_caixa": {
        "comissao_leiloeiro_pct": 0.0,       # SEM LEILOEIRO na venda online!
        "taxa_administrativa_pct": 0.0,
        "custas_processuais": 0,
        "honorarios_advogado_pct": 5.0,
        "honorarios_minimo": 3000,
        "honorarios_maximo": 10000,
    }
}

# ==============================================================================
# CUSTOS DE DESOCUPACAO POR SITUACAO
# ==============================================================================
CUSTOS_DESOCUPACAO = {
    "desocupado": 0,                    # Imovel vazio
    "ocupado_proprietario": 5000,       # Ex-proprietario, geralmente cooperativo
    "ocupado_inquilino": 8000,          # Inquilino, pode ter direitos
    "ocupado_invasor": 12000,           # Invasao, mais complexo
    "ocupado_litigioso": 15000,         # Disputa judicial
    "ocupado_desconhecido": 10000,      # Situacao nao informada
    "nao_informado": 10000,             # Edital nao especifica
}

# ==============================================================================
# TABELA DE EMOLUMENTOS SP 2024
# Fonte: TJSP - Tabela de Custas e Emolumentos
# ==============================================================================
TABELA_ESCRITURA_SP = [
    (30000, 650),
    (50000, 950),
    (100000, 1600),
    (150000, 2300),
    (200000, 2900),
    (300000, 3700),
    (400000, 4200),
    (500000, 4800),
    (750000, 5500),
    (1000000, 6200),
    (float('inf'), 7000)
]

TABELA_REGISTRO_SP = [
    (30000, 550),
    (50000, 850),
    (100000, 1300),
    (150000, 1900),
    (200000, 2400),
    (300000, 3000),
    (400000, 3500),
    (500000, 3900),
    (750000, 4500),
    (1000000, 5200),
    (float('inf'), 6000)
]

# Certidoes e taxas adicionais de cartorio
CUSTOS_CERTIDOES = {
    "matricula_atualizada": 80,
    "onus_reais": 60,
    "distribuicao_civel": 50,
    "distribuicao_federal": 50,
    "protesto": 30,
    "quitacao_iptu": 0,  # Gratuito na prefeitura
    "quitacao_condominio": 0,  # Solicita ao sindico
    "autenticacoes": 100,
    "reconhecimento_firma": 50,
    "total_estimado": 420  # Soma aproximada
}

# ==============================================================================
# IRPF Ganho de Capital - Tabela Progressiva 2024
# ==============================================================================
IRPF_FAIXAS = [
    (5000000, 0.15),      # Ate R$ 5M: 15%
    (10000000, 0.175),    # R$ 5M a R$ 10M: 17.5%
    (30000000, 0.20),     # R$ 10M a R$ 30M: 20%
    (float('inf'), 0.225) # Acima R$ 30M: 22.5%
]

# Reducao IRPF por tempo de posse (Lei 11.196/2005)
# 0% nos primeiros 5 anos, depois reducao gradual
IRPF_REDUCAO_TEMPO = {
    0: 0.0,    # 0-5 anos: sem reducao
    5: 0.0,
    6: 0.05,   # 6 anos: 5% de reducao
    7: 0.10,
    8: 0.15,
    9: 0.20,
    10: 0.25,
    11: 0.30,
    12: 0.35,
    13: 0.40,
    14: 0.45,
    15: 0.50,  # 15+ anos: 50% de reducao no IR
}


def calc_itbi(valor_arrematacao: float, cidade: str) -> Dict:
    """
    Calcula o ITBI (Imposto de Transmissao de Bens Imoveis) baseado na cidade.
    IMPORTANTE: STJ determina que base de calculo deve ser valor de arrematacao,
    nao o valor venal. Algumas prefeituras contestam - consulte advogado.

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
        "base_calculo": valor_arrematacao,
        "observacao": "Base STJ: valor arrematacao (algumas prefeituras usam valor venal)"
    }


def calc_honorarios_advogado(valor_arrematacao: float, tipo_leilao: str = "venda_online_caixa") -> Dict:
    """
    Calcula honorarios advocaticios baseado no tipo de leilao.
    Judicial requer mais trabalho (10%), extrajudicial menos (5%).

    Args:
        valor_arrematacao: Valor do lance em reais
        tipo_leilao: judicial, extrajudicial, ou venda_online_caixa

    Returns:
        Dict com valor dos honorarios e percentual aplicado
    """
    tipo = tipo_leilao.lower().replace(" ", "_")
    config = CUSTOS_POR_TIPO_LEILAO.get(tipo, CUSTOS_POR_TIPO_LEILAO["venda_online_caixa"])

    percentual = config["honorarios_advogado_pct"] / 100
    valor_calculado = valor_arrematacao * percentual

    # Aplica limites minimo e maximo
    valor_final = max(config["honorarios_minimo"],
                      min(valor_calculado, config["honorarios_maximo"]))

    return {
        "valor_honorarios": round(valor_final, 2),
        "percentual_aplicado": round((valor_final / valor_arrematacao) * 100, 2) if valor_arrematacao > 0 else 0,
        "percentual_base": config["honorarios_advogado_pct"],
        "minimo": config["honorarios_minimo"],
        "maximo": config["honorarios_maximo"],
        "tipo_leilao": tipo,
        "justificativa": f"{'Judicial requer mais trabalho' if tipo == 'judicial' else 'Processo simplificado'}"
    }


def calc_comissao_leiloeiro(valor_arrematacao: float, tipo_leilao: str = "venda_online_caixa") -> Dict:
    """
    Calcula comissao do leiloeiro baseado no tipo de leilao.
    IMPORTANTE: Venda Online da Caixa NAO tem leiloeiro (0%)!

    Args:
        valor_arrematacao: Valor do lance em reais
        tipo_leilao: judicial, extrajudicial, ou venda_online_caixa

    Returns:
        Dict com valor da comissao e percentual
    """
    tipo = tipo_leilao.lower().replace(" ", "_")
    config = CUSTOS_POR_TIPO_LEILAO.get(tipo, CUSTOS_POR_TIPO_LEILAO["venda_online_caixa"])

    percentual = config["comissao_leiloeiro_pct"] / 100
    valor_comissao = valor_arrematacao * percentual

    return {
        "valor_comissao": round(valor_comissao, 2),
        "percentual": config["comissao_leiloeiro_pct"],
        "tipo_leilao": tipo,
        "tem_leiloeiro": config["comissao_leiloeiro_pct"] > 0,
        "observacao": "Sem leiloeiro na Venda Online Caixa" if tipo == "venda_online_caixa" else "Comissao padrao 5%"
    }


def calc_custo_desocupacao(situacao_ocupacao: str) -> Dict:
    """
    Calcula custo estimado de desocupacao baseado na situacao.

    Args:
        situacao_ocupacao: desocupado, ocupado_proprietario, ocupado_inquilino,
                          ocupado_invasor, ocupado_litigioso, ocupado_desconhecido

    Returns:
        Dict com valor estimado e detalhes
    """
    situacao = situacao_ocupacao.lower().replace(" ", "_")
    custo = CUSTOS_DESOCUPACAO.get(situacao, CUSTOS_DESOCUPACAO["ocupado_desconhecido"])

    detalhes = {
        "desocupado": "Imovel vazio, sem custos de desocupacao",
        "ocupado_proprietario": "Ex-proprietario, negociacao amigavel possivel",
        "ocupado_inquilino": "Inquilino com contrato, verificar direitos",
        "ocupado_invasor": "Invasao, requer acao judicial",
        "ocupado_litigioso": "Disputa judicial em andamento",
        "ocupado_desconhecido": "Situacao nao informada, usar estimativa media",
        "nao_informado": "Edital nao especifica, assumir ocupado",
    }

    return {
        "valor_desocupacao": custo,
        "situacao": situacao,
        "descricao": detalhes.get(situacao, "Situacao nao categorizada"),
        "recomendacao": "Visitar imovel antes de arrematar" if custo > 0 else "Baixo risco"
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
    tipo_leilao: str = "venda_online_caixa",
    situacao_ocupacao: str = "nao_informado",
    debitos_edital: float = 0,
    gravames_matricula: float = 0,
    area_m2: float = 50,
    custo_reforma_m2: float = 300,
    preco_venda_estimado: float = 0,
    condominio_mensal: float = 0,
    iptu_mensal: float = 0,
    meses_manutencao: int = 6,
    # Parametros legados (mantidos para compatibilidade)
    ocupado: bool = None,
    comissao_leiloeiro_pct: float = None,
    honorarios_advogado: float = None
) -> Dict:
    """
    Calcula todos os custos de aquisicao, manutencao e venda de um imovel de leilao.
    ATUALIZADO: Dezembro 2024 - Com custos diferenciados por tipo de leilao.

    Args:
        valor_arrematacao: Valor do lance
        cidade: Cidade do imovel (para calculo ITBI)
        tipo_leilao: judicial, extrajudicial, ou venda_online_caixa
        situacao_ocupacao: desocupado, ocupado_proprietario, ocupado_inquilino, etc
        debitos_edital: Total de debitos no edital (IPTU + Condominio)
        gravames_matricula: Valor dos gravames transferidos ao comprador
        area_m2: Area do imovel em m2
        custo_reforma_m2: Custo de reforma por m2
        preco_venda_estimado: Preco de venda estimado (para cenario de lucro)
        condominio_mensal: Valor do condominio mensal
        iptu_mensal: Valor do IPTU mensal
        meses_manutencao: Meses de manutencao ate venda (default: 6)

    Returns:
        Dict completo com todos os custos detalhados, ROI e comparativos
    """
    # Compatibilidade com parametros antigos
    if ocupado is not None:
        situacao_ocupacao = "ocupado_desconhecido" if ocupado else "desocupado"

    # 1. CUSTOS DE AQUISICAO (baseados no tipo de leilao)
    comissao_calc = calc_comissao_leiloeiro(valor_arrematacao, tipo_leilao)
    honorarios_calc = calc_honorarios_advogado(valor_arrematacao, tipo_leilao)
    desocupacao_calc = calc_custo_desocupacao(situacao_ocupacao)
    itbi_calc = calc_itbi(valor_arrematacao, cidade)
    cartorio_calc = calc_cartorio(valor_arrematacao)

    # Usa valores calculados ou override manual se fornecido
    comissao_leiloeiro = valor_arrematacao * (comissao_leiloeiro_pct / 100) if comissao_leiloeiro_pct is not None else comissao_calc["valor_comissao"]
    honorarios = honorarios_advogado if honorarios_advogado is not None else honorarios_calc["valor_honorarios"]
    custo_desocupacao = desocupacao_calc["valor_desocupacao"]
    custo_reforma = area_m2 * custo_reforma_m2

    # Custas processuais (so em judicial)
    config_tipo = CUSTOS_POR_TIPO_LEILAO.get(tipo_leilao.lower(), CUSTOS_POR_TIPO_LEILAO["venda_online_caixa"])
    custas_processuais = config_tipo.get("custas_processuais", 0)

    custos_aquisicao = {
        "valor_arrematacao": round(valor_arrematacao, 2),
        "comissao_leiloeiro": round(comissao_leiloeiro, 2),
        "comissao_leiloeiro_pct": comissao_calc["percentual"],
        "itbi": itbi_calc["valor_itbi"],
        "itbi_aliquota_pct": itbi_calc["aliquota_percentual"],
        "escritura": cartorio_calc["escritura"],
        "registro": cartorio_calc["registro"],
        "certidoes": cartorio_calc["certidoes"],
        "honorarios_advogado": round(honorarios, 2),
        "honorarios_pct": honorarios_calc["percentual_aplicado"],
        "custas_processuais": custas_processuais,
        "custo_desocupacao": round(custo_desocupacao, 2),
        "situacao_ocupacao": situacao_ocupacao,
        "debitos_edital": round(debitos_edital, 2),
        "gravames_matricula": round(gravames_matricula, 2),
        "custo_reforma": round(custo_reforma, 2),
        "tipo_leilao": tipo_leilao
    }

    total_custos_aquisicao = sum([
        comissao_leiloeiro,
        itbi_calc["valor_itbi"],
        cartorio_calc["total_cartorio"],
        honorarios,
        custas_processuais,
        custo_desocupacao,
        debitos_edital,
        gravames_matricula,
        custo_reforma
    ])

    investimento_total = valor_arrematacao + total_custos_aquisicao

    # 2. CUSTOS DE MANUTENCAO (6 meses ate venda)
    manutencao_condominio = condominio_mensal * meses_manutencao
    manutencao_iptu = iptu_mensal * meses_manutencao
    manutencao_luz_agua = 120 * meses_manutencao  # R$ 120/mes estimado
    manutencao_seguro = 80 * meses_manutencao     # R$ 80/mes estimado

    custos_manutencao = {
        "condominio": round(manutencao_condominio, 2),
        "iptu": round(manutencao_iptu, 2),
        "luz_agua": round(manutencao_luz_agua, 2),
        "seguro": round(manutencao_seguro, 2),
        "meses": meses_manutencao,
        "total_mensal": round((condominio_mensal + iptu_mensal + 120 + 80), 2)
    }

    total_manutencao = sum([
        manutencao_condominio,
        manutencao_iptu,
        manutencao_luz_agua,
        manutencao_seguro
    ])

    investimento_total_com_manutencao = investimento_total + total_manutencao

    # 3. CUSTOS DE VENDA E ANALISE DE RESULTADO
    custos_venda = {}
    resultado_venda = {}
    cenario_6_meses = {}

    if preco_venda_estimado > 0:
        # Comissao corretor (6% padrao)
        comissao_corretor = preco_venda_estimado * 0.06

        # Lucro bruto antes de impostos
        lucro_bruto = preco_venda_estimado - investimento_total_com_manutencao - comissao_corretor

        # IRPF sobre ganho de capital
        irpf_calc = calc_irpf(lucro_bruto)

        custos_venda = {
            "comissao_corretor": round(comissao_corretor, 2),
            "comissao_corretor_pct": 6.0,
            "irpf": irpf_calc["valor_irpf"],
            "irpf_aliquota_pct": irpf_calc["aliquota_percentual"],
            "total_custos_venda": round(comissao_corretor + irpf_calc["valor_irpf"], 2)
        }

        lucro_liquido = lucro_bruto - irpf_calc["valor_irpf"]
        roi_total = (lucro_liquido / investimento_total_com_manutencao) * 100 if investimento_total_com_manutencao > 0 else 0
        roi_mensal = roi_total / meses_manutencao if meses_manutencao > 0 else 0
        margem_seguranca = ((preco_venda_estimado - investimento_total_com_manutencao) / preco_venda_estimado) * 100 if preco_venda_estimado > 0 else 0

        # Comparativos de investimento
        taxa_cdi_anual = 0.1315  # CDI aproximado 13.15% a.a. (Dez/2024)
        rendimento_cdi = investimento_total_com_manutencao * (taxa_cdi_anual * meses_manutencao / 12)
        rendimento_poupanca = investimento_total_com_manutencao * (0.07 * meses_manutencao / 12)  # ~7% a.a.

        resultado_venda = {
            "preco_venda": round(preco_venda_estimado, 2),
            "lucro_bruto": round(lucro_bruto, 2),
            "lucro_liquido": round(lucro_liquido, 2),
            "roi_total_percentual": round(roi_total, 2),
            "roi_mensal_percentual": round(roi_mensal, 2),
            "roi_anualizado_percentual": round(roi_mensal * 12, 2),
            "margem_seguranca_percentual": round(margem_seguranca, 2),
            "comparativo_cdi": round(rendimento_cdi, 2),
            "comparativo_poupanca": round(rendimento_poupanca, 2),
            "diferenca_vs_cdi": round(lucro_liquido - rendimento_cdi, 2),
            "multiplicador_cdi": round(lucro_liquido / rendimento_cdi, 2) if rendimento_cdi > 0 else 0
        }

        # Cenario especifico de 6 meses
        cenario_6_meses = {
            "meses": meses_manutencao,
            "investimento_total": round(investimento_total_com_manutencao, 2),
            "preco_venda_estimado": round(preco_venda_estimado, 2),
            "lucro_liquido": round(lucro_liquido, 2),
            "roi_percentual": round(roi_total, 2),
            "margem_seguranca_pct": round(margem_seguranca, 2),
            "viabilidade": "EXCELENTE" if roi_total > 50 else "BOA" if roi_total > 30 else "MODERADA" if roi_total > 15 else "BAIXA"
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
        "cenario_6_meses": cenario_6_meses,
        "resumo": {
            "valor_arrematacao": round(valor_arrematacao, 2),
            "total_custos": round(total_custos_aquisicao + total_manutencao, 2),
            "investimento_final": round(investimento_total_com_manutencao, 2),
            "cidade": cidade,
            "tipo_leilao": tipo_leilao,
            "situacao_ocupacao": situacao_ocupacao,
            "meses_cenario": meses_manutencao,
            "tem_leiloeiro": comissao_calc["tem_leiloeiro"],
            "aliquota_itbi": itbi_calc["aliquota_percentual"]
        }
    }


# ==============================================================================
# EXEMPLO DE USO E TESTES
# ==============================================================================
if __name__ == "__main__":
    import json

    print("=" * 70)
    print("TESTE DE CALCULOS - LEILAO DE IMOVEIS")
    print("=" * 70)

    # Teste 1: Venda Online Caixa (sem leiloeiro)
    print("\n[TESTE 1] Venda Online Caixa - Sao Paulo")
    print("-" * 50)
    resultado_caixa = calc_custos_totais(
        valor_arrematacao=120000,
        cidade="SAO PAULO",
        tipo_leilao="venda_online_caixa",
        situacao_ocupacao="ocupado_desconhecido",
        debitos_edital=15000,
        gravames_matricula=0,
        area_m2=65,
        custo_reforma_m2=300,
        preco_venda_estimado=280000,
        condominio_mensal=500,
        iptu_mensal=150,
        meses_manutencao=6
    )
    print(f"  Arrematacao: R$ {resultado_caixa['resumo']['valor_arrematacao']:,.2f}")
    print(f"  Comissao Leiloeiro: R$ {resultado_caixa['custos_aquisicao']['comissao_leiloeiro']:,.2f} (0% - sem leiloeiro)")
    print(f"  ITBI ({resultado_caixa['resumo']['aliquota_itbi']}%): R$ {resultado_caixa['custos_aquisicao']['itbi']:,.2f}")
    print(f"  Honorarios: R$ {resultado_caixa['custos_aquisicao']['honorarios_advogado']:,.2f}")
    print(f"  Investimento Total: R$ {resultado_caixa['investimento_total_com_manutencao']:,.2f}")
    print(f"  Lucro Liquido: R$ {resultado_caixa['resultado_venda'].get('lucro_liquido', 0):,.2f}")
    print(f"  ROI: {resultado_caixa['resultado_venda'].get('roi_total_percentual', 0):.1f}%")
    print(f"  Viabilidade: {resultado_caixa['cenario_6_meses'].get('viabilidade', 'N/A')}")

    # Teste 2: Leilao Judicial
    print("\n[TESTE 2] Leilao Judicial - Santos")
    print("-" * 50)
    resultado_judicial = calc_custos_totais(
        valor_arrematacao=150000,
        cidade="SANTOS",
        tipo_leilao="judicial",
        situacao_ocupacao="ocupado_litigioso",
        debitos_edital=20000,
        gravames_matricula=5000,
        area_m2=80,
        custo_reforma_m2=350,
        preco_venda_estimado=350000,
        condominio_mensal=800,
        iptu_mensal=200,
        meses_manutencao=6
    )
    print(f"  Arrematacao: R$ {resultado_judicial['resumo']['valor_arrematacao']:,.2f}")
    print(f"  Comissao Leiloeiro: R$ {resultado_judicial['custos_aquisicao']['comissao_leiloeiro']:,.2f} (5%)")
    print(f"  ITBI ({resultado_judicial['resumo']['aliquota_itbi']}%): R$ {resultado_judicial['custos_aquisicao']['itbi']:,.2f}")
    print(f"  Honorarios: R$ {resultado_judicial['custos_aquisicao']['honorarios_advogado']:,.2f} (10%)")
    print(f"  Custas Processuais: R$ {resultado_judicial['custos_aquisicao']['custas_processuais']:,.2f}")
    print(f"  Desocupacao: R$ {resultado_judicial['custos_aquisicao']['custo_desocupacao']:,.2f}")
    print(f"  Investimento Total: R$ {resultado_judicial['investimento_total_com_manutencao']:,.2f}")
    print(f"  Lucro Liquido: R$ {resultado_judicial['resultado_venda'].get('lucro_liquido', 0):,.2f}")
    print(f"  ROI: {resultado_judicial['resultado_venda'].get('roi_total_percentual', 0):.1f}%")

    # Teste 3: Extrajudicial (banco)
    print("\n[TESTE 3] Leilao Extrajudicial - Guaruja")
    print("-" * 50)
    resultado_extra = calc_custos_totais(
        valor_arrematacao=100000,
        cidade="GUARUJA",
        tipo_leilao="extrajudicial",
        situacao_ocupacao="desocupado",
        debitos_edital=8000,
        gravames_matricula=0,
        area_m2=55,
        custo_reforma_m2=250,
        preco_venda_estimado=200000,
        condominio_mensal=400,
        iptu_mensal=100,
        meses_manutencao=6
    )
    print(f"  Arrematacao: R$ {resultado_extra['resumo']['valor_arrematacao']:,.2f}")
    print(f"  Comissao Leiloeiro: R$ {resultado_extra['custos_aquisicao']['comissao_leiloeiro']:,.2f} (5%)")
    print(f"  ITBI ({resultado_extra['resumo']['aliquota_itbi']}%): R$ {resultado_extra['custos_aquisicao']['itbi']:,.2f}")
    print(f"  Desocupacao: R$ {resultado_extra['custos_aquisicao']['custo_desocupacao']:,.2f} (desocupado)")
    print(f"  Investimento Total: R$ {resultado_extra['investimento_total_com_manutencao']:,.2f}")
    print(f"  Lucro Liquido: R$ {resultado_extra['resultado_venda'].get('lucro_liquido', 0):,.2f}")
    print(f"  ROI: {resultado_extra['resultado_venda'].get('roi_total_percentual', 0):.1f}%")
    print(f"  Multiplicador CDI: {resultado_extra['resultado_venda'].get('multiplicador_cdi', 0):.1f}x")

    print("\n" + "=" * 70)
    print("TESTES CONCLUIDOS COM SUCESSO!")
    print("=" * 70)
