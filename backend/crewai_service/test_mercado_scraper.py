"""
Teste do Pipeline com Pesquisa de Mercado Real
Imovel: Estacao Primavera - Guaianazes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tools.data_tools import pesquisar_mercado, comparar_imovel_mercado

# Dados do imovel Estacao Primavera
IMOVEL = {
    "id_imovel": "estacao_primavera_01",
    "endereco": "Rua Eduardo Rizk, 200 - Apto 23 Bloco A - Ed. Residencial Estacao Primavera",
    "bairro": "Guaianazes",
    "cidade": "SAO PAULO",
    "uf": "SP",
    "tipo_imovel": "Apartamento",
    "area_privativa": 38.72,
    "quartos": 2,
    "vagas": 1,
    "preco": 78000.00,  # Preco de venda Caixa
    "valor_avaliacao": 178000.00,  # Valor de avaliacao
    "desconto": 56.2,  # Desconto sobre avaliacao
    "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=estacao_primavera_01"
}


def main():
    print("=" * 70)
    print("TESTE - PESQUISA DE MERCADO COM WEB SCRAPING")
    print("Imovel: Estacao Primavera - Guaianazes/SP")
    print("=" * 70)

    # 1. Pesquisa de mercado
    print("\n[1] PESQUISANDO MERCADO...")
    print("-" * 50)

    resultado_mercado = pesquisar_mercado(
        bairro="guaianazes",
        cidade="sao-paulo",
        uf="sp",
        tipo="apartamento",
        quartos=2,
        area_m2=38.72,
        fontes=['vivareal', 'olx']
    )

    print(f"\nStatus: {resultado_mercado.get('status')}")
    print(f"Fonte: {resultado_mercado.get('fonte')}")
    print(f"Total encontrados: {resultado_mercado.get('total_encontrados')}")

    if resultado_mercado.get('precos'):
        print(f"\nPrecos de Mercado:")
        print(f"  Medio:   R$ {resultado_mercado['precos']['medio']:,.2f}")
        print(f"  Mediano: R$ {resultado_mercado['precos']['mediano']:,.2f}")
        print(f"  Minimo:  R$ {resultado_mercado['precos']['minimo']:,.2f}")
        print(f"  Maximo:  R$ {resultado_mercado['precos']['maximo']:,.2f}")

    if resultado_mercado.get('preco_m2'):
        print(f"\nPreco por m2:")
        print(f"  Medio:   R$ {resultado_mercado['preco_m2']['medio']:,.2f}/m2")

    if resultado_mercado.get('valor_estimado'):
        print(f"\nValor Estimado (area {resultado_mercado['valor_estimado']['area_referencia']}m2):")
        print(f"  R$ {resultado_mercado['valor_estimado']['valor']:,.2f}")

    # 2. Comparacao com imovel de leilao
    print("\n" + "-" * 50)
    print("[2] COMPARACAO COM IMOVEL DE LEILAO")
    print("-" * 50)

    comparacao = comparar_imovel_mercado(IMOVEL, resultado_mercado)

    print(f"\nPreco Leilao:        R$ {comparacao['preco_leilao']:,.2f}")
    print(f"Valor Avaliacao:     R$ {comparacao['valor_avaliacao']:,.2f}")
    print(f"Preco Mercado Medio: R$ {comparacao['preco_mercado_medio']:,.2f}")

    print(f"\nDescontos:")
    print(f"  vs. Avaliacao: {comparacao['desconto_vs_avaliacao']:.1f}%")
    print(f"  vs. Mercado:   {comparacao['desconto_vs_mercado']:.1f}%")

    print(f"\nPotencial de Lucro:")
    print(f"  Lucro Bruto:   R$ {comparacao['lucro_bruto_potencial']:,.2f}")
    print(f"  Margem Bruta:  {comparacao['margem_bruta_pct']:.1f}%")

    print(f"\nClassificacao: {comparacao['classificacao_oportunidade']}")

    # 3. Calculo de ROI
    print("\n" + "-" * 50)
    print("[3] CALCULO DE ROI")
    print("-" * 50)

    preco_compra = IMOVEL['preco']
    itbi = preco_compra * 0.03  # 3% SP
    cartorio = 2500
    reforma = 38.72 * 500  # R$ 500/m2
    custos_aquisicao = preco_compra + itbi + cartorio + reforma

    valor_venda = resultado_mercado.get('valor_estimado', {}).get('valor', 0) * 0.95  # -5% para venda rapida
    comissao = valor_venda * 0.06  # 6% corretor
    ir = max(0, (valor_venda - custos_aquisicao) * 0.15)  # 15% IR sobre lucro

    lucro_liquido = valor_venda - custos_aquisicao - comissao - ir
    roi = (lucro_liquido / custos_aquisicao) * 100

    print(f"\nCustos de Aquisicao:")
    print(f"  Preco:        R$ {preco_compra:,.2f}")
    print(f"  ITBI (3%):    R$ {itbi:,.2f}")
    print(f"  Cartorio:     R$ {cartorio:,.2f}")
    print(f"  Reforma:      R$ {reforma:,.2f}")
    print(f"  TOTAL:        R$ {custos_aquisicao:,.2f}")

    print(f"\nVenda:")
    print(f"  Valor Venda:  R$ {valor_venda:,.2f}")
    print(f"  Comissao:     R$ {comissao:,.2f}")
    print(f"  IR (15%):     R$ {ir:,.2f}")

    print(f"\nResultado:")
    print(f"  Lucro Liquido: R$ {lucro_liquido:,.2f}")
    print(f"  ROI:           {roi:.1f}%")

    # 4. Recomendacao
    print("\n" + "=" * 70)
    print("RECOMENDACAO FINAL")
    print("=" * 70)

    if comparacao['classificacao_oportunidade'] in ['EXCELENTE', 'MUITO_BOA'] and roi > 30:
        print("\n>>> COMPRAR <<<")
        print(f"Oportunidade {comparacao['classificacao_oportunidade']} com ROI de {roi:.1f}%")
    elif comparacao['classificacao_oportunidade'] == 'BOA' and roi > 20:
        print("\n>>> ANALISAR COM CAUTELA <<<")
        print(f"Oportunidade BOA com ROI de {roi:.1f}%")
    else:
        print("\n>>> AGUARDAR <<<")
        print(f"Oportunidade {comparacao['classificacao_oportunidade']} com ROI de {roi:.1f}%")

    print("\n" + "=" * 70)
    print("TESTE CONCLUIDO")
    print("=" * 70)


if __name__ == "__main__":
    main()
