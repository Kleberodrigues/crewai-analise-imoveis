# Historico de Migracoes - Supabase

**Ultima Atualizacao**: 2025-12-16
**Tipo**: Uso Pessoal (sem SaaS)

---

## Schema Atual

| Arquivo | Status | Descricao |
|---------|--------|-----------|
| `schema_pessoal.sql` | RECOMENDADO | Schema simplificado para uso pessoal |
| `schema.sql` | Legado | Schema original com analises |
| `schema_leilao_v2.sql` | Alternativo | Schema v2 normalizado |

---

## Tabelas Principais

### schema_pessoal.sql (Recomendado)

```sql
-- 4 tabelas simplificadas:
imoveis_leilao        -- Dados dos imoveis
analises_viabilidade  -- Resultados das analises IA
favoritos             -- Imoveis marcados
pipeline_execucoes    -- Historico de execucoes

-- 3 views:
vw_oportunidades      -- Imoveis recomendados para compra
vw_estatisticas       -- Estatisticas gerais
vw_resumo_cidades     -- Resumo por cidade
```

---

## Como Aplicar

1. Acesse o SQL Editor do Supabase
2. Cole o conteudo de `schema_pessoal.sql`
3. Execute

---

## Arquivos de Suporte

| Arquivo | Uso |
|---------|-----|
| `FIX_TRIGGER.sql` | Corrigir trigger se necessario |
| `DESABILITAR_TRIGGER.sql` | Desabilitar trigger para debug |
| `verificar_tabela.sql` | Verificar estrutura das tabelas |
| `setup_database.py` | Script Python para setup |

---

## Notas

- RLS desabilitado (uso pessoal, sem multi-tenant)
- Sem tabelas de usuarios, assinaturas ou pagamentos
- Schema otimizado para analise de investimentos
