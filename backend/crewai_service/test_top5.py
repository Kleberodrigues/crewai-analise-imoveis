"""
Teste do sistema de selecao Top 5 e geracao de relatorios
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Configura encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Adiciona diretorio ao path
sys.path.insert(0, str(Path(__file__).parent))

from tools.top5_selector import selecionar_top5, gerar_resumo_selecao, calcular_score_oportunidade
from tools.output_tools import gerar_csv_top5, gerar_pdf_top5_consolidado

print("=" * 60)
print("TESTE DO SISTEMA TOP 5")
print("=" * 60)

# Dados de teste (simulando imoveis analisados)
imoveis_teste = [
    {
        "id_imovel": "1001",
        "endereco": "Rua das Flores, 123 - Apto 45",
        "bairro": "Vila Mariana",
        "cidade": "SAO PAULO",
        "tipo_imovel": "Apartamento",
        "area_privativa": 65,
        "quartos": 2,
        "vagas": 1,
        "preco": 95000,
        "valor_avaliacao": 180000,
        "desconto": 47.2,
        "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=1001",
        "recomendacao": "COMPRAR",
        "nivel_risco": "BAIXO",
        "justificativa": "Excelente ROI de 120% em 6 meses com desconto de 47%",
        "pontos_atencao": ["Imovel ocupado", "Debitos condominio R$ 8.000"],
        "scores": {
            "edital": 75,
            "matricula": 85,
            "localizacao": 90,
            "financeiro": 92,
            "liquidez": 85,
            "geral": 85.5
        },
        "custos": {
            "investimento_total": 145000,
            "resultado_venda": {
                "preco_venda": 350000,
                "lucro_liquido": 180000,
                "roi_total_percentual": 124.1,
                "roi_mensal_percentual": 20.7,
                "margem_seguranca_percentual": 58.5
            }
        },
        "pesquisa_mercado": {
            "valor_estimado": 350000,
            "preco_m2": 5384
        },
        "analise_matricula": {
            "valor_gravames": 8000
        }
    },
    {
        "id_imovel": "1002",
        "endereco": "Av. Brasil, 456 - Bloco B Apto 12",
        "bairro": "Gonzaga",
        "cidade": "SANTOS",
        "tipo_imovel": "Apartamento",
        "area_privativa": 72,
        "quartos": 3,
        "vagas": 1,
        "preco": 120000,
        "valor_avaliacao": 220000,
        "desconto": 45.5,
        "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=1002",
        "recomendacao": "COMPRAR",
        "nivel_risco": "MEDIO",
        "justificativa": "Bom ROI de 95% com localizacao privilegiada no litoral",
        "pontos_atencao": ["Penhora de R$ 15.000", "Condominio atrasado"],
        "scores": {
            "edital": 70,
            "matricula": 75,
            "localizacao": 85,
            "financeiro": 88,
            "liquidez": 80,
            "geral": 80.1
        },
        "custos": {
            "investimento_total": 175000,
            "resultado_venda": {
                "preco_venda": 380000,
                "lucro_liquido": 165000,
                "roi_total_percentual": 94.3,
                "roi_mensal_percentual": 15.7,
                "margem_seguranca_percentual": 45.2
            }
        },
        "pesquisa_mercado": {
            "valor_estimado": 380000,
            "preco_m2": 5277
        },
        "analise_matricula": {
            "valor_gravames": 15000
        }
    },
    {
        "id_imovel": "1003",
        "endereco": "Rua dos Pinheiros, 789 - Apto 301",
        "bairro": "Mooca",
        "cidade": "SAO PAULO",
        "tipo_imovel": "Apartamento",
        "area_privativa": 55,
        "quartos": 2,
        "vagas": 1,
        "preco": 85000,
        "valor_avaliacao": 160000,
        "desconto": 46.9,
        "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=1003",
        "recomendacao": "COMPRAR",
        "nivel_risco": "BAIXO",
        "justificativa": "ROI de 110% com risco baixo",
        "pontos_atencao": ["Imovel ocupado"],
        "scores": {
            "edital": 78,
            "matricula": 88,
            "localizacao": 82,
            "financeiro": 85,
            "liquidez": 78,
            "geral": 82.4
        },
        "custos": {
            "investimento_total": 130000,
            "resultado_venda": {
                "preco_venda": 290000,
                "lucro_liquido": 140000,
                "roi_total_percentual": 107.7,
                "roi_mensal_percentual": 17.9,
                "margem_seguranca_percentual": 52.3
            }
        },
        "pesquisa_mercado": {
            "valor_estimado": 290000,
            "preco_m2": 5272
        },
        "analise_matricula": {
            "valor_gravames": 5000
        }
    },
    {
        "id_imovel": "1004",
        "endereco": "Rua Augusta, 1000 - Apto 88",
        "bairro": "Consolacao",
        "cidade": "SAO PAULO",
        "tipo_imovel": "Apartamento",
        "area_privativa": 48,
        "quartos": 1,
        "vagas": 0,
        "preco": 75000,
        "valor_avaliacao": 140000,
        "desconto": 46.4,
        "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=1004",
        "recomendacao": "ANALISAR_MELHOR",
        "nivel_risco": "MEDIO",
        "justificativa": "ROI bom mas area pequena pode dificultar venda",
        "pontos_atencao": ["Apenas 1 quarto", "Sem vaga"],
        "scores": {
            "edital": 72,
            "matricula": 80,
            "localizacao": 88,
            "financeiro": 78,
            "liquidez": 65,
            "geral": 77.0
        },
        "custos": {
            "investimento_total": 115000,
            "resultado_venda": {
                "preco_venda": 220000,
                "lucro_liquido": 85000,
                "roi_total_percentual": 73.9,
                "roi_mensal_percentual": 12.3,
                "margem_seguranca_percentual": 38.5
            }
        },
        "pesquisa_mercado": {
            "valor_estimado": 220000,
            "preco_m2": 4583
        },
        "analise_matricula": {
            "valor_gravames": 10000
        }
    },
    {
        "id_imovel": "1005",
        "endereco": "Rua do Porto, 555 - Casa 2",
        "bairro": "Centro",
        "cidade": "GUARUJA",
        "tipo_imovel": "Apartamento",
        "area_privativa": 80,
        "quartos": 3,
        "vagas": 2,
        "preco": 140000,
        "valor_avaliacao": 280000,
        "desconto": 50.0,
        "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=1005",
        "recomendacao": "COMPRAR",
        "nivel_risco": "MEDIO",
        "justificativa": "Desconto de 50% e boa area",
        "pontos_atencao": ["Penhora R$ 25.000", "Ocupado"],
        "scores": {
            "edital": 68,
            "matricula": 72,
            "localizacao": 80,
            "financeiro": 90,
            "liquidez": 75,
            "geral": 77.9
        },
        "custos": {
            "investimento_total": 200000,
            "resultado_venda": {
                "preco_venda": 420000,
                "lucro_liquido": 190000,
                "roi_total_percentual": 95.0,
                "roi_mensal_percentual": 15.8,
                "margem_seguranca_percentual": 42.0
            }
        },
        "pesquisa_mercado": {
            "valor_estimado": 420000,
            "preco_m2": 5250
        },
        "analise_matricula": {
            "valor_gravames": 25000
        }
    },
    {
        "id_imovel": "1006",
        "endereco": "Rua Sao Bento, 200 - Apto 1502",
        "bairro": "Centro",
        "cidade": "SAO PAULO",
        "tipo_imovel": "Apartamento",
        "area_privativa": 45,
        "quartos": 1,
        "vagas": 0,
        "preco": 65000,
        "valor_avaliacao": 120000,
        "desconto": 45.8,
        "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=1006",
        "recomendacao": "ANALISAR_MELHOR",
        "nivel_risco": "MEDIO",
        "justificativa": "Localizacao central mas area muito pequena",
        "pontos_atencao": ["1 quarto", "Centro historico"],
        "scores": {
            "edital": 70,
            "matricula": 82,
            "localizacao": 75,
            "financeiro": 72,
            "liquidez": 60,
            "geral": 72.2
        },
        "custos": {
            "investimento_total": 100000,
            "resultado_venda": {
                "preco_venda": 180000,
                "lucro_liquido": 60000,
                "roi_total_percentual": 60.0,
                "roi_mensal_percentual": 10.0,
                "margem_seguranca_percentual": 32.0
            }
        },
        "pesquisa_mercado": {
            "valor_estimado": 180000,
            "preco_m2": 4000
        },
        "analise_matricula": {
            "valor_gravames": 8000
        }
    },
    {
        "id_imovel": "1007",
        "endereco": "Av. Paulista, 900 - Apto 45",
        "bairro": "Bela Vista",
        "cidade": "SAO PAULO",
        "tipo_imovel": "Apartamento",
        "area_privativa": 58,
        "quartos": 2,
        "vagas": 1,
        "preco": 110000,
        "valor_avaliacao": 200000,
        "desconto": 45.0,
        "link": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=1007",
        "recomendacao": "EVITAR",
        "nivel_risco": "ALTO",
        "justificativa": "Penhoras muito altas comprometem investimento",
        "pontos_atencao": ["Penhoras R$ 120.000", "Multiplas acoes judiciais"],
        "scores": {
            "edital": 45,
            "matricula": 35,
            "localizacao": 92,
            "financeiro": 55,
            "liquidez": 70,
            "geral": 58.2
        },
        "custos": {
            "investimento_total": 280000,
            "resultado_venda": {
                "preco_venda": 320000,
                "lucro_liquido": 20000,
                "roi_total_percentual": 7.1,
                "roi_mensal_percentual": 1.2,
                "margem_seguranca_percentual": 8.5
            }
        },
        "pesquisa_mercado": {
            "valor_estimado": 320000,
            "preco_m2": 5517
        },
        "analise_matricula": {
            "valor_gravames": 120000
        }
    }
]

print(f"\n1. Total de imoveis de teste: {len(imoveis_teste)}")

# Teste do calculo de score de oportunidade
print("\n2. Testando calculo de score de oportunidade:")
for imovel in imoveis_teste[:3]:
    score = calcular_score_oportunidade(imovel)
    print(f"   {imovel['id_imovel']} ({imovel['bairro']}): Score Oport. = {score:.1f}")

# Teste da selecao top 5
print("\n3. Selecionando top 5...")
top5 = selecionar_top5(imoveis_teste, quantidade=5)

print(f"\n4. Top 5 selecionados:")
for i, imovel in enumerate(top5, 1):
    print(f"   #{i} - ID: {imovel.get('id_imovel')}")
    print(f"       Endereco: {imovel.get('endereco')[:45]}...")
    print(f"       Score Geral: {imovel.get('scores', {}).get('geral', 0):.1f}")
    print(f"       Score Oportunidade: {imovel.get('score_oportunidade', 0):.1f}")
    print(f"       ROI: {imovel.get('custos', {}).get('resultado_venda', {}).get('roi_total_percentual', 0):.1f}%")
    print(f"       Recomendacao: {imovel.get('recomendacao')}")
    print()

# Teste do resumo de selecao
print("5. Gerando resumo da selecao...")
resumo = gerar_resumo_selecao(top5, len(imoveis_teste))
print(f"   Total analisados: {resumo.get('total_analisados')}")
print(f"   Total selecionados: {resumo.get('total_selecionados')}")
print(f"   Taxa de selecao: {resumo.get('taxa_selecao_pct')}%")

if resumo.get("estatisticas"):
    stats = resumo["estatisticas"]
    print(f"   Score medio: {stats.get('score_oportunidade', {}).get('media', 0):.1f}")
    print(f"   ROI medio: {stats.get('roi_percentual', {}).get('media', 0):.1f}%")
    print(f"   Investimento total: R$ {stats.get('investimento_total', {}).get('total', 0):,.2f}")

# Teste da geracao de CSV Top 5
print("\n6. Gerando CSV Top 5...")
csv_result = gerar_csv_top5(top5)
print(f"   Status: {csv_result.get('status')}")
print(f"   Arquivo: {csv_result.get('filepath')}")

# Teste da geracao de PDF Top 5
print("\n7. Gerando PDF Top 5 consolidado...")
pdf_result = gerar_pdf_top5_consolidado(
    top5,
    titulo="Top 5 Oportunidades - Teste",
    resumo_selecao=resumo
)
print(f"   Status: {pdf_result.get('status')}")
print(f"   Arquivo: {pdf_result.get('filepath')}")
if pdf_result.get('total_paginas'):
    print(f"   Paginas: {pdf_result.get('total_paginas')}")

print("\n" + "=" * 60)
print("TESTE CONCLUIDO COM SUCESSO!")
print("=" * 60)

# Mostra arquivos gerados
print("\nArquivos gerados:")
print(f"  - {csv_result.get('filepath')}")
print(f"  - {pdf_result.get('filepath')}")
