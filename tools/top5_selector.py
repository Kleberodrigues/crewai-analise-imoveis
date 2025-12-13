"""
Top 5 Selector - Seleciona as 5 melhores oportunidades de imoveis
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calcular_score_oportunidade(imovel: Dict) -> float:
    """
    Calcula score de oportunidade composto para ranking.

    Combina:
    - Score geral (40%)
    - Margem de seguranca (25%)
    - ROI (20%)
    - Desconto (15%)

    Returns:
        Score de 0-100
    """
    scores = imovel.get("scores", {})
    custos = imovel.get("custos", {})
    resultado = custos.get("resultado_venda", {})

    score_geral = scores.get("geral", 0)
    margem = resultado.get("margem_seguranca_percentual", 0)
    roi = resultado.get("roi_total_percentual", 0)
    desconto = imovel.get("desconto", 0)

    # Normaliza valores para 0-100
    margem_norm = min(margem, 100)  # Cap em 100
    roi_norm = min(roi / 2, 100)     # 200% ROI = 100 pontos
    desconto_norm = min(desconto * 2, 100)  # 50% desconto = 100 pontos

    # Score composto
    score_oportunidade = (
        score_geral * 0.40 +
        margem_norm * 0.25 +
        roi_norm * 0.20 +
        desconto_norm * 0.15
    )

    return round(score_oportunidade, 2)


def filtrar_candidatos(imoveis: List[Dict], config: Optional[Dict] = None) -> List[Dict]:
    """
    Filtra imoveis que atendem aos criterios minimos de qualidade.

    Args:
        imoveis: Lista de imoveis analisados
        config: Configuracoes de filtro opcionais

    Returns:
        Lista de imoveis que passaram nos filtros
    """
    if config is None:
        config = {}

    # Criterios de filtro (podem ser customizados)
    score_minimo = config.get("score_minimo", 55)
    recomendacoes_aceitas = config.get("recomendacoes", ["COMPRAR", "ANALISAR_MELHOR"])
    risco_maximo = config.get("risco_maximo", ["BAIXO", "MEDIO"])
    valor_penhoras_max = config.get("valor_penhoras_max", 80000)

    candidatos = []

    for imovel in imoveis:
        # Verifica recomendacao
        recomendacao = imovel.get("recomendacao", "")
        if recomendacao not in recomendacoes_aceitas:
            continue

        # Verifica score minimo
        scores = imovel.get("scores", {})
        score_geral = scores.get("geral", 0)
        if score_geral < score_minimo:
            continue

        # Verifica nivel de risco
        nivel_risco = imovel.get("nivel_risco", "ALTO")
        if nivel_risco not in risco_maximo:
            continue

        # Verifica valor de penhoras/gravames
        matricula = imovel.get("analise_matricula", {})
        valor_gravames = matricula.get("valor_gravames", 0)
        if valor_gravames > valor_penhoras_max:
            continue

        candidatos.append(imovel)

    logger.info(f"Filtrados {len(candidatos)} candidatos de {len(imoveis)} imoveis")
    return candidatos


def selecionar_top5(
    imoveis_analisados: List[Dict],
    quantidade: int = 5,
    config: Optional[Dict] = None
) -> List[Dict]:
    """
    Seleciona as N melhores oportunidades de imoveis.

    Criterios de selecao:
    1. Filtra por recomendacao (COMPRAR ou ANALISAR_MELHOR)
    2. Filtra por score minimo (>= 55)
    3. Filtra por nivel de risco (BAIXO ou MEDIO)
    4. Filtra por valor maximo de penhoras (R$ 80.000)
    5. Ordena por score de oportunidade composto
    6. Retorna top N

    Args:
        imoveis_analisados: Lista completa de imoveis analisados
        quantidade: Numero de imoveis a selecionar (default: 5)
        config: Configuracoes customizadas de filtro

    Returns:
        Lista com os top N imoveis ordenados por score
    """
    if not imoveis_analisados:
        logger.warning("Lista de imoveis vazia")
        return []

    # Aplica filtros de qualidade
    candidatos = filtrar_candidatos(imoveis_analisados, config)

    if not candidatos:
        logger.warning("Nenhum imovel passou nos filtros de qualidade")
        # Fallback: pega os melhores mesmo sem passar nos filtros
        candidatos = sorted(
            imoveis_analisados,
            key=lambda x: x.get("scores", {}).get("geral", 0),
            reverse=True
        )[:quantidade]
        for c in candidatos:
            c["_nota_selecao"] = "Selecionado por fallback (nenhum passou nos filtros)"

    # Calcula score de oportunidade para cada candidato
    for candidato in candidatos:
        candidato["score_oportunidade"] = calcular_score_oportunidade(candidato)

    # Ordena por score de oportunidade (maior para menor)
    candidatos_ordenados = sorted(
        candidatos,
        key=lambda x: (
            x.get("score_oportunidade", 0),
            x.get("scores", {}).get("geral", 0),
            x.get("custos", {}).get("resultado_venda", {}).get("margem_seguranca_percentual", 0),
            x.get("custos", {}).get("resultado_venda", {}).get("roi_total_percentual", 0)
        ),
        reverse=True
    )

    # Seleciona top N
    top_n = candidatos_ordenados[:quantidade]

    # Adiciona ranking
    for i, imovel in enumerate(top_n, 1):
        imovel["ranking_top5"] = i

    logger.info(f"Selecionados top {len(top_n)} de {len(candidatos)} candidatos")

    return top_n


def gerar_resumo_selecao(top_imoveis: List[Dict], total_analisados: int) -> Dict:
    """
    Gera resumo estatistico da selecao.

    Args:
        top_imoveis: Lista dos imoveis selecionados
        total_analisados: Total de imoveis analisados

    Returns:
        Dict com estatisticas da selecao
    """
    if not top_imoveis:
        return {
            "total_analisados": total_analisados,
            "total_selecionados": 0,
            "taxa_selecao": 0,
            "resumo": "Nenhum imovel selecionado"
        }

    # Estatisticas
    scores = [i.get("score_oportunidade", 0) for i in top_imoveis]
    rois = [i.get("custos", {}).get("resultado_venda", {}).get("roi_total_percentual", 0) for i in top_imoveis]
    margens = [i.get("custos", {}).get("resultado_venda", {}).get("margem_seguranca_percentual", 0) for i in top_imoveis]
    descontos = [i.get("desconto", 0) for i in top_imoveis]
    investimentos = [i.get("custos", {}).get("investimento_total", 0) for i in top_imoveis]

    # Contagem por recomendacao
    recomendacoes = {}
    for i in top_imoveis:
        rec = i.get("recomendacao", "OUTRO")
        recomendacoes[rec] = recomendacoes.get(rec, 0) + 1

    # Contagem por cidade
    cidades = {}
    for i in top_imoveis:
        cidade = i.get("cidade", "OUTRA")
        cidades[cidade] = cidades.get(cidade, 0) + 1

    resumo = {
        "data_selecao": datetime.now().isoformat(),
        "total_analisados": total_analisados,
        "total_selecionados": len(top_imoveis),
        "taxa_selecao_pct": round(len(top_imoveis) / total_analisados * 100, 1) if total_analisados > 0 else 0,
        "estatisticas": {
            "score_oportunidade": {
                "min": round(min(scores), 1),
                "max": round(max(scores), 1),
                "media": round(sum(scores) / len(scores), 1)
            },
            "roi_percentual": {
                "min": round(min(rois), 1),
                "max": round(max(rois), 1),
                "media": round(sum(rois) / len(rois), 1)
            },
            "margem_seguranca_pct": {
                "min": round(min(margens), 1),
                "max": round(max(margens), 1),
                "media": round(sum(margens) / len(margens), 1)
            },
            "desconto_pct": {
                "min": round(min(descontos), 1),
                "max": round(max(descontos), 1),
                "media": round(sum(descontos) / len(descontos), 1)
            },
            "investimento_total": {
                "min": round(min(investimentos), 2),
                "max": round(max(investimentos), 2),
                "media": round(sum(investimentos) / len(investimentos), 2),
                "total": round(sum(investimentos), 2)
            }
        },
        "distribuicao_recomendacao": recomendacoes,
        "distribuicao_cidade": cidades,
        "ids_selecionados": [i.get("id_imovel") for i in top_imoveis]
    }

    return resumo


# Exemplo de uso
if __name__ == "__main__":
    import json

    # Dados de exemplo
    imoveis_exemplo = [
        {
            "id_imovel": "123456",
            "endereco": "Rua A, 100",
            "cidade": "SAO PAULO",
            "bairro": "Vila Mariana",
            "desconto": 45,
            "recomendacao": "COMPRAR",
            "nivel_risco": "BAIXO",
            "scores": {"geral": 82, "financeiro": 90, "localizacao": 85},
            "custos": {
                "investimento_total": 180000,
                "resultado_venda": {
                    "roi_total_percentual": 125,
                    "margem_seguranca_percentual": 55
                }
            },
            "analise_matricula": {"valor_gravames": 10000}
        },
        {
            "id_imovel": "789012",
            "endereco": "Rua B, 200",
            "cidade": "SANTOS",
            "bairro": "Gonzaga",
            "desconto": 38,
            "recomendacao": "COMPRAR",
            "nivel_risco": "MEDIO",
            "scores": {"geral": 78, "financeiro": 85, "localizacao": 80},
            "custos": {
                "investimento_total": 150000,
                "resultado_venda": {
                    "roi_total_percentual": 95,
                    "margem_seguranca_percentual": 42
                }
            },
            "analise_matricula": {"valor_gravames": 20000}
        },
        {
            "id_imovel": "345678",
            "endereco": "Rua C, 300",
            "cidade": "SAO PAULO",
            "bairro": "Mooca",
            "desconto": 50,
            "recomendacao": "ANALISAR_MELHOR",
            "nivel_risco": "MEDIO",
            "scores": {"geral": 65, "financeiro": 75, "localizacao": 70},
            "custos": {
                "investimento_total": 120000,
                "resultado_venda": {
                    "roi_total_percentual": 80,
                    "margem_seguranca_percentual": 35
                }
            },
            "analise_matricula": {"valor_gravames": 5000}
        }
    ]

    # Seleciona top 5
    top5 = selecionar_top5(imoveis_exemplo, quantidade=5)

    print("=== TOP 5 SELECIONADOS ===")
    for i in top5:
        print(f"\n#{i['ranking_top5']} - {i['id_imovel']}")
        print(f"   Endereco: {i['endereco']}")
        print(f"   Score Oportunidade: {i['score_oportunidade']}")
        print(f"   Recomendacao: {i['recomendacao']}")

    # Gera resumo
    resumo = gerar_resumo_selecao(top5, len(imoveis_exemplo))
    print("\n=== RESUMO DA SELECAO ===")
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
