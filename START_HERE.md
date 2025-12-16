# COMECE AQUI - Guia Rapido

Sistema de analise de imoveis de leilao para uso pessoal.

---

## O Que Voce Precisa

1. **Conta Supabase** (banco de dados)
2. **Chave OpenAI** (analise IA)
3. **Docker** (opcional, para N8N)

---

## Setup em 3 Passos

### 1. Banco de Dados (5 minutos)

```bash
# 1. Acesse seu projeto Supabase
https://supabase.com/dashboard

# 2. Va em "SQL Editor"

# 3. Cole o conteudo de:
supabase/schema_pessoal.sql

# 4. Clique em "RUN"

# Tabelas criadas:
# - imoveis_leilao
# - analises_viabilidade
# - favoritos
# - pipeline_execucoes
```

### 2. Configurar .env (2 minutos)

```bash
# Copie o exemplo
cp .env.example .env

# Edite com suas chaves:
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJxxx...
SUPABASE_SERVICE_KEY=eyJxxx...
OPENAI_API_KEY=sk-xxx...
```

### 3. Iniciar Backend (2 minutos)

```bash
cd backend
pip install -r requirements.txt
python main.py

# API rodando em http://localhost:5000
```

---

## Testar

```bash
# Listar imoveis
curl http://localhost:5000/api/imoveis

# Analisar imovel
curl -X POST http://localhost:5000/api/analise \
  -H "Content-Type: application/json" \
  -d '{"imovel_id": "uuid-do-imovel"}'
```

---

## Proximos Passos

1. Importar imoveis da Caixa
2. Configurar N8N para automacao (opcional)
3. Analisar oportunidades

---

## Arquivos Importantes

| Arquivo | Descricao |
|---------|-----------|
| `backend/main.py` | API Flask |
| `backend/crewai_service/` | Agentes de IA |
| `supabase/schema_pessoal.sql` | Schema do banco |
| `.env` | Configuracoes |

---

## Problemas Comuns

### Erro de conexao Supabase
- Verifique SUPABASE_URL e chaves no .env

### Erro OpenAI
- Verifique OPENAI_API_KEY no .env
- Verifique creditos na conta OpenAI

### Imoveis nao aparecem
- Execute o schema no Supabase
- Importe dados da Caixa

---

## Suporte

Consulte o README.md para documentacao completa.
