#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E via APIs: CrewAI ↔ n8n ↔ Supabase usando apenas bibliotecas padrão.

Pré-requisitos (.env na raiz ou variáveis de ambiente):
  CREWAI_URL=http://localhost:5000
  CREWAI_API_TOKEN=seu_token
  N8N_URL=http://localhost:5678
  SUPABASE_URL=https://YOUR-PROJECT-REF.supabase.co
  SUPABASE_SERVICE_KEY=service_role_key

Uso:
  python scripts/e2e_n8n_test.py
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env_file(path: str) -> dict:
    env = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env


def get_cfg(key: str, default: str = "") -> str:
    # Prioriza env do SO; cai para .env
    if key in os.environ:
        return os.environ[key]
    return ENV_FILE.get(key, default)


def http_request(method: str, url: str, headers: dict | None = None, data: dict | None = None, timeout: int = 30):
    headers = headers or {}
    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        headers.setdefault('Content-Type', 'application/json')
    req = urllib.request.Request(url=url, method=method.upper(), headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            try:
                return resp.getcode(), json.loads(raw)
            except json.JSONDecodeError:
                return resp.getcode(), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', errors='replace')
        try:
            return e.getcode(), json.loads(raw)
        except json.JSONDecodeError:
            return e.getcode(), raw
    except Exception as e:
        return -1, str(e)


def pretty(title: str, status: int, payload):
    print("\n" + "=" * 60)
    print(f"{title}")
    print("-" * 60)
    print(f"Status: {status}")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:2000])
    else:
        print(str(payload)[:2000])


if __name__ == '__main__':
    # Carregar .env
    ENV_FILE = load_env_file(os.path.join(ROOT, '.env'))

    CREWAI_URL = get_cfg('CREWAI_URL', 'http://localhost:5000').rstrip('/')
    CREWAI_API_TOKEN = get_cfg('CREWAI_API_TOKEN', '')
    N8N_URL = get_cfg('N8N_URL', 'http://localhost:5678').rstrip('/')
    SUPABASE_URL = get_cfg('SUPABASE_URL', '').rstrip('/')
    SUPABASE_SERVICE_KEY = get_cfg('SUPABASE_SERVICE_KEY', '')

    missing = []
    if not SUPABASE_URL:
        missing.append('SUPABASE_URL')
    if not SUPABASE_SERVICE_KEY:
        missing.append('SUPABASE_SERVICE_KEY')
    if missing:
        print(f"Variáveis ausentes: {', '.join(missing)}")
        print("Defina no ambiente ou no arquivo .env na raiz.")
        sys.exit(1)

    # 1) Health do CrewAI (fallback para /healthz)
    s, p = http_request('GET', f"{CREWAI_URL}/health")
    if s == 404:
        s, p = http_request('GET', f"{CREWAI_URL}/healthz")
    pretty('GET /health(healthz) (CrewAI)', s, p)

    # 2) Smoke test do CrewAI
    headers = {'x-api-key': CREWAI_API_TOKEN} if CREWAI_API_TOKEN else {}
    s, p = http_request('POST', f"{CREWAI_URL}/test", headers=headers, data={})
    if s == 404:
        # Tentar /analisar com payload mínimo
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
            "observacoes": "Teste via /analisar"
        }
        s, p = http_request('POST', f"{CREWAI_URL}/analisar", headers=headers, data=payload, timeout=180)
        pretty('POST /analisar (fallback CrewAI)', s, p)
    else:
        pretty('POST /test (CrewAI)', s, p)

    # 3) Buscar um imovel_id
    headers_sb = {
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}'
    }
    s, p = http_request('GET', f"{SUPABASE_URL}/rest/v1/imoveis_leilao?select=id&limit=1", headers=headers_sb)
    pretty('GET Supabase imoveis_leilao (1 id)', s, p)
    if not (isinstance(p, list) and p and 'id' in p[0]):
        print('Não foi possível obter um imovel_id. Verifique se a tabela possui dados.')
        sys.exit(1)
    imovel_id = p[0]['id']

    # 4) Disparar webhook n8n
    s, p = http_request('POST', f"{N8N_URL}/webhook/analisar-imovel", headers={'Content-Type': 'application/json'}, data={'imovel_id': imovel_id})
    pretty('POST n8n /webhook/analisar-imovel', s, p)
    analise_id = p['analise_id'] if isinstance(p, dict) else None

    # 5) Aguardar conclusão e verificar no Supabase
    print("\nAguardando processamento da análise (até 120s)...")
    deadline = time.time() + 120
    status = None
    last = None
    while time.time() < deadline:
        if analise_id:
            url = f"{SUPABASE_URL}/rest/v1/analises_viabilidade?id=eq.{analise_id}&select=*&limit=1"
        else:
            url = f"{SUPABASE_URL}/rest/v1/analises_viabilidade?imovel_id=eq.{imovel_id}&order=created_at.desc&limit=1"
        s, p = http_request('GET', url, headers=headers_sb)
        if isinstance(p, list) and p:
            last = p[0]
            status = last.get('status')
            if status in ('concluido', 'erro'):
                break
        time.sleep(5)

    pretty('Supabase analises_viabilidade (resultado)', 200 if last else -1, last or {'erro': 'sem dados'})
    if status != 'concluido':
        print('Análise não ficou concluída dentro do tempo. Verifique logs do n8n e CrewAI.')
        sys.exit(2)

    print("\n✔ E2E concluído com sucesso.")
