# Analise de Imoveis de Leilao - Uso Pessoal

Sistema de analise automatizada de imoveis de leilao da Caixa em Sao Paulo.
Utiliza agentes de IA para avaliar viabilidade financeira e recomendar oportunidades de investimento.

## Funcionalidades

- Analise automatica de imoveis em menos de 2 minutos
- Calculo de ROI, lucro liquido e todos os custos
- Avaliacao de localizacao, edital e matricula
- Recomendacao objetiva: COMPRAR, ANALISAR MELHOR ou EVITAR
- Comparacao de retorno com Tesouro Direto e CDB

## Stack

- **Backend**: Python + Flask
- **IA**: CrewAI (5 agentes especializados)
- **Banco de Dados**: Supabase (PostgreSQL)
- **Automacao**: N8N
- **Containers**: Docker

## Estrutura do Projeto

```
projeto-analise-imoveis-leilao/
|-- backend/
|   |-- crewai_service/     # Servico de analise IA
|   |-- main.py             # API Flask
|-- supabase/
|   |-- schema_pessoal.sql  # Schema simplificado
|   |-- schema.sql          # Schema original
|-- workflows/              # Workflows N8N
|-- tests/                  # Testes
|-- docker-compose.yml      # Configuracao Docker
```

## Configuracao

### 1. Variaveis de Ambiente

Copie `.env.example` para `.env` e configure:

```bash
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon
SUPABASE_SERVICE_KEY=sua-chave-service

# OpenAI
OPENAI_API_KEY=sua-chave-openai

# N8N
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=sua-chave-n8n
```

### 2. Banco de Dados

Aplique o schema simplificado no Supabase:

```sql
-- No SQL Editor do Supabase, execute:
-- supabase/schema_pessoal.sql
```

Tabelas criadas:
- `imoveis_leilao` - Dados dos imoveis
- `analises_viabilidade` - Resultados das analises
- `favoritos` - Imoveis marcados
- `pipeline_execucoes` - Historico de execucoes

### 3. Docker

```bash
docker-compose up -d
```

## Uso

### Iniciar Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

API disponivel em: http://localhost:5000

### Endpoints Principais

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | /api/imoveis | Listar imoveis |
| GET | /api/imoveis/{id} | Detalhes de um imovel |
| POST | /api/analise | Iniciar analise |
| GET | /api/analise/{id} | Status da analise |
| GET | /api/oportunidades | Top imoveis recomendados |

### Exemplo de Analise

```bash
curl -X POST http://localhost:5000/api/analise \
  -H "Content-Type: application/json" \
  -d '{"imovel_id": "uuid-do-imovel"}'
```

## Agentes de IA

O sistema utiliza 5 agentes CrewAI especializados:

1. **Analista de Localizacao** - Avalia bairro, infraestrutura, potencial
2. **Analista de Edital** - Verifica riscos juridicos e condicoes
3. **Analista de Matricula** - Identifica gravames e irregularidades
4. **Analista Financeiro** - Calcula custos, ROI, comparativos
5. **Coordenador** - Consolida analises e gera recomendacao

## Filtros de Imoveis

- **Faixa de preco**: R$ 50.000 a R$ 200.000
- **Localizacao**: Sao Paulo (capital e interior)
- **Tipos**: Apartamentos, Casas, Terrenos, Comercial

## Manutencao

### Atualizar Lista de Imoveis

Os imoveis sao importados do site da Caixa via workflow N8N.

### Limpar Analises Antigas

```sql
DELETE FROM analises_viabilidade
WHERE created_at < NOW() - INTERVAL '30 days';
```

## Desenvolvimento

### Testes

```bash
cd tests
pytest
```

### Logs

```bash
docker-compose logs -f crewai_service
```

## Licenca

Uso pessoal - Projeto privado para investimentos.
