# -*- coding: utf-8 -*-
"""
Teste de inicialização do backend
Verifica se todos os módulos podem ser importados
"""

import sys
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

print("="*60)
print("TESTE DE INICIALIZACAO DO BACKEND")
print("="*60)

# Adicionar path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'crewai_service'))

print("\n[1/6] Testando importacao de config_saas...")
try:
    from config_saas import Config, TIER_CONFIGS, SubscriptionTier
    print(f"[OK] Config importado")
    print(f"     API Key AbacatePay: {Config.ABACATEPAY_API_KEY[:20]}...")
except Exception as e:
    print(f"[ERRO] {e}")
    sys.exit(1)

print("\n[2/6] Testando importacao de auth_saas...")
try:
    from auth_saas import init_supabase, require_auth
    print("[OK] Auth importado")
except Exception as e:
    print(f"[ERRO] {e}")
    sys.exit(1)

print("\n[3/6] Testando importacao de payments_abacatepay...")
try:
    from payments_abacatepay import init_abacatepay, register_payment_routes
    print("[OK] Payments importado")
except Exception as e:
    print(f"[ERRO] {e}")
    sys.exit(1)

print("\n[4/6] Testando inicializacao do cliente AbacatePay...")
try:
    client = init_abacatepay()
    if client:
        print("[OK] Cliente AbacatePay inicializado")
    else:
        print("[AVISO] Cliente retornou None (verifique API key)")
except Exception as e:
    print(f"[ERRO] {e}")

print("\n[5/6] Testando importacao de cache_redis...")
try:
    from cache_redis import get_cached_analysis, set_cached_analysis
    print("[OK] Cache importado")
except Exception as e:
    print(f"[AVISO] Cache nao disponivel: {e}")

print("\n[6/6] Testando importacao de celery_tasks...")
try:
    from celery_tasks import analyze_property_async
    print("[OK] Celery tasks importado")
except Exception as e:
    print(f"[AVISO] Celery nao disponivel: {e}")

print("\n" + "="*60)
print("RESUMO")
print("="*60)
print("[OK] Todos os modulos principais foram importados com sucesso!")
print("\nSistema pronto para iniciar!")
print("\nPara iniciar o backend:")
print("  cd backend/crewai_service")
print("  python main_saas.py")
print("="*60)
