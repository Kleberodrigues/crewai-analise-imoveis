-- ============================================
-- SCRIPT DE VERIFICAÇÃO DA TABELA imoveis_leilao
-- ============================================
-- Execute este script ANTES do schema.sql para ver a estrutura atual

-- Ver todas as colunas da tabela imoveis_leilao
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'imoveis_leilao'
ORDER BY ordinal_position;

-- Ver total de registros
SELECT COUNT(*) as total_registros FROM imoveis_leilao;

-- Ver amostra de 3 registros
SELECT * FROM imoveis_leilao LIMIT 3;
