# 🏗️ Arquitetura Técnica Detalhada

## Visão Geral do Sistema

Sistema distribuído baseado em microserviços com arquitetura orientada a eventos, utilizando agentes de IA especializados para análise automatizada de imóveis de leilão.

## Diagrama de Componentes

```
┌───────────────────────────────────────────────────────────────────┐
│                         CAMADA DE APRESENTAÇÃO                     │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              LOVABLE (React Frontend)                     │   │
│  │                                                            │   │
│  │  • BuscadorImoveis.tsx (Busca e filtros)                 │   │
│  │  • AnaliseViabilidade.tsx (Visualização resultados)      │   │
│  │  • Dashboard.tsx (Estatísticas)                          │   │
│  │                                                            │   │
│  │  Hooks:                                                    │   │
│  │  • useImoveis.ts (Lógica de negócio)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬──────────────────────────────────────────┘
                         │ HTTP/REST
                         │
┌────────────────────────┴──────────────────────────────────────────┐
│                    CAMADA DE ORQUESTRAÇÃO                          │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    N8N WORKFLOW                           │   │
│  │                                                            │   │
│  │  Fluxo Principal (analise_imovel.json):                  │   │
│  │                                                            │   │
│  │  1. Webhook Trigger ─────────────────┐                   │   │
│  │  2. Buscar Imóvel (Supabase) ────────┤                   │   │
│  │  3. Criar Análise (status: processando)                  │   │
│  │  4. HTTP Request → CrewAI ────────────┤                   │   │
│  │  5. Processar Response ───────────────┤                   │   │
│  │  6. Salvar Análise (Supabase) ────────┤                   │   │
│  │  7. Retornar Resultado ───────────────┘                   │   │
│  │                                                            │   │
│  │  Error Handling:                                          │   │
│  │  • Log Erro (analises_logs)                              │   │
│  │  • Update status = 'erro'                                │   │
│  │  • Webhook Response com erro                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬──────────────────────────────────────────┘
                         │ HTTP POST
                         │
┌────────────────────────┴──────────────────────────────────────────┐
│                    CAMADA DE INTELIGÊNCIA                          │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              CREWAI (Agentes de IA - Python)              │   │
│  │                                                            │   │
│  │  Manager LLM: GPT-4o (OpenAI)                            │   │
│  │  Process: Hierarchical                                    │   │
│  │                                                            │   │
│  │  Agentes:                                                  │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────────┐             │   │
│  │  │ 1. Analista Financeiro SP                │             │   │
│  │  │    • Calcula custos (ITBI, escritura,    │             │   │
│  │  │      comissões, reforma)                 │             │   │
│  │  │    • Projeta ROI e lucro líquido         │             │   │
│  │  │    • Estima aluguel e venda              │             │   │
│  │  └─────────────────────────────────────────┘             │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────────┐             │   │
│  │  │ 2. Analista de Localização SP            │             │   │
│  │  │    • Avalia região/bairro                 │             │   │
│  │  │    • Score 0-100 baseado em infraestrutura│             │   │
│  │  │    • Potencial de valorização             │             │   │
│  │  └─────────────────────────────────────────┘             │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────────┐             │   │
│  │  │ 3. Analista Jurídico de Editais          │             │   │
│  │  │    • Analisa riscos do edital             │             │   │
│  │  │    • Identifica ocupação, débitos         │             │   │
│  │  │    • Score 0-100 segurança jurídica       │             │   │
│  │  └─────────────────────────────────────────┘             │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────────┐             │   │
│  │  │ 4. Analista de Matrícula                  │             │   │
│  │  │    • Identifica gravames                  │             │   │
│  │  │    • Avalia regularidade registral        │             │   │
│  │  │    • Score 0-100 situação matrícula       │             │   │
│  │  └─────────────────────────────────────────┘             │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────────┐             │   │
│  │  │ 5. Revisor Sênior (Consolidador)         │             │   │
│  │  │    • Recebe todas análises anteriores     │             │   │
│  │  │    • Calcula score geral ponderado        │             │   │
│  │  │    • Gera recomendação final              │             │   │
│  │  │    • Compara com Tesouro/CDB              │             │   │
│  │  └─────────────────────────────────────────┘             │   │
│  │                                                            │   │
│  │  API Endpoints:                                           │   │
│  │  • GET /health                                            │   │
│  │  • POST /analisar                                         │   │
│  │  • POST /test                                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬──────────────────────────────────────────┘
                         │ PostgreSQL Protocol
                         │
┌────────────────────────┴──────────────────────────────────────────┐
│                      CAMADA DE DADOS                               │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              SUPABASE (PostgreSQL + Auth)                 │   │
│  │                                                            │   │
│  │  Tabelas:                                                  │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────┐                 │   │
│  │  │ imoveis_leilao (2.334 registros)    │                 │   │
│  │  │                                      │                 │   │
│  │  │ • id (UUID, PK)                     │                 │   │
│  │  │ • codigo_imovel (TEXT, UNIQUE)      │                 │   │
│  │  │ • endereco, bairro, cidade          │                 │   │
│  │  │ • tipo_imovel, area_total           │                 │   │
│  │  │ • valor_avaliacao, valor_minimo     │                 │   │
│  │  │ • situacao (disponivel|arrematado)  │                 │   │
│  │  └─────────────────────────────────────┘                 │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────┐                 │   │
│  │  │ analises_viabilidade                │                 │   │
│  │  │                                      │                 │   │
│  │  │ • id (UUID, PK)                     │                 │   │
│  │  │ • imovel_id (FK)                    │                 │   │
│  │  │ • Custos: ITBI, reforma, comissões  │                 │   │
│  │  │ • Resultados: ROI, lucro            │                 │   │
│  │  │ • Scores: geral, localização...     │                 │   │
│  │  │ • Recomendação: comprar|evitar      │                 │   │
│  │  │ • status (processando|concluido)    │                 │   │
│  │  └─────────────────────────────────────┘                 │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────┐                 │   │
│  │  │ analises_logs                       │                 │   │
│  │  │                                      │                 │   │
│  │  │ • id (UUID, PK)                     │                 │   │
│  │  │ • imovel_id (FK)                    │                 │   │
│  │  │ • tipo_log (erro|info|warning)      │                 │   │
│  │  │ • mensagem, detalhes (JSONB)        │                 │   │
│  │  └─────────────────────────────────────┘                 │   │
│  │                                                            │   │
│  │  Recursos:                                                │   │
│  │  • Row Level Security (RLS)                              │   │
│  │  • Real-time Subscriptions                               │   │
│  │  • Auto-generated REST API                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados Completo

### 1. Busca de Imóveis
```
Usuário → Lovable → Supabase.from('imoveis_leilao').select()
                   ↓
           Retorna lista filtrada
```

### 2. Solicitação de Análise
```
Usuário clica "Analisar"
    ↓
Lovable.solicitarAnalise(imovelId)
    ↓
POST /webhook/analisar-imovel (n8n)
    ↓
n8n:
  1. SELECT * FROM imoveis_leilao WHERE id = imovelId
  2. INSERT INTO analises_viabilidade (status: processando)
  3. POST http://crewai:5000/analisar (dados do imóvel)
    ↓
CrewAI:
  1. Manager LLM inicia coordenação
  2. Executa Agente 1 (Financeiro)
  3. Executa Agente 2 (Localização)
  4. Executa Agente 3 (Jurídico)
  5. Executa Agente 4 (Matrícula)
  6. Executa Agente 5 (Revisor) - recebe outputs 1-4
  7. Retorna JSON consolidado
    ↓
n8n:
  4. Processar Response (extrair campos)
  5. UPDATE analises_viabilidade SET ... WHERE id = analiseId
  6. Response → Lovable
    ↓
Lovable:
  - Atualiza UI
  - Exibe análise completa
```

### 3. Visualização de Análise
```
Usuário acessa /analise/:id
    ↓
Lovable.buscarAnalise(analiseId)
    ↓
Supabase.from('analises_viabilidade').select().eq('id', analiseId)
    ↓
Lovable renderiza AnaliseViabilidade.tsx
```

## Decisões Arquiteturais

### Por que CrewAI?
- ✅ Framework especializado em agentes hierárquicos
- ✅ Manager LLM coordena execução automaticamente
- ✅ Cada agente com backstory especializado
- ✅ Process.hierarchical permite delegação
- ✅ Fácil integração com OpenAI GPT-4o

### Por que n8n?
- ✅ Orquestração visual de workflows
- ✅ Webhooks nativos
- ✅ Integração fácil com Supabase
- ✅ Error handling robusto
- ✅ Deploy simples (n8n.cloud ou self-hosted)

### Por que Supabase?
- ✅ PostgreSQL completo com REST API automática
- ✅ Row Level Security (RLS) nativo
- ✅ Real-time subscriptions
- ✅ 2.334 imóveis já importados
- ✅ Integração nativa com Lovable

### Por que Lovable?
- ✅ React + TypeScript + Tailwind pré-configurado
- ✅ Integração nativa com Supabase
- ✅ Deploy automático
- ✅ Ideal para MVPs rápidos

## Padrões de Design

### 1. Microserviços
- CrewAI: Serviço independente
- n8n: Orquestrador central
- Supabase: Serviço de dados

### 2. Event-Driven Architecture
- Webhooks para comunicação assíncrona
- n8n como event broker

### 3. Separation of Concerns
- Frontend: Apenas UI/UX
- n8n: Orquestração e lógica de negócio
- CrewAI: Inteligência artificial
- Supabase: Persistência

### 4. Hierarchical Agents
- Manager LLM coordena
- Agentes especializados executam
- Revisor consolida resultados

## Segurança

### 1. API Keys
- OpenAI API Key: Backend apenas
- Supabase Service Key: Backend apenas
- Supabase Anon Key: Frontend (limitado por RLS)

### 2. Row Level Security (RLS)
```sql
-- Exemplo de policy no Supabase
CREATE POLICY "Usuários podem ver apenas suas análises"
ON analises_viabilidade
FOR SELECT
USING (auth.uid() = user_id);
```

### 3. CORS
```python
# Flask backend
CORS(app)  # Configurado apenas para domínios permitidos
```

### 4. Validação de Dados
- n8n: Valida estrutura de dados
- CrewAI: Valida inputs antes de processar
- Frontend: Valida antes de enviar

## Performance

### 1. Tempo de Resposta
- Busca de imóveis: < 500ms
- Análise completa: 60-120 segundos
- Visualização: < 200ms

### 2. Otimizações
- **Supabase**: Índices em `situacao`, `cidade`, `valor_minimo`
- **n8n**: Timeout de 180s para CrewAI
- **CrewAI**: Temperatura 0.2 para respostas mais rápidas
- **Frontend**: Lazy loading de componentes

### 3. Escalabilidade
```yaml
# Horizontal Scaling
CrewAI:
  replicas: 3  # Load balancer
  resources:
    cpu: 1 core
    memory: 2GB

n8n:
  replicas: 2
  database: PostgreSQL (separado)
```

## Monitoramento

### 1. Logs
```bash
# CrewAI
docker-compose logs -f crewai

# n8n
docker-compose logs -f n8n

# Supabase
# Dashboard → Logs
```

### 2. Métricas
- Tempo de processamento médio
- Taxa de sucesso/erro
- Uso de API OpenAI
- Número de análises por dia

### 3. Alertas
- n8n: Email em caso de erro
- Supabase: Webhook para status = 'erro'
- CrewAI: Log de exceções

## Backup e Recuperação

### 1. Banco de Dados (Supabase)
- Backup automático diário
- Point-in-time recovery
- Exportação manual via Dashboard

### 2. Workflows (n8n)
- Exportar JSON periodicamente
- Versionamento no Git
- Backup do volume Docker

### 3. Código
- Git repository
- Tags de versão
- CI/CD pipeline

## Roadmap Técnico

### Fase 1 (MVP) ✅
- Backend CrewAI com 5 agentes
- Workflow n8n completo
- Frontend Lovable básico

### Fase 2 (2 semanas)
- [ ] Autenticação Supabase Auth
- [ ] Sistema de cache (Redis)
- [ ] Queue system (RabbitMQ)
- [ ] Exportação PDF

### Fase 3 (1 mês)
- [ ] Analytics (Mixpanel/Amplitude)
- [ ] A/B Testing
- [ ] Mobile app (React Native)
- [ ] Notifications (Push/Email)

### Fase 4 (3 meses)
- [ ] Multi-tenancy
- [ ] White-label
- [ ] API pública
- [ ] Marketplace de agentes

---

**Última atualização:** Janeiro 2025
**Versão:** 1.0.0
**Autor:** Claude Code
