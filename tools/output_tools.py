"""
Tools de Output - Geracao de CSV e PDF com Analise Completa
"""

import os
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
# Removido decorador @tool para permitir chamada direta
# from crewai_tools import tool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))

# Colunas do CSV completo
CSV_COLUMNS = [
    # Dados do Imovel
    "id_imovel", "data_analise", "endereco", "bairro", "cidade", "tipo_imovel",
    "area_privativa_m2", "quartos", "vagas", "link_imovel",
    # Valores Leilao
    "valor_avaliacao", "valor_minimo_leilao", "desconto_percentual", "tipo_leilao",
    "data_leilao", "modalidade",
    # Analise Edital
    "edital_ocupacao", "edital_debitos_iptu", "edital_debitos_condominio",
    "edital_outros_debitos", "edital_total_debitos", "edital_comissao_leiloeiro_pct",
    "edital_prazo_pagamento", "edital_riscos", "edital_score",
    # Analise Matricula
    "matricula_numero", "matricula_cartorio", "matricula_gravames_extintos",
    "matricula_gravames_transferidos", "matricula_valor_gravames",
    "matricula_irregularidades", "matricula_score",
    # Pesquisa Mercado
    "mercado_preco_m2_regiao", "mercado_preco_m2_min", "mercado_preco_m2_max",
    "mercado_valor_estimado", "mercado_valor_min", "mercado_valor_max",
    "mercado_condominio_mensal", "mercado_iptu_mensal", "mercado_aluguel_estimado",
    "mercado_liquidez", "mercado_demanda", "mercado_tempo_venda_medio_dias",
    "mercado_fonte", "mercado_confianca", "mercado_amostras",
    # Custos Aquisicao
    "custo_valor_arrematacao", "custo_comissao_leiloeiro", "custo_itbi",
    "custo_escritura", "custo_registro", "custo_certidoes", "custo_advocaticios",
    "custo_desocupacao", "custo_debitos_edital", "custo_gravames_matricula",
    "custo_reforma_estimado", "custo_total_aquisicao", "investimento_total",
    # Manutencao
    "manutencao_total_6m", "investimento_total_6m",
    # Custos Venda
    "venda_comissao_corretor", "venda_irpf_ganho_capital", "venda_custos_totais",
    # Cenario 6 Meses
    "cenario_preco_venda", "cenario_lucro_liquido", "cenario_roi_percentual",
    "cenario_roi_mensal", "cenario_margem_seguranca",
    # Scores
    "score_edital", "score_matricula", "score_localizacao", "score_financeiro",
    "score_liquidez", "score_geral", "recomendacao", "nivel_risco",
    "justificativa", "pontos_atencao", "proximos_passos"
]


def flatten_analysis(analise: Dict) -> Dict:
    """Achata estrutura aninhada para CSV"""
    flat = {}

    # Dados basicos
    flat["id_imovel"] = analise.get("id_imovel", "")
    flat["data_analise"] = analise.get("data_analise", datetime.now().strftime("%Y-%m-%d"))
    flat["endereco"] = analise.get("endereco", "")
    flat["bairro"] = analise.get("bairro", "")
    flat["cidade"] = analise.get("cidade", "")
    flat["tipo_imovel"] = analise.get("tipo_imovel", "")
    flat["area_privativa_m2"] = analise.get("area_privativa", 0)
    flat["quartos"] = analise.get("quartos", 0)
    flat["vagas"] = analise.get("vagas", 0)
    flat["link_imovel"] = analise.get("link", "")

    # Valores leilao
    flat["valor_avaliacao"] = analise.get("valor_avaliacao", 0)
    flat["valor_minimo_leilao"] = analise.get("preco", 0)
    flat["desconto_percentual"] = analise.get("desconto", 0)
    flat["tipo_leilao"] = analise.get("praca", "")
    flat["data_leilao"] = analise.get("data_leilao", "")
    flat["modalidade"] = analise.get("modalidade", "")

    # Analise edital
    edital = analise.get("analise_edital", {})
    flat["edital_ocupacao"] = edital.get("ocupacao", "nao_informado")
    flat["edital_debitos_iptu"] = edital.get("debitos_iptu", 0)
    flat["edital_debitos_condominio"] = edital.get("debitos_condominio", 0)
    flat["edital_outros_debitos"] = edital.get("outros_debitos", 0)
    flat["edital_total_debitos"] = edital.get("total_debitos", 0)
    flat["edital_comissao_leiloeiro_pct"] = edital.get("comissao_leiloeiro_pct", 5)
    flat["edital_prazo_pagamento"] = edital.get("prazo_pagamento", "")
    flat["edital_riscos"] = "; ".join(edital.get("riscos", []))
    flat["edital_score"] = edital.get("score", 0)

    # Analise matricula
    matricula = analise.get("analise_matricula", {})
    flat["matricula_numero"] = matricula.get("numero", "")
    flat["matricula_cartorio"] = matricula.get("cartorio", "")
    flat["matricula_gravames_extintos"] = "; ".join(matricula.get("gravames_extintos", []))
    flat["matricula_gravames_transferidos"] = "; ".join(matricula.get("gravames_transferidos", []))
    flat["matricula_valor_gravames"] = matricula.get("valor_gravames", 0)
    flat["matricula_irregularidades"] = "; ".join(matricula.get("irregularidades", []))
    flat["matricula_score"] = matricula.get("score", 0)

    # Pesquisa mercado
    mercado = analise.get("pesquisa_mercado", {})
    flat["mercado_preco_m2_regiao"] = mercado.get("preco_m2", 0)
    flat["mercado_preco_m2_min"] = mercado.get("preco_m2_min", 0)
    flat["mercado_preco_m2_max"] = mercado.get("preco_m2_max", 0)
    flat["mercado_valor_estimado"] = mercado.get("valor_estimado", 0)
    flat["mercado_valor_min"] = mercado.get("valor_min", 0)
    flat["mercado_valor_max"] = mercado.get("valor_max", 0)
    flat["mercado_condominio_mensal"] = mercado.get("condominio_mensal", 0)
    flat["mercado_iptu_mensal"] = mercado.get("iptu_mensal", 0)
    flat["mercado_aluguel_estimado"] = mercado.get("aluguel_estimado", 0)
    flat["mercado_liquidez"] = mercado.get("liquidez", "media")
    flat["mercado_demanda"] = mercado.get("demanda", "media")
    flat["mercado_tempo_venda_medio_dias"] = mercado.get("tempo_venda_dias", 90)
    flat["mercado_fonte"] = mercado.get("fonte", "estimativa")
    flat["mercado_confianca"] = mercado.get("confianca", "baixa")
    flat["mercado_amostras"] = mercado.get("amostras", 0)

    # Custos aquisicao
    custos = analise.get("custos", {}).get("custos_aquisicao", {})
    flat["custo_valor_arrematacao"] = custos.get("valor_arrematacao", 0)
    flat["custo_comissao_leiloeiro"] = custos.get("comissao_leiloeiro", 0)
    flat["custo_itbi"] = custos.get("itbi", 0)
    flat["custo_escritura"] = custos.get("escritura", 0)
    flat["custo_registro"] = custos.get("registro", 0)
    flat["custo_certidoes"] = custos.get("certidoes", 0)
    flat["custo_advocaticios"] = custos.get("honorarios_advogado", 0)
    flat["custo_desocupacao"] = custos.get("custo_desocupacao", 0)
    flat["custo_debitos_edital"] = custos.get("debitos_edital", 0)
    flat["custo_gravames_matricula"] = custos.get("gravames_matricula", 0)
    flat["custo_reforma_estimado"] = custos.get("custo_reforma", 0)
    flat["custo_total_aquisicao"] = analise.get("custos", {}).get("total_custos_aquisicao", 0)
    flat["investimento_total"] = analise.get("custos", {}).get("investimento_total", 0)

    # Manutencao
    flat["manutencao_total_6m"] = analise.get("custos", {}).get("total_manutencao", 0)
    flat["investimento_total_6m"] = analise.get("custos", {}).get("investimento_total_com_manutencao", 0)

    # Custos venda
    venda = analise.get("custos", {}).get("custos_venda", {})
    flat["venda_comissao_corretor"] = venda.get("comissao_corretor", 0)
    flat["venda_irpf_ganho_capital"] = venda.get("irpf", 0)
    flat["venda_custos_totais"] = venda.get("total_custos_venda", 0)

    # Cenario 6 meses
    resultado = analise.get("custos", {}).get("resultado_venda", {})
    flat["cenario_preco_venda"] = resultado.get("preco_venda", 0)
    flat["cenario_lucro_liquido"] = resultado.get("lucro_liquido", 0)
    flat["cenario_roi_percentual"] = resultado.get("roi_total_percentual", 0)
    flat["cenario_roi_mensal"] = resultado.get("roi_mensal_percentual", 0)
    flat["cenario_margem_seguranca"] = resultado.get("margem_seguranca_percentual", 0)

    # Scores
    scores = analise.get("scores", {})
    flat["score_edital"] = scores.get("edital", 0)
    flat["score_matricula"] = scores.get("matricula", 0)
    flat["score_localizacao"] = scores.get("localizacao", 0)
    flat["score_financeiro"] = scores.get("financeiro", 0)
    flat["score_liquidez"] = scores.get("liquidez", 0)
    flat["score_geral"] = scores.get("geral", 0)
    flat["recomendacao"] = analise.get("recomendacao", "ANALISAR_MELHOR")
    flat["nivel_risco"] = analise.get("nivel_risco", "MEDIO")
    flat["justificativa"] = analise.get("justificativa", "")
    flat["pontos_atencao"] = "; ".join(analise.get("pontos_atencao", []))
    flat["proximos_passos"] = "; ".join(analise.get("proximos_passos", []))

    return flat


def generate_csv_report(
    analises: List[Dict],
    filename: Optional[str] = None,
    append: bool = False
) -> Dict:
    """
    Gera relatorio CSV com todas as analises de imoveis.

    Args:
        analises: Lista de analises completas de imoveis
        filename: Nome do arquivo (default: analise_YYYYMMDD_HHMMSS.csv)
        append: Se True, adiciona ao arquivo existente

    Returns:
        Dict com caminho do arquivo e estatisticas
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analise_leilao_{timestamp}.csv"

    filepath = OUTPUT_DIR / filename

    # Achata todas as analises
    rows = [flatten_analysis(a) for a in analises]

    # Estatisticas
    stats = {
        "total_imoveis": len(rows),
        "comprar": sum(1 for r in rows if r.get("recomendacao") == "COMPRAR"),
        "analisar": sum(1 for r in rows if r.get("recomendacao") == "ANALISAR_MELHOR"),
        "evitar": sum(1 for r in rows if r.get("recomendacao") == "EVITAR"),
        "roi_medio": sum(r.get("cenario_roi_percentual", 0) for r in rows) / len(rows) if rows else 0,
        "score_medio": sum(r.get("score_geral", 0) for r in rows) / len(rows) if rows else 0
    }

    # Escreve CSV
    mode = 'a' if append and filepath.exists() else 'w'
    write_header = mode == 'w' or not filepath.exists()

    try:
        with open(filepath, mode, newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=';')

            if write_header:
                writer.writeheader()

            for row in rows:
                # Garante que todas as colunas existam
                row_complete = {col: row.get(col, "") for col in CSV_COLUMNS}
                writer.writerow(row_complete)

        return {
            "status": "success",
            "filepath": str(filepath),
            "filename": filename,
            "stats": stats,
            "colunas": len(CSV_COLUMNS),
            "linhas": len(rows),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erro ao gerar CSV: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def generate_pdf_report(
    analise: Dict,
    filename: Optional[str] = None,
    include_charts: bool = True
) -> Dict:
    """
    Gera relatorio PDF detalhado de um imovel.

    Args:
        analise: Analise completa do imovel
        filename: Nome do arquivo PDF
        include_charts: Incluir graficos

    Returns:
        Dict com caminho do arquivo
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not filename:
        id_imovel = analise.get("id_imovel", "imovel")
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"relatorio_{id_imovel}_{timestamp}.pdf"

    filepath = OUTPUT_DIR / filename

    try:
        # Tenta usar reportlab
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm

        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Titulo
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=30
        )
        story.append(Paragraph("RELATORIO DE ANALISE - LEILAO IMOVEL", title_style))
        story.append(Spacer(1, 0.5*cm))

        # Data
        story.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        # Dados do Imovel
        story.append(Paragraph("DADOS DO IMOVEL", styles['Heading2']))
        dados_imovel = [
            ["Endereco:", analise.get("endereco", "")],
            ["Bairro:", analise.get("bairro", "")],
            ["Cidade:", analise.get("cidade", "")],
            ["Tipo:", analise.get("tipo_imovel", "")],
            ["Area:", f"{analise.get('area_privativa', 0)} m2"],
            ["Quartos:", str(analise.get("quartos", 0))]
        ]
        t = Table(dados_imovel, colWidths=[4*cm, 12*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        # Valores do Leilao
        story.append(Paragraph("VALORES DO LEILAO", styles['Heading2']))
        valores = [
            ["Valor Avaliacao:", f"R$ {analise.get('valor_avaliacao', 0):,.2f}"],
            ["Valor Minimo:", f"R$ {analise.get('preco', 0):,.2f}"],
            ["Desconto:", f"{analise.get('desconto', 0):.1f}%"],
            ["Praca:", analise.get("praca", "")]
        ]
        t = Table(valores, colWidths=[4*cm, 12*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        # Custos
        custos = analise.get("custos", {})
        if custos:
            story.append(Paragraph("CUSTOS DE AQUISICAO", styles['Heading2']))
            custos_aquisicao = custos.get("custos_aquisicao", {})
            custos_data = [
                ["Valor Arrematacao:", f"R$ {custos_aquisicao.get('valor_arrematacao', 0):,.2f}"],
                ["Comissao Leiloeiro:", f"R$ {custos_aquisicao.get('comissao_leiloeiro', 0):,.2f}"],
                ["ITBI:", f"R$ {custos_aquisicao.get('itbi', 0):,.2f}"],
                ["Cartorio:", f"R$ {custos_aquisicao.get('escritura', 0) + custos_aquisicao.get('registro', 0):,.2f}"],
                ["Advocaticios:", f"R$ {custos_aquisicao.get('honorarios_advogado', 0):,.2f}"],
                ["Desocupacao:", f"R$ {custos_aquisicao.get('custo_desocupacao', 0):,.2f}"],
                ["Debitos Edital:", f"R$ {custos_aquisicao.get('debitos_edital', 0):,.2f}"],
                ["Reforma:", f"R$ {custos_aquisicao.get('custo_reforma', 0):,.2f}"],
                ["TOTAL CUSTOS:", f"R$ {custos.get('total_custos_aquisicao', 0):,.2f}"],
                ["INVESTIMENTO TOTAL:", f"R$ {custos.get('investimento_total', 0):,.2f}"]
            ]
            t = Table(custos_data, colWidths=[5*cm, 11*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('BACKGROUND', (0, -2), (-1, -1), colors.lightyellow),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold')
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))

        # Resultado
        resultado = custos.get("resultado_venda", {})
        if resultado:
            story.append(Paragraph("CENARIO VENDA 6 MESES", styles['Heading2']))
            resultado_data = [
                ["Preco Venda Estimado:", f"R$ {resultado.get('preco_venda', 0):,.2f}"],
                ["Lucro Liquido:", f"R$ {resultado.get('lucro_liquido', 0):,.2f}"],
                ["ROI Total:", f"{resultado.get('roi_total_percentual', 0):.1f}%"],
                ["ROI Mensal:", f"{resultado.get('roi_mensal_percentual', 0):.1f}%"],
                ["Margem Seguranca:", f"{resultado.get('margem_seguranca_percentual', 0):.1f}%"]
            ]
            t = Table(resultado_data, colWidths=[5*cm, 11*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))

        # Score e Recomendacao
        story.append(Paragraph("SCORE E RECOMENDACAO", styles['Heading2']))
        scores = analise.get("scores", {})
        rec = analise.get("recomendacao", "ANALISAR_MELHOR")
        rec_color = colors.green if rec == "COMPRAR" else (colors.red if rec == "EVITAR" else colors.orange)

        score_data = [
            ["Score Geral:", f"{scores.get('geral', 0):.0f}/100"],
            ["Recomendacao:", rec],
            ["Nivel Risco:", analise.get("nivel_risco", "MEDIO")]
        ]
        t = Table(score_data, colWidths=[5*cm, 11*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('BACKGROUND', (1, 1), (1, 1), rec_color),
            ('TEXTCOLOR', (1, 1), (1, 1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        # Justificativa
        if analise.get("justificativa"):
            story.append(Paragraph("JUSTIFICATIVA", styles['Heading2']))
            story.append(Paragraph(analise.get("justificativa", ""), styles['Normal']))
            story.append(Spacer(1, 0.5*cm))

        # Pontos de Atencao
        if analise.get("pontos_atencao"):
            story.append(Paragraph("PONTOS DE ATENCAO", styles['Heading2']))
            for ponto in analise.get("pontos_atencao", []):
                story.append(Paragraph(f"• {ponto}", styles['Normal']))
            story.append(Spacer(1, 0.5*cm))

        # Proximos Passos
        if analise.get("proximos_passos"):
            story.append(Paragraph("PROXIMOS PASSOS", styles['Heading2']))
            for i, passo in enumerate(analise.get("proximos_passos", []), 1):
                story.append(Paragraph(f"{i}. {passo}", styles['Normal']))

        # Gera PDF
        doc.build(story)

        return {
            "status": "success",
            "filepath": str(filepath),
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        }

    except ImportError:
        logger.warning("reportlab nao instalado, gerando TXT")
        # Fallback para TXT
        txt_path = filepath.with_suffix('.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("RELATORIO DE ANALISE - LEILAO IMOVEL\n")
            f.write("=" * 60 + "\n\n")
            f.write(json.dumps(analise, indent=2, ensure_ascii=False))

        return {
            "status": "success_txt",
            "filepath": str(txt_path),
            "message": "PDF nao disponivel, gerado TXT"
        }

    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def generate_summary_csv(analises: List[Dict], filename: Optional[str] = None) -> Dict:
    """
    Gera CSV resumido com apenas as colunas principais para decisao rapida.

    Args:
        analises: Lista de analises
        filename: Nome do arquivo

    Returns:
        Dict com caminho do arquivo
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resumo_oportunidades_{timestamp}.csv"

    filepath = OUTPUT_DIR / filename

    # Colunas resumidas
    summary_columns = [
        "id_imovel", "endereco", "bairro", "cidade",
        "valor_minimo_leilao", "desconto_percentual",
        "investimento_total_6m", "cenario_preco_venda",
        "cenario_lucro_liquido", "cenario_roi_percentual",
        "score_geral", "recomendacao", "nivel_risco"
    ]

    rows = []
    for a in analises:
        flat = flatten_analysis(a)
        row = {col: flat.get(col, "") for col in summary_columns}
        rows.append(row)

    # Ordena por score
    rows.sort(key=lambda x: x.get("score_geral", 0), reverse=True)

    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=summary_columns, delimiter=';')
            writer.writeheader()
            writer.writerows(rows)

        return {
            "status": "success",
            "filepath": str(filepath),
            "total": len(rows),
            "top_oportunidades": [r["id_imovel"] for r in rows[:5] if r.get("recomendacao") == "COMPRAR"]
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============================================================
# FUNCOES TOP 5 - PDF CONSOLIDADO E CSV RESUMIDO
# ============================================================

TOP5_CSV_COLUMNS = [
    "ranking", "id_imovel", "endereco", "cidade", "bairro",
    "valor_venda", "valor_mercado", "desconto_pct",
    "area_m2", "quartos", "score_geral", "score_oportunidade",
    "score_financeiro", "score_localizacao", "score_edital",
    "score_matricula", "score_liquidez", "roi_estimado_pct",
    "margem_seguranca_pct", "investimento_total", "lucro_projetado",
    "tempo_retorno_meses", "nivel_risco", "recomendacao", "link"
]


def gerar_csv_top5(
    top_imoveis: List[Dict],
    output_dir: Optional[Path] = None,
    filename: Optional[str] = None
) -> Dict:
    """
    Gera CSV resumido com os top N imoveis selecionados.

    Args:
        top_imoveis: Lista de imoveis selecionados (ja ordenados por ranking)
        output_dir: Diretorio de saida (default: OUTPUT_DIR)
        filename: Nome do arquivo (default: top5_oportunidades_YYYYMMDD.csv)

    Returns:
        Dict com status e caminho do arquivo
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"top5_oportunidades_{timestamp}.csv"

    filepath = output_dir / filename

    rows = []
    for imovel in top_imoveis:
        scores = imovel.get("scores", {})
        custos = imovel.get("custos", {})
        resultado = custos.get("resultado_venda", {})
        mercado = imovel.get("pesquisa_mercado", {})

        row = {
            "ranking": imovel.get("ranking_top5", 0),
            "id_imovel": imovel.get("id_imovel", ""),
            "endereco": imovel.get("endereco", ""),
            "cidade": imovel.get("cidade", ""),
            "bairro": imovel.get("bairro", ""),
            "valor_venda": imovel.get("preco", 0),
            "valor_mercado": mercado.get("valor_estimado", 0),
            "desconto_pct": imovel.get("desconto", 0),
            "area_m2": imovel.get("area_privativa", 0),
            "quartos": imovel.get("quartos", 0),
            "score_geral": scores.get("geral", 0),
            "score_oportunidade": imovel.get("score_oportunidade", 0),
            "score_financeiro": scores.get("financeiro", 0),
            "score_localizacao": scores.get("localizacao", 0),
            "score_edital": scores.get("edital", 0),
            "score_matricula": scores.get("matricula", 0),
            "score_liquidez": scores.get("liquidez", 0),
            "roi_estimado_pct": resultado.get("roi_total_percentual", 0),
            "margem_seguranca_pct": resultado.get("margem_seguranca_percentual", 0),
            "investimento_total": custos.get("investimento_total", 0),
            "lucro_projetado": resultado.get("lucro_liquido", 0),
            "tempo_retorno_meses": 6,  # Cenario padrao
            "nivel_risco": imovel.get("nivel_risco", "MEDIO"),
            "recomendacao": imovel.get("recomendacao", ""),
            "link": imovel.get("link", "")
        }
        rows.append(row)

    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=TOP5_CSV_COLUMNS, delimiter=';')
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"CSV Top 5 gerado: {filepath}")
        return {
            "status": "success",
            "filepath": str(filepath),
            "filename": filename,
            "total_imoveis": len(rows),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erro ao gerar CSV Top 5: {str(e)}")
        return {"status": "error", "error": str(e)}


def gerar_pdf_top5_consolidado(
    top_imoveis: List[Dict],
    output_dir: Optional[Path] = None,
    filename: Optional[str] = None,
    titulo: str = "Top 5 Oportunidades de Leilao",
    resumo_selecao: Optional[Dict] = None
) -> Dict:
    """
    Gera PDF consolidado com os top N imoveis.

    Estrutura do PDF:
    - Pagina 1: Capa com resumo
    - Paginas 2-6: Um imovel por pagina
    - Pagina final: Tabela comparativa

    Args:
        top_imoveis: Lista de imoveis selecionados
        output_dir: Diretorio de saida
        filename: Nome do arquivo
        titulo: Titulo do relatorio
        resumo_selecao: Dict com estatisticas da selecao

    Returns:
        Dict com status e caminho do arquivo
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"top5_oportunidades_{timestamp}.pdf"

    filepath = output_dir / filename

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, KeepTogether
        )
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()

        # Estilos customizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a365d')
        )

        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4a5568')
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=12,
            spaceAfter=8,
            textColor=colors.HexColor('#2d3748')
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14
        )

        story = []

        # ========== PAGINA 1: CAPA ==========
        story.append(Spacer(1, 3*cm))
        story.append(Paragraph(titulo, title_style))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            f"Relatorio gerado em {datetime.now().strftime('%d/%m/%Y as %H:%M')}",
            subtitle_style
        ))
        story.append(Spacer(1, 2*cm))

        # Resumo da selecao
        if resumo_selecao:
            stats = resumo_selecao.get("estatisticas", {})
            resumo_data = [
                ["RESUMO DA SELECAO", ""],
                ["Total Analisados:", str(resumo_selecao.get("total_analisados", 0))],
                ["Total Selecionados:", str(resumo_selecao.get("total_selecionados", 0))],
                ["Taxa de Selecao:", f"{resumo_selecao.get('taxa_selecao_pct', 0):.1f}%"],
                ["", ""],
                ["ESTATISTICAS DOS SELECIONADOS", ""],
                ["Score Medio:", f"{stats.get('score_oportunidade', {}).get('media', 0):.1f}"],
                ["ROI Medio:", f"{stats.get('roi_percentual', {}).get('media', 0):.1f}%"],
                ["Margem Media:", f"{stats.get('margem_seguranca_pct', {}).get('media', 0):.1f}%"],
                ["Desconto Medio:", f"{stats.get('desconto_pct', {}).get('media', 0):.1f}%"],
                ["Investimento Total:", f"R$ {stats.get('investimento_total', {}).get('total', 0):,.2f}"]
            ]
        else:
            resumo_data = [
                ["IMOVEIS SELECIONADOS", str(len(top_imoveis))],
                ["Data da Analise", datetime.now().strftime('%d/%m/%Y')]
            ]

        t = Table(resumo_data, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (0, 5), (-1, 5), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t)

        story.append(PageBreak())

        # ========== PAGINAS 2-N: UM IMOVEL POR PAGINA ==========
        for idx, imovel in enumerate(top_imoveis, 1):
            scores = imovel.get("scores", {})
            custos = imovel.get("custos", {})
            resultado = custos.get("resultado_venda", {})
            mercado = imovel.get("pesquisa_mercado", {})

            # Titulo do imovel
            ranking = imovel.get("ranking_top5", idx)
            rec = imovel.get("recomendacao", "")
            rec_color = colors.HexColor('#38a169') if rec == "COMPRAR" else (
                colors.HexColor('#e53e3e') if rec == "EVITAR" else colors.HexColor('#dd6b20')
            )

            story.append(Paragraph(
                f"#{ranking} - {imovel.get('endereco', 'Endereco nao informado')}",
                title_style
            ))
            story.append(Spacer(1, 0.3*cm))

            # Dados basicos
            story.append(Paragraph("DADOS DO IMOVEL", heading_style))
            dados_basicos = [
                ["Cidade:", imovel.get("cidade", ""), "Bairro:", imovel.get("bairro", "")],
                ["Tipo:", imovel.get("tipo_imovel", ""), "Area:", f"{imovel.get('area_privativa', 0)} m2"],
                ["Quartos:", str(imovel.get("quartos", 0)), "Vagas:", str(imovel.get("vagas", 0))]
            ]
            t = Table(dados_basicos, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#edf2f7')),
                ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#edf2f7')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))

            # Valores
            story.append(Paragraph("VALORES E OPORTUNIDADE", heading_style))
            valores_data = [
                ["Valor Avaliacao:", f"R$ {imovel.get('valor_avaliacao', 0):,.2f}"],
                ["Valor Minimo Leilao:", f"R$ {imovel.get('preco', 0):,.2f}"],
                ["Desconto:", f"{imovel.get('desconto', 0):.1f}%"],
                ["Valor Mercado Estimado:", f"R$ {mercado.get('valor_estimado', 0):,.2f}"],
                ["Investimento Total:", f"R$ {custos.get('investimento_total', 0):,.2f}"]
            ]
            t = Table(valores_data, colWidths=[6*cm, 10*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#edf2f7')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))

            # ROI e Resultado
            story.append(Paragraph("CENARIO DE VENDA (6 MESES)", heading_style))
            roi_data = [
                ["Preco Venda Estimado:", f"R$ {resultado.get('preco_venda', 0):,.2f}"],
                ["Lucro Liquido:", f"R$ {resultado.get('lucro_liquido', 0):,.2f}"],
                ["ROI Total:", f"{resultado.get('roi_total_percentual', 0):.1f}%"],
                ["ROI Mensal:", f"{resultado.get('roi_mensal_percentual', 0):.1f}%"],
                ["Margem de Seguranca:", f"{resultado.get('margem_seguranca_percentual', 0):.1f}%"]
            ]
            t = Table(roi_data, colWidths=[6*cm, 10*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#edf2f7')),
                ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#c6f6d5')),  # Lucro verde
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))

            # Scores
            story.append(Paragraph("SCORES DE ANALISE", heading_style))
            score_data = [
                ["Dimensao", "Score", "Peso", "Contribuicao"],
                ["Edital", f"{scores.get('edital', 0):.0f}", "20%", f"{scores.get('edital', 0) * 0.2:.1f}"],
                ["Matricula", f"{scores.get('matricula', 0):.0f}", "20%", f"{scores.get('matricula', 0) * 0.2:.1f}"],
                ["Localizacao", f"{scores.get('localizacao', 0):.0f}", "25%", f"{scores.get('localizacao', 0) * 0.25:.1f}"],
                ["Financeiro", f"{scores.get('financeiro', 0):.0f}", "25%", f"{scores.get('financeiro', 0) * 0.25:.1f}"],
                ["Liquidez", f"{scores.get('liquidez', 0):.0f}", "10%", f"{scores.get('liquidez', 0) * 0.1:.1f}"],
                ["SCORE GERAL", f"{scores.get('geral', 0):.1f}", "100%", ""]
            ]
            t = Table(score_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#bee3f8')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))

            # Recomendacao
            story.append(Paragraph("RECOMENDACAO", heading_style))
            rec_data = [
                ["Recomendacao:", rec],
                ["Nivel de Risco:", imovel.get("nivel_risco", "MEDIO")],
                ["Score Oportunidade:", f"{imovel.get('score_oportunidade', 0):.1f}"]
            ]
            t = Table(rec_data, colWidths=[6*cm, 10*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#edf2f7')),
                ('BACKGROUND', (1, 0), (1, 0), rec_color),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))

            # Justificativa
            if imovel.get("justificativa"):
                story.append(Paragraph("Justificativa:", heading_style))
                story.append(Paragraph(imovel.get("justificativa", ""), normal_style))

            # Pontos de Atencao
            if imovel.get("pontos_atencao"):
                story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph("Pontos de Atencao:", heading_style))
                for ponto in imovel.get("pontos_atencao", [])[:5]:
                    story.append(Paragraph(f"  * {ponto}", normal_style))

            # Link
            if imovel.get("link"):
                story.append(Spacer(1, 0.3*cm))
                story.append(Paragraph(f"Link: {imovel.get('link', '')}", normal_style))

            # Page break entre imoveis
            if idx < len(top_imoveis):
                story.append(PageBreak())

        # ========== PAGINA FINAL: TABELA COMPARATIVA ==========
        story.append(PageBreak())
        story.append(Paragraph("TABELA COMPARATIVA", title_style))
        story.append(Spacer(1, 0.5*cm))

        # Cabecalho da tabela
        comparativo_header = ["#", "Endereco", "Cidade", "Valor", "Desc.", "ROI", "Score", "Rec."]
        comparativo_data = [comparativo_header]

        for imovel in top_imoveis:
            resultado = imovel.get("custos", {}).get("resultado_venda", {})
            row = [
                str(imovel.get("ranking_top5", "")),
                imovel.get("endereco", "")[:30] + "..." if len(imovel.get("endereco", "")) > 30 else imovel.get("endereco", ""),
                imovel.get("cidade", "")[:15],
                f"R$ {imovel.get('preco', 0)/1000:.0f}k",
                f"{imovel.get('desconto', 0):.0f}%",
                f"{resultado.get('roi_total_percentual', 0):.0f}%",
                f"{imovel.get('scores', {}).get('geral', 0):.0f}",
                imovel.get("recomendacao", "")[:3]
            ]
            comparativo_data.append(row)

        t = Table(comparativo_data, colWidths=[1*cm, 5*cm, 2.5*cm, 2.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

        # Rodape
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            "Este relatorio foi gerado automaticamente pelo Sistema de Analise de Leiloes.",
            subtitle_style
        ))
        story.append(Paragraph(
            "As informacoes sao baseadas em dados publicos e estimativas de mercado.",
            subtitle_style
        ))

        # Gera o PDF
        doc.build(story)

        logger.info(f"PDF Top 5 consolidado gerado: {filepath}")
        return {
            "status": "success",
            "filepath": str(filepath),
            "filename": filename,
            "total_paginas": len(top_imoveis) + 2,  # Capa + imoveis + comparativo
            "total_imoveis": len(top_imoveis),
            "timestamp": datetime.now().isoformat()
        }

    except ImportError as e:
        logger.warning(f"reportlab nao instalado: {e}")
        # Fallback para TXT
        txt_path = filepath.with_suffix('.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write(f"  {titulo}\n")
            f.write(f"  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write("=" * 70 + "\n\n")

            for idx, imovel in enumerate(top_imoveis, 1):
                scores = imovel.get("scores", {})
                custos = imovel.get("custos", {})
                resultado = custos.get("resultado_venda", {})

                f.write(f"\n{'=' * 70}\n")
                f.write(f"  #{idx} - {imovel.get('endereco', '')}\n")
                f.write(f"{'=' * 70}\n\n")
                f.write(f"Cidade: {imovel.get('cidade', '')} | Bairro: {imovel.get('bairro', '')}\n")
                f.write(f"Tipo: {imovel.get('tipo_imovel', '')} | Area: {imovel.get('area_privativa', 0)} m2\n")
                f.write(f"Quartos: {imovel.get('quartos', 0)} | Vagas: {imovel.get('vagas', 0)}\n\n")
                f.write(f"Valor Avaliacao: R$ {imovel.get('valor_avaliacao', 0):,.2f}\n")
                f.write(f"Valor Leilao: R$ {imovel.get('preco', 0):,.2f}\n")
                f.write(f"Desconto: {imovel.get('desconto', 0):.1f}%\n\n")
                f.write(f"Investimento Total: R$ {custos.get('investimento_total', 0):,.2f}\n")
                f.write(f"Lucro Projetado: R$ {resultado.get('lucro_liquido', 0):,.2f}\n")
                f.write(f"ROI: {resultado.get('roi_total_percentual', 0):.1f}%\n")
                f.write(f"Margem Seguranca: {resultado.get('margem_seguranca_percentual', 0):.1f}%\n\n")
                f.write(f"SCORE GERAL: {scores.get('geral', 0):.1f}/100\n")
                f.write(f"RECOMENDACAO: {imovel.get('recomendacao', '')}\n")
                f.write(f"RISCO: {imovel.get('nivel_risco', '')}\n\n")
                if imovel.get('link'):
                    f.write(f"Link: {imovel.get('link', '')}\n")

            f.write(f"\n{'=' * 70}\n")
            f.write("  TABELA COMPARATIVA\n")
            f.write(f"{'=' * 70}\n\n")
            f.write(f"{'#':<3} {'Endereco':<35} {'Valor':<12} {'ROI':<8} {'Score':<6} {'Rec.':<10}\n")
            f.write("-" * 70 + "\n")
            for imovel in top_imoveis:
                resultado = imovel.get("custos", {}).get("resultado_venda", {})
                endereco = imovel.get('endereco', '')[:32] + '...' if len(imovel.get('endereco', '')) > 32 else imovel.get('endereco', '')
                f.write(f"{imovel.get('ranking_top5', ''):<3} {endereco:<35} R${imovel.get('preco', 0)/1000:>7.0f}k {resultado.get('roi_total_percentual', 0):>6.0f}% {imovel.get('scores', {}).get('geral', 0):>5.0f} {imovel.get('recomendacao', ''):<10}\n")

        return {
            "status": "success_txt",
            "filepath": str(txt_path),
            "message": "PDF nao disponivel, gerado TXT",
            "total_imoveis": len(top_imoveis)
        }

    except Exception as e:
        logger.error(f"Erro ao gerar PDF Top 5: {str(e)}")
        return {"status": "error", "error": str(e)}


# Exemplo de uso
if __name__ == "__main__":
    # Analise de exemplo
    analise_exemplo = {
        "id_imovel": "8787718781523",
        "endereco": "Rua Exemplo, 123 Apto 45",
        "bairro": "Vila Mariana",
        "cidade": "SAO PAULO",
        "tipo_imovel": "Apartamento",
        "area_privativa": 65,
        "quartos": 2,
        "vagas": 1,
        "valor_avaliacao": 200000,
        "preco": 120000,
        "desconto": 40,
        "praca": "2a Praca",
        "custos": {
            "custos_aquisicao": {
                "valor_arrematacao": 120000,
                "comissao_leiloeiro": 6000,
                "itbi": 3600,
                "escritura": 2800,
                "registro": 2200,
                "honorarios_advogado": 4000,
                "custo_desocupacao": 10000,
                "debitos_edital": 17000,
                "custo_reforma": 19500
            },
            "total_custos_aquisicao": 65100,
            "investimento_total": 185100,
            "total_manutencao": 5880,
            "investimento_total_com_manutencao": 190980,
            "resultado_venda": {
                "preco_venda": 524875,
                "lucro_liquido": 249562,
                "roi_total_percentual": 130.67,
                "roi_mensal_percentual": 21.78,
                "margem_seguranca_percentual": 63.62
            }
        },
        "scores": {
            "edital": 65,
            "matricula": 75,
            "localizacao": 85,
            "financeiro": 90,
            "liquidez": 80,
            "geral": 79.75
        },
        "recomendacao": "COMPRAR",
        "nivel_risco": "MEDIO",
        "justificativa": "Excelente ROI de 130% em 6 meses. Desconto de 40% e localizacao privilegiada.",
        "pontos_atencao": ["Imovel ocupado", "Debitos condominio R$ 12.000"],
        "proximos_passos": ["Baixar edital completo", "Visitar imovel", "Consultar advogado"]
    }

    # Gera CSV
    result_csv = generate_csv_report([analise_exemplo])
    print(json.dumps(result_csv, indent=2))

    # Gera PDF
    result_pdf = generate_pdf_report(analise_exemplo)
    print(json.dumps(result_pdf, indent=2))
