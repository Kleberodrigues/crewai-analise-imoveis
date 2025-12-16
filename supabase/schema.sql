-- ============================================
-- SCHEMA COMPLETO - ANÁLISE DE IMÓVEIS LEILÃO
-- ============================================

-- ============================================
-- 1. TABELA: imoveis_leilao
-- ============================================
-- Já existe com 2.334 registros
-- Verificar se possui todos os campos necessários

-- Adicionar campos se não existirem (executar apenas se necessário)
ALTER TABLE imoveis_leilao
  ADD COLUMN IF NOT EXISTS situacao TEXT DEFAULT 'disponivel' CHECK (situacao IN ('disponivel', 'arrematado', 'cancelado')),
  ADD COLUMN IF NOT EXISTS tipo_imovel TEXT,
  ADD COLUMN IF NOT EXISTS area_total NUMERIC,
  ADD COLUMN IF NOT EXISTS quartos INTEGER,
  ADD COLUMN IF NOT EXISTS banheiros INTEGER,
  ADD COLUMN IF NOT EXISTS vagas_garagem INTEGER,
  ADD COLUMN IF NOT EXISTS iptu_anual NUMERIC,
  ADD COLUMN IF NOT EXISTS condominio_mensal NUMERIC,
  ADD COLUMN IF NOT EXISTS descricao TEXT,
  ADD COLUMN IF NOT EXISTS observacoes TEXT,
  ADD COLUMN IF NOT EXISTS edital_url TEXT,
  ADD COLUMN IF NOT EXISTS matricula_url TEXT,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_imoveis_situacao ON imoveis_leilao(situacao);
CREATE INDEX IF NOT EXISTS idx_imoveis_cidade ON imoveis_leilao(cidade);
CREATE INDEX IF NOT EXISTS idx_imoveis_valor ON imoveis_leilao(valor_minimo);
CREATE INDEX IF NOT EXISTS idx_imoveis_tipo ON imoveis_leilao(tipo_imovel);

-- ============================================
-- 2. TABELA: analises_viabilidade
-- ============================================
DROP TABLE IF EXISTS analises_viabilidade CASCADE;

CREATE TABLE analises_viabilidade (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  imovel_id UUID NOT NULL REFERENCES imoveis_leilao(id) ON DELETE CASCADE,
  user_id UUID, -- Para multi-tenant futuro

  -- Status da análise
  status TEXT NOT NULL DEFAULT 'processando' CHECK (status IN ('processando', 'concluido', 'erro')),

  -- Resultado geral
  score_geral INTEGER CHECK (score_geral BETWEEN 0 AND 100),
  recomendacao TEXT CHECK (recomendacao IN ('comprar', 'analisar_melhor', 'evitar')),
  justificativa_ia TEXT,

  -- Análise financeira
  custo_total NUMERIC,
  custo_aquisicao NUMERIC,
  custo_itbi NUMERIC,
  custo_escritura NUMERIC,
  custo_registro NUMERIC,
  custo_reforma_estimado NUMERIC,
  custo_comissoes NUMERIC,

  -- Projeções financeiras
  valor_mercado_estimado NUMERIC,
  valor_aluguel_estimado NUMERIC,
  roi_percentual NUMERIC,
  lucro_liquido NUMERIC,
  tempo_retorno_meses INTEGER,

  -- Comparação com investimentos
  comparacao_tesouro JSONB,
  comparacao_cdb JSONB,

  -- Análise de localização
  score_localizacao INTEGER CHECK (score_localizacao BETWEEN 0 AND 100),
  analise_localizacao JSONB, -- {transporte, comercio, educacao, saude, seguranca}
  potencial_valorizacao TEXT,

  -- Análise jurídica (edital)
  score_edital INTEGER CHECK (score_edital BETWEEN 0 AND 100),
  analise_edital_score INTEGER CHECK (analise_edital_score BETWEEN 0 AND 100),
  riscos_edital JSONB, -- Array de riscos identificados
  ocupacao_detectada BOOLEAN,
  debitos_detectados BOOLEAN,

  -- Análise de matrícula
  score_matricula INTEGER CHECK (score_matricula BETWEEN 0 AND 100),
  analise_matricula_score INTEGER CHECK (analise_matricula_score BETWEEN 0 AND 100),
  gravames_detectados JSONB, -- Array de gravames
  irregularidades_matricula JSONB,

  -- Recomendações e alertas
  pontos_atencao JSONB, -- Array de strings
  proximos_passos JSONB, -- Array de strings
  observacoes_ia TEXT,

  -- Metadados
  tempo_processamento_segundos INTEGER,
  modelo_ia_usado TEXT DEFAULT 'gpt-4o',
  versao_analise TEXT DEFAULT '1.0.0',

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  processado_at TIMESTAMPTZ
);

-- Índices
CREATE INDEX idx_analises_imovel ON analises_viabilidade(imovel_id);
CREATE INDEX idx_analises_status ON analises_viabilidade(status);
CREATE INDEX idx_analises_user ON analises_viabilidade(user_id);
CREATE INDEX idx_analises_recomendacao ON analises_viabilidade(recomendacao);
CREATE INDEX idx_analises_created ON analises_viabilidade(created_at DESC);

-- ============================================
-- 3. TABELA: analises_logs
-- ============================================
DROP TABLE IF EXISTS analises_logs CASCADE;

CREATE TABLE analises_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  imovel_id UUID REFERENCES imoveis_leilao(id) ON DELETE CASCADE,
  analise_id UUID REFERENCES analises_viabilidade(id) ON DELETE CASCADE,

  tipo_log TEXT NOT NULL CHECK (tipo_log IN ('info', 'warning', 'erro', 'debug')),
  mensagem TEXT NOT NULL,
  detalhes JSONB,

  stack_trace TEXT,
  user_agent TEXT,
  ip_address INET,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_logs_analise ON analises_logs(analise_id);
CREATE INDEX idx_logs_imovel ON analises_logs(imovel_id);
CREATE INDEX idx_logs_tipo ON analises_logs(tipo_log);
CREATE INDEX idx_logs_created ON analises_logs(created_at DESC);

-- ============================================
-- 4. FUNCTIONS & TRIGGERS
-- ============================================

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para imoveis_leilao
DROP TRIGGER IF EXISTS update_imoveis_updated_at ON imoveis_leilao;
CREATE TRIGGER update_imoveis_updated_at
  BEFORE UPDATE ON imoveis_leilao
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Trigger para analises_viabilidade
DROP TRIGGER IF EXISTS update_analises_updated_at ON analises_viabilidade;
CREATE TRIGGER update_analises_updated_at
  BEFORE UPDATE ON analises_viabilidade
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 5. ROW LEVEL SECURITY (RLS)
-- ============================================

-- Habilitar RLS
ALTER TABLE imoveis_leilao ENABLE ROW LEVEL SECURITY;
ALTER TABLE analises_viabilidade ENABLE ROW LEVEL SECURITY;
ALTER TABLE analises_logs ENABLE ROW LEVEL SECURITY;

-- Políticas públicas para leitura (todos podem ver imóveis disponíveis)
DROP POLICY IF EXISTS "Imóveis públicos para leitura" ON imoveis_leilao;
CREATE POLICY "Imóveis públicos para leitura"
  ON imoveis_leilao FOR SELECT
  USING (true);

-- Análises: usuários autenticados podem ver todas (por enquanto)
DROP POLICY IF EXISTS "Análises públicas para leitura" ON analises_viabilidade;
CREATE POLICY "Análises públicas para leitura"
  ON analises_viabilidade FOR SELECT
  USING (true);

-- Logs: apenas leitura por admin (service role)
DROP POLICY IF EXISTS "Logs apenas para service role" ON analises_logs;
CREATE POLICY "Logs apenas para service role"
  ON analises_logs FOR SELECT
  TO service_role
  USING (true);

-- ============================================
-- 6. VIEWS ÚTEIS
-- ============================================

-- View: Imóveis com última análise
CREATE OR REPLACE VIEW vw_imoveis_com_analise AS
SELECT
  i.id,
  i.cidade,
  i.endereco,
  i.valor_minimo,
  i.situacao,
  i.tipo_imovel,
  i.area_total,
  i.quartos,
  i.banheiros,
  i.vagas_garagem,
  i.descricao,
  i.edital_url,
  i.matricula_url,
  i.created_at as imovel_created_at,
  i.updated_at as imovel_updated_at,
  a.id as analise_id,
  a.status as analise_status,
  a.score_geral,
  a.recomendacao,
  a.roi_percentual,
  a.lucro_liquido,
  a.created_at as analise_created_at
FROM imoveis_leilao i
LEFT JOIN LATERAL (
  SELECT * FROM analises_viabilidade
  WHERE imovel_id = i.id
  ORDER BY created_at DESC
  LIMIT 1
) a ON true;

-- View: Estatísticas de análises
CREATE OR REPLACE VIEW vw_estatisticas_analises AS
SELECT
  COUNT(*) as total_analises,
  COUNT(CASE WHEN status = 'concluido' THEN 1 END) as concluidas,
  COUNT(CASE WHEN status = 'processando' THEN 1 END) as em_processamento,
  COUNT(CASE WHEN status = 'erro' THEN 1 END) as com_erro,
  COUNT(CASE WHEN recomendacao = 'comprar' THEN 1 END) as recomendadas_comprar,
  COUNT(CASE WHEN recomendacao = 'analisar_melhor' THEN 1 END) as analisar_melhor,
  COUNT(CASE WHEN recomendacao = 'evitar' THEN 1 END) as evitar,
  AVG(score_geral) as score_medio,
  AVG(tempo_processamento_segundos) as tempo_medio_segundos
FROM analises_viabilidade;

-- ============================================
-- 7. DADOS DE EXEMPLO (OPCIONAL)
-- ============================================

-- Comentar se não quiser inserir dados de teste
-- INSERT INTO analises_viabilidade (
--   imovel_id,
--   status,
--   score_geral,
--   recomendacao,
--   justificativa_ia
-- ) VALUES (
--   (SELECT id FROM imoveis_leilao LIMIT 1),
--   'concluido',
--   85,
--   'comprar',
--   'Imóvel com excelente localização e potencial de valorização.'
-- );

-- ============================================
-- 8. COMENTÁRIOS
-- ============================================

COMMENT ON TABLE imoveis_leilao IS 'Imóveis de leilão da Caixa Econômica Federal - SP até R$ 200k';
COMMENT ON TABLE analises_viabilidade IS 'Análises de viabilidade de investimento realizadas pela IA';
COMMENT ON TABLE analises_logs IS 'Logs de processamento das análises';

COMMENT ON COLUMN analises_viabilidade.score_geral IS 'Score de 0-100 calculado pelo Revisor Sênior';
COMMENT ON COLUMN analises_viabilidade.recomendacao IS 'comprar | analisar_melhor | evitar';
COMMENT ON COLUMN analises_viabilidade.roi_percentual IS 'Return on Investment (ROI) em percentual';

-- ============================================
-- FIM DO SCHEMA
-- ============================================
