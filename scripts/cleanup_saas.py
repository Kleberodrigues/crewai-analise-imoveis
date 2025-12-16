#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Limpeza SaaS - Converter para Uso Pessoal
====================================================
Remove toda a complexidade SaaS e mantém apenas o core
de análise de imóveis para uso pessoal.

USO:
    python scripts/cleanup_saas.py --dry-run    # Simular
    python scripts/cleanup_saas.py --execute    # Executar

O QUE SERÁ REMOVIDO:
- Sistema de assinaturas (Stripe/AbacatePay)
- Sistema de usuários/perfis multi-tenant
- Sistema de créditos e pagamentos
- Documentação SaaS
- Testes de billing
- Frontend Lovable (SaaS)

O QUE SERÁ MANTIDO:
- Análise de imóveis (CrewAI)
- Schema de imóveis e análises
- Workflows N8N
- Backend de análise
"""

import os
import shutil
import argparse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.absolute()

# ============================================
# ARQUIVOS PARA REMOVER (SaaS)
# ============================================

# Schemas SaaS (manter apenas core de análise)
SAAS_SCHEMAS = [
    "supabase/schema_saas.sql",           # Profiles, subscriptions, payments
    "supabase_schema_n8n.sql",            # Credits, orders (AbacatePay)
    "supabase/ADD_ABACATEPAY_COLUMN.sql",
    "supabase/ADD_ABACATEPAY_COLUMNS_SUBSCRIPTIONS.sql",
    "supabase/ADD_BILLING_ID_COLUMN.sql",
    "supabase/ADD_PENDING_STATUS.sql",
    "supabase/FIX_RLS_SUBSCRIPTIONS.sql",
    "supabase/REMOVE_STRIPE_NOT_NULL.sql",
    "supabase/FIX_RLS_CRITICAL.sql",      # Criado para SaaS
]

# Documentação SaaS
SAAS_DOCS = [
    "DEPLOY_SAAS.md",
    "DEPLOY_COMPLETO.md",
    "DEPLOY_VPS.md",
    "RAILWAY_DEPLOY_GUIDE.md",
    "IMPLEMENTACAO_COMPLETA.md",
    "LOVABLE_PROMPT.md",
    "PROMPT_LOVABLE_FRONTEND.md",
    "PROMPT_LOVABLE_PREMIUM.md",
    "INTEGRAR_LOVABLE_BACKEND.md",
    "ENVIAR_PARA_LOVABLE.md",
    "INTEGRACOES_COMPLETAS.md",
    "INTEGRACAO_FRONTEND_N8N.md",
    "SECURITY.md",
    "LOVABLE_api_ts_CORRETO.txt",
]

# Testes de billing/pagamento
SAAS_TESTS = [
    "test_abacatepay.py",
    "test_abacatepay_simple.py",
    "test_billing_only.py",
    "test_integration_frontend.py",
    "billing_success.json",
    "test_billing_info.json",
]

# Diretórios SaaS inteiros
SAAS_DIRS = [
    "frontend",              # Frontend Lovable SaaS
    "frontend-examples",     # Exemplos Lovable
]

# Documentação redundante (independente de SaaS)
REDUNDANT_DOCS = [
    "README_FINAL.md",
    "START_AQUI.md",
    "CONFIGURAR_N8N.md",
    "CONFIGURAR_SUPABASE_N8N.md",
    "CORRECOES_CRITICAS_N8N.md",
    "CORRIGIR_TRIGGER_SUPABASE.md",
    "CORRIGIR_WORKFLOW_N8N.md",
    "DIAGNOSTICO_WORKFLOW_N8N.md",
    "GUIA_CRIACAO_WORKFLOWS_N8N.md",
    "RESUMO_IMPLEMENTACAO_N8N.md",
    "N8N_ARQUITETURA_COMPLETA.md",
    "APLICAR_SCHEMA_SUPABASE.md",
    "PLANO_AGENTES_LEILAO_V2.md",
    "ESTRUTURA_OUTPUT_ANALISE.md",
    "EXECUTAR_AGORA.md",
    "SOLUCAO_CORS_NGROK.md",
    "CONFIGURAR_CLAUDE_PROMPTS_MCP.md",
    "NEXT_STEPS.md",
]

# Scripts de setup redundantes
REDUNDANT_SCRIPTS = [
    "setup_n8n.py",
    "setup_completo_n8n.py",
    "create_n8n_workflows.py",
    "create_workflow_corrected.py",
    "create_complete_workflow.py",
    "import_workflow_n8n.py",
    "atualizar_n8n_url.py",
    "confirmar_email.py",
    "confirmar_usuario_sql.py",
    "check_analise.py",
]

# Testes para mover (não remover, reorganizar)
TESTS_TO_ORGANIZE = [
    "test_backend_api.py",
    "test_backend_completo.py",
    "test_backend_startup.py",
    "test_crewai_direto.py",
    "test_integracao.py",
    "test_integration_complete.py",
    "test_n8n_env.py",
    "test_n8n_workflow.py",
    "test_supabase_direct.py",
]

# ============================================
# FUNÇÕES
# ============================================

def log(msg, level="INFO"):
    icons = {"INFO": "[i]", "DELETE": "[X]", "SKIP": "[-]", "ERROR": "[!]", "SUCCESS": "[+]", "KEEP": "[+]"}
    print(f"{icons.get(level, '[*]')} {msg}")


def remove_file(path: Path, dry_run: bool = True) -> bool:
    if not path.exists():
        return False

    if dry_run:
        log(f"REMOVER: {path.relative_to(BASE_DIR)}", "DELETE")
        return True

    try:
        path.unlink()
        log(f"Removido: {path.relative_to(BASE_DIR)}", "DELETE")
        return True
    except Exception as e:
        log(f"Erro: {path.name} - {e}", "ERROR")
        return False


def remove_dir(path: Path, dry_run: bool = True) -> bool:
    if not path.exists():
        return False

    if dry_run:
        log(f"REMOVER DIRETÓRIO: {path.relative_to(BASE_DIR)}/", "DELETE")
        return True

    try:
        shutil.rmtree(path)
        log(f"Removido: {path.relative_to(BASE_DIR)}/", "DELETE")
        return True
    except Exception as e:
        log(f"Erro: {path.name} - {e}", "ERROR")
        return False


def move_file(src: Path, dst: Path, dry_run: bool = True) -> bool:
    if not src.exists():
        return False

    if dry_run:
        log(f"MOVER: {src.name} -> tests/", "INFO")
        return True

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        log(f"Movido: {src.name} -> tests/", "SUCCESS")
        return True
    except Exception as e:
        log(f"Erro: {src.name} - {e}", "ERROR")
        return False


def run_cleanup(dry_run: bool = True, force: bool = False):
    print("\n" + "=" * 60)
    print("LIMPEZA SAAS - CONVERTER PARA USO PESSOAL")
    print("=" * 60)

    if dry_run:
        print("\n[!] MODO DRY-RUN: Nenhuma alteracao sera feita!\n")
    else:
        print("\n[!] MODO EXECUCAO!")
        if not force:
            confirm = input("Digite 'CONFIRMAR' para continuar: ")
            if confirm != "CONFIRMAR":
                print("Cancelado.")
                return
        else:
            print("[!] Modo --force ativado, pulando confirmacao.\n")

    removed = 0

    # 1. Remover schemas SaaS
    print("\n--- Removendo Schemas SaaS ---")
    for f in SAAS_SCHEMAS:
        if remove_file(BASE_DIR / f, dry_run):
            removed += 1

    # 2. Remover docs SaaS
    print("\n--- Removendo Documentação SaaS ---")
    for f in SAAS_DOCS:
        if remove_file(BASE_DIR / f, dry_run):
            removed += 1

    # 3. Remover testes SaaS
    print("\n--- Removendo Testes de Billing ---")
    for f in SAAS_TESTS:
        if remove_file(BASE_DIR / f, dry_run):
            removed += 1

    # 4. Remover diretórios SaaS
    print("\n--- Removendo Diretórios SaaS ---")
    for d in SAAS_DIRS:
        if remove_dir(BASE_DIR / d, dry_run):
            removed += 1

    # 5. Remover docs redundantes
    print("\n--- Removendo Documentação Redundante ---")
    for f in REDUNDANT_DOCS:
        if remove_file(BASE_DIR / f, dry_run):
            removed += 1

    # 6. Remover scripts redundantes
    print("\n--- Removendo Scripts Obsoletos ---")
    for f in REDUNDANT_SCRIPTS:
        if remove_file(BASE_DIR / f, dry_run):
            removed += 1

    # 7. Organizar testes restantes
    print("\n--- Organizando Testes ---")
    tests_dir = BASE_DIR / "tests"
    if not dry_run:
        tests_dir.mkdir(exist_ok=True)
    for f in TESTS_TO_ORGANIZE:
        src = BASE_DIR / f
        dst = tests_dir / f
        move_file(src, dst, dry_run)

    # Resumo
    print("\n" + "=" * 60)
    print(f"RESUMO: {removed} itens para {'remover' if dry_run else 'removidos'}")
    print("=" * 60)

    print("\n[+] O QUE SERA MANTIDO:")
    print("   - backend/crewai_service/ (analise IA)")
    print("   - supabase/schema.sql (imoveis + analises)")
    print("   - supabase/schema_leilao_v2.sql (schema completo)")
    print("   - workflows/ (automacao N8N)")
    print("   - docker-compose.yml (desenvolvimento)")
    print("   - README.md, START_HERE.md")
    print("   - tests/ (reorganizados)")

    if dry_run:
        print("\n>> Para executar: python scripts/cleanup_saas.py --execute")


def main():
    parser = argparse.ArgumentParser(description="Remove complexidade SaaS do projeto")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Simular")
    group.add_argument("--execute", action="store_true", help="Executar")
    parser.add_argument("--force", action="store_true", help="Pular confirmacao")

    args = parser.parse_args()
    run_cleanup(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
