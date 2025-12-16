# 🚀 Guia de Início Rápido

Este guia vai te ajudar a rodar o projeto completo em **menos de 15 minutos**.

## ⚡ Início Rápido (5 minutos)

### 1. Pré-requisitos
```bash
# Verificar se Docker está instalado
docker --version
docker-compose --version

# Verificar se você tem as credenciais necessárias:
# - OpenAI API Key (GPT-4o)
# - Supabase já configurado (https://YOUR-PROJECT-REF.supabase.co)

⚠️ Segurança: use apenas placeholders neste guia. Configure chaves reais apenas em variáveis de ambiente, nunca nos arquivos de código.
```

### 2. Clone e Configure
```bash
# Clone o projeto
git clone https://github.com/seu-usuario/projeto-analise-imoveis-leilao.git
cd projeto-analise-imoveis-leilao

# Copie o arquivo de configuração
cp .env.example .env

# Edite com suas credenciais (APENAS OpenAI necessário para começar)
nano .env  # ou use seu editor preferido
```

**Configuração mínima do .env:**
```env
OPENAI_API_KEY=YOUR_OPENAI_API_KEY  # ⚠️ OBRIGATÓRIO
SUPABASE_URL=https://YOUR-PROJECT-REF.supabase.co
SUPABASE_SERVICE_KEY=sua_service_key_aqui
```

### 3. Iniciar Serviços
```bash
# Iniciar tudo com Docker Compose
docker-compose up -d

# Aguardar ~30 segundos para inicialização

# Verificar se está tudo rodando
docker-compose ps
```

**Você deve ver:**
- ✅ `crewai-analise-imoveis` (UP) - porta 5000
- ✅ `n8n-workflows` (UP) - porta 5678

### 4. Testar Backend
```bash
# Testar health check
curl http://localhost:5000/health

# Deve retornar:
# {"status":"ok","service":"crewai-analise-imoveis","version":"1.0.0"}
```

### 5. Configurar n8n (3 minutos)
```bash
# Abrir n8n no navegador
open http://localhost:5678  # ou acesse manualmente
```

**No n8n:**
1. Login: `admin` / `admin123`
2. Ir em **Settings** → **Import from File**
3. Selecionar: `workflows/analise_imovel.json`
4. Configurar credenciais Supabase:
   - **Credentials** → **Add Credential** → **Supabase API**
   - URL: `https://YOUR-PROJECT-REF.supabase.co`
   - Service Key: sua chave do .env
5. **Ativar workflow** (toggle no canto superior direito)

### 6. Testar Integração Completa
```bash
# Buscar ID de um imóvel real no Supabase
# Acesse: https://YOUR-PROJECT-REF.supabase.co
# Tabela: imoveis_leilao → copie um ID

# Testar webhook (substitua UUID_REAL pelo ID copiado)
curl -X POST http://localhost:5678/webhook/analisar-imovel \
  -H "Content-Type: application/json" \
  -d '{"imovel_id": "UUID_REAL"}'
```

**Resultado esperado:**
- Tempo: ~60-120 segundos
- Retorno com `analise_id`, `score_geral`, `recomendacao`

✅ **Pronto! Backend funcionando!**

---

## 🎨 Frontend (Lovable)

O frontend deve ser desenvolvido na plataforma Lovable.

### Setup no Lovable (5 minutos)

1. **Criar projeto no Lovable:**
   - Acesse https://lovable.dev
   - Criar novo projeto React

2. **Copiar componentes:**
   - Copiar conteúdo de `frontend/src/components/BuscadorImoveis.tsx`
   - Criar componente no Lovable
   - Copiar conteúdo de `frontend/src/components/AnaliseViabilidade.tsx`
   - Criar componente no Lovable

3. **Copiar hooks:**
   - Copiar conteúdo de `frontend/src/hooks/useImoveis.ts`
   - Criar hook no Lovable

4. **Configurar variáveis de ambiente no Lovable:**
   ```
   VITE_SUPABASE_URL=https://YOUR-PROJECT-REF.supabase.co
   VITE_SUPABASE_ANON_KEY=sua_anon_key_aqui
   VITE_N8N_WEBHOOK_URL=http://localhost:5678/webhook/analisar-imovel
   ```

5. **Instalar dependências no Lovable:**
   ```
   @supabase/supabase-js
   lucide-react
   ```

6. **Testar:**
   - Buscar "São Paulo"
   - Clicar em "Analisar Imóvel"
   - Ver análise completa em ~2 minutos

---

## 📊 Verificar Dados no Supabase

### Ver imóveis disponíveis:
```sql
SELECT
  codigo_imovel,
  endereco,
  cidade,
  tipo_imovel,
  valor_minimo
FROM imoveis_leilao
WHERE situacao = 'disponivel'
LIMIT 10;
```

### Ver estatísticas:
```sql
-- Total de imóveis
SELECT COUNT(*) as total FROM imoveis_leilao WHERE situacao = 'disponivel';

-- Por cidade
SELECT
  cidade,
  COUNT(*) as total,
  AVG(valor_minimo) as media_preco
FROM imoveis_leilao
WHERE situacao = 'disponivel'
GROUP BY cidade
ORDER BY total DESC
LIMIT 10;

-- Por tipo
SELECT
  tipo_imovel,
  COUNT(*) as total
FROM imoveis_leilao
WHERE situacao = 'disponivel'
GROUP BY tipo_imovel
ORDER BY total DESC;
```

---

## 🐛 Troubleshooting Rápido

### Erro: "Connection refused" no CrewAI
```bash
# Verificar se está rodando
docker-compose ps

# Ver logs
docker-compose logs crewai

# Reiniciar
docker-compose restart crewai
```

### Erro: "OPENAI_API_KEY not found"
```bash
# Verificar .env
cat .env | grep OPENAI_API_KEY

# Se vazio, edite .env e adicione sua chave
# Depois reinicie:
docker-compose restart crewai
```

### Erro: n8n não conecta ao Supabase
1. Verificar se credenciais estão corretas
2. Testar conexão manualmente:
   ```bash
   curl -H "apikey: SUA_SERVICE_KEY" \
     https://YOUR-PROJECT-REF.supabase.co/rest/v1/imoveis_leilao?limit=1
   ```

### Análise muito lenta (> 3 minutos)
- Rate limit da OpenAI (aguardar 1 minuto)
- Rede lenta (verificar conexão)
- Timeout do n8n (aumentar para 180s no HTTP Request node)

---

## 📝 Próximos Passos

Depois de ter tudo funcionando:

1. ✅ **Testar com imóveis reais**
   - Buscar diferentes cidades
   - Testar diferentes faixas de preço

2. ✅ **Analisar resultados**
   - Ver análises salvas no Supabase
   - Validar scores e recomendações

3. ✅ **Personalizar**
   - Ajustar prompts dos agentes
   - Customizar frontend

4. ✅ **Deploy**
   - Railway/Render para backend
   - n8n.cloud para workflows
   - Lovable deploy automático

---

## 🎯 Checklist de Sucesso

- [ ] Docker Compose rodando (crewai + n8n)
- [ ] Health check do CrewAI OK (`/health`)
- [ ] n8n acessível (http://localhost:5678)
- [ ] Workflow importado e ativo no n8n
- [ ] Credenciais Supabase configuradas no n8n
- [ ] Teste de análise completa bem-sucedido
- [ ] Frontend Lovable conectado
- [ ] Busca de imóveis funcionando
- [ ] Análise E2E completa (< 2 minutos)

✅ **Tudo funcionando? Parabéns! Sistema pronto para uso!**

---

## 🆘 Precisa de Ajuda?

- Consulte o [README.md](../README.md) para documentação completa
- Veja logs: `docker-compose logs -f`
- Teste individual de cada componente
- Verifique variáveis de ambiente

**Boa sorte! 🚀**
