#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste direto do CrewAI sem passar pelo n8n
"""

import sys
import requests
import os
import json

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Dados de teste simplificados
dados_teste = {
    "id": "5fbeb640-65ec-4745-bab3-e80e93846878",
    "codigo_imovel": "SP-TEST-001",
    "endereco": "Rua Exemplo, 123",
    "bairro": "Vila Mariana",
    "cidade": "São Paulo",
    "estado": "SP",
    "regiao_sp": "capital",
    "zona_sp": "sul",
    "tipo_imovel": "Apartamento",
    "area_total": 65.0,
    "quartos": 2,
    "banheiros": 1,
    "valor_avaliacao": 180000.00,
    "valor_minimo": 150000.00,
    "tipo_leilao": "1º Leilão",
    "link_edital": "https://exemplo.com/edital",
    "observacoes": "Imóvel desocupado, em bom estado",
    "situacao": "disponivel"
}

print("=" * 60)
print("🧪 TESTE DIRETO DO CREWAI")
print("=" * 60)

url = os.getenv("CREWAI_URL", "https://your-crewai.example.com/analisar")
api_token = os.getenv("CREWAI_API_TOKEN")
print(f"\n📍 URL: {url}")
print(f"📦 Payload: {json.dumps(dados_teste, indent=2)}")

print("\n⏳ Enviando requisição...")
print("   (Isso pode levar 60-120 segundos - os agentes de IA estão analisando)")

try:
    headers = {"x-api-key": api_token} if api_token else {}
    response = requests.post(url, json=dados_teste, headers=headers, timeout=180)

    print(f"\n📊 Status Code: {response.status_code}")

    if response.status_code == 200:
        print("✅ SUCESSO!")
        print("\n📄 Resposta:")
        try:
            resultado = response.json()
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        except:
            print(response.text)
    else:
        print(f"❌ ERRO!")
        print(f"\n📄 Response: {response.text}")

except requests.exceptions.Timeout:
    print("\n⏰ TIMEOUT: A análise demorou mais de 3 minutos")
    print("   Isso pode acontecer na primeira execução ou com muitos dados")
except Exception as e:
    print(f"\n❌ ERRO: {e}")

print("\n" + "=" * 60)
