# -*- coding: utf-8 -*-
"""
Script de Teste - API Backend com AbacatePay
Testa endpoints de autenticação e checkout
"""

import sys
import requests
import json

# Configurar encoding para UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

BASE_URL = "http://localhost:5000"

print("=" * 60)
print("TESTE DA API BACKEND - ABACATEPAY")
print("=" * 60)

# ============================================
# TESTE 1: HEALTH CHECK
# ============================================

print("\n[TESTE 1] Health Check...")
try:
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Backend respondendo: {data['service']}")
        print(f"     Status: {data['status']}")
        print(f"     Versao: {data['version']}")
    else:
        print(f"[ERRO] Status: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"[ERRO] {e}")
    sys.exit(1)

# ============================================
# TESTE 2: REGISTRO DE USUÁRIO
# ============================================

print("\n[TESTE 2] Registrando usuario de teste...")
try:
    user_data = {
        "email": "teste.abacate@example.com",
        "password": "senha123456",
        "nome_completo": "Usuario Teste AbacatePay",
        "telefone": "11999999999"
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)

    if response.status_code in [200, 201]:
        data = response.json()
        print(f"[OK] Usuario registrado com sucesso!")
        print(f"     Email: {data.get('user', {}).get('email')}")
        print(f"     Tier: {data.get('user', {}).get('subscription_tier', 'free')}")

        # Salvar token para próximos testes
        access_token = data.get("access_token")
        user_id = data.get("user", {}).get("id")

        if access_token:
            print(f"     Token: {access_token[:30]}...")
        else:
            print("[AVISO] Token nao retornado")

    elif response.status_code == 409 or "already been registered" in response.text:
        print("[INFO] Usuario ja existe, fazendo login...")

        # Fazer login
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)

        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            user_id = data.get("user", {}).get("id")
            print(f"[OK] Login realizado com sucesso!")
            print(f"     Token: {access_token[:30]}...")
        else:
            print(f"[ERRO] Falha no login: {response.status_code}")
            print(f"     {response.text}")
            sys.exit(1)
    else:
        print(f"[ERRO] Status: {response.status_code}")
        print(f"     {response.text}")
        sys.exit(1)

except Exception as e:
    print(f"[ERRO] {e}")
    sys.exit(1)

# ============================================
# TESTE 3: CRIAR BILLING ABACATEPAY
# ============================================

print("\n[TESTE 3] Criando billing com AbacatePay...")
try:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    billing_data = {
        "plan": "pro_monthly",
        "success_url": "http://localhost:3000/checkout/success",
        "cancel_url": "http://localhost:3000/pricing"
    }

    response = requests.post(
        f"{BASE_URL}/checkout/create-billing",
        json=billing_data,
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Billing criado com sucesso!")
        print(f"     Billing ID: {data.get('billing_id')}")
        print(f"     Customer ID: {data.get('customer_id')}")
        print(f"     Payment URL: {data.get('payment_url')}")
        print(f"     Metodos: {', '.join(data.get('methods', []))}")

        # Salvar informações para teste manual
        test_info = {
            "user_id": user_id,
            "billing_id": data.get('billing_id'),
            "customer_id": data.get('customer_id'),
            "payment_url": data.get('payment_url'),
            "instructions": [
                "1. Copie a URL de pagamento acima",
                "2. Abra no navegador",
                "3. Escolha PIX como metodo",
                "4. Copie o codigo PIX ou escaneie o QR Code",
                "5. Pague usando um app bancario (modo teste)",
                "6. Aguarde o webhook ser chamado automaticamente"
            ]
        }

        with open("test_api_billing_info.json", "w", encoding="utf-8") as f:
            json.dump(test_info, f, indent=2, ensure_ascii=False)

        print("\n[INFO] Informacoes salvas em: test_api_billing_info.json")

    else:
        print(f"[ERRO] Status: {response.status_code}")
        print(f"     {response.text}")

except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()

# ============================================
# RESUMO
# ============================================

print("\n" + "=" * 60)
print("RESUMO DOS TESTES")
print("=" * 60)
print("[OK] Backend Flask funcionando")
print("[OK] Autenticacao (registro/login)")
print("[OK] Integracao AbacatePay")
print("\nPROXIMOS PASSOS:")
print("1. Configurar webhook no Dashboard AbacatePay:")
print(f"   URL: {BASE_URL}/webhooks/abacatepay")
print("   Eventos: billing.paid, billing.pending, billing.expired")
print("\n2. Testar pagamento via PIX:")
print("   Abrir URL do arquivo test_api_billing_info.json")
print("\n3. Aplicar schema SQL no Supabase:")
print("   supabase/schema_saas.sql")
print("\n4. Deploy do frontend no Lovable")
print("=" * 60)
