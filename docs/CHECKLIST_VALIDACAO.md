# ✅ Checklist de Validação End-to-End

Use este checklist para validar que todos os componentes do sistema estão funcionando corretamente.

## 📋 Pré-Requisitos

- [ ] Docker e Docker Compose instalados
- [ ] OpenAI API Key configurada
- [ ] Supabase acessível (https://YOUR-PROJECT-REF.supabase.co)
- [ ] Nenhuma chave/segredo real em arquivos (confira `.env.example`, READMEs)
- [ ] Credenciais Supabase (Service Key e Anon Key)
- [ ] Node.js 18+ (para testes)

## 🐳 Infraestrutura

### Docker Compose
- [ ] Arquivo `.env` criado e configurado
- [ ] `docker-compose up -d` executado sem erros
- [ ] Container `crewai-analise-imoveis` rodando (status: UP)
- [ ] Container `n8n-workflows` rodando (status: UP)
- [ ] Portas 5000 e 5678 acessíveis

**Comando de verificação:**
```bash
docker-compose ps
# Deve mostrar 2 containers com status "Up"
```

## 🔧 Backend CrewAI

### Health Check
- [ ] Endpoint `/health` responde com status 200
- [ ] Response contém `{"status": "ok"}`

**Teste:**
```bash
curl http://localhost:5000/health
```

**Resultado esperado:**
```json
{
  "status": "ok",
  "service": "crewai-analise-imoveis",
  "version": "1.0.0"
}
```

### Variáveis de Ambiente
- [ ] `OPENAI_API_KEY` configurada
- [ ] `SUPABASE_URL` configurada
- [ ] `SUPABASE_SERVICE_KEY` configurada

**Verificação:**
```bash
docker exec crewai-analise-imoveis env | grep -E 'OPENAI|SUPABASE'
```

### Teste de Análise (Mock)
- [ ] Endpoint `/test` responde
- [ ] Retorna estrutura JSON com análise

**Teste:**
```bash
curl -X POST http://localhost:5000/test
# Aguardar ~60-120 segundos
```

## 🔀 N8N Workflow

### Acesso
- [ ] n8n acessível em http://localhost:5678
- [ ] Login funciona (admin/admin123)
- [ ] Dashboard carrega sem erros

### Workflow Importado
- [ ] Workflow `analise_imovel.json` importado
- [ ] Todos os nodos visíveis
- [ ] Sem erros de configuração

**Nodos esperados:**
1. Webhook Trigger
2. Supabase: Buscar Imóvel
3. Supabase: Criar Análise
4. HTTP: Chamar CrewAI
5. Function: Processar Response
6. Supabase: Atualizar Análise
7. Webhook Response
8. Supabase: Log Erro (error path)
9. Supabase: Marcar Como Erro (error path)
10. Webhook Response Erro (error path)

### Credenciais Supabase
- [ ] Credencial "Supabase API" criada
- [ ] URL configurada: `https://YOUR-PROJECT-REF.supabase.co`
- [ ] Service Key configurada
- [ ] Teste de conexão OK

**Teste de conexão:**
1. Abrir qualquer nodo Supabase
2. Testar conexão
3. Deve retornar sucesso

### Workflow Ativo
- [ ] Toggle do workflow ativado (verde)
- [ ] URL do webhook copiada
- [ ] Formato: `http://localhost:5678/webhook/analisar-imovel`

## 💾 Supabase Database

### Conexão
- [ ] Dashboard Supabase acessível
- [ ] Login OK
- [ ] Projeto correto selecionado

### Tabelas
- [ ] Tabela `imoveis_leilao` existe
- [ ] Tabela `analises_viabilidade` existe
- [ ] Tabela `analises_logs` existe

**Query de verificação:**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('imoveis_leilao', 'analises_viabilidade', 'analises_logs');
```

### Dados de Imóveis
- [ ] Tabela `imoveis_leilao` contém dados
- [ ] Pelo menos 1.000 imóveis com `situacao = 'disponivel'`
- [ ] Campos essenciais preenchidos

**Query de verificação:**
```sql
SELECT
  COUNT(*) as total,
  COUNT(DISTINCT cidade) as cidades,
  MIN(valor_minimo) as min_valor,
  MAX(valor_minimo) as max_valor
FROM imoveis_leilao
WHERE situacao = 'disponivel';
```

**Resultado esperado:**
- Total: >= 1000
- Cidades: >= 50
- Min valor: ~50.000
- Max valor: ~200.000

## 🧪 Testes Unitários

### Backend
- [ ] Testes instalados: `pip install -r tests/requirements-test.txt`
- [ ] `test_crewai_api.py` passa
- [ ] `test_supabase_integration.py` passa

**Executar testes:**
```bash
cd backend/crewai_service
pytest ../../tests/ -v
```

### Resultados Esperados
- [ ] `test_health_check`: PASSED
- [ ] `test_analisar_endpoint_sem_dados`: PASSED
- [ ] `test_supabase_connection`: PASSED
- [ ] `test_buscar_imoveis_disponiveis`: PASSED

## 🔗 Integração End-to-End

### 1. Preparação
- [ ] Pegar ID de um imóvel real do Supabase

**Query:**
```sql
SELECT id, codigo_imovel, endereco, cidade
FROM imoveis_leilao
WHERE situacao = 'disponivel'
LIMIT 1;
```

### 2. Executar Análise Completa
- [ ] Fazer request ao webhook n8n com ID real

**Comando:**
```bash
export IMOVEL_ID="UUID_AQUI"

curl -X POST http://localhost:5678/webhook/analisar-imovel \
  -H "Content-Type: application/json" \
  -d "{\"imovel_id\": \"$IMOVEL_ID\"}"
```

### 3. Validar Execução
- [ ] Request aceita (status 200 ou processamento iniciado)
- [ ] Tempo de processamento: 60-180 segundos
- [ ] Response contém `analise_id`

**Response esperado:**
```json
{
  "analise_id": "uuid-da-analise",
  "status": "concluido",
  "score_geral": 75,
  "recomendacao": "comprar",
  "tempo_processamento": 87
}
```

### 4. Verificar no Supabase
- [ ] Análise salva em `analises_viabilidade`
- [ ] Status = 'concluido'
- [ ] Todos os campos preenchidos

**Query de verificação:**
```sql
SELECT
  id,
  imovel_id,
  status,
  score_geral,
  recomendacao,
  roi_percentual,
  lucro_liquido,
  tempo_processamento_segundos
FROM analises_viabilidade
ORDER BY created_at DESC
LIMIT 1;
```

### 5. Validar Campos da Análise
- [ ] `score_geral`: 0-100
- [ ] `recomendacao`: "comprar" | "analisar_melhor" | "evitar"
- [ ] `roi_percentual`: > 0
- [ ] `lucro_liquido`: valor numérico
- [ ] `score_localizacao`: 0-100
- [ ] `analise_edital_score`: 0-100
- [ ] `analise_matricula_score`: 0-100
- [ ] `justificativa_ia`: texto preenchido
- [ ] `pontos_atencao`: array com itens
- [ ] `proximos_passos`: array com itens

### 6. Logs
- [ ] Sem erros no log do CrewAI
- [ ] Sem erros no log do n8n
- [ ] Nenhum registro em `analises_logs` com tipo='erro'

**Verificar logs:**
```bash
# CrewAI
docker-compose logs crewai | grep -i error

# n8n
docker-compose logs n8n | grep -i error

# Supabase
SELECT * FROM analises_logs WHERE tipo_log = 'erro' ORDER BY created_at DESC LIMIT 5;
```

## 🎨 Frontend Lovable

### Componentes
- [ ] `useImoveis.ts` hook criado no Lovable
- [ ] `BuscadorImoveis.tsx` componente criado
- [ ] `AnaliseViabilidade.tsx` componente criado

### Configuração
- [ ] Variáveis de ambiente configuradas:
  - [ ] `VITE_SUPABASE_URL`
  - [ ] `VITE_SUPABASE_ANON_KEY`
  - [ ] `VITE_N8N_WEBHOOK_URL`
- [ ] Dependências instaladas:
  - [ ] `@supabase/supabase-js`
  - [ ] `lucide-react`

### Funcionalidades
- [ ] Busca de imóveis funciona
- [ ] Filtros aplicam corretamente
- [ ] Lista exibe imóveis
- [ ] Botão "Analisar Imóvel" funciona
- [ ] Análise é exibida após processamento

## 📊 Testes de Casos de Uso

### Caso 1: Busca Simples
**Passos:**
1. Abrir frontend Lovable
2. Buscar por "São Paulo"
3. Ver resultados

**Validações:**
- [ ] Retorna imóveis de São Paulo
- [ ] Cards exibem informações corretas
- [ ] Filtros aplicam corretamente

### Caso 2: Análise de Imóvel Completa
**Passos:**
1. Buscar imóvel
2. Clicar em "Analisar Imóvel"
3. Aguardar processamento (~2 min)
4. Ver análise completa

**Validações:**
- [ ] Loading indicator durante processamento
- [ ] Análise exibida após conclusão
- [ ] Score geral entre 0-100
- [ ] Recomendação clara
- [ ] Justificativa detalhada
- [ ] Pontos de atenção listados
- [ ] Próximos passos listados
- [ ] Indicadores financeiros corretos

### Caso 3: Filtros Avançados
**Passos:**
1. Aplicar filtros:
   - Cidade: "Campinas"
   - Valor máximo: R$ 120.000
   - Tipo: "Apartamento"
   - Quartos: 2

**Validações:**
- [ ] Resultados respeitam todos os filtros
- [ ] Número de resultados correto

## 🚨 Testes de Erro

### Erro 1: OpenAI API Key Inválida
**Cenário:**
- Configurar key inválida
- Tentar análise

**Validação:**
- [ ] Erro tratado graciosamente
- [ ] Status = 'erro' salvo
- [ ] Log de erro criado
- [ ] Mensagem amigável ao usuário

### Erro 2: Supabase Indisponível
**Cenário:**
- Simular falha de conexão

**Validação:**
- [ ] n8n detecta erro
- [ ] Workflow não trava
- [ ] Erro logado

### Erro 3: Timeout CrewAI
**Cenário:**
- Processamento > 180s

**Validação:**
- [ ] Timeout configurado no n8n
- [ ] Erro tratado
- [ ] Status atualizado

## 📈 Performance

### Benchmarks
- [ ] Busca de imóveis: < 500ms
- [ ] Análise completa: 60-180 segundos
- [ ] Visualização: < 200ms

**Teste de carga:**
```bash
# Fazer 10 buscas seguidas
for i in {1..10}; do
  time curl http://localhost:5000/health
done
```

## 🎯 Checklist Final de Produção

### Antes do Deploy
- [ ] Todos os testes passando
- [ ] Variáveis de ambiente configuradas para produção
- [ ] Secrets seguros (não commitados)
- [ ] Logs configurados
- [ ] Monitoramento ativo
- [ ] Backup do banco configurado

### Deploy Backend (Railway/Render)
- [ ] Serviço CrewAI deployado
- [ ] Health check OK
- [ ] Variáveis de ambiente configuradas
- [ ] URL pública acessível

### Deploy n8n (n8n.cloud)
- [ ] Workflow importado
- [ ] Credenciais configuradas
- [ ] Webhook URL atualizada
- [ ] Workflow ativo

### Deploy Frontend (Lovable)
- [ ] Build sem erros
- [ ] Variáveis de ambiente configuradas
- [ ] URL do webhook atualizada para produção
- [ ] Site acessível

## ✅ Critérios de Aceitação

Para considerar o sistema **PRONTO PARA PRODUÇÃO**, todos os itens abaixo devem estar OK:

### Funcionalidade
- [x] Busca de imóveis funciona
- [x] Análise completa em < 3 minutos
- [x] Resultados salvos no Supabase
- [x] Frontend exibe análise corretamente

### Performance
- [x] 100% das análises concluem com sucesso
- [x] Tempo médio < 2 minutos
- [x] Sem timeouts ou crashes

### Qualidade
- [x] 0 erros críticos nos logs
- [x] Análises com qualidade consistente
- [x] Todos os campos preenchidos

### Segurança
- [x] API Keys seguras (não expostas)
- [x] RLS configurado no Supabase
- [x] CORS configurado corretamente

---

## 📝 Registro de Validação

**Data:** ___/___/2025
**Responsável:** ________________
**Versão:** 1.0.0

**Resultado Geral:** ☐ APROVADO ☐ REPROVADO

**Observações:**
_______________________________________________________
_______________________________________________________
_______________________________________________________

**Próximos Passos:**
- [ ] _________________________________________________
- [ ] _________________________________________________
- [ ] _________________________________________________

---

**🎉 Parabéns! Se todos os itens estão OK, seu sistema está pronto para produção!**
