-- ============================================
-- DIAGNÓSTICO E CORREÇÃO DO TRIGGER
-- ============================================

-- PROBLEMA: O trigger handle_new_user() está falhando
-- CAUSA: Tentativa de inserir em profiles com foreign key para auth.users

-- ============================================
-- PASSO 1: REMOVER TRIGGER PROBLEMÁTICO
-- ============================================

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- ============================================
-- PASSO 2: RECRIAR FUNÇÃO COM TRATAMENTO DE ERRO
-- ============================================

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Inserir perfil
  INSERT INTO public.profiles (id, email, nome_completo, subscription_tier, subscription_status, limite_analises_mes, analises_usadas_mes_atual)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'nome_completo', ''),
    'free',
    'active',
    3,
    0
  )
  ON CONFLICT (id) DO NOTHING;

  -- Criar notificação de boas-vindas
  INSERT INTO public.notifications (user_id, type, title, message, priority)
  VALUES (
    NEW.id,
    'success',
    'Bem-vindo à Plataforma!',
    'Você tem 3 análises gratuitas este mês. Explore nossos imóveis!',
    1
  )
  ON CONFLICT DO NOTHING;

  RETURN NEW;
EXCEPTION
  WHEN OTHERS THEN
    -- Log do erro (mas não falha a criação do usuário)
    RAISE WARNING 'Erro ao criar perfil para usuário %: %', NEW.id, SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- PASSO 3: RECRIAR TRIGGER
-- ============================================

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_user();

-- ============================================
-- PASSO 4: TESTAR (opcional)
-- ============================================

-- Para testar, você pode criar um usuário via dashboard do Supabase
-- ou via SQL (se tiver permissão):

-- INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, raw_user_meta_data)
-- VALUES (
--   gen_random_uuid(),
--   'teste@example.com',
--   crypt('senha123', gen_salt('bf')),
--   NOW(),
--   '{"nome_completo": "Usuario Teste"}'::jsonb
-- );

-- Depois verificar se o perfil foi criado:
-- SELECT * FROM profiles WHERE email = 'teste@example.com';

-- ============================================
-- ALTERNATIVA: DESABILITAR TRIGGER COMPLETAMENTE
-- ============================================

-- Se o trigger continuar falhando, você pode desabilitá-lo
-- e deixar o backend criar os perfis manualmente:

-- DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Com isso, o backend precisa criar o perfil manualmente
-- usando client.auth.admin.create_user() seguido de
-- client.table("profiles").insert()

-- ============================================
-- VERIFICAÇÃO FINAL
-- ============================================

-- Verificar se o trigger foi criado:
SELECT tgname, tgtype, tgenabled
FROM pg_trigger
WHERE tgname = 'on_auth_user_created';

-- Verificar foreign keys da tabela profiles:
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table_name,
  ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name='profiles';
