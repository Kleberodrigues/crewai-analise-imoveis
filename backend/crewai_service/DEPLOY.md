# Deploy do Pipeline de Analise de Leiloes

## Pre-Requisitos na VPS

- Docker e Docker Compose instalados
- Git instalado
- Acesso SSH a VPS
- Portas 5000 (API) e 6379 (Redis) liberadas

## Passos de Deploy

### 1. Conectar na VPS

```bash
ssh usuario@seu-servidor.com
```

### 2. Clonar ou Copiar o Projeto

```bash
# Opcao A: Clonar do repositorio
git clone https://github.com/seu-usuario/projeto-analise-imoveis-leilao.git
cd projeto-analise-imoveis-leilao/backend/crewai_service

# Opcao B: Copiar via SCP (do seu PC)
scp -r backend/crewai_service usuario@servidor:/home/usuario/leilao-pipeline
```

### 3. Configurar Variaveis de Ambiente

```bash
# Criar arquivo .env
nano .env
```

Conteudo do .env:
```env
# OpenAI API (OBRIGATORIO)
OPENAI_API_KEY=sk-proj-sua-chave-aqui
LLM_MODEL=gpt-4o

# Supabase (OPCIONAL - funciona sem)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_KEY=eyJ...sua-chave

# Apify (OPCIONAL - para scraping do Portal Zuk)
APIFY_TOKEN=
APIFY_ACTOR_ID=apify/web-scraper

# Diretorios (mantenha assim para Docker)
DATA_DIR=/app/data
OUTPUT_DIR=/app/output

# API
PORT=5000
DEBUG=false

# Timezone
TZ=America/Sao_Paulo
```

### 4. Build e Iniciar com Docker

```bash
# Build da imagem
docker compose build

# Iniciar em background
docker compose up -d

# Verificar se esta rodando
docker compose ps

# Ver logs
docker compose logs -f leilao-pipeline
```

### 5. Testar a API

```bash
# Health check
curl http://localhost:5000/health

# Deve retornar:
# {"status": "ok", "service": "crewai-analise-imoveis", "version": "1.0.0"}
```

## Comandos Uteis

```bash
# Parar servicos
docker compose down

# Reiniciar
docker compose restart

# Ver logs em tempo real
docker compose logs -f

# Acessar container
docker exec -it leilao-pipeline bash

# Verificar espaco em disco
docker system df

# Limpar recursos nao usados
docker system prune -a
```

## Expor para Internet (Opcional)

### Com Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name leilao-api.seudominio.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Com Cloudflare Tunnel (Recomendado)

```bash
cloudflared tunnel create leilao-pipeline
cloudflared tunnel route dns leilao-pipeline leilao-api.seudominio.com
cloudflared tunnel run leilao-pipeline
```

## Agendar Execucao Automatica

O pipeline pode ser executado automaticamente 2x por semana via cron:

```bash
# Editar crontab
crontab -e

# Adicionar (Segunda e Quinta as 8h)
0 8 * * 1,4 curl -X POST http://localhost:5000/run
```

## Endpoints da API

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/health` | GET | Health check |
| `/status` | GET | Status do pipeline |
| `/run` | POST | Executar pipeline manualmente |
| `/results` | GET | Listar resultados |
| `/stats` | GET | Estatisticas |
| `/files` | GET | Listar arquivos gerados |
| `/download/<nome>` | GET | Download de arquivo |
| `/analisar` | POST | Analisar imovel com CrewAI |
| `/test` | GET/POST | Testar analise com dados mock |

## Troubleshooting

### Container nao inicia
```bash
docker compose logs leilao-pipeline
```

### Erro de OpenAI API
- Verifique se OPENAI_API_KEY esta correto no .env
- Verifique saldo da conta OpenAI

### Erro de Supabase
- Normal se projeto estiver pausado
- Pipeline funciona sem Supabase (salva em arquivos locais)

### Memoria insuficiente
```bash
# Verificar memoria
free -h

# Limitar memoria do container no docker-compose.yml:
services:
  leilao-pipeline:
    deploy:
      resources:
        limits:
          memory: 2G
```

## Monitoramento

### Logs estruturados
Os logs sao salvos em `/app/logs` dentro do container e podem ser visualizados:
```bash
docker exec leilao-pipeline cat /app/logs/pipeline.log
```

### Health Check automatico
O Docker Compose ja configura health check a cada 30s.

## Atualizacao

```bash
# Parar
docker compose down

# Baixar atualizacoes
git pull

# Rebuild e reiniciar
docker compose up -d --build
```
