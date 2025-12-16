#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes locais sem pytest para validar a API Flask do CrewAI.
Executa via test_client do Flask, sem depender de rede externa.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.crewai_service.main import app


def print_result(title: str, resp):
    try:
        data = resp.get_json()
    except Exception:
        data = None
    print(f"\n== {title} ==")
    print(f"Status: {resp.status_code}")
    if data is not None:
        # Limitar a saída
        snippet = json.dumps(data, ensure_ascii=False)[:1000]
        print(f"Body: {snippet}")
    else:
        print("Body: <non-json>")


def main():
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Health
        r = client.get("/health")
        print_result("GET /health", r)

        # POST /analisar com payload mínimo
        payload = {
            "id": "00000000-0000-0000-0000-000000000000",
            "codigo_imovel": "SP-LOCAL-TEST",
            "endereco": "Rua Teste, 123",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "estado": "SP",
            "tipo_imovel": "Apartamento",
            "area_total": 60.0,
            "quartos": 2,
            "banheiros": 1,
            "valor_avaliacao": 180000.00,
            "valor_minimo": 150000.00,
            "tipo_leilao": "1º Leilão",
            "observacoes": "Teste local"
        }
        r = client.post("/analisar", json=payload)
        print_result("POST /analisar", r)

        # POST /test (mock)
        r = client.post("/test")
        print_result("POST /test", r)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erro ao executar testes locais: {e}")
        sys.exit(1)
