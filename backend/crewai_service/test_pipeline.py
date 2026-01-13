#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste do Pipeline de Análise de Imóveis em Leilão
Testa todos os componentes: scrapers, cálculos, análises e geração de relatórios

Versão 2.0 - Atualizado com testes para:
- ITBI por município (70+ municípios SP)
- Custos diferenciados por tipo de leilão (judicial, extrajudicial, venda_online_caixa)
- Honorários advocatícios como percentual
- Custos de desocupação por situação
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Adiciona path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


def print_header(title: str):
    """Imprime cabeçalho formatado"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Imprime resultado do teste"""
    status = "[OK]" if passed else "[FALHOU]"
    print(f"  {status} {test_name}")
    if details:
        print(f"         {details}")


def print_info(msg: str):
    """Imprime informação"""
    print(f"  [INFO] {msg}")


# ============================================================================
# TESTE 1: Variáveis de Ambiente
# ============================================================================
def test_env_variables():
    """Testa variáveis de ambiente"""
    print_header("TESTE 1: Variáveis de Ambiente")

    required_vars = [
        ("OPENAI_API_KEY", "sk-"),
    ]

    optional_vars = [
        ("SUPABASE_URL", "https://"),
        ("SUPABASE_SERVICE_KEY", "eyJ"),
        ("APIFY_TOKEN", "apify_api_"),
    ]

    all_ok = True

    for var, prefix in required_vars:
        value = os.getenv(var)
        if value and value.startswith(prefix):
            print_result(f"{var}", True, "Configurado")
        elif value:
            print_result(f"{var}", True, "Configurado (formato diferente)")
        else:
            print_result(f"{var}", False, "NAO CONFIGURADO")
            all_ok = False

    for var, prefix in optional_vars:
        value = os.getenv(var)
        if value:
            print_result(f"{var} (opcional)", True, "Configurado")
        else:
            print_info(f"{var}: Não configurado (opcional)")

    return all_ok


# ============================================================================
# TESTE 2: ITBI por Município
# ============================================================================
def test_itbi_por_municipio():
    """Testa cálculo de ITBI com alíquotas por município"""
    print_header("TESTE 2: ITBI por Município SP")

    try:
        from tools.calc_tools import calc_itbi, ITBI_ALIQUOTAS

        # Verifica quantidade de municípios
        num_municipios = len(ITBI_ALIQUOTAS)
        print_result(f"Tabela ITBI carregada", True, f"{num_municipios} municípios")

        if num_municipios < 50:
            print_result("Quantidade mínima", False, f"Esperado >=50, obtido {num_municipios}")
            return False

        # Testa alíquotas específicas (calc_itbi retorna dict)
        testes = [
            ("SAO PAULO", 100000, 3000, "3%"),
            ("SANTOS", 100000, 2000, "2%"),
            ("CAMPINAS", 100000, 3000, "3%"),
            ("GUARULHOS", 100000, 2000, "2%"),
            ("RIBEIRAO PRETO", 100000, 2000, "2%"),
        ]

        all_ok = True
        for cidade, valor, esperado, aliquota in testes:
            resultado = calc_itbi(valor, cidade)
            valor_itbi = resultado.get("valor_itbi", 0)
            if valor_itbi == esperado:
                print_result(f"ITBI {cidade}", True, f"R$ {valor_itbi:,.0f} ({aliquota})")
            else:
                print_result(f"ITBI {cidade}", False, f"Esperado R$ {esperado}, obtido R$ {valor_itbi}")
                all_ok = False

        # Testa cidade não cadastrada (deve usar DEFAULT)
        itbi_default = calc_itbi(100000, "CIDADE_INEXISTENTE")
        print_result("ITBI cidade não cadastrada (DEFAULT)", True, f"R$ {itbi_default.get('valor_itbi', 0):,.0f}")

        return all_ok

    except ImportError as e:
        print_result("Importação calc_tools", False, str(e))
        return False
    except Exception as e:
        print_result("Teste ITBI", False, str(e))
        return False


# ============================================================================
# TESTE 3: Custos por Tipo de Leilão
# ============================================================================
def test_custos_tipo_leilao():
    """Testa custos diferenciados por tipo de leilão"""
    print_header("TESTE 3: Custos por Tipo de Leilão")

    try:
        from tools.calc_tools import (
            calc_comissao_leiloeiro,
            calc_honorarios_advogado,
            CUSTOS_POR_TIPO_LEILAO
        )

        # Verifica tipos cadastrados
        tipos = list(CUSTOS_POR_TIPO_LEILAO.keys())
        print_result("Tipos de leilão cadastrados", True, f"{tipos}")

        valor_teste = 100000
        all_ok = True

        # Teste JUDICIAL (funções retornam dict)
        comissao_jud = calc_comissao_leiloeiro(valor_teste, "judicial")
        hon_jud = calc_honorarios_advogado(valor_teste, "judicial")

        val_comissao_jud = comissao_jud.get("valor_comissao", 0)
        val_hon_jud = hon_jud.get("valor_honorarios", 0)

        if val_comissao_jud == 5000:  # 5% de 100k
            print_result("Comissão leiloeiro JUDICIAL", True, f"R$ {val_comissao_jud:,.0f} (5%)")
        else:
            print_result("Comissão leiloeiro JUDICIAL", False, f"Esperado R$ 5.000, obtido R$ {val_comissao_jud:,.0f}")
            all_ok = False

        if val_hon_jud == 10000:  # 10% de 100k
            print_result("Honorários adv. JUDICIAL", True, f"R$ {val_hon_jud:,.0f} (10%)")
        else:
            print_result("Honorários adv. JUDICIAL", False, f"Esperado R$ 10.000, obtido R$ {val_hon_jud:,.0f}")
            all_ok = False

        # Teste EXTRAJUDICIAL
        comissao_ext = calc_comissao_leiloeiro(valor_teste, "extrajudicial")
        hon_ext = calc_honorarios_advogado(valor_teste, "extrajudicial")

        val_comissao_ext = comissao_ext.get("valor_comissao", 0)
        val_hon_ext = hon_ext.get("valor_honorarios", 0)

        if val_comissao_ext == 5000:  # 5%
            print_result("Comissão leiloeiro EXTRAJUDICIAL", True, f"R$ {val_comissao_ext:,.0f} (5%)")
        else:
            print_result("Comissão leiloeiro EXTRAJUDICIAL", False, f"Esperado R$ 5.000, obtido R$ {val_comissao_ext:,.0f}")
            all_ok = False

        if val_hon_ext == 5000:  # 5% de 100k
            print_result("Honorários adv. EXTRAJUDICIAL", True, f"R$ {val_hon_ext:,.0f} (5%)")
        else:
            print_result("Honorários adv. EXTRAJUDICIAL", False, f"Esperado R$ 5.000, obtido R$ {val_hon_ext:,.0f}")
            all_ok = False

        # Teste VENDA ONLINE CAIXA (sem leiloeiro!)
        comissao_caixa = calc_comissao_leiloeiro(valor_teste, "venda_online_caixa")
        hon_caixa = calc_honorarios_advogado(valor_teste, "venda_online_caixa")

        val_comissao_caixa = comissao_caixa.get("valor_comissao", 0)
        val_hon_caixa = hon_caixa.get("valor_honorarios", 0)

        if val_comissao_caixa == 0:  # SEM COMISSÃO!
            print_result("Comissão leiloeiro VENDA ONLINE CAIXA", True, "R$ 0 (SEM LEILOEIRO)")
        else:
            print_result("Comissão leiloeiro VENDA ONLINE CAIXA", False, f"Esperado R$ 0, obtido R$ {val_comissao_caixa:,.0f}")
            all_ok = False

        if val_hon_caixa == 5000:  # 5%
            print_result("Honorários adv. VENDA ONLINE CAIXA", True, f"R$ {val_hon_caixa:,.0f} (5%)")
        else:
            print_result("Honorários adv. VENDA ONLINE CAIXA", False, f"Esperado R$ 5.000, obtido R$ {val_hon_caixa:,.0f}")
            all_ok = False

        # Teste limites de honorários (mínimo e máximo)
        print_info("Testando limites de honorários...")

        # Valor baixo - deve usar mínimo
        hon_minimo = calc_honorarios_advogado(20000, "judicial")
        val_hon_min = hon_minimo.get("valor_honorarios", 0)
        if val_hon_min == 5000:
            print_result("Honorários MÍNIMO", True, f"R$ {val_hon_min:,.0f}")
        else:
            print_result("Honorários MÍNIMO", False, f"Esperado R$ 5.000 (mínimo), obtido R$ {val_hon_min:,.0f}")

        # Valor alto - deve usar máximo
        hon_maximo = calc_honorarios_advogado(500000, "judicial")
        val_hon_max = hon_maximo.get("valor_honorarios", 0)
        if val_hon_max == 20000:
            print_result("Honorários MÁXIMO", True, f"R$ {val_hon_max:,.0f}")
        else:
            print_result("Honorários MÁXIMO", False, f"Esperado R$ 20.000 (máximo), obtido R$ {val_hon_max:,.0f}")

        return all_ok

    except ImportError as e:
        print_result("Importação calc_tools", False, str(e))
        return False
    except Exception as e:
        print_result("Teste custos tipo leilão", False, str(e))
        return False


# ============================================================================
# TESTE 4: Custos de Desocupação
# ============================================================================
def test_custos_desocupacao():
    """Testa custos de desocupação por situação"""
    print_header("TESTE 4: Custos de Desocupação")

    try:
        from tools.calc_tools import calc_custo_desocupacao, CUSTOS_DESOCUPACAO

        # Verifica situações cadastradas
        situacoes = list(CUSTOS_DESOCUPACAO.keys())
        print_result("Situações cadastradas", True, f"{len(situacoes)} tipos")

        testes = [
            ("desocupado", 0),
            ("ocupado_proprietario", 5000),
            ("ocupado_inquilino", 8000),
            ("ocupado_invasor", 12000),
            ("ocupado_litigioso", 15000),
            ("ocupado_desconhecido", 10000),
        ]

        all_ok = True
        for situacao, esperado in testes:
            resultado = calc_custo_desocupacao(situacao)
            valor = resultado.get("valor_desocupacao", 0)  # Função retorna dict
            if valor == esperado:
                print_result(f"Desocupação '{situacao}'", True, f"R$ {valor:,}")
            else:
                print_result(f"Desocupação '{situacao}'", False, f"Esperado R$ {esperado:,}, obtido R$ {valor:,}")
                all_ok = False

        return all_ok

    except ImportError as e:
        print_result("Importação calc_tools", False, str(e))
        return False
    except Exception as e:
        print_result("Teste desocupação", False, str(e))
        return False


# ============================================================================
# TESTE 5: Custos Totais Integrados
# ============================================================================
def test_custos_totais():
    """Testa cálculo integrado de custos totais"""
    print_header("TESTE 5: Custos Totais Integrados")

    try:
        from tools.calc_tools import calc_custos_totais

        # Cenário 1: Leilão judicial em SP, ocupado
        print_info("Cenário 1: Judicial SP, ocupado litigioso")
        custos1 = calc_custos_totais(
            valor_arrematacao=150000,
            cidade="SAO PAULO",
            tipo_leilao="judicial",
            situacao_ocupacao="ocupado_litigioso",
            preco_venda_estimado=300000
        )

        # O resultado tem estrutura aninhada
        custos_aquisicao = custos1.get("custos_aquisicao", {})

        all_ok = True
        print_result("  ITBI", True, f"R$ {custos_aquisicao.get('itbi', 0):,.2f}")
        print_result("  Comissão leiloeiro", True, f"R$ {custos_aquisicao.get('comissao_leiloeiro', 0):,.2f}")
        print_result("  Honorários advogado", True, f"R$ {custos_aquisicao.get('honorarios_advogado', 0):,.2f}")
        print_result("  Custo desocupação", True, f"R$ {custos_aquisicao.get('custo_desocupacao', 0):,.2f}")
        print_result("  Investimento total", True, f"R$ {custos1.get('investimento_total_com_manutencao', 0):,.2f}")

        # Cenário 2: Venda online Caixa em Santos, desocupado
        print_info("\nCenário 2: Venda Online Caixa Santos, desocupado")
        custos2 = calc_custos_totais(
            valor_arrematacao=100000,
            cidade="SANTOS",
            tipo_leilao="venda_online_caixa",
            situacao_ocupacao="desocupado",
            preco_venda_estimado=200000
        )

        custos_aquisicao2 = custos2.get("custos_aquisicao", {})

        # Venda online deve ter comissão 0
        comissao = custos_aquisicao2.get("comissao_leiloeiro", -1)
        if comissao == 0:
            print_result("  Comissão zerada (venda online)", True, "R$ 0,00")
        else:
            print_result("  Comissão zerada (venda online)", False, f"R$ {comissao:,.2f}")
            all_ok = False

        # Desocupação deve ser 0
        desocup = custos_aquisicao2.get("custo_desocupacao", -1)
        if desocup == 0:
            print_result("  Desocupação zerada", True, "R$ 0,00")
        else:
            print_result("  Desocupação zerada", False, f"R$ {desocup:,.2f}")
            all_ok = False

        # ITBI Santos deve ser 2%
        itbi_esperado = 100000 * 0.02  # 2000
        itbi_obtido = custos_aquisicao2.get("itbi", 0)
        if abs(itbi_obtido - itbi_esperado) < 1:
            print_result("  ITBI Santos 2%", True, f"R$ {itbi_obtido:,.2f}")
        else:
            print_result("  ITBI Santos 2%", False, f"Esperado R$ {itbi_esperado:,.2f}, obtido R$ {itbi_obtido:,.2f}")
            all_ok = False

        print_result("  Investimento total", True, f"R$ {custos2.get('investimento_total_com_manutencao', 0):,.2f}")

        # Comparação: Judicial vs Venda Online
        print_info("\nComparação de custos:")
        total1 = custos1.get("total_custos_aquisicao", 0)
        total2 = custos2.get("total_custos_aquisicao", 0)
        diff = total1 - total2
        print_info(f"  Judicial SP ocupado: R$ {total1:,.2f}")
        print_info(f"  Venda Online Santos: R$ {total2:,.2f}")
        print_info(f"  Diferença: R$ {diff:,.2f}")

        return all_ok

    except ImportError as e:
        print_result("Importação calc_tools", False, str(e))
        return False
    except Exception as e:
        print_result("Teste custos totais", False, str(e))
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TESTE 6: Cenários ROI (usando calc_custos_totais)
# ============================================================================
def test_cenarios_roi():
    """Testa cálculo de ROI através de calc_custos_totais"""
    print_header("TESTE 6: Cenários de ROI")

    try:
        from tools.calc_tools import calc_custos_totais

        # Calcula custos com preço de venda para obter ROI
        resultado = calc_custos_totais(
            valor_arrematacao=150000,
            cidade="SAO PAULO",
            tipo_leilao="venda_online_caixa",
            situacao_ocupacao="desocupado",
            preco_venda_estimado=300000,
            meses_manutencao=6
        )

        resultado_venda = resultado.get("resultado_venda", {})
        cenario_6m = resultado.get("cenario_6_meses", {})

        all_ok = True

        # Verifica ROI calculado
        roi_total = resultado_venda.get("roi_total_percentual", 0)
        if roi_total > 0:
            print_result("ROI total calculado", True, f"{roi_total:.1f}%")
        else:
            print_result("ROI total calculado", False, "ROI zero ou negativo")
            all_ok = False

        # Verifica lucro
        lucro = resultado_venda.get("lucro_liquido", 0)
        if lucro > 0:
            print_result("Lucro líquido", True, f"R$ {lucro:,.2f}")
        else:
            print_result("Lucro líquido", False, f"R$ {lucro:,.2f}")
            all_ok = False

        # Verifica margem de segurança
        margem = resultado_venda.get("margem_seguranca_percentual", 0)
        if margem > 0:
            print_result("Margem segurança", True, f"{margem:.1f}%")
        else:
            print_result("Margem segurança", False, f"{margem:.1f}%")

        # Verifica comparativo CDI
        diff_cdi = resultado_venda.get("diferenca_vs_cdi", 0)
        mult_cdi = resultado_venda.get("multiplicador_cdi", 0)
        print_result("Comparativo CDI", True, f"{mult_cdi:.1f}x o CDI")

        # Verifica cenário 6 meses
        viabilidade = cenario_6m.get("viabilidade", "N/A")
        print_result("Viabilidade 6 meses", True, viabilidade)

        return all_ok

    except ImportError as e:
        print_result("Importação calc_tools", False, str(e))
        return False
    except Exception as e:
        print_result("Teste ROI", False, str(e))
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TESTE 7: Score Tools
# ============================================================================
def test_score_tools():
    """Testa ferramentas de scoring"""
    print_header("TESTE 7: Ferramentas de Score")

    try:
        from tools.score_tools import (
            calc_score_edital, calc_score_matricula, calc_score_localizacao,
            calc_score_financeiro, calc_score_liquidez, calc_score_oportunidade,
            classificar_recomendacao
        )

        # Cenário positivo
        edital = calc_score_edital(ocupacao="desocupado", debitos_total=5000, riscos=[])
        matricula = calc_score_matricula(gravames_extintos=["Hipoteca"], gravames_transferidos=[])
        localizacao = calc_score_localizacao(bairro="Vila Mariana", cidade="SAO PAULO")
        financeiro = calc_score_financeiro(roi_percentual=80, margem_seguranca=40, desconto_percentual=45)
        liquidez = calc_score_liquidez(tempo_venda_dias=60, demanda_regiao="alta")

        score_geral = calc_score_oportunidade(
            score_edital=edital["score"],
            score_matricula=matricula["score"],
            score_localizacao=localizacao["score"],
            score_financeiro=financeiro["score"],
            score_liquidez=liquidez["score"]
        )

        recomendacao = classificar_recomendacao(
            score_geral=score_geral["score_geral"],
            ocupado=False,
            debitos_alto=False
        )

        print_result("Score Edital", True, f"{edital['score']}/100")
        print_result("Score Matrícula", True, f"{matricula['score']}/100")
        print_result("Score Localização", True, f"{localizacao['score']}/100")
        print_result("Score Financeiro", True, f"{financeiro['score']}/100")
        print_result("Score Liquidez", True, f"{liquidez['score']}/100")
        print_result("SCORE GERAL", True, f"{score_geral['score_geral']}/100")
        print_result("Recomendação", True, recomendacao['recomendacao'])

        return True

    except ImportError as e:
        print_result("Importação score_tools", False, str(e))
        return False
    except Exception as e:
        print_result("Teste scores", False, str(e))
        return False


# ============================================================================
# TESTE 8: Scrapers (Importação)
# ============================================================================
def test_scrapers():
    """Testa importação dos scrapers"""
    print_header("TESTE 8: Scrapers (Importação)")

    scrapers = [
        ("Zuk", "scrapers.zuk_scraper", "ZukScraper"),
        ("Superbid", "scrapers.superbid_scraper", "SuperbidScraper"),
        ("Mega Leilões", "scrapers.mega_scraper", "MegaLeiloesScraper"),
        ("Frazão", "scrapers.frazao_scraper", "FrazaoScraper"),
        ("Biasi", "scrapers.biasi_scraper", "BiasiScraper"),
    ]

    ok_count = 0
    for name, module, class_name in scrapers:
        try:
            mod = __import__(module, fromlist=[class_name])
            scraper_class = getattr(mod, class_name)
            print_result(f"Scraper {name}", True, f"Classe {class_name}")
            ok_count += 1
        except ImportError as e:
            print_result(f"Scraper {name}", False, f"Import error: {str(e)[:40]}")
        except AttributeError as e:
            print_result(f"Scraper {name}", False, f"Classe não encontrada")

    print_info(f"Resumo: {ok_count}/{len(scrapers)} scrapers disponíveis")
    return ok_count >= 3  # Pelo menos 3 scrapers devem funcionar


# ============================================================================
# TESTE 9: Main Pipeline
# ============================================================================
def test_main_pipeline():
    """Testa configuração do pipeline principal"""
    print_header("TESTE 9: Main Pipeline")

    try:
        from main_pipeline import PipelineLeilao, FILTROS

        print_result("Importação main_pipeline", True)

        # Verifica filtro de preço
        preco_max = FILTROS.get("preco_max", 0)
        if preco_max == 200000:
            print_result("Filtro preco_max", True, f"R$ {preco_max:,}")
        else:
            print_result("Filtro preco_max", False, f"Esperado R$ 200.000, configurado R$ {preco_max:,}")

        # Verifica se scrapers estão habilitados lendo o arquivo diretamente
        from pathlib import Path
        pipeline_path = Path(__file__).parent / "main_pipeline.py"
        with open(pipeline_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Procura pela linha que retorna coletar_multifonte
        if "usar_scrapers=True" in source:
            print_result("Scrapers habilitados", True, "usar_scrapers=True encontrado")
        elif "usar_scrapers=False" in source:
            print_result("Scrapers habilitados", False, "ATENÇÃO: usar_scrapers=False!")
            return False
        else:
            print_result("Scrapers habilitados", True, "Configuração padrão (True)")

        # Verifica se a classe existe e tem os métodos necessários
        pipeline = PipelineLeilao()
        has_methods = hasattr(pipeline, 'coletar_multifonte') and hasattr(pipeline, 'coletar_caixa')
        if has_methods:
            print_result("Métodos de coleta", True, "coletar_multifonte, coletar_caixa")
        else:
            print_result("Métodos de coleta", False, "Métodos faltando")
            return False

        return True

    except ImportError as e:
        print_result("Importação main_pipeline", False, str(e))
        return False
    except Exception as e:
        print_result("Teste pipeline", False, str(e))
        return False


# ============================================================================
# EXECUÇÃO
# ============================================================================
def run_all_tests():
    """Executa todos os testes"""
    print("\n")
    print("=" * 70)
    print("   TESTE DO PIPELINE DE ANÁLISE DE IMÓVEIS EM LEILÃO v2.0")
    print(f"   Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 70)

    results = {}

    # Executa testes
    results["env"] = test_env_variables()
    results["itbi_municipio"] = test_itbi_por_municipio()
    results["custos_tipo_leilao"] = test_custos_tipo_leilao()
    results["custos_desocupacao"] = test_custos_desocupacao()
    results["custos_totais"] = test_custos_totais()
    results["cenarios_roi"] = test_cenarios_roi()
    results["score_tools"] = test_score_tools()
    results["scrapers"] = test_scrapers()
    results["main_pipeline"] = test_main_pipeline()

    # Resumo
    print_header("RESUMO FINAL")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, passed_test in results.items():
        status = "[OK]" if passed_test else "[FALHOU]"
        print(f"  {status} {test_name}")

    print(f"\n  Resultado: {passed}/{total} testes passaram")

    if passed == total:
        print("\n  === TODOS OS TESTES PASSARAM! ===")
        print("  O pipeline está pronto para execução.")
        print("\n  Próximos passos:")
        print("    1. Execute: python main_pipeline.py")
        print("    2. Ou inicie a API: python api.py")
    else:
        print(f"\n  === {total - passed} TESTE(S) FALHARAM ===")
        print("  Corrija os problemas antes de executar o pipeline.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
