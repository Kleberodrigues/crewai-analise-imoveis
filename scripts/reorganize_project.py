#!/usr/bin/env python3
"""
Script de Reorganização do Projeto - Análise Imóveis Leilão
============================================================
Este script reorganiza a estrutura do projeto, movendo arquivos
obsoletos, consolidando documentação e limpando a raiz.

USO:
    python scripts/reorganize_project.py --dry-run    # Simular (recomendado primeiro)
    python scripts/reorganize_project.py --execute    # Executar de fato
    python scripts/reorganize_project.py --rollback   # Desfazer (se backup existir)

IMPORTANTE: Execute --dry-run primeiro para revisar as mudanças!
"""

import os
import shutil
import argparse
import json
from datetime import datetime
from pathlib import Path

# Diretório base do projeto
BASE_DIR = Path(__file__).parent.parent.absolute()

# Arquivo de backup para rollback
BACKUP_FILE = BASE_DIR / "scripts" / ".reorganize_backup.json"

# ============================================
# CONFIGURAÇÃO DE MOVIMENTAÇÃO DE ARQUIVOS
# ============================================

# Arquivos para MOVER para docs/archive/ (documentação obsoleta)
DOCS_TO_ARCHIVE = [
    "README_FINAL.md",
    "CONFIGURAR_N8N.md",
    "CONFIGURAR_SUPABASE_N8N.md",
    "CORRECOES_CRITICAS_N8N.md",
    "CORRIGIR_TRIGGER_SUPABASE.md",
    "CORRIGIR_WORKFLOW_N8N.md",
    "DIAGNOSTICO_WORKFLOW_N8N.md",
    "GUIA_CRIACAO_WORKFLOWS_N8N.md",
    "RESUMO_IMPLEMENTACAO_N8N.md",
    "N8N_ARQUITETURA_COMPLETA.md",
    "INTEGRACAO_FRONTEND_N8N.md",
    "APLICAR_SCHEMA_SUPABASE.md",
    "ENVIAR_PARA_LOVABLE.md",
    "PROMPT_LOVABLE_FRONTEND.md",
    "PROMPT_LOVABLE_PREMIUM.md",
    "INTEGRAR_LOVABLE_BACKEND.md",
    "INTEGRACOES_COMPLETAS.md",
    "PLANO_AGENTES_LEILAO_V2.md",
    "ESTRUTURA_OUTPUT_ANALISE.md",
    "EXECUTAR_AGORA.md",
    "DEPLOY_COMPLETO.md",
    "DEPLOY_VPS.md",
    "SOLUCAO_CORS_NGROK.md",
    "CONFIGURAR_CLAUDE_PROMPTS_MCP.md",
]

# Arquivos para MOVER para docs/guides/
DOCS_TO_GUIDES = [
    "LOVABLE_PROMPT.md",
    "RAILWAY_DEPLOY_GUIDE.md",
    "IMPLEMENTACAO_COMPLETA.md",
    "NEXT_STEPS.md",
]

# Arquivos para MOVER para tests/ (scripts de teste na raiz)
TESTS_TO_MOVE = [
    "test_abacatepay.py",
    "test_abacatepay_simple.py",
    "test_backend_api.py",
    "test_backend_completo.py",
    "test_backend_startup.py",
    "test_billing_only.py",
    "test_crewai_direto.py",
    "test_integracao.py",
    "test_integration_complete.py",
    "test_integration_frontend.py",
    "test_n8n_env.py",
    "test_n8n_workflow.py",
    "test_supabase_direct.py",
]

# Arquivos para MOVER para scripts/setup/
SCRIPTS_TO_SETUP = [
    "setup_n8n.py",
    "setup_completo_n8n.py",
    "create_n8n_workflows.py",
    "create_workflow_corrected.py",
    "create_complete_workflow.py",
    "import_workflow_n8n.py",
]

# Arquivos para MOVER para scripts/admin/
SCRIPTS_TO_ADMIN = [
    "confirmar_email.py",
    "confirmar_usuario_sql.py",
    "check_analise.py",
    "atualizar_n8n_url.py",
]

# Arquivos JSON para MOVER para workflows/
JSON_TO_WORKFLOWS = [
    "workflow_analyze_property.json",
    "n8n-workflow-agendamento-leilao.json",
]

# Arquivos para REMOVER (dados de teste, obsoletos)
FILES_TO_DELETE = [
    "billing_success.json",
    "test_billing_info.json",
    "LOVABLE_api_ts_CORRETO.txt",
]

# Arquivos SQL para MOVER para supabase/migrations/
SQL_TO_MIGRATIONS = [
    "supabase_schema_n8n.sql",
    "supabase_migration_pipeline_execucoes.sql",
]

# Arquivos SQL dentro de supabase/ para MOVER para supabase/patches/
SQL_PATCHES = [
    "supabase/ADD_ABACATEPAY_COLUMN.sql",
    "supabase/ADD_ABACATEPAY_COLUMNS_SUBSCRIPTIONS.sql",
    "supabase/ADD_BILLING_ID_COLUMN.sql",
    "supabase/ADD_PENDING_STATUS.sql",
    "supabase/DESABILITAR_TRIGGER.sql",
    "supabase/FIX_RLS_SUBSCRIPTIONS.sql",
    "supabase/FIX_TRIGGER.sql",
    "supabase/REMOVE_STRIPE_NOT_NULL.sql",
    "supabase/verificar_tabela.sql",
]

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def log(message: str, level: str = "INFO"):
    """Log com timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {
        "INFO": "ℹ️",
        "MOVE": "📦",
        "CREATE": "📁",
        "DELETE": "🗑️",
        "SKIP": "⏭️",
        "ERROR": "❌",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
    }
    icon = icons.get(level, "•")
    print(f"[{timestamp}] {icon} {message}")


def create_directory(path: Path, dry_run: bool = True) -> bool:
    """Criar diretório se não existir"""
    if path.exists():
        return True

    if dry_run:
        log(f"CRIAR diretório: {path.relative_to(BASE_DIR)}", "CREATE")
        return True

    try:
        path.mkdir(parents=True, exist_ok=True)
        log(f"Criado: {path.relative_to(BASE_DIR)}", "CREATE")
        return True
    except Exception as e:
        log(f"Erro ao criar {path}: {e}", "ERROR")
        return False


def move_file(src: Path, dst: Path, dry_run: bool = True, backup: dict = None) -> bool:
    """Mover arquivo de src para dst"""
    if not src.exists():
        log(f"Arquivo não encontrado: {src.name}", "SKIP")
        return False

    if dst.exists():
        log(f"Destino já existe: {dst.relative_to(BASE_DIR)}", "SKIP")
        return False

    if dry_run:
        log(f"MOVER: {src.name} → {dst.relative_to(BASE_DIR)}", "MOVE")
        return True

    try:
        # Garantir que o diretório destino existe
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Mover arquivo
        shutil.move(str(src), str(dst))
        log(f"Movido: {src.name} → {dst.relative_to(BASE_DIR)}", "MOVE")

        # Registrar no backup para rollback
        if backup is not None:
            backup["moves"].append({
                "from": str(dst),  # Invertido para rollback
                "to": str(src)
            })

        return True
    except Exception as e:
        log(f"Erro ao mover {src.name}: {e}", "ERROR")
        return False


def delete_file(path: Path, dry_run: bool = True, backup: dict = None) -> bool:
    """Deletar arquivo"""
    if not path.exists():
        log(f"Arquivo não encontrado: {path.name}", "SKIP")
        return False

    if dry_run:
        log(f"DELETAR: {path.name}", "DELETE")
        return True

    try:
        # Backup do conteúdo antes de deletar
        if backup is not None:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            backup["deleted"].append({
                "path": str(path),
                "content": content
            })

        path.unlink()
        log(f"Deletado: {path.name}", "DELETE")
        return True
    except Exception as e:
        log(f"Erro ao deletar {path.name}: {e}", "ERROR")
        return False


def save_backup(backup: dict):
    """Salvar backup para rollback"""
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)
    log(f"Backup salvo em: {BACKUP_FILE.name}", "SUCCESS")


def load_backup() -> dict:
    """Carregar backup para rollback"""
    if not BACKUP_FILE.exists():
        return None
    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================
# FUNÇÕES PRINCIPAIS
# ============================================

def create_new_structure(dry_run: bool = True):
    """Criar nova estrutura de diretórios"""
    log("=" * 50, "INFO")
    log("FASE 1: Criando estrutura de diretórios", "INFO")
    log("=" * 50, "INFO")

    directories = [
        BASE_DIR / "docs" / "archive",
        BASE_DIR / "docs" / "guides",
        BASE_DIR / "docs" / "architecture",
        BASE_DIR / "scripts" / "setup",
        BASE_DIR / "scripts" / "admin",
        BASE_DIR / "supabase" / "migrations",
        BASE_DIR / "supabase" / "patches",
        BASE_DIR / "tests" / "integration",
        BASE_DIR / "tests" / "unit",
    ]

    for dir_path in directories:
        create_directory(dir_path, dry_run)


def move_documentation(dry_run: bool = True, backup: dict = None):
    """Mover documentação para locais apropriados"""
    log("=" * 50, "INFO")
    log("FASE 2: Movendo documentação", "INFO")
    log("=" * 50, "INFO")

    # Mover para archive
    log("--- Arquivando documentação obsoleta ---", "INFO")
    for filename in DOCS_TO_ARCHIVE:
        src = BASE_DIR / filename
        dst = BASE_DIR / "docs" / "archive" / filename
        move_file(src, dst, dry_run, backup)

    # Mover para guides
    log("--- Movendo guias ativos ---", "INFO")
    for filename in DOCS_TO_GUIDES:
        src = BASE_DIR / filename
        dst = BASE_DIR / "docs" / "guides" / filename
        move_file(src, dst, dry_run, backup)


def move_tests(dry_run: bool = True, backup: dict = None):
    """Mover testes para pasta tests/"""
    log("=" * 50, "INFO")
    log("FASE 3: Organizando testes", "INFO")
    log("=" * 50, "INFO")

    for filename in TESTS_TO_MOVE:
        src = BASE_DIR / filename
        dst = BASE_DIR / "tests" / "integration" / filename
        move_file(src, dst, dry_run, backup)


def move_scripts(dry_run: bool = True, backup: dict = None):
    """Mover scripts para pastas apropriadas"""
    log("=" * 50, "INFO")
    log("FASE 4: Organizando scripts", "INFO")
    log("=" * 50, "INFO")

    # Scripts de setup
    log("--- Scripts de setup ---", "INFO")
    for filename in SCRIPTS_TO_SETUP:
        src = BASE_DIR / filename
        dst = BASE_DIR / "scripts" / "setup" / filename
        move_file(src, dst, dry_run, backup)

    # Scripts admin
    log("--- Scripts administrativos ---", "INFO")
    for filename in SCRIPTS_TO_ADMIN:
        src = BASE_DIR / filename
        dst = BASE_DIR / "scripts" / "admin" / filename
        move_file(src, dst, dry_run, backup)


def move_workflows(dry_run: bool = True, backup: dict = None):
    """Mover JSONs de workflow"""
    log("=" * 50, "INFO")
    log("FASE 5: Organizando workflows", "INFO")
    log("=" * 50, "INFO")

    for filename in JSON_TO_WORKFLOWS:
        src = BASE_DIR / filename
        dst = BASE_DIR / "workflows" / filename
        move_file(src, dst, dry_run, backup)


def move_sql_files(dry_run: bool = True, backup: dict = None):
    """Mover arquivos SQL"""
    log("=" * 50, "INFO")
    log("FASE 6: Organizando SQL", "INFO")
    log("=" * 50, "INFO")

    # SQLs da raiz para migrations
    log("--- SQLs da raiz ---", "INFO")
    for filename in SQL_TO_MIGRATIONS:
        src = BASE_DIR / filename
        dst = BASE_DIR / "supabase" / "migrations" / Path(filename).name
        move_file(src, dst, dry_run, backup)

    # Patches dentro de supabase
    log("--- Patches SQL ---", "INFO")
    for filepath in SQL_PATCHES:
        src = BASE_DIR / filepath
        dst = BASE_DIR / "supabase" / "patches" / Path(filepath).name
        move_file(src, dst, dry_run, backup)


def delete_obsolete_files(dry_run: bool = True, backup: dict = None):
    """Deletar arquivos obsoletos"""
    log("=" * 50, "INFO")
    log("FASE 7: Removendo arquivos obsoletos", "INFO")
    log("=" * 50, "INFO")

    for filename in FILES_TO_DELETE:
        path = BASE_DIR / filename
        delete_file(path, dry_run, backup)


def create_index_file(dry_run: bool = True):
    """Criar arquivo de índice na pasta docs/archive"""
    log("=" * 50, "INFO")
    log("FASE 8: Criando índice de arquivos arquivados", "INFO")
    log("=" * 50, "INFO")

    index_path = BASE_DIR / "docs" / "archive" / "INDEX.md"

    if dry_run:
        log(f"CRIAR: {index_path.relative_to(BASE_DIR)}", "CREATE")
        return

    content = f"""# 📦 Documentação Arquivada

**Data de arquivamento**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

Esta pasta contém documentação que foi considerada obsoleta ou redundante
durante a reorganização do projeto.

## Arquivos Arquivados

### Documentação N8N (Consolidada)
- CONFIGURAR_N8N.md
- GUIA_CRIACAO_WORKFLOWS_N8N.md
- N8N_ARQUITETURA_COMPLETA.md
- RESUMO_IMPLEMENTACAO_N8N.md
- CORRIGIR_WORKFLOW_N8N.md
- DIAGNOSTICO_WORKFLOW_N8N.md
- CORRECOES_CRITICAS_N8N.md
- INTEGRACAO_FRONTEND_N8N.md
- CONFIGURAR_SUPABASE_N8N.md

### Documentação Supabase (Consolidada)
- APLICAR_SCHEMA_SUPABASE.md
- CORRIGIR_TRIGGER_SUPABASE.md

### Documentação Lovable (Consolidada)
- ENVIAR_PARA_LOVABLE.md
- PROMPT_LOVABLE_FRONTEND.md
- PROMPT_LOVABLE_PREMIUM.md
- INTEGRAR_LOVABLE_BACKEND.md
- INTEGRACOES_COMPLETAS.md

### Outros
- README_FINAL.md (duplicado do README.md)
- PLANO_AGENTES_LEILAO_V2.md (plano histórico)
- ESTRUTURA_OUTPUT_ANALISE.md
- EXECUTAR_AGORA.md
- DEPLOY_COMPLETO.md (redundante)
- DEPLOY_VPS.md
- SOLUCAO_CORS_NGROK.md
- CONFIGURAR_CLAUDE_PROMPTS_MCP.md

## Nota

Estes arquivos foram movidos, não deletados. Se precisar de alguma
informação contida neles, eles estão disponíveis aqui.

A documentação ativa está em:
- `/docs/guides/` - Guias ativos
- `/README.md` - Documentação principal
- `/START_HERE.md` - Ponto de entrada
"""

    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log(f"Criado: {index_path.relative_to(BASE_DIR)}", "CREATE")
    except Exception as e:
        log(f"Erro ao criar índice: {e}", "ERROR")


def run_reorganization(dry_run: bool = True):
    """Executar reorganização completa"""
    print("\n" + "=" * 60)
    print("🔧 REORGANIZAÇÃO DO PROJETO - ANÁLISE IMÓVEIS LEILÃO")
    print("=" * 60)

    if dry_run:
        print("\n⚠️  MODO DRY-RUN: Nenhuma alteração será feita!")
        print("    Execute com --execute para aplicar as mudanças.\n")
    else:
        print("\n🚨 MODO EXECUÇÃO: As alterações serão aplicadas!")
        confirm = input("    Digite 'CONFIRMAR' para continuar: ")
        if confirm != "CONFIRMAR":
            print("    Operação cancelada.")
            return
        print()

    # Inicializar backup
    backup = {
        "timestamp": datetime.now().isoformat(),
        "moves": [],
        "deleted": [],
    }

    # Executar fases
    create_new_structure(dry_run)
    move_documentation(dry_run, backup if not dry_run else None)
    move_tests(dry_run, backup if not dry_run else None)
    move_scripts(dry_run, backup if not dry_run else None)
    move_workflows(dry_run, backup if not dry_run else None)
    move_sql_files(dry_run, backup if not dry_run else None)
    delete_obsolete_files(dry_run, backup if not dry_run else None)
    create_index_file(dry_run)

    # Salvar backup se executou de verdade
    if not dry_run:
        save_backup(backup)

    # Resumo
    print("\n" + "=" * 60)
    if dry_run:
        print("✅ DRY-RUN CONCLUÍDO")
        print("\nPara aplicar as mudanças, execute:")
        print("    python scripts/reorganize_project.py --execute")
    else:
        print("✅ REORGANIZAÇÃO CONCLUÍDA")
        print(f"\nBackup salvo em: {BACKUP_FILE}")
        print("Para desfazer, execute:")
        print("    python scripts/reorganize_project.py --rollback")
    print("=" * 60 + "\n")


def run_rollback():
    """Desfazer reorganização usando backup"""
    print("\n" + "=" * 60)
    print("🔄 ROLLBACK - DESFAZENDO REORGANIZAÇÃO")
    print("=" * 60 + "\n")

    backup = load_backup()
    if not backup:
        log("Nenhum backup encontrado para rollback", "ERROR")
        return

    log(f"Backup encontrado de: {backup['timestamp']}", "INFO")

    # Restaurar arquivos movidos
    for move in backup["moves"]:
        src = Path(move["from"])
        dst = Path(move["to"])
        if src.exists():
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                log(f"Restaurado: {dst.name}", "MOVE")
            except Exception as e:
                log(f"Erro ao restaurar {dst.name}: {e}", "ERROR")

    # Restaurar arquivos deletados
    for deleted in backup["deleted"]:
        path = Path(deleted["path"])
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(deleted["content"])
            log(f"Restaurado: {path.name}", "CREATE")
        except Exception as e:
            log(f"Erro ao restaurar {path.name}: {e}", "ERROR")

    # Remover backup após rollback
    BACKUP_FILE.unlink()
    log("Backup removido após rollback", "SUCCESS")

    print("\n" + "=" * 60)
    print("✅ ROLLBACK CONCLUÍDO")
    print("=" * 60 + "\n")


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Reorganiza a estrutura do projeto",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/reorganize_project.py --dry-run    # Simular (recomendado)
  python scripts/reorganize_project.py --execute    # Executar
  python scripts/reorganize_project.py --rollback   # Desfazer
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="Simular mudanças sem executar")
    group.add_argument("--execute", action="store_true",
                       help="Executar reorganização")
    group.add_argument("--rollback", action="store_true",
                       help="Desfazer reorganização")

    args = parser.parse_args()

    if args.rollback:
        run_rollback()
    else:
        run_reorganization(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
