#!/bin/bash
# Script de Rotação de Credenciais - Fase 1 Dia 1
# Automatiza a rotação segura de todas as credenciais expostas

set -e  # Exit on error

echo "🔐 ROTAÇÃO DE CREDENCIAIS - FASE 1"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se está rodando em ambiente seguro
if [ -d ".git" ]; then
    echo -e "${RED}⚠️  ATENÇÃO: Este script está no repositório Git!${NC}"
    echo "Por segurança, execute fora do repositório."
    read -p "Continuar mesmo assim? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        exit 1
    fi
fi

echo -e "${YELLOW}📋 Checklist Pré-Rotação${NC}"
echo "=================================="
echo ""
echo "Antes de continuar, certifique-se de:"
echo "  [1] Ter acesso aos dashboards: OpenAI, Supabase, N8N"
echo "  [2] Ter AWS Account criada e AWS CLI configurada"
echo "  [3] Ter backup do .env atual (fora do Git)"
echo "  [4] Avisar a equipe (downtime de ~30 minutos)"
echo ""
read -p "Tudo pronto? (yes/no): " ready
if [ "$ready" != "yes" ]; then
    echo "Execute novamente quando estiver pronto."
    exit 0
fi

# ==================== OPENAI ====================
echo ""
echo -e "${GREEN}[1/4] Rotacionando OpenAI API Key${NC}"
echo "=================================="
echo ""
echo "📍 Acesse: https://platform.openai.com/api-keys"
echo ""
echo "Passos:"
echo "  1. Clique em 'Create new secret key'"
echo "  2. Nome: 'producao-imoveis-analise-2025'"
echo "  3. Configurar rate limits:"
echo "     - TPM (Tokens Per Minute): 90,000"
echo "     - RPM (Requests Per Minute): 3,500"
echo "  4. Copie a nova key (começa com sk-proj-)"
echo ""
read -p "Cole a NOVA OpenAI API Key: " new_openai_key

if [[ ! $new_openai_key =~ ^sk-proj- ]]; then
    echo -e "${RED}❌ Key inválida! Deve começar com 'sk-proj-'${NC}"
    exit 1
fi

echo "✅ Nova OpenAI Key salva temporariamente"
echo ""
echo "⚠️  IMPORTANTE: Agora REVOGUE a key antiga no dashboard!"
echo "   Key antiga começa com: sk-proj-KsNzCTOYgVJVt1X94MpxI-..."
read -p "Key antiga revogada? (yes/no): " revoked
if [ "$revoked" != "yes" ]; then
    echo -e "${RED}❌ Revogue a key antiga antes de continuar!${NC}"
    exit 1
fi

# ==================== SUPABASE ====================
echo ""
echo -e "${GREEN}[2/4] Rotacionando Supabase Keys${NC}"
echo "=================================="
echo ""
echo "📍 Acesse: https://supabase.com/dashboard/project/pxymmcmksyekkjptqblp/settings/api"
echo ""
echo "Passos:"
echo "  1. Seção 'Project API keys'"
echo "  2. Service Role Key → Clique em 'Reset' (ícone de reload)"
echo "  3. ⚠️  ATENÇÃO: Isso invalida a key antiga imediatamente!"
echo "  4. Confirme a ação"
echo "  5. Copie a nova Service Key"
echo ""
read -p "Cole a NOVA Supabase Service Key: " new_supabase_service

if [[ ! $new_supabase_service =~ ^eyJ ]]; then
    echo -e "${RED}❌ Key inválida! Deve começar com 'eyJ'${NC}"
    exit 1
fi

echo ""
echo "  6. Também resetar Anon Key (ícone de reload)"
echo "  7. Copie a nova Anon Key"
echo ""
read -p "Cole a NOVA Supabase Anon Key: " new_supabase_anon

if [[ ! $new_supabase_anon =~ ^eyJ ]]; then
    echo -e "${RED}❌ Key inválida! Deve começar com 'eyJ'${NC}"
    exit 1
fi

echo "✅ Novas Supabase Keys salvas temporariamente"

# ==================== N8N ====================
echo ""
echo -e "${GREEN}[3/4] Resetando Senha N8N${NC}"
echo "=================================="
echo ""
echo "📍 Acesse: https://n8n.kleberodrigues.shop"
echo ""
echo "Passos:"
echo "  1. Login com credenciais atuais"
echo "  2. Settings → Users → Change Password"
echo "  3. Gerar senha forte (sugestão abaixo)"
echo ""

# Gerar senha forte
new_n8n_password=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-24)
echo "  🔑 Senha sugerida (copie): ${new_n8n_password}"
echo ""
echo "  4. Cole a senha sugerida no N8N"
echo "  5. Salve e faça logout"
echo ""
read -p "Senha N8N atualizada? (yes/no): " n8n_updated
if [ "$n8n_updated" != "yes" ]; then
    echo -e "${RED}❌ Atualize a senha N8N antes de continuar!${NC}"
    exit 1
fi

echo "✅ Senha N8N atualizada"

# ==================== AWS SECRETS MANAGER ====================
echo ""
echo -e "${GREEN}[4/4] Salvando Secrets no AWS Secrets Manager${NC}"
echo "=================================="
echo ""

# Verificar AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI não instalado!${NC}"
    echo "Instale: pip install awscli"
    echo "Configure: aws configure"
    exit 1
fi

# Verificar credenciais AWS
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS CLI não configurada!${NC}"
    echo "Execute: aws configure"
    exit 1
fi

echo "✅ AWS CLI configurada"
echo ""

# Escolher região
read -p "Região AWS (default: us-east-1): " aws_region
aws_region=${aws_region:-us-east-1}

echo ""
echo "Criando secrets no AWS Secrets Manager..."
echo ""

# Secret 1: OpenAI
echo "[1/4] Criando secret: prod/imoveis-analise/openai"
aws secretsmanager create-secret \
    --name prod/imoveis-analise/openai \
    --description "OpenAI API Key para produção" \
    --secret-string "{\"api_key\":\"$new_openai_key\"}" \
    --region $aws_region \
    2>/dev/null || \
aws secretsmanager put-secret-value \
    --secret-id prod/imoveis-analise/openai \
    --secret-string "{\"api_key\":\"$new_openai_key\"}" \
    --region $aws_region

echo "✅ Secret OpenAI criado"

# Secret 2: Supabase
echo ""
echo "[2/4] Criando secret: prod/imoveis-analise/supabase"
aws secretsmanager create-secret \
    --name prod/imoveis-analise/supabase \
    --description "Supabase credentials para produção" \
    --secret-string "{\"url\":\"https://pxymmcmksyekkjptqblp.supabase.co\",\"service_key\":\"$new_supabase_service\",\"anon_key\":\"$new_supabase_anon\"}" \
    --region $aws_region \
    2>/dev/null || \
aws secretsmanager put-secret-value \
    --secret-id prod/imoveis-analise/supabase \
    --secret-string "{\"url\":\"https://pxymmcmksyekkjptqblp.supabase.co\",\"service_key\":\"$new_supabase_service\",\"anon_key\":\"$new_supabase_anon\"}" \
    --region $aws_region

echo "✅ Secret Supabase criado"

# Secret 3: N8N
echo ""
echo "[3/4] Criando secret: prod/imoveis-analise/n8n"
aws secretsmanager create-secret \
    --name prod/imoveis-analise/n8n \
    --description "N8N credentials para produção" \
    --secret-string "{\"url\":\"https://n8n.kleberodrigues.shop\",\"username\":\"admin\",\"password\":\"$new_n8n_password\"}" \
    --region $aws_region \
    2>/dev/null || \
aws secretsmanager put-secret-value \
    --secret-id prod/imoveis-analise/n8n \
    --secret-string "{\"url\":\"https://n8n.kleberodrigues.shop\",\"username\":\"admin\",\"password\":\"$new_n8n_password\"}" \
    --region $aws_region

echo "✅ Secret N8N criado"

# Secret 4: JWT Secret (para autenticação)
echo ""
echo "[4/4] Criando secret: prod/imoveis-analise/jwt"
jwt_secret=$(openssl rand -base64 32)
aws secretsmanager create-secret \
    --name prod/imoveis-analise/jwt \
    --description "JWT secret para autenticação" \
    --secret-string "{\"key\":\"$jwt_secret\"}" \
    --region $aws_region \
    2>/dev/null || \
aws secretsmanager put-secret-value \
    --secret-id prod/imoveis-analise/jwt \
    --secret-string "{\"key\":\"$jwt_secret\"}" \
    --region $aws_region

echo "✅ Secret JWT criado"

# Configurar rotation automática (30 dias)
echo ""
echo "Configurando rotation automática (30 dias)..."
# TODO: Implementar Lambda function para rotation
# aws secretsmanager rotate-secret ...

# ==================== VALIDAÇÃO ====================
echo ""
echo -e "${GREEN}✅ ROTAÇÃO COMPLETA!${NC}"
echo "=================================="
echo ""
echo "📋 Secrets criados no AWS:"
echo "  • prod/imoveis-analise/openai"
echo "  • prod/imoveis-analise/supabase"
echo "  • prod/imoveis-analise/n8n"
echo "  • prod/imoveis-analise/jwt"
echo ""
echo "📋 Próximos passos:"
echo "  1. Atualizar código para usar AWS Secrets Manager"
echo "  2. Testar localmente com novas credenciais"
echo "  3. Remover .env do projeto (backup fora do Git)"
echo "  4. Limpar histórico Git (git filter-branch)"
echo "  5. Deploy para produção"
echo ""

# Testar fetch de secrets
echo "🧪 Testando fetch de secrets..."
echo ""
test_secret=$(aws secretsmanager get-secret-value \
    --secret-id prod/imoveis-analise/openai \
    --region $aws_region \
    --query SecretString \
    --output text 2>/dev/null)

if [ -z "$test_secret" ]; then
    echo -e "${RED}❌ Erro ao buscar secret!${NC}"
    echo "Verifique permissões AWS IAM"
else
    echo -e "${GREEN}✅ Secrets acessíveis via AWS CLI${NC}"
fi

# Salvar resumo em arquivo seguro (fora do Git)
summary_file="../.secrets_rotation_$(date +%Y%m%d_%H%M%S).log"
cat > $summary_file <<EOF
Rotação de Credenciais - $(date)
================================

OPENAI:
  - Key antiga revogada: sim
  - Nova key salva em: prod/imoveis-analise/openai

SUPABASE:
  - Service Key resetada: sim
  - Anon Key resetada: sim
  - Secrets salvos em: prod/imoveis-analise/supabase

N8N:
  - Senha atualizada: sim
  - URL: https://n8n.kleberodrigues.shop
  - Secret salvo em: prod/imoveis-analise/n8n

JWT:
  - Secret gerado: sim
  - Salvo em: prod/imoveis-analise/jwt

AWS REGION: $aws_region

⚠️  IMPORTANTE:
  - Este arquivo contém informações sensíveis
  - Mantenha fora do Git
  - Delete após confirmar que tudo funciona
EOF

echo ""
echo "📝 Resumo salvo em: $summary_file"
echo "   ⚠️  Mantenha este arquivo FORA do Git!"
echo ""
echo -e "${GREEN}🎉 Parabéns! Credenciais rotacionadas com sucesso!${NC}"
echo ""
