# 🤖 CrewAI - Backend de Análise de Imóveis

Backend com 5 agentes de IA especializados para análise de imóveis de leilão.

## 🏗️ Arquitetura

- **Flask 3.0**: API REST
- **CrewAI 1.0.0**: Orquestração de agentes
- **GPT-4o**: Modelo de linguagem
- **Supabase**: Persistência de dados

## 🤖 Agentes

1. **Analista Financeiro SP** - Cálculo de ROI e custos
2. **Analista de Localização SP** - Avaliação de bairros e potencial
3. **Analista Jurídico de Editais** - Riscos e pendências
4. **Analista de Matrícula** - Gravames e irregularidades
5. **Revisor Sênior** - Consolidação e recomendação final

## 🚀 Deploy no Easypanel

### Variáveis de Ambiente

```env
OPENAI_API_KEY=sk-proj-...
SUPABASE_URL=https://pxymmcmksyekkjptqblp.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
PORT=5000
```

### Comandos

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar
python main.py
```

## 📡 Endpoints

### `GET /health`
Health check do serviço

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-24T10:30:00Z"
}
```

### `POST /analisar`
Inicia análise de imóvel

**Request:**
```json
{
  "imovel_id": "uuid-do-imovel",
  "dados_imovel": {
    "endereco": "Rua X, 123",
    "valor_minimo": 150000,
    "cidade": "São Paulo"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "analise": {
    "score_geral": 85,
    "recomendacao": "comprar",
    "roi_percentual": 18.5,
    "justificativa_ia": "..."
  }
}
```

## 🧪 Testes

```bash
# Health check
curl https://n8n-crewai.zq1zp2.easypanel.host/health

# Análise (via n8n webhook)
curl -X POST https://n8n.kleberodrigues.shop/webhook/analisar-imovel \
  -H "Content-Type: application/json" \
  -d '{"imovel_id": "uuid-aqui"}'
```

## 📝 Logs

Os logs são enviados para `analises_logs` no Supabase.
