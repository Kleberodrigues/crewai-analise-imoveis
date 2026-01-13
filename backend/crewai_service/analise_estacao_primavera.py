"""
ANÁLISE COMPLETA - APARTAMENTO ESTAÇÃO PRIMAVERA
Imóvel Caixa - Compra Direta Online
Data: 17/12/2025
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any
import json

# =============================================================================
# CUSTOS MENSAIS DE MANUTENÇÃO (HOLDING COSTS)
# Estimativas baseadas no perfil do imóvel:
# - Apartamento popular 2 quartos em Guaianazes
# - Área privativa: 38,72m² | Valor fiscal: R$ 189.066,00
# =============================================================================

CUSTOS_MENSAIS = {
    "condominio": {
        "valor": 400.00,
        "descricao": "Taxa condominial mensal",
        "fonte": "Valor real informado pelo usuario"
    },
    "iptu": {
        "valor": 157.55,
        "descricao": "IPTU mensal (parcelado em 10x)",
        "fonte": "Valor fiscal R$ 189.066 × 1% ÷ 12 meses"
    },
    "agua": {
        "valor": 55.00,
        "descricao": "Água - taxa mínima Sabesp",
        "fonte": "Sabesp tarifa residencial mínima 2024"
    },
    "luz": {
        "valor": 45.00,
        "descricao": "Energia - taxa mínima + disponibilidade",
        "fonte": "Enel SP tarifa B1 residencial mínima"
    },
    "gas": {
        "valor": 25.00,
        "descricao": "Gás encanado - taxa mínima",
        "fonte": "Comgás tarifa residencial mínima (se houver)"
    },
    "seguro_incendio": {
        "valor": 35.00,
        "descricao": "Seguro incêndio obrigatório",
        "fonte": "Média seguros residenciais básicos"
    },
    "manutencao_basica": {
        "valor": 100.00,
        "descricao": "Manutenção preventiva e limpeza",
        "fonte": "Reserva para pequenos reparos e visitas de interessados"
    }
}


def calcular_custos_holding(meses: int = 9) -> Dict[str, Any]:
    """Calcula custos de manutenção enquanto aguarda venda."""
    custo_mensal_total = sum(item["valor"] for item in CUSTOS_MENSAIS.values())

    custos_essenciais = {
        "condominio": CUSTOS_MENSAIS["condominio"]["valor"],
        "iptu": CUSTOS_MENSAIS["iptu"]["valor"],
        "seguro_incendio": CUSTOS_MENSAIS["seguro_incendio"]["valor"],
    }
    custo_mensal_minimo = sum(custos_essenciais.values())

    custos_variaveis = {
        "agua": CUSTOS_MENSAIS["agua"]["valor"],
        "luz": CUSTOS_MENSAIS["luz"]["valor"],
        "gas": CUSTOS_MENSAIS["gas"]["valor"],
        "manutencao_basica": CUSTOS_MENSAIS["manutencao_basica"]["valor"],
    }

    cenarios = {}
    for m in [3, 6, 9, 12]:
        cenarios[f"{m}_meses"] = {
            "meses": m,
            "custo_total": custo_mensal_total * m,
            "custo_minimo": custo_mensal_minimo * m,
        }

    return {
        "custos_detalhados": CUSTOS_MENSAIS,
        "custo_mensal_total": custo_mensal_total,
        "custo_mensal_minimo": custo_mensal_minimo,
        "custos_essenciais": custos_essenciais,
        "custos_variaveis": custos_variaveis,
        "cenarios": cenarios,
        "meses_referencia": meses,
        "custo_total_referencia": custo_mensal_total * meses,
        "custo_minimo_referencia": custo_mensal_minimo * meses
    }


# ============================================================
# DADOS DO IMÓVEL (extraídos da página da Caixa e Matrícula)
# ============================================================

IMOVEL = {
    "condominio": "ESTAÇÃO PRIMAVERA",
    "endereco": "RUA RAPOSO DA FONSECA, N. 1044 APTO. 22 BL 04",
    "bairro": "CIDADE POPULAR",
    "distrito": "GUAIANAZES",
    "cidade": "SÃO PAULO",
    "uf": "SP",
    "cep": "08460-520",

    # Características
    "tipo": "Apartamento",
    "quartos": 2,
    "area_total": 81.70,
    "area_privativa": 38.72,
    "area_comum": 42.98,
    "andar": 2,
    "bloco": "04",
    "unidade": "22",

    # Valores
    "valor_avaliacao": 178000.00,
    "valor_venda": 105481.84,
    "desconto_percentual": 40.74,

    # Documentação
    "numero_imovel": "855553745579-8",
    "matricula": "190686",
    "cartorio": "7º Oficial de Registro de Imóveis de São Paulo",
    "comarca": "SAO PAULO-SP",
    "inscricao_imobiliaria": "23603200721",

    # Modalidade
    "modalidade": "Compra Direta Online",  # SEM comissão de leiloeiro!
    "aceita_fgts": True,
    "aceita_financiamento": True,
    "financiamento_tipo": "SBPE",

    # Regras de débitos
    "limite_condominio_percentual": 10,  # Caixa paga o que exceder 10%
    "tributos_responsabilidade": "comprador",

    # Link
    "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=855553745579-8"
}

# ============================================================
# ANÁLISE DA MATRÍCULA
# ============================================================

ANALISE_MATRICULA = {
    "numero": "190686",
    "cartorio": "7º Oficial de Registro de Imóveis de SP",
    "data_abertura": "03/05/2017",
    "data_emissao": "24/02/2025",

    # Proprietário anterior (devedor)
    "proprietario_anterior": {
        "nome": "RAELSON MACIEL DOS SANTOS",
        "cpf": "440.477.138-05",
        "estado_civil": "solteiro"
    },

    # Proprietário atual
    "proprietario_atual": "CAIXA ECONÔMICA FEDERAL - CEF",
    "data_consolidacao": "20/02/2025",
    "valor_fiscal_consolidacao": 189066.00,

    # Histórico de alienação fiduciária
    "alienacao_fiduciaria": {
        "valor_original": 118588.52,
        "data_original": "21/09/2016",
        "valor_retificado": 120393.40,
        "data_retificacao": "30/10/2024",
        "status": "CONSOLIDADA - Propriedade transferida para Caixa"
    },

    # Ônus e gravames
    "onus": {
        "hipoteca": False,
        "penhora": False,
        "usufruto": False,
        "alienacao_fiduciaria": False,  # Extinta pela consolidação
        "indisponibilidade": False,
        "regime_afetacao": True,  # Não impede venda
        "area_verde_cetesb": True  # Apenas informativo
    },

    # Alertas
    "alertas": [
        "✅ Matrícula LIMPA - sem ônus impeditivos",
        "✅ Propriedade consolidada em nome da Caixa",
        "✅ Pronta para transferência ao comprador",
        "ℹ️ Regime de Afetação (Lei 10.931/2004) - não impede venda",
        "ℹ️ Área Verde CETESB - apenas preservação ambiental do condomínio"
    ],

    "score_matricula": 95,  # 0-100
    "risco_juridico": "BAIXO"
}

# ============================================================
# TABELAS DE CUSTOS
# ============================================================

# ITBI São Paulo Capital - 3%
ITBI_SP = 0.03

# Tabela de Emolumentos SP 2024
def calcular_emolumentos_registro(valor: float) -> float:
    """Tabela de emolumentos para registro de imóveis SP 2024"""
    if valor <= 26500: return 633.75
    if valor <= 39700: return 870.80
    if valor <= 59600: return 1159.23
    if valor <= 119200: return 1590.10
    if valor <= 238400: return 2077.20
    if valor <= 397400: return 2654.91
    if valor <= 794700: return 3419.91
    if valor <= 1192100: return 4300.96
    return 5384.49

# ============================================================
# CÁLCULOS DE CUSTOS
# ============================================================

def calcular_custos_aquisicao(valor_arrematacao: float, modalidade: str) -> Dict:
    """Calcula todos os custos de aquisição"""

    # Comissão do Leiloeiro
    # COMPRA DIRETA CAIXA = SEM COMISSÃO!
    if modalidade in ["Compra Direta Online", "Venda Direta Online", "Venda Online"]:
        comissao_leiloeiro = 0
    elif modalidade in ["Leilão SFI", "Licitação Aberta"]:
        comissao_leiloeiro = valor_arrematacao * 0.05
    else:
        comissao_leiloeiro = valor_arrematacao * 0.05

    # ITBI (3% em SP Capital)
    itbi = valor_arrematacao * ITBI_SP

    # Registro de Imóvel
    registro = calcular_emolumentos_registro(valor_arrematacao)

    # Escritura - Na compra direta Caixa, não precisa de escritura pública
    # O próprio contrato de compra e venda serve como título
    escritura = 0

    # Honorários Advocatícios (opcional em compra direta, mas recomendado)
    # Estimativa: 3% ou mínimo R$ 2.500
    honorarios_advogado = max(2500, valor_arrematacao * 0.03)

    return {
        "valor_arrematacao": valor_arrematacao,
        "comissao_leiloeiro": comissao_leiloeiro,
        "itbi": itbi,
        "registro": registro,
        "escritura": escritura,
        "honorarios_advogado": honorarios_advogado,
        "total": valor_arrematacao + comissao_leiloeiro + itbi + registro + escritura + honorarios_advogado
    }

def calcular_custos_regularizacao(valor_avaliacao: float, limite_condominio_pct: float = 10) -> Dict:
    """Calcula custos de regularização"""

    # Débitos Condominiais
    # Caixa limita a 10% do valor de avaliação
    # Comprador paga até esse limite, Caixa paga o excedente
    limite_condominio = valor_avaliacao * (limite_condominio_pct / 100)
    condominio_estimado = min(limite_condominio, 15000)  # Estimativa conservadora

    # IPTU atrasado (responsabilidade do comprador)
    iptu_estimado = 3000  # Estimativa para 2-3 anos de atraso

    # Custos de desocupação
    # Na compra direta, geralmente o imóvel já está desocupado ou
    # há processo de desocupação em andamento
    desocupacao = 0  # Assumindo desocupado

    # Reformas (estimativa 5% do valor)
    reformas = valor_avaliacao * 0.05

    return {
        "condominio": condominio_estimado,
        "condominio_limite_caixa": limite_condominio,
        "iptu": iptu_estimado,
        "desocupacao": desocupacao,
        "reformas": reformas,
        "total": condominio_estimado + iptu_estimado + desocupacao + reformas
    }

def calcular_valor_mercado(area_privativa: float, bairro: str, cidade: str) -> Dict:
    """
    Valor de mercado baseado em pesquisa REAL no VivaReal.
    Condomínio Estação Primavera - Guaianazes - Dez/2024

    Dados reais:
    - Mais barato à venda: R$ 172.000
    - Média de preços: R$ 180.000
    - Desconsiderado: R$ 103k (leilão/anúncio antigo)
    """
    # Valores REAIS do VivaReal para o mesmo condomínio
    valor_mercado = 180000.00       # Média real de venda
    valor_mais_barato = 172000.00   # Menor preço atual

    preco_m2 = valor_mercado / area_privativa  # R$ 4.648/m²

    return {
        "preco_m2": preco_m2,
        "area_privativa": area_privativa,
        "valor_mercado": valor_mercado,
        "valor_mais_barato": valor_mais_barato,
        "valor_venda_conservador": valor_mais_barato,  # Conservador = menor preço
        "valor_venda_otimista": valor_mercado,         # Otimista = média
        "fonte": "VivaReal - pesquisa Dez/2024"
    }

def calcular_custos_venda(valor_venda: float) -> Dict:
    """Calcula custos para revenda do imóvel"""

    # Comissão do Corretor (6% padrão CRECI)
    comissao_corretor = valor_venda * 0.06

    # Marketing e despesas de venda
    marketing = 1500

    # Certidões para venda
    certidoes = 500

    return {
        "comissao_corretor": comissao_corretor,
        "marketing": marketing,
        "certidoes": certidoes,
        "total": comissao_corretor + marketing + certidoes
    }

def calcular_imposto_ganho_capital(valor_venda: float, custo_aquisicao_total: float) -> Dict:
    """Calcula IR sobre ganho de capital (15%)"""

    ganho_capital = valor_venda - custo_aquisicao_total

    if ganho_capital <= 0:
        return {
            "ganho_capital": 0,
            "ir_devido": 0,
            "aliquota": 0.15,
            "observacao": "Sem ganho de capital - sem IR devido"
        }

    # Alíquota de 15% sobre ganho de capital para PF
    ir_devido = ganho_capital * 0.15

    return {
        "ganho_capital": ganho_capital,
        "ir_devido": ir_devido,
        "aliquota": 0.15,
        "observacao": "Declarar no GCAP e recolher até último dia útil do mês seguinte à venda"
    }

# ============================================================
# ANÁLISE COMPLETA
# ============================================================

def gerar_analise_completa():
    """Gera análise financeira completa do imóvel"""

    print("=" * 80)
    print("ANÁLISE COMPLETA DE INVESTIMENTO")
    print("APARTAMENTO ESTAÇÃO PRIMAVERA - CAIXA COMPRA DIRETA")
    print("=" * 80)

    # --------------------------------------------------------
    # 1. DADOS DO IMÓVEL
    # --------------------------------------------------------
    print("\n" + "=" * 80)
    print("1. DADOS DO IMÓVEL")
    print("=" * 80)
    print(f"""
    Condomínio: {IMOVEL['condominio']}
    Endereço: {IMOVEL['endereco']}
    Bairro: {IMOVEL['bairro']} - {IMOVEL['distrito']}
    Cidade: {IMOVEL['cidade']}/{IMOVEL['uf']}
    CEP: {IMOVEL['cep']}

    Tipo: {IMOVEL['tipo']}
    Quartos: {IMOVEL['quartos']}
    Área Total: {IMOVEL['area_total']}m²
    Área Privativa: {IMOVEL['area_privativa']}m²
    Andar: {IMOVEL['andar']}º
    Bloco: {IMOVEL['bloco']}

    Matrícula: {IMOVEL['matricula']}
    Cartório: {IMOVEL['cartorio']}

    Link: {IMOVEL['link']}
    """)

    # --------------------------------------------------------
    # 2. VALORES
    # --------------------------------------------------------
    print("\n" + "=" * 80)
    print("2. VALORES")
    print("=" * 80)
    print(f"""
    Valor de Avaliação: R$ {IMOVEL['valor_avaliacao']:,.2f}
    Valor de Venda:     R$ {IMOVEL['valor_venda']:,.2f}
    DESCONTO:           {IMOVEL['desconto_percentual']:.2f}%

    Economia imediata:  R$ {IMOVEL['valor_avaliacao'] - IMOVEL['valor_venda']:,.2f}

    Modalidade: {IMOVEL['modalidade']}
    Aceita FGTS: {'Sim' if IMOVEL['aceita_fgts'] else 'Não'}
    Aceita Financiamento: {'Sim' if IMOVEL['aceita_financiamento'] else 'Não'}
    """)

    # --------------------------------------------------------
    # 3. ANÁLISE DA MATRÍCULA
    # --------------------------------------------------------
    print("\n" + "=" * 80)
    print("3. ANÁLISE DA MATRÍCULA")
    print("=" * 80)
    print(f"""
    Matrícula: {ANALISE_MATRICULA['numero']}
    Cartório: {ANALISE_MATRICULA['cartorio']}
    Data Emissão: {ANALISE_MATRICULA['data_emissao']}

    Proprietário Atual: {ANALISE_MATRICULA['proprietario_atual']}
    Data Consolidação: {ANALISE_MATRICULA['data_consolidacao']}

    ÔNUS E GRAVAMES:
    - Hipoteca: {'❌ SIM' if ANALISE_MATRICULA['onus']['hipoteca'] else '✅ NÃO'}
    - Penhora: {'❌ SIM' if ANALISE_MATRICULA['onus']['penhora'] else '✅ NÃO'}
    - Usufruto: {'❌ SIM' if ANALISE_MATRICULA['onus']['usufruto'] else '✅ NÃO'}
    - Alienação Fiduciária: {'❌ SIM' if ANALISE_MATRICULA['onus']['alienacao_fiduciaria'] else '✅ NÃO (extinta)'}
    - Indisponibilidade: {'❌ SIM' if ANALISE_MATRICULA['onus']['indisponibilidade'] else '✅ NÃO'}

    ALERTAS:
    """)
    for alerta in ANALISE_MATRICULA['alertas']:
        print(f"    {alerta}")

    print(f"""
    SCORE DA MATRÍCULA: {ANALISE_MATRICULA['score_matricula']}/100
    RISCO JURÍDICO: {ANALISE_MATRICULA['risco_juridico']}
    """)

    # --------------------------------------------------------
    # 4. CUSTOS DE AQUISIÇÃO
    # --------------------------------------------------------
    custos_aquisicao = calcular_custos_aquisicao(
        IMOVEL['valor_venda'],
        IMOVEL['modalidade']
    )

    print("\n" + "=" * 80)
    print("4. CUSTOS DE AQUISIÇÃO")
    print("=" * 80)
    print(f"""
    Valor de Arrematação:    R$ {custos_aquisicao['valor_arrematacao']:>12,.2f}
    Comissão Leiloeiro:      R$ {custos_aquisicao['comissao_leiloeiro']:>12,.2f}  {'(ISENTO - Compra Direta!)' if custos_aquisicao['comissao_leiloeiro'] == 0 else '(5%)'}
    ITBI (3% SP):            R$ {custos_aquisicao['itbi']:>12,.2f}
    Registro de Imóvel:      R$ {custos_aquisicao['registro']:>12,.2f}
    Escritura:               R$ {custos_aquisicao['escritura']:>12,.2f}  (não necessária em compra direta)
    Honorários Advocatícios: R$ {custos_aquisicao['honorarios_advogado']:>12,.2f}  (3% - recomendado)
    ─────────────────────────────────────────────────────────
    TOTAL AQUISIÇÃO:         R$ {custos_aquisicao['total']:>12,.2f}
    """)

    # --------------------------------------------------------
    # 5. CUSTOS DE REGULARIZAÇÃO
    # --------------------------------------------------------
    custos_regularizacao = calcular_custos_regularizacao(
        IMOVEL['valor_avaliacao'],
        IMOVEL['limite_condominio_percentual']
    )

    print("\n" + "=" * 80)
    print("5. CUSTOS DE REGULARIZAÇÃO")
    print("=" * 80)
    print(f"""
    Débitos Condominiais:    R$ {custos_regularizacao['condominio']:>12,.2f}  (limite Caixa: R$ {custos_regularizacao['condominio_limite_caixa']:,.2f})
    IPTU Atrasado:           R$ {custos_regularizacao['iptu']:>12,.2f}  (estimativa)
    Desocupação:             R$ {custos_regularizacao['desocupacao']:>12,.2f}  (verificar situação)
    Reformas (5%):           R$ {custos_regularizacao['reformas']:>12,.2f}
    ─────────────────────────────────────────────────────────
    TOTAL REGULARIZAÇÃO:     R$ {custos_regularizacao['total']:>12,.2f}
    """)

    # --------------------------------------------------------
    # 6. INVESTIMENTO TOTAL
    # --------------------------------------------------------
    investimento_total = custos_aquisicao['total'] + custos_regularizacao['total']

    print("\n" + "=" * 80)
    print("6. INVESTIMENTO TOTAL")
    print("=" * 80)
    print(f"""
    Custos de Aquisição:     R$ {custos_aquisicao['total']:>12,.2f}
    Custos de Regularização: R$ {custos_regularizacao['total']:>12,.2f}
    ─────────────────────────────────────────────────────────
    INVESTIMENTO TOTAL:      R$ {investimento_total:>12,.2f}
    """)

    # --------------------------------------------------------
    # 7. VALOR DE MERCADO E PROJEÇÃO DE VENDA
    # --------------------------------------------------------
    mercado = calcular_valor_mercado(
        IMOVEL['area_privativa'],
        IMOVEL['distrito'],
        IMOVEL['cidade']
    )

    print("\n" + "=" * 80)
    print("7. VALOR DE MERCADO (PESQUISA VIVAREAL DEZ/2024)")
    print("=" * 80)
    print(f"""
    FONTE: VivaReal - Condomínio Estação Primavera - Guaianazes

    Menor preço anunciado:         R$ {mercado['valor_mais_barato']:>12,.2f}
    Média de preços:               R$ {mercado['valor_mercado']:>12,.2f}
    Preço/m² calculado:            R$ {mercado['preco_m2']:>12,.2f}/m²

    Comparação com Avaliação Caixa (R$ {IMOVEL['valor_avaliacao']:,.2f}):
    - Mercado está {'ABAIXO' if mercado['valor_mercado'] < IMOVEL['valor_avaliacao'] else 'ACIMA'} da avaliação
    - Diferença: R$ {abs(mercado['valor_mercado'] - IMOVEL['valor_avaliacao']):,.2f}
    - POTENCIAL DE LUCRO: R$ {mercado['valor_mercado'] - IMOVEL['valor_venda']:,.2f} (mercado - compra)
    """)

    # Usar valor de MERCADO REAL do VivaReal como referência
    valor_venda_referencia = mercado['valor_mercado']  # R$ 180.000 (média VivaReal)

    # --------------------------------------------------------
    # 8. CUSTOS DE VENDA (REVENDA)
    # --------------------------------------------------------
    custos_venda = calcular_custos_venda(valor_venda_referencia)

    print("\n" + "=" * 80)
    print("8. CUSTOS DE VENDA (PARA REVENDA)")
    print("=" * 80)
    print(f"""
    Valor de Venda Projetado: R$ {valor_venda_referencia:>12,.2f} (média VivaReal Dez/2024)

    Comissão Corretor (6%):  R$ {custos_venda['comissao_corretor']:>12,.2f}
    Marketing/Anúncios:      R$ {custos_venda['marketing']:>12,.2f}
    Certidões:               R$ {custos_venda['certidoes']:>12,.2f}
    ─────────────────────────────────────────────────────────
    TOTAL CUSTOS VENDA:      R$ {custos_venda['total']:>12,.2f}
    """)

    # --------------------------------------------------------
    # 9. IMPOSTO SOBRE GANHO DE CAPITAL
    # --------------------------------------------------------
    custo_aquisicao_fiscal = custos_aquisicao['total'] + custos_regularizacao['total']
    imposto = calcular_imposto_ganho_capital(valor_venda_referencia, custo_aquisicao_fiscal)

    print("\n" + "=" * 80)
    print("9. IMPOSTO SOBRE GANHO DE CAPITAL")
    print("=" * 80)
    print(f"""
    Valor de Venda:          R$ {valor_venda_referencia:>12,.2f}
    (-) Custo de Aquisição:  R$ {custo_aquisicao_fiscal:>12,.2f}
    ─────────────────────────────────────────────────────────
    GANHO DE CAPITAL:        R$ {imposto['ganho_capital']:>12,.2f}

    IR devido (15%):         R$ {imposto['ir_devido']:>12,.2f}

    ⚠️  {imposto['observacao']}
    """)

    # --------------------------------------------------------
    # 10. RESULTADO FINAL
    # --------------------------------------------------------
    lucro_bruto = valor_venda_referencia - investimento_total - custos_venda['total']
    lucro_liquido = lucro_bruto - imposto['ir_devido']
    roi_bruto = (lucro_bruto / investimento_total) * 100
    roi_liquido = (lucro_liquido / investimento_total) * 100

    # Margem de segurança
    break_even = investimento_total + custos_venda['total'] + (imposto['ir_devido'] if imposto['ganho_capital'] > 0 else 0)
    margem_seguranca = ((valor_venda_referencia - break_even) / valor_venda_referencia) * 100

    print("\n" + "=" * 80)
    print("10. RESULTADO FINAL")
    print("=" * 80)
    print(f"""
    ┌─────────────────────────────────────────────────────────┐
    │  DEMONSTRATIVO DE RESULTADO                             │
    ├─────────────────────────────────────────────────────────┤
    │  Valor de Venda Projetado:     R$ {valor_venda_referencia:>12,.2f}       │
    │  (-) Investimento Total:       R$ {investimento_total:>12,.2f}       │
    │  (-) Custos de Venda:          R$ {custos_venda['total']:>12,.2f}       │
    │  (-) IR Ganho de Capital:      R$ {imposto['ir_devido']:>12,.2f}       │
    ├─────────────────────────────────────────────────────────┤
    │  LUCRO LÍQUIDO:                R$ {lucro_liquido:>12,.2f}       │
    │                                                         │
    │  ROI BRUTO:                    {roi_bruto:>12.2f}%          │
    │  ROI LÍQUIDO:                  {roi_liquido:>12.2f}%          │
    │  MARGEM DE SEGURANÇA:          {margem_seguranca:>12.2f}%          │
    └─────────────────────────────────────────────────────────┘
    """)

    # --------------------------------------------------------
    # 11. CUSTOS DE HOLDING (ATÉ 9 MESES)
    # --------------------------------------------------------
    print("\n" + "=" * 80)
    print("11. CUSTOS DE HOLDING (MANUTENÇÃO ENQUANTO VENDE)")
    print("=" * 80)

    holding = calcular_custos_holding(9)

    print(f"""
    ┌─────────────────────────────────────────────────────────────────┐
    │  CUSTOS MENSAIS ESTIMADOS                                       │
    ├─────────────────────────────────────────────────────────────────┤""")

    for item, dados in CUSTOS_MENSAIS.items():
        nome = dados['descricao'][:35].ljust(35)
        print(f"    │  {nome}  R$ {dados['valor']:>8,.2f}     │")

    print(f"""    ├─────────────────────────────────────────────────────────────────┤
    │  TOTAL MENSAL:                              R$ {holding['custo_mensal_total']:>8,.2f}     │
    │  (Mínimo essencial: Cond+IPTU+Seguro)       R$ {holding['custo_mensal_minimo']:>8,.2f}     │
    └─────────────────────────────────────────────────────────────────┘

    CENÁRIOS DE TEMPO PARA VENDA:
    ┌──────────────────────────────────────────────────────────────────┐
    │  Tempo      Custo Total    Custo Mínimo    Situação             │
    ├──────────────────────────────────────────────────────────────────┤
    │  3 meses    R$ {holding['cenarios']['3_meses']['custo_total']:>8,.2f}    R$ {holding['cenarios']['3_meses']['custo_minimo']:>8,.2f}    Venda rápida         │
    │  6 meses    R$ {holding['cenarios']['6_meses']['custo_total']:>8,.2f}    R$ {holding['cenarios']['6_meses']['custo_minimo']:>8,.2f}    Mercado normal       │
    │  9 meses    R$ {holding['cenarios']['9_meses']['custo_total']:>8,.2f}    R$ {holding['cenarios']['9_meses']['custo_minimo']:>8,.2f}    Conservador          │
    │  12 meses   R$ {holding['cenarios']['12_meses']['custo_total']:>8,.2f}   R$ {holding['cenarios']['12_meses']['custo_minimo']:>8,.2f}   Mercado difícil      │
    └──────────────────────────────────────────────────────────────────┘
    """)

    # --------------------------------------------------------
    # 12. ROI AJUSTADO COM HOLDING (9 MESES)
    # --------------------------------------------------------
    print("\n" + "=" * 80)
    print("12. ROI AJUSTADO COM HOLDING (CENÁRIO 9 MESES)")
    print("=" * 80)

    custo_holding_9m = holding['cenarios']['9_meses']['custo_total']
    investimento_ajustado = investimento_total + custo_holding_9m

    # Recalcular com holding
    ganho_capital_ajustado = valor_venda_referencia - investimento_ajustado
    ir_ajustado = max(0, ganho_capital_ajustado * 0.15)
    lucro_liquido_ajustado = valor_venda_referencia - investimento_ajustado - custos_venda['total'] - ir_ajustado
    roi_liquido_ajustado = (lucro_liquido_ajustado / investimento_ajustado) * 100
    roi_anualizado = (roi_liquido_ajustado / 9) * 12

    print(f"""
    ┌─────────────────────────────────────────────────────────────────┐
    │  INVESTIMENTO AJUSTADO (COM 9 MESES DE HOLDING)                 │
    ├─────────────────────────────────────────────────────────────────┤
    │  Investimento Original:              R$ {investimento_total:>12,.2f}          │
    │  (+) Custos de Holding (9 meses):    R$ {custo_holding_9m:>12,.2f}          │
    ├─────────────────────────────────────────────────────────────────┤
    │  INVESTIMENTO TOTAL AJUSTADO:        R$ {investimento_ajustado:>12,.2f}          │
    └─────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │  RESULTADO COM HOLDING                                          │
    ├─────────────────────────────────────────────────────────────────┤
    │  Valor de Venda Projetado:           R$ {valor_venda_referencia:>12,.2f}          │
    │  (-) Investimento Ajustado:          R$ {investimento_ajustado:>12,.2f}          │
    │  (-) Custos de Venda:                R$ {custos_venda['total']:>12,.2f}          │
    │  (-) IR Ganho de Capital (15%):      R$ {ir_ajustado:>12,.2f}          │
    ├─────────────────────────────────────────────────────────────────┤
    │  LUCRO LÍQUIDO AJUSTADO:             R$ {lucro_liquido_ajustado:>12,.2f}          │
    │                                                                 │
    │  ROI LÍQUIDO (9 meses):                     {roi_liquido_ajustado:>8.2f}%          │
    │  ROI ANUALIZADO:                            {roi_anualizado:>8.2f}%          │
    └─────────────────────────────────────────────────────────────────┘
    """)

    # Comparativo SEM e COM holding
    print("""
    COMPARATIVO SEM vs COM HOLDING (9 MESES):
    ┌────────────────────────────────────────────────────────────────────────┐
    │  Cenário                    Investimento      Lucro Líq.    ROI Líq.  │
    ├────────────────────────────────────────────────────────────────────────┤""")
    print(f"    │  SEM holding (venda imediata)   R$ {investimento_total:>10,.2f}   R$ {lucro_liquido:>10,.2f}   {roi_liquido:>6.2f}%    │")
    print(f"    │  COM 9 meses de holding         R$ {investimento_ajustado:>10,.2f}   R$ {lucro_liquido_ajustado:>10,.2f}   {roi_liquido_ajustado:>6.2f}%    │")
    diferenca_lucro = lucro_liquido - lucro_liquido_ajustado
    print(f"""    ├────────────────────────────────────────────────────────────────────────┤
    │  DIFERENÇA (custo do tempo):                  R$ {diferenca_lucro:>10,.2f}            │
    └────────────────────────────────────────────────────────────────────────┘
    """)

    # --------------------------------------------------------
    # 13. CENÁRIOS DE VENDA COM HOLDING
    # --------------------------------------------------------
    print("\n" + "=" * 80)
    print("13. CENÁRIOS DE VENDA (COM HOLDING DE 9 MESES)")
    print("=" * 80)

    # Cenários baseados em dados REAIS do VivaReal
    cenarios = [
        ("PESSIMISTA", 165000.00),    # Abaixo do menor anunciado
        ("CONSERVADOR", 172000.00),   # Menor preço atual VivaReal
        ("MODERADO", 180000.00),      # Média de preços VivaReal
        ("OTIMISTA", 190000.00),      # Acima da média (mercado aquecido)
    ]

    print(f"\n    {'Cenário':<15} {'Venda':<15} {'Lucro Líq.':<15} {'ROI Líq.':<10}")
    print("    " + "-" * 70)

    for nome, valor_venda_cenario in cenarios:
        custos_v = calcular_custos_venda(valor_venda_cenario)
        # Custo de aquisição + holding para IR
        custo_total_fiscal = investimento_ajustado
        imp = calcular_imposto_ganho_capital(valor_venda_cenario, custo_total_fiscal)
        lucro_liq = valor_venda_cenario - investimento_ajustado - custos_v['total'] - imp['ir_devido']
        roi_liq = (lucro_liq / investimento_ajustado) * 100
        roi_anual = (roi_liq / 9) * 12

        status = "✅" if lucro_liq > 0 else "❌"
        print(f"    {nome:<15} R$ {valor_venda_cenario:>10,.0f}  R$ {lucro_liq:>10,.0f}  {roi_liq:>6.1f}% ({roi_anual:>5.1f}%/ano)  {status}")

    # --------------------------------------------------------
    # 14. RECOMENDAÇÃO FINAL
    # --------------------------------------------------------
    print("\n" + "=" * 80)
    print("14. RECOMENDAÇÃO FINAL")
    print("=" * 80)

    # Score geral (usando ROI ajustado com holding)
    score_financeiro = min(100, max(0, roi_liquido_ajustado * 3 + 50))  # Ajustado para ROI menor
    score_desconto = min(100, IMOVEL['desconto_percentual'] * 2)
    score_localizacao = 55  # Zona Leste SP - liquidez média
    score_liquidez = 60  # Apartamento 2 quartos - boa liquidez
    score_matricula = ANALISE_MATRICULA['score_matricula']
    score_holding = max(0, 100 - (custo_holding_9m / 100))  # Penalidade por custos de holding

    score_geral = (
        score_financeiro * 0.25 +
        score_desconto * 0.20 +
        score_localizacao * 0.15 +
        score_liquidez * 0.15 +
        score_matricula * 0.15 +
        score_holding * 0.10
    )

    if score_geral >= 70:
        recomendacao = "COMPRAR"
        emoji = "🟢"
    elif score_geral >= 50:
        recomendacao = "ANALISAR MELHOR"
        emoji = "🟡"
    else:
        recomendacao = "EVITAR"
        emoji = "🔴"

    print(f"""
    SCORES (considerando 9 meses de holding):
    ├── Financeiro (ROI):    {score_financeiro:.0f}/100  (ROI ajustado: {roi_liquido_ajustado:.1f}%)
    ├── Desconto:            {score_desconto:.0f}/100  (desconto: {IMOVEL['desconto_percentual']:.1f}%)
    ├── Localização:         {score_localizacao:.0f}/100  (Guaianazes - Zona Leste)
    ├── Liquidez:            {score_liquidez:.0f}/100  (Apto 2 quartos)
    ├── Matrícula:           {score_matricula:.0f}/100  (Limpa, sem ônus)
    └── Custos Holding:      {score_holding:.0f}/100  (R$ {custo_holding_9m:,.2f} em 9 meses)

    ══════════════════════════════════════════════════════════
    SCORE GERAL:             {score_geral:.1f}/100
    RECOMENDAÇÃO:            {emoji} {recomendacao}
    ══════════════════════════════════════════════════════════
    """)

    # Pontos positivos e negativos
    print(f"""
    PONTOS POSITIVOS:
    [+] Desconto de 40,74% sobre avaliação
    [+] SEM comissao de leiloeiro (Compra Direta - economia de 5%)
    [+] Matricula LIMPA - sem onus impeditivos
    [+] Aceita FGTS e Financiamento
    [+] Caixa assume debitos de condominio acima de 10%
    [+] Propriedade ja consolidada - processo rapido

    PONTOS DE ATENCAO:
    [!] Localizacao em Guaianazes (Zona Leste) - liquidez media
    [!] ROI liquido com holding: {roi_liquido_ajustado:.1f}% (anualizado: {roi_anualizado:.1f}%)
    [!] Custos de holding em 9 meses: R$ {custo_holding_9m:,.2f}
    [!] Verificar situacao de ocupacao antes de comprar
    [!] Confirmar debitos de condominio e IPTU atualizados

    CUSTOS MENSAIS PARA PLANEJAMENTO:
    - Condominio:      R$ 400,00/mes
    - IPTU:            R$ 157,55/mes
    - Agua + Luz:      R$ 100,00/mes
    - Manutencao:      R$ 100,00/mes
    - TOTAL MENSAL:    R$ {holding['custo_mensal_total']:,.2f}/mes

    PROXIMOS PASSOS:
    1. Visitar o imovel pessoalmente
    2. Solicitar certidoes de debitos atualizadas
    3. Verificar situacao de ocupacao com sindico
    4. Consultar valor de mercado com corretores locais
    5. Calcular tempo estimado de venda na regiao
    6. Reservar capital para {holding['custo_mensal_total'] * 6:,.2f} a {holding['custo_mensal_total'] * 12:,.2f} de holding
    7. Fazer proposta formal no site da Caixa
    """)

    print("=" * 80)
    print("FIM DA ANÁLISE")
    print("=" * 80)

    return {
        "imovel": IMOVEL,
        "matricula": ANALISE_MATRICULA,
        "custos_aquisicao": custos_aquisicao,
        "custos_regularizacao": custos_regularizacao,
        "investimento_total": investimento_total,
        "holding": {
            "meses": 9,
            "custo_mensal": holding['custo_mensal_total'],
            "custo_total": custo_holding_9m,
            "investimento_ajustado": investimento_ajustado,
            "detalhes": holding
        },
        "valor_venda_projetado": valor_venda_referencia,
        "custos_venda": custos_venda,
        "imposto": imposto,
        "lucro_liquido_sem_holding": lucro_liquido,
        "lucro_liquido_com_holding": lucro_liquido_ajustado,
        "roi_liquido_sem_holding": roi_liquido,
        "roi_liquido_com_holding": roi_liquido_ajustado,
        "roi_anualizado": roi_anualizado,
        "score_geral": score_geral,
        "recomendacao": recomendacao
    }

if __name__ == "__main__":
    resultado = gerar_analise_completa()
