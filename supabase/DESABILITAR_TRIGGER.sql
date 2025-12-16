-- ============================================
-- DESABILITAR TRIGGER PROBLEMÁTICO
-- ============================================
-- Este script remove o trigger que está falhando
-- O backend vai criar os perfis manualmente

-- Remover trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Verificar se foi removido
SELECT 'Trigger removido com sucesso!' AS status;

-- Listar triggers restantes (deve estar vazio)
SELECT tgname FROM pg_trigger WHERE tgname = 'on_auth_user_created';
