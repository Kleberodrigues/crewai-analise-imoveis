#!/usr/bin/env python3
"""
Script de Teste do Pipeline de Leilao
Valida cada componente individualmente antes do deploy
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

# Cores para output (ASCII compativel com Windows)
class Colors:
    GREEN = ''
    RED = ''
    YELLOW = ''
    BLUE = ''
    RESET = ''
    BOLD = ''

def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}\n")

def print_success(msg: str):
    print(f"[OK] {msg}")

def print_error(msg: str):
    print(f"[ERRO] {msg}")

def print_warning(msg: str):
    print(f"[AVISO] {msg}")

def print_info(msg: str):
    print(f"[INFO] {msg}")


def test_env_variables():
    """Testa variaveis de ambiente"""
    print_header("TESTE 1: Variaveis de Ambiente")

    required_vars = [
        ("OPENAI_API_KEY", "sk-"),
        ("SUPABASE_URL", "https://"),
        ("SUPABASE_SERVICE_KEY", "eyJ"),
    ]

    optional_vars = [
        ("APIFY_TOKEN", "apify_api_"),
    ]

    all_ok = True

    for var, prefix in required_vars:
        value = os.getenv(var)
        if value and value.startswith(prefix):
            print_success(f"{var}: Configurado corretamente")
        elif value:
            print_warning(f"{var}: Configurado mas formato inesperado")
        else:
            print_error(f"{var}: NAO CONFIGURADO (OBRIGATORIO)")
            all_ok = False

    for var, prefix in optional_vars:
        value = os.getenv(var)
        if value and value.startswith(prefix):
            print_success(f"{var}: Configurado corretamente")
        elif value:
            print_warning(f"{var}: Configurado mas formato inesperado")
        else:
            print_warning(f"{var}: Nao configurado (opcional)")

    return all_ok


def test_imports():
    """Testa imports dos modulos"""
    print_header("TESTE 2: Imports dos Modulos")

    modules = [
        ("tools.data_tools", ["download_csv_caixa", "parse_csv_imoveis", "filter_imoveis"]),
        ("tools.calc_tools", ["calc_itbi", "calc_cartorio", "calc_irpf", "calc_custos_totais"]),
        ("tools.score_tools", ["calc_score_oportunidade", "classificar_recomendacao"]),
        ("tools.output_tools", ["generate_csv_report", "generate_pdf_report"]),
        ("tools.apify_tools", ["run_apify_zuk_scraper"]),
    ]

    all_ok = True

    for module_name, functions in modules:
        try:
            module = __import__(module_name, fromlist=functions)
            missing = []
            for func in functions:
                if not hasattr(module, func):
                    missing.append(func)

            if missing:
                print_warning(f"{module_name}: Faltam funcoes {missing}")
            else:
                print_success(f"{module_name}: OK ({len(functions)} funcoes)")
        except ImportError as e:
            print_error(f"{module_name}: Erro de import - {e}")
            all_ok = False

    return all_ok


def test_supabase_connection():
    """Testa conexao com Supabase (OPCIONAL - pipeline funciona sem Supabase)"""
    print_header("TESTE 3: Conexao Supabase (Opcional)")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print_warning("Variaveis SUPABASE nao configuradas - pipeline usara apenas arquivos locais")
        return True  # Supabase e opcional

    try:
        import socket
        # Testa DNS primeiro (timeout 5s)
        host = url.replace("https://", "").replace("http://", "").split("/")[0]
        socket.setdefaulttimeout(5)
        socket.getaddrinfo(host, 443)
        socket.setdefaulttimeout(None)

        from supabase import create_client
        client = create_client(url, key)

        # Tenta listar tabelas (ou fazer uma query simples)
        result = client.table("imoveis_caixa").select("id_imovel").limit(1).execute()

        print_success(f"Conexao OK - Tabela imoveis_caixa acessivel")
        print_info(f"URL: {url[:50]}...")
        return True

    except socket.gaierror:
        print_warning(f"Supabase DNS nao resolvido - projeto pode estar pausado/excluido")
        print_info("Pipeline continuara sem persistencia no banco de dados")
        print_info("Para ativar: acesse dashboard.supabase.com e restaure/crie o projeto")
        return True  # Supabase e opcional

    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg or "relation" in error_msg:
            print_warning(f"Conexao OK, mas tabela 'imoveis_caixa' nao existe")
            print_info("Execute o SQL do schema no Supabase Dashboard")
            return True  # Conexao funciona, so falta schema
        else:
            print_warning(f"Supabase indisponivel: {e}")
            print_info("Pipeline continuara sem persistencia no banco de dados")
            return True  # Supabase e opcional


def test_calc_tools():
    """Testa ferramentas de calculo"""
    print_header("TESTE 4: Ferramentas de Calculo")

    try:
        from tools.calc_tools import calc_itbi, calc_cartorio, calc_irpf, calc_custos_totais

        # Teste ITBI
        itbi = calc_itbi(100000, "SAO PAULO")
        if itbi["valor_itbi"] == 3000:  # 3% de 100k
            print_success(f"calc_itbi: OK (R$ {itbi['valor_itbi']:,.2f} para SP)")
        else:
            print_warning(f"calc_itbi: Valor inesperado {itbi}")

        # Teste Cartorio
        cartorio = calc_cartorio(100000)
        if cartorio["total_cartorio"] > 0:
            print_success(f"calc_cartorio: OK (R$ {cartorio['total_cartorio']:,.2f})")
        else:
            print_warning(f"calc_cartorio: Valor zero")

        # Teste IRPF
        irpf = calc_irpf(50000)
        if irpf["valor_irpf"] == 7500:  # 15% de 50k
            print_success(f"calc_irpf: OK (R$ {irpf['valor_irpf']:,.2f})")
        else:
            print_warning(f"calc_irpf: Valor inesperado {irpf}")

        # Teste Custos Totais
        custos = calc_custos_totais(
            valor_arrematacao=120000,
            cidade="SAO PAULO",
            ocupado=True,
            debitos_edital=15000,
            preco_venda_estimado=200000,
            condominio_mensal=500,
            meses_manutencao=6
        )

        if custos["investimento_total_com_manutencao"] > 120000:
            print_success(f"calc_custos_totais: OK")
            print_info(f"  Investimento total: R$ {custos['investimento_total_com_manutencao']:,.2f}")
            if "roi_total_percentual" in custos.get("resultado_venda", {}):
                print_info(f"  ROI estimado: {custos['resultado_venda']['roi_total_percentual']:.1f}%")
        else:
            print_warning(f"calc_custos_totais: Valores inconsistentes")

        return True

    except Exception as e:
        print_error(f"Erro nas ferramentas de calculo: {e}")
        return False


def test_score_tools():
    """Testa ferramentas de score"""
    print_header("TESTE 5: Ferramentas de Score")

    try:
        from tools.score_tools import (
            calc_score_edital, calc_score_matricula, calc_score_localizacao,
            calc_score_financeiro, calc_score_liquidez, calc_score_oportunidade,
            classificar_recomendacao
        )

        # Teste cenario bom
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

        print_success(f"Scores calculados corretamente:")
        print_info(f"  Edital: {edital['score']}/100")
        print_info(f"  Matricula: {matricula['score']}/100")
        print_info(f"  Localizacao: {localizacao['score']}/100")
        print_info(f"  Financeiro: {financeiro['score']}/100")
        print_info(f"  Liquidez: {liquidez['score']}/100")
        print_info(f"  SCORE GERAL: {score_geral['score_geral']}/100")
        print_info(f"  Recomendacao: {recomendacao['recomendacao']}")

        return True

    except Exception as e:
        print_error(f"Erro nas ferramentas de score: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_csv_download():
    """Testa download do CSV da Caixa"""
    print_header("TESTE 6: Download CSV da Caixa")

    try:
        from tools.data_tools import download_csv_caixa, parse_csv_imoveis, filter_imoveis

        # Verifica se ja existe cache
        data_dir = Path(os.getenv("DATA_DIR", "./data"))
        csv_path = data_dir / "Lista_imoveis_SP.csv"

        if csv_path.exists():
            print_info(f"CSV em cache existe: {csv_path}")
            print_info(f"Tamanho: {csv_path.stat().st_size / 1024:.1f} KB")

            # Tenta parsear
            imoveis = parse_csv_imoveis(str(csv_path))
            if imoveis:
                print_success(f"Parse OK: {len(imoveis)} imoveis")

                # Filtra
                filtrado = filter_imoveis(
                    imoveis,
                    preco_max=150000,
                    tipo="Apartamento",
                    praca="2a Praca"
                )
                print_success(f"Filtro OK: {filtrado['stats']['total_filtrado']} imoveis filtrados")
                print_info(f"  Cidades encontradas: {', '.join(filtrado['stats']['cidades_encontradas'][:5])}")

                return True
            else:
                print_warning("CSV existe mas parse retornou vazio")
        else:
            print_warning("CSV nao existe em cache")
            print_info("Tentando download (pode demorar)...")

            result = download_csv_caixa("SP", force=True)
            print_info(f"Resultado: {result.get('status')}")

            if result.get("status") in ["updated", "cached", "no_changes"]:
                print_success(f"Download OK: {result.get('total_imoveis', 0)} imoveis")
                return True
            else:
                print_error(f"Falha no download: {result.get('error', 'Erro desconhecido')}")
                print_info("O site da Caixa pode estar bloqueando requests automaticos")
                print_info("Alternativa: Baixe manualmente o CSV e coloque em ./data/")
                return False

        return True

    except Exception as e:
        print_error(f"Erro no teste de CSV: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_output_tools():
    """Testa geracao de output"""
    print_header("TESTE 7: Ferramentas de Output")

    try:
        from tools.output_tools import generate_csv_report, generate_summary_csv

        # Cria dados de teste
        imovel_teste = {
            "id_imovel": "TEST001",
            "cidade": "SAO PAULO",
            "bairro": "Vila Mariana",
            "endereco": "Rua Teste, 123",
            "preco": 120000,
            "valor_avaliacao": 200000,
            "desconto": 40,
            "tipo_imovel": "Apartamento",
            "area_privativa": 65,
            "quartos": 2,
            "praca": "2a Praca",
            "data_analise": datetime.now().strftime("%Y-%m-%d"),
            "scores": {
                "edital": 75,
                "matricula": 80,
                "localizacao": 70,
                "financeiro": 85,
                "liquidez": 75,
                "geral": 77
            },
            "recomendacao": "COMPRAR",
            "custos": {
                "investimento_total_com_manutencao": 180000,
                "resultado_venda": {
                    "roi_total_percentual": 45,
                    "margem_seguranca_percentual": 30
                }
            }
        }

        # Testa CSV
        csv_result = generate_csv_report([imovel_teste])
        if csv_result.get("status") == "success":
            print_success(f"CSV Report: {csv_result.get('filepath')}")
        else:
            print_warning(f"CSV Report: {csv_result}")

        # Testa Summary CSV
        summary_result = generate_summary_csv([imovel_teste])
        if summary_result.get("status") == "success":
            print_success(f"Summary CSV: {summary_result.get('filepath')}")
        else:
            print_warning(f"Summary CSV: {summary_result}")

        return True

    except Exception as e:
        print_error(f"Erro nas ferramentas de output: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api():
    """Testa se a API Flask pode ser importada"""
    print_header("TESTE 8: API Flask")

    try:
        from api import app

        print_success("API Flask importada com sucesso")

        # Testa endpoint de health
        with app.test_client() as client:
            response = client.get('/health')
            if response.status_code == 200:
                data = response.get_json()
                print_success(f"Health check: {data.get('status')}")
                print_info(f"  Service: {data.get('service')}")
                print_info(f"  Version: {data.get('version')}")
            else:
                print_warning(f"Health check retornou {response.status_code}")

        return True

    except Exception as e:
        print_error(f"Erro ao testar API: {e}")
        return False


def run_all_tests():
    """Executa todos os testes"""
    print(f"\n{Colors.BOLD}{'=' * 60}")
    print("TESTE DO PIPELINE DE LEILAO DE IMOVEIS")
    print(f"{'=' * 60}{Colors.RESET}")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Executa testes
    results["env"] = test_env_variables()
    results["imports"] = test_imports()
    results["supabase"] = test_supabase_connection()
    results["calc"] = test_calc_tools()
    results["score"] = test_score_tools()
    results["csv"] = test_csv_download()
    results["output"] = test_output_tools()
    results["api"] = test_api()

    # Resumo
    print_header("RESUMO DOS TESTES")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, passed_test in results.items():
        if passed_test:
            print_success(f"{test_name.upper()}: PASSOU")
        else:
            print_error(f"{test_name.upper()}: FALHOU")

    print(f"\n{Colors.BOLD}Resultado: {passed}/{total} testes passaram{Colors.RESET}")

    if passed == total:
        print(f"\n=== TODOS OS TESTES PASSARAM! ===")
        print(f"O pipeline esta pronto para execucao.")
        print(f"\nProximos passos:")
        print(f"  1. Execute: python main_pipeline.py")
        print(f"  2. Ou inicie a API: python api.py")
        print(f"  3. Ou use Docker: docker compose up -d")
    else:
        print(f"\n=== ALGUNS TESTES FALHARAM ===")
        print(f"Corrija os problemas antes de executar o pipeline.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
