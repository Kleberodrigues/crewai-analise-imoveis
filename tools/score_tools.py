"""
Tools de Score - Calculo de Score de Oportunidade e Classificacao
"""

# Removido decorador @tool para permitir chamada direta
# from crewai_tools import tool
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Recomendacao(Enum):
    COMPRAR = "COMPRAR"
    ANALISAR_MELHOR = "ANALISAR_MELHOR"
    EVITAR = "EVITAR"


class NivelRisco(Enum):
    BAIXO = "BAIXO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"


# Pesos para calculo do score geral
PESOS_SCORE = {
    "edital": 0.20,      # 20%
    "matricula": 0.20,   # 20%
    "localizacao": 0.25, # 25%
    "financeiro": 0.25,  # 25%
    "liquidez": 0.10     # 10%
}


def calc_score_edital(
    ocupacao: str = "nao_informado",
    debitos_total: float = 0,
    riscos: Optional[List[str]] = None,
    comissao_leiloeiro: float = 5.0
) -> Dict:
    """
    Calcula score do edital (0-100) baseado em riscos juridicos.

    Args:
        ocupacao: Status de ocupacao (ocupado, desocupado, nao_informado)
        debitos_total: Total de debitos no edital
        riscos: Lista de riscos identificados
        comissao_leiloeiro: Percentual da comissao

    Returns:
        Dict com score e detalhamento
    """
    if riscos is None:
        riscos = []

    score = 100
    deducoes = []

    # Ocupacao
    if ocupacao.lower() == "ocupado":
        score -= 25
        deducoes.append(("Imovel ocupado", -25))
    elif ocupacao.lower() == "nao_informado":
        score -= 10
        deducoes.append(("Ocupacao nao informada", -10))

    # Debitos (cada R$ 1.000 = -1 ponto, max -30)
    deducao_debitos = min(30, debitos_total / 1000)
    if deducao_debitos > 0:
        score -= deducao_debitos
        deducoes.append((f"Debitos R$ {debitos_total:,.2f}", -deducao_debitos))

    # Riscos identificados (cada risco = -5 pontos)
    for risco in riscos:
        score -= 5
        deducoes.append((f"Risco: {risco[:30]}...", -5))

    # Comissao acima do normal
    if comissao_leiloeiro > 5:
        deducao_comissao = (comissao_leiloeiro - 5) * 2
        score -= deducao_comissao
        deducoes.append((f"Comissao {comissao_leiloeiro}%", -deducao_comissao))

    score = max(0, min(100, score))

    return {
        "score": round(score, 2),
        "deducoes": deducoes,
        "classificacao": "Bom" if score >= 70 else ("Regular" if score >= 50 else "Ruim"),
        "ocupacao": ocupacao,
        "debitos_total": debitos_total,
        "total_riscos": len(riscos)
    }


def calc_score_matricula(
    gravames_extintos: Optional[List[str]] = None,
    gravames_transferidos: Optional[List[str]] = None,
    irregularidades: Optional[List[str]] = None,
    valor_gravames: float = 0
) -> Dict:
    """
    Calcula score da matricula (0-100).

    Args:
        gravames_extintos: Gravames que serao extintos no leilao
        gravames_transferidos: Gravames transferidos ao arrematante
        irregularidades: Irregularidades na matricula
        valor_gravames: Valor estimado dos gravames transferidos

    Returns:
        Dict com score e detalhamento
    """
    if gravames_extintos is None:
        gravames_extintos = []
    if gravames_transferidos is None:
        gravames_transferidos = []
    if irregularidades is None:
        irregularidades = []

    score = 100
    deducoes = []

    # Gravames transferidos (-15 cada)
    for gravame in gravames_transferidos:
        score -= 15
        deducoes.append((f"Gravame transferido: {gravame[:25]}...", -15))

    # Irregularidades (-20 cada)
    for irreg in irregularidades:
        score -= 20
        deducoes.append((f"Irregularidade: {irreg[:25]}...", -20))

    # Valor dos gravames (cada R$ 5.000 = -5 pontos, max -20)
    deducao_valor = min(20, valor_gravames / 5000 * 5)
    if deducao_valor > 0:
        score -= deducao_valor
        deducoes.append((f"Valor gravames R$ {valor_gravames:,.2f}", -deducao_valor))

    # Bonus por gravames extintos (+5 cada, max +10)
    bonus = min(10, len(gravames_extintos) * 5)
    if bonus > 0:
        score += bonus
        deducoes.append((f"{len(gravames_extintos)} gravames extintos", bonus))

    score = max(0, min(100, score))

    return {
        "score": round(score, 2),
        "deducoes": deducoes,
        "classificacao": "Limpa" if score >= 80 else ("Regular" if score >= 50 else "Problematica"),
        "total_gravames_extintos": len(gravames_extintos),
        "total_gravames_transferidos": len(gravames_transferidos),
        "total_irregularidades": len(irregularidades)
    }


def calc_score_localizacao(
    bairro: str,
    cidade: str,
    infraestrutura: int = 50,
    seguranca: int = 50,
    valorizacao: int = 50,
    transporte: int = 50
) -> Dict:
    """
    Calcula score de localizacao (0-100).

    Args:
        bairro: Nome do bairro
        cidade: Nome da cidade
        infraestrutura: Score de infraestrutura (0-100)
        seguranca: Score de seguranca (0-100)
        valorizacao: Potencial de valorizacao (0-100)
        transporte: Acesso a transporte (0-100)

    Returns:
        Dict com score e detalhamento
    """
    # Bairros premium de SP (score base alto)
    BAIRROS_PREMIUM = [
        "VILA MARIANA", "MOEMA", "PINHEIROS", "ITAIM BIBI", "JARDINS",
        "PERDIZES", "HIGIENOPOLIS", "BROOKLIN", "VILA OLIMPIA", "PARAISO",
        "CONSOLACAO", "SANTA CECILIA", "BELA VISTA", "LIBERDADE"
    ]

    # Bairros bons
    BAIRROS_BONS = [
        "TATUAPE", "SANTANA", "LAPA", "ACLIMACAO", "CAMBUCI", "MOOCA",
        "VILA PRUDENTE", "PENHA", "CASA VERDE", "TUCURUVI", "MANDAQUI"
    ]

    # Cidades litoral premium
    CIDADES_LITORAL_PREMIUM = ["SANTOS", "GUARUJA", "SAO VICENTE"]

    bairro_upper = bairro.upper()
    cidade_upper = cidade.upper()

    # Score base por localizacao
    if bairro_upper in BAIRROS_PREMIUM:
        score_base = 90
        categoria = "Premium"
    elif bairro_upper in BAIRROS_BONS:
        score_base = 75
        categoria = "Bom"
    elif cidade_upper in CIDADES_LITORAL_PREMIUM:
        score_base = 80
        categoria = "Litoral Premium"
    elif cidade_upper == "SAO PAULO":
        score_base = 60
        categoria = "SP Capital"
    else:
        score_base = 50
        categoria = "Outros"

    # Ajusta com subscores (media ponderada)
    subscores = {
        "infraestrutura": infraestrutura * 0.25,
        "seguranca": seguranca * 0.30,
        "valorizacao": valorizacao * 0.25,
        "transporte": transporte * 0.20
    }

    ajuste = sum(subscores.values()) / 100 * 20 - 10  # -10 a +10

    score = score_base + ajuste
    score = max(0, min(100, score))

    return {
        "score": round(score, 2),
        "score_base": score_base,
        "categoria": categoria,
        "bairro": bairro,
        "cidade": cidade,
        "subscores": {
            "infraestrutura": infraestrutura,
            "seguranca": seguranca,
            "valorizacao": valorizacao,
            "transporte": transporte
        },
        "classificacao": "Excelente" if score >= 85 else ("Boa" if score >= 70 else ("Regular" if score >= 50 else "Ruim"))
    }


def calc_score_financeiro(
    roi_percentual: float,
    margem_seguranca: float,
    desconto_percentual: float,
    tempo_retorno_meses: int = 6
) -> Dict:
    """
    Calcula score financeiro (0-100) baseado em ROI e margem.

    Args:
        roi_percentual: ROI esperado em %
        margem_seguranca: Margem de seguranca em %
        desconto_percentual: Desconto sobre avaliacao em %
        tempo_retorno_meses: Tempo para retorno

    Returns:
        Dict com score e detalhamento
    """
    score = 0
    componentes = []

    # ROI (max 50 pontos)
    # ROI 200%+ = 50 pontos, proporcional abaixo
    score_roi = min(50, roi_percentual / 4)
    score += score_roi
    componentes.append((f"ROI {roi_percentual:.1f}%", score_roi))

    # Margem de seguranca (max 25 pontos)
    # Margem 50%+ = 25 pontos, proporcional abaixo
    score_margem = min(25, margem_seguranca / 2)
    score += score_margem
    componentes.append((f"Margem {margem_seguranca:.1f}%", score_margem))

    # Desconto (max 25 pontos)
    # Desconto 50%+ = 25 pontos, proporcional abaixo
    score_desconto = min(25, desconto_percentual / 2)
    score += score_desconto
    componentes.append((f"Desconto {desconto_percentual:.1f}%", score_desconto))

    # Bonus/penalidade por tempo
    if tempo_retorno_meses <= 6:
        bonus = 5
        componentes.append(("Retorno rapido (<=6m)", 5))
    elif tempo_retorno_meses > 12:
        bonus = -10
        componentes.append(("Retorno lento (>12m)", -10))
    else:
        bonus = 0

    score += bonus
    score = max(0, min(100, score))

    # Comparativo com CDI
    cdi_6m = 6.5  # Aproximado
    diferenca_cdi = roi_percentual - cdi_6m

    return {
        "score": round(score, 2),
        "componentes": componentes,
        "roi_percentual": roi_percentual,
        "margem_seguranca": margem_seguranca,
        "desconto_percentual": desconto_percentual,
        "comparativo_cdi": {
            "cdi_6m": cdi_6m,
            "diferenca": round(diferenca_cdi, 2),
            "vezes_cdi": round(roi_percentual / cdi_6m, 1) if cdi_6m > 0 else 0
        },
        "classificacao": "Excelente" if score >= 85 else ("Bom" if score >= 70 else ("Regular" if score >= 50 else "Ruim"))
    }


def calc_score_liquidez(
    tempo_venda_dias: int = 90,
    demanda_regiao: str = "media",
    tipo_imovel: str = "Apartamento"
) -> Dict:
    """
    Calcula score de liquidez (0-100).

    Args:
        tempo_venda_dias: Tempo medio de venda na regiao
        demanda_regiao: alta, media, baixa
        tipo_imovel: Tipo do imovel

    Returns:
        Dict com score e detalhamento
    """
    score = 100
    fatores = []

    # Tempo de venda (100 - dias/2, min 0)
    score_tempo = max(0, 100 - tempo_venda_dias / 2)
    fatores.append((f"Tempo venda {tempo_venda_dias} dias", score_tempo - 50))

    # Ajuste por demanda
    demanda_ajuste = {"alta": 20, "media": 0, "baixa": -20}
    ajuste = demanda_ajuste.get(demanda_regiao.lower(), 0)
    fatores.append((f"Demanda {demanda_regiao}", ajuste))

    # Ajuste por tipo de imovel
    tipo_ajuste = {
        "Apartamento": 10,
        "Casa": 0,
        "Terreno": -10,
        "Comercial": -15
    }
    ajuste_tipo = tipo_ajuste.get(tipo_imovel, 0)
    fatores.append((f"Tipo {tipo_imovel}", ajuste_tipo))

    score = score_tempo + ajuste + ajuste_tipo
    score = max(0, min(100, score))

    return {
        "score": round(score, 2),
        "fatores": fatores,
        "tempo_venda_dias": tempo_venda_dias,
        "demanda": demanda_regiao,
        "tipo_imovel": tipo_imovel,
        "classificacao": "Alta" if score >= 70 else ("Media" if score >= 40 else "Baixa")
    }


def calc_score_oportunidade(
    score_edital: float,
    score_matricula: float,
    score_localizacao: float,
    score_financeiro: float,
    score_liquidez: float
) -> Dict:
    """
    Calcula score geral de oportunidade (0-100) ponderado.

    Args:
        score_edital: Score do edital (0-100)
        score_matricula: Score da matricula (0-100)
        score_localizacao: Score da localizacao (0-100)
        score_financeiro: Score financeiro (0-100)
        score_liquidez: Score de liquidez (0-100)

    Returns:
        Dict com score geral e classificacao
    """
    scores = {
        "edital": score_edital,
        "matricula": score_matricula,
        "localizacao": score_localizacao,
        "financeiro": score_financeiro,
        "liquidez": score_liquidez
    }

    # Calcula score ponderado
    score_geral = sum(scores[k] * PESOS_SCORE[k] for k in scores)

    # Componentes
    componentes = [
        {"nome": "Edital", "score": score_edital, "peso": f"{PESOS_SCORE['edital']*100:.0f}%", "contribuicao": score_edital * PESOS_SCORE['edital']},
        {"nome": "Matricula", "score": score_matricula, "peso": f"{PESOS_SCORE['matricula']*100:.0f}%", "contribuicao": score_matricula * PESOS_SCORE['matricula']},
        {"nome": "Localizacao", "score": score_localizacao, "peso": f"{PESOS_SCORE['localizacao']*100:.0f}%", "contribuicao": score_localizacao * PESOS_SCORE['localizacao']},
        {"nome": "Financeiro", "score": score_financeiro, "peso": f"{PESOS_SCORE['financeiro']*100:.0f}%", "contribuicao": score_financeiro * PESOS_SCORE['financeiro']},
        {"nome": "Liquidez", "score": score_liquidez, "peso": f"{PESOS_SCORE['liquidez']*100:.0f}%", "contribuicao": score_liquidez * PESOS_SCORE['liquidez']}
    ]

    return {
        "score_geral": round(score_geral, 2),
        "componentes": componentes,
        "scores_individuais": scores,
        "pesos": PESOS_SCORE
    }


def classificar_recomendacao(
    score_geral: float,
    ocupado: bool = False,
    debitos_alto: bool = False,
    roi_minimo: float = 50
) -> Dict:
    """
    Classifica recomendacao final baseado no score e fatores de risco.

    Args:
        score_geral: Score geral de oportunidade (0-100)
        ocupado: Se o imovel esta ocupado
        debitos_alto: Se tem debitos elevados
        roi_minimo: ROI minimo esperado

    Returns:
        Dict com recomendacao, nivel de risco e justificativa
    """
    # Determina recomendacao base
    if score_geral >= 75:
        recomendacao = Recomendacao.COMPRAR.value
    elif score_geral >= 50:
        recomendacao = Recomendacao.ANALISAR_MELHOR.value
    else:
        recomendacao = Recomendacao.EVITAR.value

    # Calcula nivel de risco
    fatores_risco = 0
    alertas = []

    if ocupado:
        fatores_risco += 2
        alertas.append("Imovel ocupado - risco de demora na desocupacao")

    if debitos_alto:
        fatores_risco += 2
        alertas.append("Debitos elevados no edital")

    if score_geral < 50:
        fatores_risco += 2
        alertas.append("Score geral baixo")

    # Nivel de risco
    if fatores_risco <= 2:
        nivel_risco = NivelRisco.BAIXO.value
    elif fatores_risco <= 4:
        nivel_risco = NivelRisco.MEDIO.value
    else:
        nivel_risco = NivelRisco.ALTO.value

    # Justificativa automatica
    if recomendacao == Recomendacao.COMPRAR.value:
        justificativa = f"Score de {score_geral:.0f}/100 indica excelente oportunidade. "
        if not ocupado:
            justificativa += "Imovel desocupado facilita a transacao. "
        justificativa += "Recomendamos prosseguir com analise detalhada do edital."
    elif recomendacao == Recomendacao.ANALISAR_MELHOR.value:
        justificativa = f"Score de {score_geral:.0f}/100 indica potencial, mas requer validacao adicional. "
        if alertas:
            justificativa += f"Pontos de atencao: {'; '.join(alertas[:2])}. "
        justificativa += "Sugerimos analise mais aprofundada antes de decidir."
    else:
        justificativa = f"Score de {score_geral:.0f}/100 indica oportunidade de alto risco. "
        justificativa += "Recomendamos evitar ou buscar outras opcoes."

    # Proximos passos sugeridos
    proximos_passos = []
    if recomendacao != Recomendacao.EVITAR.value:
        proximos_passos = [
            "Baixar e analisar edital completo",
            "Solicitar matricula atualizada no cartorio",
            "Pesquisar historico do imovel",
            "Visitar o imovel (exterior)",
            "Consultar advogado especialista em leiloes"
        ]
        if ocupado:
            proximos_passos.insert(2, "Verificar possibilidade de acordo com ocupante")

    return {
        "score_geral": round(score_geral, 2),
        "recomendacao": recomendacao,
        "nivel_risco": nivel_risco,
        "fatores_risco": fatores_risco,
        "alertas": alertas,
        "justificativa": justificativa,
        "proximos_passos": proximos_passos,
        "estrelas": "★" * (5 if score_geral >= 80 else (4 if score_geral >= 70 else (3 if score_geral >= 60 else (2 if score_geral >= 50 else 1))))
    }


# Exemplo de uso
if __name__ == "__main__":
    import json

    # Testa scores individuais
    edital = calc_score_edital(
        ocupacao="ocupado",
        debitos_total=17000,
        riscos=["Debito condominio elevado"]
    )
    print("Score Edital:", json.dumps(edital, indent=2))

    matricula = calc_score_matricula(
        gravames_extintos=["Hipoteca CEF"],
        gravames_transferidos=["Penhora fiscal"],
        valor_gravames=8000
    )
    print("\nScore Matricula:", json.dumps(matricula, indent=2))

    localizacao = calc_score_localizacao(
        bairro="VILA MARIANA",
        cidade="SAO PAULO",
        infraestrutura=85,
        seguranca=80,
        valorizacao=90,
        transporte=95
    )
    print("\nScore Localizacao:", json.dumps(localizacao, indent=2))

    financeiro = calc_score_financeiro(
        roi_percentual=130,
        margem_seguranca=64,
        desconto_percentual=40
    )
    print("\nScore Financeiro:", json.dumps(financeiro, indent=2))

    liquidez = calc_score_liquidez(
        tempo_venda_dias=60,
        demanda_regiao="alta",
        tipo_imovel="Apartamento"
    )
    print("\nScore Liquidez:", json.dumps(liquidez, indent=2))

    # Score geral
    geral = calc_score_oportunidade(
        score_edital=edital["score"],
        score_matricula=matricula["score"],
        score_localizacao=localizacao["score"],
        score_financeiro=financeiro["score"],
        score_liquidez=liquidez["score"]
    )
    print("\nScore Geral:", json.dumps(geral, indent=2))

    # Recomendacao
    rec = classificar_recomendacao(
        score_geral=geral["score_geral"],
        ocupado=True,
        debitos_alto=True
    )
    print("\nRecomendacao:", json.dumps(rec, indent=2, ensure_ascii=False))
