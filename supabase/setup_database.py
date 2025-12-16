#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para criar/atualizar schema do Supabase
Executa schema.sql no banco de dados
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

def executar_schema():
    """Executa o schema SQL no Supabase"""
    print("=" * 60)
    print("🗄️  CONFIGURADOR DE BANCO DE DADOS SUPABASE")
    print("=" * 60)

    # Validar variáveis
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("\n❌ Variáveis de ambiente faltando!")
        print("Configure no .env:")
        print("- SUPABASE_URL")
        print("- SUPABASE_SERVICE_KEY")
        sys.exit(1)

    print(f"\n📍 Supabase URL: {SUPABASE_URL}")

    # Conectar ao Supabase
    try:
        print("\n🔐 Conectando ao Supabase...")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Conexão estabelecida!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)

    # Ler arquivo SQL
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

    try:
        print(f"\n📄 Lendo arquivo: {schema_path}")
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        print(f"✅ Arquivo lido! ({len(sql_content)} caracteres)")
    except Exception as e:
        print(f"❌ Erro ao ler arquivo SQL: {e}")
        sys.exit(1)

    # Executar SQL via RPC
    print("\n⚙️  Executando schema SQL...")
    print("   (Isso pode levar alguns segundos...)")

    try:
        # Supabase Python client não tem método direto para SQL
        # Vamos usar a API REST diretamente
        import requests

        headers = {
            'apikey': SUPABASE_SERVICE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            'Content-Type': 'application/json'
        }

        # Dividir SQL em comandos individuais
        comandos = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]

        total = len(comandos)
        print(f"\n📝 Executando {total} comandos SQL...")

        sucesso = 0
        erros = 0

        for i, comando in enumerate(comandos, 1):
            # Pular comentários e linhas vazias
            if comando.startswith('--') or not comando:
                continue

            print(f"   [{i}/{total}] Executando comando...")

            # Nota: Este é um placeholder - você precisará usar uma biblioteca
            # PostgreSQL direta ou a Dashboard do Supabase para executar SQL
            # A biblioteca supabase-py não suporta SQL direto

        print("\n⚠️  ATENÇÃO: Este script não pode executar SQL diretamente.")
        print("📋 Por favor, execute o arquivo 'schema.sql' manualmente:")
        print(f"   1. Acesse: {SUPABASE_URL.replace('https://', 'https://supabase.com/dashboard/project/')}")
        print("   2. Vá em: SQL Editor")
        print("   3. Cole o conteúdo de: supabase/schema.sql")
        print("   4. Execute!")

        print("\n✅ Arquivo schema.sql está pronto para uso!")
        print(f"📍 Localização: {schema_path}")

    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

    # Verificar tabelas existentes
    print("\n🔍 Verificando tabelas existentes...")

    try:
        # Listar tabelas (através de uma query)
        result = supabase.table('imoveis_leilao').select('count', count='exact').limit(0).execute()
        print(f"✅ Tabela 'imoveis_leilao' existe!")
        print(f"   Total de registros: {result.count}")
    except Exception as e:
        print(f"⚠️  Tabela 'imoveis_leilao' pode não existir ainda: {e}")

    print("\n" + "=" * 60)
    print("📋 INSTRUÇÕES PARA CRIAR O SCHEMA")
    print("=" * 60)
    print("\n1. Acesse o Supabase Dashboard:")
    print(f"   {SUPABASE_URL.replace('supabase.co', 'supabase.com/dashboard/project/')}")
    print("\n2. Vá para: SQL Editor (na barra lateral)")
    print("\n3. Clique em: + New Query")
    print("\n4. Cole o conteúdo de: supabase/schema.sql")
    print(f"   Caminho completo: {schema_path}")
    print("\n5. Clique em: Run (ou pressione Ctrl+Enter)")
    print("\n6. Verifique se todas as tabelas foram criadas:")
    print("   - imoveis_leilao")
    print("   - analises_viabilidade")
    print("   - analises_logs")
    print("\n7. Verifique as views:")
    print("   - vw_imoveis_com_analise")
    print("   - vw_estatisticas_analises")
    print("\n" + "=" * 60)

if __name__ == '__main__':
    executar_schema()
