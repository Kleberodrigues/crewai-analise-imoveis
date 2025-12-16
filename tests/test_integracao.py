#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste de integração completa
Testa: Supabase → n8n → CrewAI → Supabase
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/analisar-imovel')
CREWAI_URL = os.getenv('CREWAI_URL', 'http://localhost:5000')

def print_header(text):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def test_supabase():
    """Testa conexão com Supabase"""
    print_header("🗄️  TESTE 1: SUPABASE")

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Conexão estabelecida")

        # Verificar tabela imoveis_leilao
        result = supabase.table('imoveis_leilao').select('count', count='exact').limit(0).execute()
        print(f"✅ Tabela 'imoveis_leilao' existe: {result.count} registros")

        # Verificar tabela analises_viabilidade
        try:
            result = supabase.table('analises_viabilidade').select('count', count='exact').limit(0).execute()
            print(f"✅ Tabela 'analises_viabilidade' existe: {result.count} análises")
        except Exception as e:
            print(f"❌ Tabela 'analises_viabilidade' não existe!")
            print(f"   Execute o schema.sql no Supabase Dashboard")
            return False

        # Pegar um imóvel para teste
        result = supabase.table('imoveis_leilao').select('id').limit(1).execute()
        if result.data:
            imovel_id = result.data[0]['id']
            print(f"✅ Imóvel de teste: {imovel_id}")
            return imovel_id
        else:
            print("❌ Nenhum imóvel encontrado no banco")
            return None

    except Exception as e:
        print(f"❌ Erro ao conectar ao Supabase: {e}")
        return None

def test_crewai():
    """Testa backend CrewAI"""
    print_header("🤖 TESTE 2: BACKEND CREWAI")

    try:
        health_url = f"{CREWAI_URL}/healthz"
        print(f"📍 Testando: {health_url}")

        response = requests.get(health_url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend respondendo: {data}")
            return True
        else:
            print(f"❌ Status Code: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Não foi possível conectar ao CrewAI em {CREWAI_URL}")
        print(f"   Verifique se o backend está rodando no Easypanel")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_n8n_webhook(imovel_id):
    """Testa webhook do n8n"""
    print_header("⚙️  TESTE 3: WEBHOOK N8N")

    if not imovel_id:
        print("❌ Não há imóvel para testar")
        return None

    try:
        print(f"📍 Webhook: {N8N_WEBHOOK_URL}")
        print(f"📦 Payload: imovel_id={imovel_id}")

        response = requests.post(
            N8N_WEBHOOK_URL,
            json={"imovel_id": imovel_id},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Webhook respondeu: {data}")

            if 'analise_id' in data:
                analise_id = data['analise_id']
                print(f"✅ Análise criada: {analise_id}")
                return analise_id
            else:
                print("⚠️  Resposta não contém 'analise_id'")
                return None
        else:
            print(f"❌ Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Erro ao chamar webhook: {e}")
        return None

def test_analise_completa(analise_id):
    """Aguarda e verifica análise completa"""
    print_header("🔍 TESTE 4: ANÁLISE COMPLETA")

    if not analise_id:
        print("❌ Não há análise para verificar")
        return False

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        print(f"⏳ Aguardando processamento da análise {analise_id}...")
        print("   (Isso pode levar 60-120 segundos)")

        max_attempts = 24  # 24 x 5s = 2 minutos
        attempt = 0

        while attempt < max_attempts:
            time.sleep(5)
            attempt += 1

            result = supabase.table('analises_viabilidade')\
                .select('*')\
                .eq('id', analise_id)\
                .execute()

            if result.data:
                analise = result.data[0]
                status = analise.get('status')

                print(f"   [{attempt}/{max_attempts}] Status: {status}")

                if status == 'concluido':
                    print("\n✅ ANÁLISE CONCLUÍDA!")
                    print(f"   Score Geral: {analise.get('score_geral')}/100")
                    print(f"   Recomendação: {analise.get('recomendacao')}")
                    print(f"   ROI: {analise.get('roi_percentual')}%")
                    return True

                elif status == 'erro':
                    print("\n❌ Análise terminou com ERRO")
                    print(f"   Detalhes: {analise.get('observacoes_ia')}")
                    return False

        print("\n⏰ Timeout: Análise ainda está processando")
        print("   Verifique manualmente no Supabase depois")
        return False

    except Exception as e:
        print(f"❌ Erro ao verificar análise: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "🚀" * 30)
    print("  TESTE DE INTEGRAÇÃO COMPLETA")
    print("  Sistema: Análise de Imóveis de Leilão")
    print("🚀" * 30)

    # Teste 1: Supabase
    imovel_id = test_supabase()
    if not imovel_id:
        print("\n❌ FALHA: Configure o Supabase primeiro")
        sys.exit(1)

    # Teste 2: CrewAI
    crewai_ok = test_crewai()
    if not crewai_ok:
        print("\n⚠️  AVISO: Backend CrewAI não está respondendo")
        print("   O webhook do n8n vai falhar sem o CrewAI")
        print("\n   ⏩ Continuando mesmo assim para testar webhook...")
        time.sleep(2)

    # Teste 3: Webhook n8n
    analise_id = test_n8n_webhook(imovel_id)
    if not analise_id:
        print("\n❌ FALHA: Webhook n8n não funcionou")
        sys.exit(1)

    # Teste 4: Análise completa
    sucesso = test_analise_completa(analise_id)

    # Resultado final
    print("\n" + "=" * 60)
    if sucesso:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("   Sistema está funcionando end-to-end")
    else:
        print("⚠️  TESTES INCOMPLETOS")
        print("   Verifique os erros acima")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
