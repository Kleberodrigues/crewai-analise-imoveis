# Setup do Agendamento no n8n

Este documento descreve como configurar o agendamento automatico do pipeline de analise de leiloes no n8n.

## Arquitetura

```
n8n (Schedule Trigger)
    |
    v (2x por semana: Seg e Qui 8h)
CrewAI API (/pipeline/executar)
    |
    v
Pipeline de Analise
    |
    +-> Coleta dados Caixa
    +-> Analisa imoveis
    +-> Seleciona Top 5
    +-> Gera PDF e CSV
    |
    v
Supabase (log de execucoes)
    |
    v
Email de notificacao
```

## Passo a Passo

### 1. Importar Workflow no n8n

1. Acesse: https://n8n.kleberodrigues.shop
2. Va em **Workflows** > **Import from File**
3. Selecione o arquivo: `n8n-workflow-agendamento-leilao.json`
4. Clique em **Import**

### 2. Configurar Credenciais

#### Supabase
1. Va em **Settings** > **Credentials** > **Add Credential**
2. Selecione **Supabase API**
3. Preencha:
   - **Host**: `https://bgmstucvkwuwbjbvdcuo.supabase.co`
   - **Service Role Key**: (ver .env do projeto)

#### SMTP (para emails)
1. Va em **Settings** > **Credentials** > **Add Credential**
2. Selecione **SMTP**
3. Para Gmail:
   - **Host**: smtp.gmail.com
   - **Port**: 587
   - **User**: seu-email@gmail.com
   - **Password**: senha de aplicativo (gerar em https://myaccount.google.com/apppasswords)
   - **SSL/TLS**: STARTTLS

### 3. Configurar Variaveis de Ambiente

No n8n, adicione as variaveis:

```
CREWAI_TOKEN=pat_Iv-4wDl4gPGGwXcoJlgUXudr5tf3jlGBCx90HJI1Dgc
NOTIFICATION_EMAIL=kleberr.rodriguess@gmail.com
```

### 4. Criar Tabela no Supabase

Execute a migracao SQL no Supabase:

```bash
# Via CLI
supabase db push supabase_migration_pipeline_execucoes.sql

# Ou via Dashboard
# Copie o conteudo do arquivo e execute no SQL Editor
```

### 5. Ativar Workflow

1. Abra o workflow importado
2. Clique no switch **Active** no canto superior direito
3. O workflow executara automaticamente:
   - **Segunda-feira** as 8h (Sao Paulo)
   - **Quinta-feira** as 8h (Sao Paulo)

## Endpoints da API

### Executar Pipeline Manualmente
```bash
curl -X POST https://n8n-crewai.zq1zp2.easypanel.host/pipeline/executar \
  -H "Content-Type: application/json" \
  -H "x-api-key: pat_Iv-4wDl4gPGGwXcoJlgUXudr5tf3jlGBCx90HJI1Dgc" \
  -d '{
    "preco_max": 150000,
    "tipo": "Apartamento",
    "quantidade_top": 5
  }'
```

### Verificar Status
```bash
curl https://n8n-crewai.zq1zp2.easypanel.host/pipeline/status
```

### Webhook Manual (n8n)
```
https://n8n.kleberodrigues.shop/webhook/executar-pipeline-leilao
```

## Resultado Esperado

Apos cada execucao:

1. **Arquivos gerados** (no servidor CrewAI):
   - `output/top5_oportunidades_YYYYMMDD.pdf`
   - `output/top5_oportunidades_YYYYMMDD.csv`

2. **Registro no Supabase** (tabela `pipeline_execucoes`):
   - Data da execucao
   - Status (success/error)
   - Estatisticas (total analisados, top5, recomendados)
   - Caminhos dos arquivos

3. **Email de notificacao**:
   - Resumo da execucao
   - Erros (se houver)

## Fluxo do Workflow

```
[Schedule Trigger] -----> [HTTP Request] -----> [IF Success?]
    (Seg/Qui 8h)           (CrewAI API)              |
                                                     |
[Webhook Trigger] ------+                           / \
    (Manual)            |                          /   \
                        +------------------------> Sim  Nao
                                                   |     |
                                                   v     v
                                            [Supabase] [Set Error]
                                            [Set OK]      |
                                                   |      |
                                                   v      v
                                              [Merge] -----> [Send Email]
```

## Troubleshooting

### Workflow nao executa
- Verifique se esta **Active**
- Verifique o timezone (deve ser America/Sao_Paulo)
- Verifique os logs em **Executions**

### Erro de conexao com CrewAI
- Verifique se o servico esta online: `https://n8n-crewai.zq1zp2.easypanel.host/health`
- Verifique o token de API

### Email nao enviado
- Verifique credenciais SMTP
- Para Gmail, use **Senha de Aplicativo** (nao a senha normal)

### Supabase nao registra
- Verifique se a tabela `pipeline_execucoes` existe
- Verifique as credenciais do Supabase

## Monitoramento

### Ver ultimas execucoes (Supabase)
```sql
SELECT * FROM v_ultimas_execucoes;
```

### Ver execucoes da semana
```sql
SELECT * FROM pipeline_execucoes
WHERE data_execucao >= NOW() - INTERVAL '7 days'
ORDER BY data_execucao DESC;
```

### Dashboard n8n
- Acesse: https://n8n.kleberodrigues.shop
- Va em **Executions** para ver historico
