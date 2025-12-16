# 🔐 FASE 1: Segurança Crítica - Guia de Implementação

**Duração**: 3 dias
**Prioridade**: 🔴 CRÍTICA
**Responsável**: DevOps + Security Engineer

---

## 📋 Checklist Geral

- [ ] Rotacionar todas as credenciais
- [ ] Configurar AWS Secrets Manager
- [ ] Implementar autenticação JWT
- [ ] Adicionar rate limiting
- [ ] Configurar HTTPS + SSL
- [ ] Atualizar CORS policy
- [ ] Adicionar security headers
- [ ] Testar end-to-end

---

## 🚨 DIA 1: Gestão de Secrets

### 1.1 Rotação de Credenciais (2 horas)

#### OpenAI API Key
```bash
# 1. Gerar nova chave no OpenAI Dashboard
https://platform.openai.com/api-keys

# 2. Criar nova key com nome identificável
Nome: "producao-imoveis-analise-2024"

# 3. Configurar rate limits
- TPM (Tokens Per Minute): 90,000
- RPM (Requests Per Minute): 3,500

# 4. REVOGAR chave antiga imediatamente
```

#### Supabase Keys
```bash
# 1. Acesso: https://supabase.com/dashboard/project/pxymmcmksyekkjptqblp

# 2. Settings → API → Reset Service Key
# ATENÇÃO: Isso invalida a chave antiga imediatamente

# 3. Também resetar Anon Key se foi exposta publicamente
```

#### N8N Password
```bash
# 1. Acesso: https://n8n.kleberodrigues.shop

# 2. Settings → Users → Change Password
# Novo password forte (mínimo 20 caracteres)

# 3. Exemplo de senha segura:
openssl rand -base64 32
```

### 1.2 AWS Secrets Manager Setup (3 horas)

#### Criar Secrets no AWS
```bash
# 1. Instalar AWS CLI
pip install awscli
aws configure

# 2. Criar secrets
aws secretsmanager create-secret \
  --name prod/imoveis-analise/openai-key \
  --secret-string "nova-openai-key-aqui" \
  --region us-east-1

aws secretsmanager create-secret \
  --name prod/imoveis-analise/supabase \
  --secret-string '{
    "url": "https://pxymmcmksyekkjptqblp.supabase.co",
    "service_key": "nova-service-key",
    "anon_key": "nova-anon-key"
  }' \
  --region us-east-1

aws secretsmanager create-secret \
  --name prod/imoveis-analise/n8n-credentials \
  --secret-string '{
    "url": "https://n8n.kleberodrigues.shop",
    "username": "admin",
    "password": "senha-forte-gerada"
  }' \
  --region us-east-1

# 3. Configurar rotation automática (30 dias)
aws secretsmanager rotate-secret \
  --secret-id prod/imoveis-analise/openai-key \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:ACCOUNT:function:rotate-secret \
  --rotation-rules AutomaticallyAfterDays=30
```

#### Atualizar Aplicação para Usar Secrets
```python
# backend/crewai_service/config.py
import boto3
import json
from botocore.exceptions import ClientError

def get_secret(secret_name: str, region: str = "us-east-1") -> dict:
    """Fetch secret from AWS Secrets Manager"""

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)

        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            # Binary secret (decode base64)
            import base64
            return json.loads(base64.b64decode(response['SecretBinary']))

    except ClientError as e:
        raise Exception(f"Erro ao buscar secret: {e}")

# Uso
openai_key = get_secret("prod/imoveis-analise/openai-key")["api_key"]
supabase_config = get_secret("prod/imoveis-analise/supabase")
```

#### Atualizar main.py
```python
# backend/crewai_service/main.py
from config import get_secret

# Substituir linhas 30-42
try:
    # Fetch secrets from AWS Secrets Manager
    supabase_config = get_secret("prod/imoveis-analise/supabase")
    SUPABASE_URL = supabase_config["url"]
    SUPABASE_KEY = supabase_config["service_key"]

    openai_config = get_secret("prod/imoveis-analise/openai-key")
    OPENAI_API_KEY = openai_config["api_key"]

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, api_key=OPENAI_API_KEY)

except Exception as e:
    logger.error(f"Erro ao configurar secrets: {e}")
    raise
```

### 1.3 Remover .env do Projeto (1 hora)

```bash
# 1. Backup do .env atual
cp .env .env.backup.local
# NUNCA commit este arquivo!

# 2. Deletar .env do projeto
rm .env

# 3. Atualizar .gitignore (já configurado)
# Confirmar que .env está no .gitignore

# 4. Remover histórico Git (se .env foi commitado antes)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# 5. Force push (CUIDADO - avise a equipe)
git push origin --force --all
```

### 1.4 Atualizar Docker Compose para Produção (1 hora)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  crewai:
    build: ./backend/crewai_service
    container_name: crewai-analise-imoveis
    ports:
      - "5000:5000"
    environment:
      # AWS Secrets Manager
      - AWS_REGION=us-east-1
      - AWS_SECRET_NAME=prod/imoveis-analise
      # App config
      - PORT=5000
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    restart: unless-stopped
    networks:
      - app-network
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  n8n:
    image: n8nio/n8n:latest
    container_name: n8n-workflows
    ports:
      - "5678:5678"
    environment:
      # AWS Secrets Manager
      - AWS_REGION=us-east-1
      - AWS_SECRET_NAME=prod/imoveis-analise/n8n-credentials
      # n8n config
      - N8N_PROTOCOL=https
      - N8N_HOST=n8n.kleberodrigues.shop
      - N8N_PORT=5678
      - WEBHOOK_URL=https://n8n.kleberodrigues.shop
      - CREWAI_API_URL=http://crewai:5000
    volumes:
      - n8n_data:/home/node/.n8n
    restart: unless-stopped
    depends_on:
      crewai:
        condition: service_healthy
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  n8n_data:
    driver: local
```

---

## 🔑 DIA 2: Autenticação & Rate Limiting

### 2.1 Implementar JWT Authentication (3 horas)

#### Instalar Dependências
```bash
# backend/crewai_service/requirements.txt
# Adicionar:
pyjwt==2.8.0
flask-jwt-extended==4.5.3
redis==5.0.0
flask-limiter==3.5.0
```

#### Criar Módulo de Autenticação
```python
# backend/crewai_service/auth.py
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from functools import wraps
from flask import request, jsonify
import redis

# Redis client para blacklist de tokens
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def init_jwt(app):
    """Initialize JWT Manager"""
    app.config['JWT_SECRET_KEY'] = get_secret("prod/imoveis-analise/jwt-secret")["key"]
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token_in_redis = redis_client.get(jti)
        return token_in_redis is not None

    return jwt

def generate_tokens(user_id: str, email: str) -> dict:
    """Generate access and refresh tokens"""
    access_token = create_access_token(
        identity=user_id,
        additional_claims={"email": email}
    )
    refresh_token = create_access_token(
        identity=user_id,
        additional_claims={"email": email},
        expires_delta=timedelta(days=30)
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer"
    }

def revoke_token(jti: str):
    """Add token to blacklist"""
    # Token expira em 24h
    redis_client.setex(jti, timedelta(hours=24), "true")

# API Key Authentication (para clientes externos)
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return jsonify({"erro": "API key required"}), 401

        # Validar API key no banco de dados
        # TODO: implementar validação real
        valid_keys = ["key_test_123"]  # Temporário

        if api_key not in valid_keys:
            return jsonify({"erro": "Invalid API key"}), 401

        return f(*args, **kwargs)

    return decorated_function
```

#### Atualizar main.py
```python
# backend/crewai_service/main.py
from auth import init_jwt, generate_tokens, require_api_key
from flask_jwt_extended import jwt_required, get_jwt_identity

# Inicializar JWT
init_jwt(app)

# Endpoint de login (integração com Supabase Auth)
@app.route('/auth/login', methods=['POST'])
def login():
    """Login endpoint - integra com Supabase Auth"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # TODO: Validar com Supabase Auth
    # Por enquanto, mock response

    user_id = "user_123"
    tokens = generate_tokens(user_id, email)

    return jsonify(tokens), 200

# Proteger endpoint /analisar
@app.route('/analisar', methods=['POST'])
@jwt_required()  # Requer JWT válido
def analisar_imovel():
    """Endpoint protegido por JWT"""
    current_user = get_jwt_identity()
    logger.info(f"Análise solicitada por usuário: {current_user}")

    # ... resto do código
```

### 2.2 Implementar Rate Limiting (2 horas)

```python
# backend/crewai_service/main.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configurar rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",
    default_limits=["200 per day", "50 per hour"]
)

# Rate limits específicos
@app.route('/analisar', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")  # FREE tier
def analisar_imovel():
    """10 análises/hora para usuários FREE"""
    pass

@app.route('/analisar/pro', methods=['POST'])
@jwt_required()
@limiter.limit("100 per hour")  # PRO tier
def analisar_imovel_pro():
    """100 análises/hora para usuários PRO"""
    pass

# Rate limit para API pública (mais restritivo)
@app.route('/health', methods=['GET'])
@limiter.limit("100 per minute")
def health_check():
    """Health check com rate limit"""
    pass
```

### 2.3 Integrar Supabase Auth (1 hora)

```python
# backend/crewai_service/auth.py
from supabase import create_client

def validate_supabase_token(token: str) -> dict:
    """Validate JWT token with Supabase"""
    try:
        supabase_config = get_secret("prod/imoveis-analise/supabase")
        supabase = create_client(supabase_config["url"], supabase_config["anon_key"])

        # Validar token
        user = supabase.auth.get_user(token)

        return {
            "valid": True,
            "user_id": user.id,
            "email": user.email
        }

    except Exception as e:
        logger.error(f"Erro ao validar token: {e}")
        return {"valid": False}
```

---

## 🔒 DIA 3: HTTPS & Network Security

### 3.1 Configurar NGINX Reverse Proxy (2 horas)

```nginx
# /etc/nginx/sites-available/imoveis-analise.conf

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=health_limit:10m rate=100r/s;

# Upstream backends
upstream crewai_backend {
    least_conn;  # Load balancing
    server 127.0.0.1:5000 max_fails=3 fail_timeout=30s;
    # Adicionar mais servers quando escalar
    # server 127.0.0.1:5001 max_fails=3 fail_timeout=30s;
}

upstream n8n_backend {
    server 127.0.0.1:5678;
}

# HTTPS Redirect
server {
    listen 80;
    server_name api.imoveis-analise.com.br;

    # Force HTTPS
    return 301 https://$server_name$request_uri;
}

# Main API Server
server {
    listen 443 ssl http2;
    server_name api.imoveis-analise.com.br;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.imoveis-analise.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.imoveis-analise.com.br/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;

    # Remove version info
    server_tokens off;

    # Proxy settings
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Timeouts
    proxy_connect_timeout 180s;
    proxy_send_timeout 180s;
    proxy_read_timeout 180s;

    # Health check (no rate limit interno)
    location /health {
        limit_req zone=health_limit burst=200 nodelay;
        proxy_pass http://crewai_backend;
    }

    # API endpoints (rate limited)
    location /analisar {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://crewai_backend;
    }

    # Catch-all
    location / {
        limit_req zone=api_limit burst=50 nodelay;
        proxy_pass http://crewai_backend;
    }
}

# n8n Server
server {
    listen 443 ssl http2;
    server_name n8n.kleberodrigues.shop;

    # SSL Configuration (same as above)
    ssl_certificate /etc/letsencrypt/live/n8n.kleberodrigues.shop/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/n8n.kleberodrigues.shop/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://n8n_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3.2 Obter Certificados SSL (Let's Encrypt) (1 hora)

```bash
# 1. Instalar Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 2. Obter certificados
sudo certbot --nginx -d api.imoveis-analise.com.br
sudo certbot --nginx -d n8n.kleberodrigues.shop

# 3. Testar renovação automática
sudo certbot renew --dry-run

# 4. Configurar cron job para renovação (certbot já faz isso automaticamente)
# Verificar: sudo systemctl status certbot.timer
```

### 3.3 Atualizar CORS Policy (30 min)

```python
# backend/crewai_service/main.py
from flask_cors import CORS

# CORS restritivo para produção
ALLOWED_ORIGINS = [
    "https://app.imoveis-analise.com.br",
    "https://www.imoveis-analise.com.br",
    "https://n8n.kleberodrigues.shop"
]

# Desenvolvimento local (remover em produção)
if os.getenv("ENVIRONMENT") == "development":
    ALLOWED_ORIGINS.extend([
        "http://localhost:3000",
        "http://localhost:5173"
    ])

CORS(app,
     resources={r"/*": {
         "origins": ALLOWED_ORIGINS,
         "methods": ["GET", "POST", "PUT", "DELETE"],
         "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
         "expose_headers": ["Content-Type", "X-Request-ID"],
         "supports_credentials": True,
         "max_age": 3600
     }})
```

### 3.4 Implementar Security Headers (30 min)

```python
# backend/crewai_service/middleware.py
from flask import make_response

def add_security_headers(response):
    """Add security headers to all responses"""

    # HSTS: Force HTTPS for 1 year
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'

    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # XSS Protection (legacy but still useful)
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' https://api.openai.com; "
        "frame-ancestors 'none';"
    )

    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions Policy (formerly Feature Policy)
    response.headers['Permissions-Policy'] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=()"
    )

    return response

# backend/crewai_service/main.py
from middleware import add_security_headers

@app.after_request
def after_request(response):
    return add_security_headers(response)
```

---

## ✅ Testes End-to-End

### Testar Autenticação
```bash
# 1. Obter token JWT
curl -X POST https://api.imoveis-analise.com.br/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Resposta esperada:
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "token_type": "Bearer"
# }

# 2. Usar token para análise
curl -X POST https://api.imoveis-analise.com.br/analisar \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{"imovel_id": "123"}'
```

### Testar Rate Limiting
```bash
# Enviar 11 requisições rapidamente (limite: 10/hora)
for i in {1..11}; do
  curl -X POST https://api.imoveis-analise.com.br/analisar \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"imovel_id": "test"}'
done

# 11ª requisição deve retornar 429 Too Many Requests
```

### Testar HTTPS
```bash
# 1. Verificar redirecionamento HTTP → HTTPS
curl -I http://api.imoveis-analise.com.br/health
# Deve retornar 301 Moved Permanently

# 2. Testar SSL
curl -I https://api.imoveis-analise.com.br/health
# Deve retornar 200 OK

# 3. Verificar certificado
openssl s_client -connect api.imoveis-analise.com.br:443 -servername api.imoveis-analise.com.br

# 4. Verificar score SSL Labs
https://www.ssllabs.com/ssltest/analyze.html?d=api.imoveis-analise.com.br
# Target: A+ rating
```

### Testar Security Headers
```bash
curl -I https://api.imoveis-analise.com.br/health

# Verificar headers presentes:
# ✅ Strict-Transport-Security
# ✅ X-Frame-Options
# ✅ X-Content-Type-Options
# ✅ Content-Security-Policy
# ✅ Referrer-Policy
```

---

## 📊 Métricas de Sucesso

### Checklist Final
- [ ] ✅ Nenhum secret em código/repositório
- [ ] ✅ AWS Secrets Manager configurado
- [ ] ✅ Rotation automática ativada
- [ ] ✅ JWT authentication funcionando
- [ ] ✅ Rate limiting ativo (10 req/min FREE, 100 req/min PRO)
- [ ] ✅ HTTPS 100% (SSL Labs A+)
- [ ] ✅ CORS restritivo (apenas origens permitidas)
- [ ] ✅ Security headers implementados
- [ ] ✅ Testes end-to-end passando

### Validação
```bash
# Executar suite de testes
pytest tests/security/ -v

# Scan de vulnerabilidades
safety check
bandit -r backend/crewai_service/

# Audit de dependências
pip-audit
```

---

## 🚨 Rollback Plan

Se algo der errado:

1. **Secrets inválidos**
   ```bash
   # Rollback para secrets antigos temporariamente
   aws secretsmanager put-secret-value \
     --secret-id prod/imoveis-analise/openai-key \
     --secret-string "old-key-backup"
   ```

2. **HTTPS breaking**
   ```bash
   # Desabilitar HTTPS temporariamente
   sudo systemctl stop nginx
   # Reverter para HTTP no docker-compose
   ```

3. **Rate limiting muito restritivo**
   ```python
   # Aumentar limites temporariamente
   @limiter.limit("100 per hour")  # Era 10
   ```

---

**🎯 Próximo: FASE 2 - Arquitetura Escalável**
