"""
Pipeline Principal - Analise de Leilao de Imoveis
Executa coleta, analise e geracao de relatorios automaticamente
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Adiciona diretorio ao path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Imports das tools
from tools.data_tools import (
    download_csv_caixa, parse_csv_imoveis, filter_imoveis,
    executar_coleta_multifonte_sync,
    pesquisar_mercado, comparar_imovel_mercado  # Novo: pesquisa de mercado real
)
from tools.calc_tools import calc_custos_totais
from tools.score_tools import (
    calc_score_edital, calc_score_matricula, calc_score_localizacao,
    calc_score_financeiro, calc_score_liquidez, calc_score_oportunidade,
    classificar_recomendacao
)
from tools.output_tools import (
    generate_csv_report, generate_pdf_report, generate_summary_csv,
    gerar_csv_top5, gerar_pdf_top5_consolidado
)
from tools.top5_selector import selecionar_top5, gerar_resumo_selecao
from tools.market_tools import buscar_preco_mercado_web, calcular_liquidez_mercado
from tools.document_tools import (
    analisar_documento_imovel, calcular_custos_documentacao, gerar_relatorio_matricula,
    analisar_edital_completo, extrair_edital_pagina
)

# Imports Supabase
from supabase import create_client, Client

# Configuracoes
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Cidades alvo
CIDADES_CAPITAL = ["SAO PAULO"]
CIDADES_LITORAL = [
    "SANTOS", "GUARUJA", "PRAIA GRANDE", "SAO VICENTE", "BERTIOGA",
    "UBATUBA", "CARAGUATATUBA", "MONGAGUA", "ITANHAEM", "PERUIBE"
]
CIDADES_ALVO = CIDADES_CAPITAL + CIDADES_LITORAL

# Criterios de filtragem (AJUSTADO para ter mais resultados)
FILTROS = {
    "preco_max": 500000,  # Aumentado para R$ 500k (mercado atual mais caro)
    "tipo": None,  # Aceita todos os tipos (apartamento, casa, comercial, etc)
    "praca": None,  # Aceita 1a e 2a praca
    "desconto_min": 0  # Aceita qualquer desconto
}


class PipelineLeilao:
    """Pipeline completo de analise de leiloes"""

    def __init__(self):
        self.supabase: Optional[Client] = None
        self.imoveis_coletados: List[Dict] = []
        self.imoveis_analisados: List[Dict] = []
        self.stats = {
            "inicio": datetime.now().isoformat(),
            "fonte_caixa": 0,
            "fonte_zuk": 0,
            "fonte_superbid": 0,
            "fonte_megaleiloes": 0,
            "fonte_frazao": 0,
            "fonte_biasi": 0,
            "total_scrapers": 0,
            "total_filtrado": 0,
            "total_analisado": 0,
            "recomendados": 0
        }

        # Inicializa Supabase (com timeout para evitar travamento em DNS)
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                import socket
                # Testa DNS antes de conectar (timeout 5s)
                host = SUPABASE_URL.replace("https://", "").replace("http://", "").split("/")[0]
                socket.setdefaulttimeout(5)
                socket.getaddrinfo(host, 443)
                socket.setdefaulttimeout(None)

                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Supabase conectado")
            except socket.gaierror:
                logger.warning(f"Supabase DNS nao resolvido - projeto pode estar pausado. Continuando sem Supabase...")
            except Exception as e:
                logger.warning(f"Supabase indisponivel: {e}. Pipeline continuara sem persistencia.")

    def coletar_caixa(self) -> List[Dict]:
        """Coleta imoveis do CSV da Caixa"""
        logger.info("=" * 50)
        logger.info("ETAPA 1: Coleta de dados da Caixa")
        logger.info("=" * 50)

        try:
            # Download do CSV
            result = download_csv_caixa("SP", force=False)

            if result.get("status") in ["cached", "updated", "no_changes"]:
                filepath = result.get("filepath")
                logger.info(f"CSV obtido: {filepath}")

                # Parse
                imoveis = parse_csv_imoveis(filepath)
                logger.info(f"Total parseado: {len(imoveis)}")

                # Filtra
                filtrado = filter_imoveis(
                    imoveis,
                    preco_max=FILTROS["preco_max"],
                    tipo=FILTROS["tipo"],
                    praca=FILTROS["praca"],
                    cidades=CIDADES_ALVO
                )

                imoveis_filtrados = filtrado.get("imoveis", [])
                self.stats["fonte_caixa"] = len(imoveis_filtrados)

                logger.info(f"Filtrados Caixa: {len(imoveis_filtrados)}")
                logger.info(f"Stats: {filtrado.get('stats')}")

                return imoveis_filtrados

            else:
                logger.error(f"Erro no download: {result}")
                return []

        except Exception as e:
            logger.error(f"Erro na coleta Caixa: {e}")
            return []

    def coletar_multifonte(self, usar_scrapers: bool = True) -> List[Dict]:
        """
        Coleta imoveis de multiplas fontes (Web Scrapers).

        Args:
            usar_scrapers: Se True, usa os 5 web scrapers (Zuk, Superbid, etc.)

        Returns:
            Lista de imoveis coletados de todas as fontes
        """
        logger.info("=" * 50)
        logger.info("ETAPA 2: Coleta Multi-Fonte (Web Scrapers)")
        logger.info("=" * 50)

        if not usar_scrapers:
            logger.info("Web Scrapers desabilitados")
            return []

        try:
            logger.info("Executando scrapers: Zuk, Superbid, Mega Leiloes, Frazao, Biasi")

            resultado = executar_coleta_multifonte_sync(
                estado="SP",
                preco_max=FILTROS["preco_max"],
                incluir_caixa=False,  # Caixa ja foi coletada separadamente
                max_por_fonte=30
            )

            imoveis = resultado.get("imoveis", [])
            stats_fontes = resultado.get("stats", {})

            # Atualiza stats do pipeline
            self.stats["fonte_zuk"] = stats_fontes.get("fonte_zuk", 0)
            self.stats["fonte_superbid"] = stats_fontes.get("fonte_superbid", 0)
            self.stats["fonte_megaleiloes"] = stats_fontes.get("fonte_megaleiloes", 0)
            self.stats["fonte_frazao"] = stats_fontes.get("fonte_frazao", 0)
            self.stats["fonte_biasi"] = stats_fontes.get("fonte_biasi", 0)
            self.stats["total_scrapers"] = len(imoveis)

            logger.info(f"Total coletado dos scrapers: {len(imoveis)}")
            logger.info(f"  Zuk: {stats_fontes.get('fonte_zuk', 0)}")
            logger.info(f"  Superbid: {stats_fontes.get('fonte_superbid', 0)}")
            logger.info(f"  Mega Leiloes: {stats_fontes.get('fonte_megaleiloes', 0)}")
            logger.info(f"  Frazao: {stats_fontes.get('fonte_frazao', 0)}")
            logger.info(f"  Biasi: {stats_fontes.get('fonte_biasi', 0)}")

            if stats_fontes.get("erros"):
                logger.warning(f"Erros nos scrapers: {stats_fontes['erros']}")

            return imoveis

        except Exception as e:
            logger.error(f"Erro na coleta multi-fonte: {e}")
            return []

    def coletar_zuk(self) -> List[Dict]:
        """
        Metodo legado - agora usa coletar_multifonte.
        Mantido para compatibilidade.
        """
        # Usa o novo sistema multi-fonte
        # Scrapers habilitados para coleta completa
        return self.coletar_multifonte(usar_scrapers=True)

    def consolidar_imoveis(self, caixa: List[Dict], zuk: List[Dict]) -> List[Dict]:
        """Consolida e remove duplicatas"""
        logger.info("=" * 50)
        logger.info("ETAPA 3: Consolidacao de imoveis")
        logger.info("=" * 50)

        todos = caixa + zuk

        # Remove duplicatas por endereco similar
        unicos = {}
        for imovel in todos:
            key = f"{imovel.get('bairro', '')}_{imovel.get('preco', 0)}"
            if key not in unicos:
                unicos[key] = imovel
            else:
                # Mantem o com mais informacoes
                if len(str(imovel)) > len(str(unicos[key])):
                    unicos[key] = imovel

        self.imoveis_coletados = list(unicos.values())
        self.stats["total_filtrado"] = len(self.imoveis_coletados)

        logger.info(f"Total consolidado: {len(self.imoveis_coletados)}")

        return self.imoveis_coletados

    def analisar_imovel(self, imovel: Dict) -> Dict:
        """Analisa um imovel individualmente"""
        logger.info(f"Analisando: {imovel.get('endereco', 'N/A')[:50]}...")

        try:
            # Dados basicos
            preco = imovel.get("preco", 0)
            cidade = imovel.get("cidade", "SAO PAULO")
            area = imovel.get("area_privativa", 50)
            bairro = imovel.get("bairro", "")
            desconto = imovel.get("desconto", 0)
            quartos = imovel.get("quartos", 2)
            imovel_id = imovel.get("id_imovel", "")

            # === ANALISE DE MATRICULA REAL ===
            doc_analise = None
            matricula_riscos = []
            matricula_score_risco = 0
            custos_documentacao = {}
            penhoras_total = 0
            dividas_matricula = 0

            if imovel_id:
                # Tenta baixar e analisar matricula
                doc_result = analisar_documento_imovel(imovel_id, "SP")

                if doc_result.get("matricula_disponivel") and doc_result.get("analise"):
                    doc_analise = doc_result["analise"]
                    matricula_riscos = doc_analise.get("riscos", [])
                    matricula_score_risco = doc_analise.get("score_risco", 0)

                    # Calcula custos de documentacao
                    custos_documentacao = calcular_custos_documentacao(doc_analise, preco)
                    penhoras_total = custos_documentacao.get("penhoras", 0)
                    dividas_matricula = custos_documentacao.get("dividas_matricula", 0)

                    logger.info(f"  Matricula analisada - Risco: {doc_analise.get('classificacao_risco', 'N/I')}")
                else:
                    logger.info(f"  Matricula nao disponivel - usando estimativas")

            # === ANALISE DO EDITAL (PAGINA DO IMOVEL) ===
            edital_dados = None
            edital_riscos = []
            limite_condominio_caixa = 10  # default 10%

            if imovel_id:
                edital_dados = extrair_edital_pagina(imovel_id)
                if edital_dados and not edital_dados.get('erro'):
                    edital_riscos = []
                    if edital_dados.get('gravames_matricula'):
                        edital_riscos.append("Gravames na matricula (edital)")
                    if edital_dados.get('regularizacao_comprador'):
                        edital_riscos.append("Regularizacao por conta do comprador")
                    limite_condominio_caixa = edital_dados.get('limite_condominio_caixa_percentual', 10)
                    logger.info(f"  Edital extraido - Limite cond: {limite_condominio_caixa}%")

            # Combina analises de matricula e edital
            # Se temos matricula, usamos dados reais de dividas
            if doc_analise:
                ocupado = True  # Caixa geralmente vende ocupado
                debitos_iptu = 5000  # Ainda estimativa (nao vem na matricula)
                debitos_cond = dividas_matricula if dividas_matricula > 0 else 10000
                total_debitos = debitos_iptu + debitos_cond + penhoras_total
                riscos_edital = matricula_riscos + edital_riscos + ["Imovel ocupado (estimado)"]
            else:
                ocupado = True
                debitos_iptu = 5000
                debitos_cond = 10000
                total_debitos = debitos_iptu + debitos_cond
                riscos_edital = edital_riscos + ["Imovel ocupado", "Debitos estimados", "Matricula nao analisada"]

            edital = calc_score_edital(
                ocupacao="ocupado",
                debitos_total=total_debitos,
                riscos=riscos_edital,
                comissao_leiloeiro=5.0
            )

            # Analise de matricula (com dados reais se disponivel)
            if doc_analise:
                gravames = doc_analise.get("gravames", [])
                penhoras = doc_analise.get("penhoras", [])

                matricula = calc_score_matricula(
                    gravames_extintos=["Alienacao Fiduciaria CEF"] if doc_analise.get("consolidacao_propriedade") else [],
                    gravames_transferidos=[g.get("tipo", "Gravame") for g in gravames],
                    valor_gravames=penhoras_total
                )
            else:
                matricula = calc_score_matricula(
                    gravames_extintos=["Hipoteca CEF"],
                    gravames_transferidos=[],
                    valor_gravames=0
                )

            # Analise de localizacao
            localizacao = calc_score_localizacao(
                bairro=bairro,
                cidade=cidade,
                infraestrutura=70,
                seguranca=70,
                valorizacao=75,
                transporte=80
            )

            # PESQUISA DE MERCADO REAL - Web Scraping (VivaReal, ZapImoveis, OLX)
            logger.info(f"  Pesquisando mercado para {bairro}, {cidade}...")
            mercado_real = pesquisar_mercado(
                bairro=bairro,
                cidade=cidade.lower().replace(" ", "-"),
                uf="sp",
                tipo="apartamento",
                quartos=quartos,
                area_m2=area,
                fontes=['vivareal', 'olx']  # Usa VivaReal + OLX + fallback FipeZap
            )

            # Compara com dados do imovel de leilao
            comparacao = comparar_imovel_mercado(imovel, mercado_real)

            # Extrai dados do mercado para uso posterior
            mercado = {
                "preco_m2": mercado_real.get("preco_m2", {}).get("medio", 5000),
                "valor_estimado": mercado_real.get("valor_estimado", {}).get("valor", area * 5000),
                "preco_m2_min": mercado_real.get("precos", {}).get("minimo", 0) / area if area > 0 else 0,
                "preco_m2_max": mercado_real.get("precos", {}).get("maximo", 0) / area if area > 0 else 0,
                "valor_min": mercado_real.get("precos", {}).get("minimo", 0),
                "valor_max": mercado_real.get("precos", {}).get("maximo", 0),
                "condominio_estimado": 500 if area < 60 else 700,
                "iptu_estimado": 150 if area < 60 else 200,
                "fonte": mercado_real.get("fonte", "estimativa"),
                "confianca": "alta" if mercado_real.get("status") == "sucesso" else "media",
                "amostras": mercado_real.get("total_encontrados", 0),
                "imoveis_similares": mercado_real.get("imoveis", [])[:5]
            }

            logger.info(f"  Mercado: {mercado['fonte']} - R$ {mercado['preco_m2']:.2f}/m2")

            # Dados de liquidez (usa mesma fonte)
            liquidez_mercado = {
                "tempo_venda_estimado_dias": 90 if mercado_real.get("total_encontrados", 0) > 5 else 120,
                "demanda": "alta" if mercado_real.get("total_encontrados", 0) > 10 else "media",
                "liquidez": "alta" if comparacao.get("classificacao_oportunidade") in ["EXCELENTE", "MUITO_BOA"] else "media",
                "dificuldade_venda": "facil" if comparacao.get("desconto_vs_mercado", 0) > 30 else "moderada"
            }

            preco_m2 = mercado.get("preco_m2", 5000)
            valor_mercado = mercado.get("valor_estimado", area * preco_m2)
            condominio = mercado.get("condominio_estimado", 500 if area < 60 else 700)
            iptu_mensal = mercado.get("iptu_estimado", 150 if area < 60 else 200)
            aluguel = area * 35  # R$ 35/m2
            tempo_venda = liquidez_mercado.get("tempo_venda_estimado_dias", 90)

            # Calculo de custos
            custos = calc_custos_totais(
                valor_arrematacao=preco,
                cidade=cidade,
                ocupado=ocupado,
                debitos_edital=total_debitos,
                gravames_matricula=0,
                area_m2=area,
                custo_reforma_m2=300,
                preco_venda_estimado=valor_mercado * 0.95,  # -5% para venda rapida
                condominio_mensal=condominio,
                iptu_mensal=iptu_mensal,
                meses_manutencao=6
            )

            # Score financeiro
            roi = custos.get("resultado_venda", {}).get("roi_total_percentual", 0)
            margem = custos.get("resultado_venda", {}).get("margem_seguranca_percentual", 0)

            financeiro = calc_score_financeiro(
                roi_percentual=roi,
                margem_seguranca=margem,
                desconto_percentual=desconto
            )

            # Score liquidez (usando dados reais de mercado)
            liquidez = calc_score_liquidez(
                tempo_venda_dias=tempo_venda,
                demanda_regiao=liquidez_mercado.get("demanda", "media"),
                tipo_imovel=imovel.get("tipo_imovel", "Apartamento")
            )

            # Score geral
            score_geral = calc_score_oportunidade(
                score_edital=edital["score"],
                score_matricula=matricula["score"],
                score_localizacao=localizacao["score"],
                score_financeiro=financeiro["score"],
                score_liquidez=liquidez["score"]
            )

            # Recomendacao final
            recomendacao = classificar_recomendacao(
                score_geral=score_geral["score_geral"],
                ocupado=ocupado,
                debitos_alto=total_debitos > 15000,
                roi_minimo=50
            )

            # Monta resultado completo
            analise = {
                **imovel,
                "data_analise": datetime.now().strftime("%Y-%m-%d"),
                "analise_edital": {
                    "edital_disponivel": edital_dados is not None and not edital_dados.get('erro'),
                    "modalidade_venda": edital_dados.get('modalidade_venda', 'Venda Online') if edital_dados else 'Venda Online',
                    "ocupacao": "ocupado",
                    "debitos_iptu": debitos_iptu,
                    "debitos_condominio": debitos_cond,
                    "total_debitos": total_debitos,
                    "comissao_leiloeiro_pct": 0,  # Venda Online nao tem leiloeiro
                    "formas_pagamento": edital_dados.get('formas_pagamento', []) if edital_dados else [],
                    "aceita_financiamento": edital_dados.get('aceita_financiamento', False) if edital_dados else False,
                    "limite_condominio_caixa_pct": limite_condominio_caixa,
                    "regras_condominio": edital_dados.get('regras_condominio') if edital_dados else None,
                    "regras_tributos": edital_dados.get('regras_tributos') if edital_dados else None,
                    "gravames_informados": edital_dados.get('gravames_matricula', False) if edital_dados else False,
                    "regularizacao_comprador": edital_dados.get('regularizacao_comprador', True) if edital_dados else True,
                    "riscos": riscos_edital,
                    "score": edital["score"]
                },
                "analise_matricula": {
                    "matricula_disponivel": doc_analise is not None,
                    "numero_matricula": doc_analise.get("matricula_numero") if doc_analise else None,
                    "gravames_extintos": ["Alienacao Fiduciaria CEF"] if doc_analise and doc_analise.get("consolidacao_propriedade") else ["Hipoteca CEF"],
                    "gravames_transferidos": [g.get("tipo") for g in doc_analise.get("gravames", [])] if doc_analise else [],
                    "penhoras": doc_analise.get("penhoras", []) if doc_analise else [],
                    "dividas_identificadas": doc_analise.get("dividas_identificadas", []) if doc_analise else [],
                    "valor_gravames": penhoras_total,
                    "score_risco_documento": matricula_score_risco,
                    "classificacao_risco": doc_analise.get("classificacao_risco", "NAO_ANALISADO") if doc_analise else "NAO_ANALISADO",
                    "riscos_documento": matricula_riscos,
                    "custos_documentacao": custos_documentacao,
                    "score": matricula["score"]
                },
                "pesquisa_mercado": {
                    "preco_m2": preco_m2,
                    "preco_m2_min": mercado.get("preco_m2_min", int(preco_m2 * 0.85)),
                    "preco_m2_max": mercado.get("preco_m2_max", int(preco_m2 * 1.15)),
                    "valor_estimado": valor_mercado,
                    "valor_min": mercado.get("valor_min", valor_mercado * 0.85),
                    "valor_max": mercado.get("valor_max", valor_mercado * 1.15),
                    "condominio_mensal": condominio,
                    "iptu_mensal": iptu_mensal,
                    "aluguel_estimado": aluguel,
                    "liquidez": liquidez_mercado.get("liquidez", "media"),
                    "tempo_venda_dias": tempo_venda,
                    "demanda": liquidez_mercado.get("demanda", "media"),
                    "dificuldade_venda": liquidez_mercado.get("dificuldade_venda", "moderada"),
                    "fonte": mercado.get("fonte", "estimativa"),
                    "confianca": mercado.get("confianca", "baixa"),
                    "amostras": mercado.get("amostras", 0),
                    "imoveis_similares": mercado.get("imoveis_similares", []),
                    "score_localizacao": localizacao["score"],
                    "score_liquidez": liquidez["score"],
                    # Novos dados de comparacao
                    "comparacao_mercado": {
                        "desconto_vs_mercado_pct": comparacao.get("desconto_vs_mercado", 0),
                        "lucro_bruto_potencial": comparacao.get("lucro_bruto_potencial", 0),
                        "margem_bruta_pct": comparacao.get("margem_bruta_pct", 0),
                        "classificacao_oportunidade": comparacao.get("classificacao_oportunidade", "N/A"),
                        "total_comparaveis": comparacao.get("total_comparaveis", 0)
                    }
                },
                "custos": custos,
                "scores": {
                    "edital": edital["score"],
                    "matricula": matricula["score"],
                    "localizacao": localizacao["score"],
                    "financeiro": financeiro["score"],
                    "liquidez": liquidez["score"],
                    "geral": score_geral["score_geral"]
                },
                "recomendacao": recomendacao["recomendacao"],
                "nivel_risco": recomendacao["nivel_risco"],
                "justificativa": recomendacao["justificativa"],
                "pontos_atencao": recomendacao["alertas"],
                "proximos_passos": recomendacao["proximos_passos"]
            }

            return analise

        except Exception as e:
            logger.error(f"Erro ao analisar imovel: {e}")
            return {**imovel, "error": str(e)}

    def analisar_todos(self):
        """Analisa todos os imoveis coletados"""
        logger.info("=" * 50)
        logger.info("ETAPA 4: Analise de imoveis")
        logger.info("=" * 50)

        self.imoveis_analisados = []

        for i, imovel in enumerate(self.imoveis_coletados, 1):
            logger.info(f"[{i}/{len(self.imoveis_coletados)}]")
            analise = self.analisar_imovel(imovel)

            if "error" not in analise:
                self.imoveis_analisados.append(analise)

                if analise.get("recomendacao") == "COMPRAR":
                    self.stats["recomendados"] += 1

        self.stats["total_analisado"] = len(self.imoveis_analisados)
        logger.info(f"Total analisado: {len(self.imoveis_analisados)}")
        logger.info(f"Recomendados (COMPRAR): {self.stats['recomendados']}")

    def gerar_relatorios(self):
        """Gera relatorios CSV e PDF"""
        logger.info("=" * 50)
        logger.info("ETAPA 5: Geracao de relatorios")
        logger.info("=" * 50)

        # CSV completo
        csv_result = generate_csv_report(self.imoveis_analisados)
        logger.info(f"CSV gerado: {csv_result.get('filepath')}")

        # CSV resumido
        summary_result = generate_summary_csv(self.imoveis_analisados)
        logger.info(f"Resumo CSV: {summary_result.get('filepath')}")

        # PDFs para imoveis recomendados
        recomendados = [a for a in self.imoveis_analisados if a.get("recomendacao") == "COMPRAR"]

        for imovel in recomendados[:10]:  # Top 10
            pdf_result = generate_pdf_report(imovel)
            logger.info(f"PDF gerado: {pdf_result.get('filepath')}")

        # ============================================================
        # TOP 5 - Selecao e Relatorios Consolidados
        # ============================================================
        logger.info("-" * 50)
        logger.info("Gerando relatorios TOP 5...")

        # Seleciona os top 5 melhores oportunidades
        top5 = selecionar_top5(self.imoveis_analisados, quantidade=5)
        logger.info(f"Top 5 selecionados: {len(top5)} imoveis")

        # Gera resumo estatistico
        resumo_top5 = gerar_resumo_selecao(top5, len(self.imoveis_analisados))

        # Gera CSV Top 5
        csv_top5_result = gerar_csv_top5(top5)
        logger.info(f"CSV Top 5: {csv_top5_result.get('filepath')}")

        # Gera PDF consolidado Top 5
        pdf_top5_result = gerar_pdf_top5_consolidado(
            top5,
            titulo="Top 5 Oportunidades de Leilao",
            resumo_selecao=resumo_top5
        )
        logger.info(f"PDF Top 5: {pdf_top5_result.get('filepath')}")

        # Atualiza stats
        self.stats["top5_selecionados"] = len(top5)
        self.stats["top5_ids"] = [i.get("id_imovel") for i in top5]

        # Log do resumo
        if resumo_top5.get("estatisticas"):
            stats_top5 = resumo_top5["estatisticas"]
            logger.info(f"  Score medio: {stats_top5.get('score_oportunidade', {}).get('media', 0):.1f}")
            logger.info(f"  ROI medio: {stats_top5.get('roi_percentual', {}).get('media', 0):.1f}%")
            logger.info(f"  Margem media: {stats_top5.get('margem_seguranca_pct', {}).get('media', 0):.1f}%")

        return {
            "csv": csv_result,
            "summary": summary_result,
            "pdfs_gerados": len(recomendados[:10]),
            "top5": {
                "csv": csv_top5_result,
                "pdf": pdf_top5_result,
                "resumo": resumo_top5,
                "analises_completas": top5  # Lista completa dos 5 imoveis com todos os dados
            }
        }

    def salvar_supabase(self):
        """Salva resultados no Supabase"""
        if not self.supabase:
            logger.warning("Supabase nao conectado, pulando salvamento")
            return

        logger.info("=" * 50)
        logger.info("ETAPA 6: Salvamento no Supabase")
        logger.info("=" * 50)

        try:
            # Salva imoveis
            for imovel in self.imoveis_analisados:
                # Prepara dados para inserir
                data = {
                    "id_imovel": imovel.get("id_imovel"),
                    "uf": "SP",
                    "cidade": imovel.get("cidade"),
                    "bairro": imovel.get("bairro"),
                    "endereco": imovel.get("endereco"),
                    "preco": imovel.get("preco"),
                    "valor_avaliacao": imovel.get("valor_avaliacao"),
                    "desconto": imovel.get("desconto"),
                    "tipo_imovel": imovel.get("tipo_imovel"),
                    "area_privativa": imovel.get("area_privativa"),
                    "quartos": imovel.get("quartos"),
                    "praca": imovel.get("praca"),
                    "link": imovel.get("link"),
                    "ativo": True
                }

                # Upsert no Supabase
                self.supabase.table("imoveis_caixa").upsert(
                    data,
                    on_conflict="id_imovel"
                ).execute()

            logger.info(f"Salvos no Supabase: {len(self.imoveis_analisados)} imoveis")

        except Exception as e:
            logger.error(f"Erro ao salvar no Supabase: {e}")

    def executar(self):
        """Executa pipeline completo"""
        logger.info("=" * 60)
        logger.info("INICIANDO PIPELINE DE ANALISE DE LEILOES")
        logger.info(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        try:
            # 1. Coleta Caixa
            imoveis_caixa = self.coletar_caixa()

            # 2. Coleta Zuk
            imoveis_zuk = self.coletar_zuk()

            # 3. Consolida
            self.consolidar_imoveis(imoveis_caixa, imoveis_zuk)

            # 4. Analisa
            self.analisar_todos()

            # 5. Gera relatorios
            relatorios = self.gerar_relatorios()

            # 6. Salva no Supabase
            self.salvar_supabase()

            # Resumo final
            self.stats["fim"] = datetime.now().isoformat()

            logger.info("=" * 60)
            logger.info("PIPELINE CONCLUIDO")
            logger.info("=" * 60)
            logger.info(f"Estatisticas: {json.dumps(self.stats, indent=2)}")

            return {
                "status": "success",
                "stats": self.stats,
                "relatorios": relatorios
            }

        except Exception as e:
            logger.error(f"ERRO NO PIPELINE: {e}")
            return {
                "status": "error",
                "error": str(e),
                "stats": self.stats
            }


def main():
    """Funcao principal"""
    pipeline = PipelineLeilao()
    result = pipeline.executar()

    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
