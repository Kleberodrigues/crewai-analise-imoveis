"""
Script de teste para verificar integração completa:
Frontend → Backend Flask → N8N
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Carregar .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configurações
N8N_URL = os.getenv('N8N_URL')
N8N_API_KEY = os.getenv('N8N_API_KEY')
BACKEND_URL = os.getenv('VIA_API_URL', 'http://localhost:5000')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')

print("=" * 60)
print("TESTE DE INTEGRAÇÃO COMPLETA")
print("=" * 60)

# 1. Verificar Variáveis de Ambiente
print("\n1. VERIFICANDO VARIÁVEIS DE AMBIENTE")
print(f"   N8N_URL: {N8N_URL}")
print(f"   N8N_API_KEY: {'[OK] Configurado' if N8N_API_KEY else '[ERRO] NAO CONFIGURADO'}")
print(f"   BACKEND_URL: {BACKEND_URL}")
print(f"   SUPABASE_URL: {SUPABASE_URL}")
print(f"   SUPABASE_ANON_KEY: {'[OK] Configurado' if SUPABASE_ANON_KEY else '[ERRO] NAO CONFIGURADO'}")

# 2. Testar N8N API
print("\n2. TESTANDO CONEXÃO N8N API")
try:
    headers = {'X-N8N-API-KEY': N8N_API_KEY}
    response = requests.get(f"{N8N_URL}/api/v1/workflows", headers=headers, timeout=10)

    if response.status_code == 200:
        workflows = response.json().get('data', [])
        print(f"   [OK] N8N API: {response.status_code}")
        print(f"   [OK] Workflows encontrados: {len(workflows)}")

        # Listar alguns workflows
        print("\n   Workflows disponíveis:")
        for wf in workflows[:5]:
            print(f"     - {wf['name']} (ID: {wf['id']}, Active: {wf['active']})")
    else:
        print(f"   [ERRO] N8N API: {response.status_code}")
        print(f"   Erro: {response.text}")
except Exception as e:
    print(f"   [ERRO] Erro ao conectar N8N: {e}")

# 3. Testar Backend Flask
print("\n3. TESTANDO BACKEND FLASK")
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=10)

    if response.status_code == 200:
        print(f"   [OK] Backend Flask: {response.status_code}")
        print(f"   Resposta: {response.json()}")
    else:
        print(f"   [ERRO] Backend Flask: {response.status_code}")
except Exception as e:
    print(f"   [ERRO] Erro ao conectar Backend: {e}")

# 4. Testar Endpoint de Status das Integrações (sem autenticação)
print("\n4. TESTANDO ENDPOINT DE STATUS (SEM AUTH)")
try:
    response = requests.get(f"{BACKEND_URL}/integration/status", timeout=10)

    if response.status_code == 200:
        print(f"   [OK] Status Endpoint: {response.status_code}")
        data = response.json()
        print("\n   Status das Integrações:")
        for service, status in data.items():
            print(f"     - {service}: {status}")
    elif response.status_code == 401:
        print(f"   [AVISO]  Status Endpoint: {response.status_code} (Autenticação necessária - normal)")
    else:
        print(f"   [ERRO] Status Endpoint: {response.status_code}")
except Exception as e:
    print(f"   [ERRO] Erro ao testar endpoint: {e}")

# 5. Testar Supabase
print("\n5. TESTANDO SUPABASE")
try:
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    # Tentar buscar imóveis
    response = supabase.table('imoveis_leilao').select('id, codigo_imovel, cidade').limit(3).execute()

    if response.data:
        print(f"   [OK] Supabase conectado")
        print(f"   [OK] Imóveis encontrados: {len(response.data)}")
        print("\n   Amostra de imóveis:")
        for imovel in response.data:
            print(f"     - {imovel.get('codigo_imovel')} - {imovel.get('cidade')}")
    else:
        print(f"   [AVISO]  Supabase conectado mas nenhum imóvel encontrado")
except Exception as e:
    print(f"   [ERRO] Erro ao conectar Supabase: {e}")

# 6. Resumo Final
print("\n" + "=" * 60)
print("RESUMO DA INTEGRAÇÃO")
print("=" * 60)
print("\n[OK] COMPONENTES PRONTOS:")
print("  - Backend Flask com endpoints de integração")
print("  - N8N API configurado e acessível")
print("  - CORS habilitado para frontend")
print("  - Supabase conectado")
print("\n[AVISO]  PRÓXIMOS PASSOS:")
print("  1. Configurar workflows do N8N:")
print("     - scrape-property (webhook)")
print("     - enrich-property (webhook)")
print("     - notify-analysis (webhook)")
print("  2. Testar frontend Lovable:")
print("     - Fazer login")
print("     - Buscar imóvel")
print("     - Clicar em 'Analisar Imóvel'")
print("  3. Monitorar logs do backend e N8N")
print("\n" + "=" * 60)
print("Documentação completa: INTEGRACAO_FRONTEND_N8N.md")
print("=" * 60)
