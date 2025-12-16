#!/usr/bin/env python3
"""
Script para testar o workflow do N8N
"""

import requests
import json

print("=" * 60)
print("TESTE DO WORKFLOW N8N")
print("=" * 60)

# URL do webhook N8N
webhook_url = "https://n8n.kleberodrigues.shop/webhook/analyze-property"

# Dados de teste
test_data = {
    "imovel_id": "teste-123-abc",
    "user_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0ZS11c2VyLWlkLTEyMyIsImVtYWlsIjoidGVzdGVAZXhhbXBsZS5jb20ifQ.test"
}

print(f"\n[INFO] Testando webhook: {webhook_url}")
print(f"[INFO] Dados enviados:")
print(json.dumps(test_data, indent=2))

try:
    print("\n[INFO] Enviando requisição POST...")

    response = requests.post(
        webhook_url,
        headers={'Content-Type': 'application/json'},
        json=test_data,
        timeout=30
    )

    print(f"\n[RESULTADO] Status Code: {response.status_code}")

    if response.status_code == 200:
        print("[OK] SUCESSO! Workflow funcionou!")
        print("\n[RESPOSTA]:")
        try:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # Validar campos esperados
            if 'user_id' in result and 'imovel_id' in result:
                print("\n[VALIDACAO] Campos user_id e imovel_id presentes!")
                print(f"  user_id: {result['user_id']}")
                print(f"  imovel_id: {result['imovel_id']}")
            else:
                print("\n[AVISO] Campos esperados não encontrados na resposta")

        except json.JSONDecodeError:
            print(response.text)
    else:
        print(f"[ERRO] Falha no workflow!")
        print(f"\n[RESPOSTA]:")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("[ERRO] Não foi possível conectar ao N8N")
    print("  Verifique se:")
    print("  1. O workflow está ATIVO (toggle verde no N8N)")
    print("  2. O path do webhook está correto: 'analyze-property'")
    print("  3. A URL do N8N está acessível")

except requests.exceptions.Timeout:
    print("[ERRO] Timeout - o workflow demorou muito para responder")
    print("  Isso pode indicar que o workflow está travado")

except Exception as e:
    print(f"[ERRO] Erro inesperado: {e}")

print("\n" + "=" * 60)
print("PRÓXIMOS PASSOS:")
print("=" * 60)

print("""
Se o teste PASSOU:
  ✅ Workflow básico funcionando!
  ✅ Próximo: Adicionar nodes do Supabase e CrewAI

Se o teste FALHOU:
  1. Abra o N8N: https://n8n.kleberodrigues.shop
  2. Abra o workflow criado
  3. Verifique se está ATIVO (toggle verde)
  4. Clique em "Execute Workflow" no N8N para testar manualmente
  5. Veja os erros no painel "Executions" do N8N
""")

print("=" * 60)
