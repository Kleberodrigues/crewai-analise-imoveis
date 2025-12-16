# -*- coding: utf-8 -*-
"""
Teste Direto do Supabase
Verifica se conseguimos criar registros nas tabelas
"""

import sys
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Configurar encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Carregar .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

print("="*60)
print("TESTE DIRETO SUPABASE - TABELAS")
print("="*60)

print(f"\nURL: {SUPABASE_URL}")
print(f"Service Key: {SUPABASE_KEY[:20]}...")

# Inicializar cliente
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n[TESTE 1] Listar tabelas...")
try:
    # Tentar listar profiles (se existir, retorna dados ou vazio)
    response = supabase.table("profiles").select("id", count="exact").limit(1).execute()
    print(f"[OK] Tabela 'profiles' existe")
    print(f"     Registros: {response.count}")
except Exception as e:
    print(f"[ERRO] Tabela 'profiles': {e}")

print("\n[TESTE 2] Criar usuário via Supabase Auth...")
try:
    # Tentar criar usuário de teste
    auth_response = supabase.auth.sign_up({
        "email": "teste.direto@example.com",
        "password": "senha123456",
        "options": {
            "data": {
                "nome_completo": "Teste Direto Supabase"
            }
        }
    })

    if auth_response.user:
        print(f"[OK] Usuário criado no Auth")
        print(f"     ID: {auth_response.user.id}")
        print(f"     Email: {auth_response.user.email}")

        # Aguardar 2 segundos para o trigger executar
        import time
        time.sleep(2)

        # Verificar se perfil foi criado
        print("\n[TESTE 3] Verificar se perfil foi criado automaticamente...")
        profile_response = supabase.table("profiles").select("*").eq("id", auth_response.user.id).execute()

        if profile_response.data and len(profile_response.data) > 0:
            print(f"[OK] Perfil criado automaticamente pelo trigger!")
            print(f"     Nome: {profile_response.data[0].get('nome_completo')}")
            print(f"     Tier: {profile_response.data[0].get('subscription_tier')}")
        else:
            print(f"[ERRO] Perfil NÃO foi criado pelo trigger")
            print(f"[INFO] Isso indica que o trigger handle_new_user() não está funcionando")
    else:
        print(f"[ERRO] Falha ao criar usuário: {auth_response}")

except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()

print("\n[TESTE 4] Inserir perfil manualmente (sem trigger)...")
try:
    # Criar um UUID fake para teste
    import uuid
    test_id = str(uuid.uuid4())

    profile_data = {
        "id": test_id,
        "email": "teste.manual@example.com",
        "nome_completo": "Teste Manual",
        "subscription_tier": "free",
        "limite_analises_mes": 3
    }

    response = supabase.table("profiles").insert(profile_data).execute()

    if response.data:
        print(f"[OK] Perfil criado manualmente")
        print(f"     ID: {response.data[0]['id']}")
        print(f"     Email: {response.data[0]['email']}")
    else:
        print(f"[ERRO] Falha ao criar perfil: {response}")

except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("DIAGNÓSTICO:")
print("="*60)
print("\nSe o TESTE 2 criar usuário mas o TESTE 3 falhar,")
print("significa que o TRIGGER handle_new_user() não está funcionando.")
print("\nSolução:")
print("1. Recriar o trigger no Supabase SQL Editor")
print("2. Ou desabilitar o trigger e criar perfis manualmente no backend")
print("="*60)
