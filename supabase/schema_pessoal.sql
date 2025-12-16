-- ============================================
-- SCHEMA SIMPLIFICADO - USO PESSOAL
-- ============================================
-- Análise de Imóveis de Leilão
-- Sem complexidade SaaS (sem usuários, pagamentos, etc.)
-- ============================================

-- Extensão UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. TABELA: imoveis_leilao
-- Dados dos imóveis de leilão da Caixa
-- ============================================

CREATE TABLE IF NOT EXISTS imoveis_leilao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificação
    codigo_imovel VARCHAR(50) UNIQUE,

    -- Localização
    endereco TEXT,
    bairro VARCHAR(100),
    cidade VARCHAR(100) NOT NULL,
    uf VARCHAR(2) DEFAULT 'SP',
    cep VARCHAR(10),

    -- Características
    tipo_imovel VARCHAR(50),
    area_total NUMERIC(10,2),
    area_privativa NUMERIC(10,2),
    quartos INTEGER DEFAULT 0,
    banheiros INTEGER DEFAULT 0,
    vagas_garagem INTEGER DEFAULT 0,

    -- Valores
    valor_avaliacao NUMERIC(15,2),
    valor_minimo NUMERIC(15,2),
    desconto NUMERIC(5,2),

    -- Leilão
    praca VARCHAR(20),              -- '1a Praca' ou '2a Praca'
    data_leilao DATE,
    modalidade VARCHAR(100),

    -- Custos mensais
    iptu_anual NUMERIC(10,2),
    condominio_mensal NUMERIC(10,2),

    -- Links
    link TEXT,
    edital_url TEXT,
    matricula_url TEXT,

    -- Descrição
    descricao TEXT,
    observacoes TEXT,

    -- Status
    situacao TEXT DEFAULT 'disponivel'
        CHECK (situacao IN ('disponivel', 'arrematado', 'cancelado', 'analisando')),

    -- Metadados
    fonte VARCHAR(50) DEFAULT 'caixa',
    hash_csv VARCHAR(32),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_imoveis_cidade ON imoveis_leilao(cidade);
CREATE INDEX IF NOT EXISTS idx_imoveis_valor ON imoveis_leilao(valor_minimo);
CREATE INDEX IF NOT EXISTS idx_imoveis_situacao ON imoveis_leilao(situacao);
CREATE INDEX IF NOT EXISTS idx_imoveis_tipo ON imoveis_leilao(tipo_imovel);
CREATE INDEX IF NOT EXISTS idx_imoveis_praca ON imoveis_leilao(praca);
CREATE INDEX IF NOT EXISTS idx_imoveis_ativo ON imoveis_leilao(ativo) WHERE ativo = TRUE;

-- ============================================
-- 2. TABELA: analises_viabilidade
-- Resultado das análises de IA
-- ============================================

CREATE TABLE IF NOT EXISTS analises_viabilidade (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    imovel_id UUID NOT NULL REFERENCES imoveis_leilao(id) ON DELETE CASCADE,

    -- Status
    status TEXT NOT NULL DEFAULT 'processando'
        CHECK (status IN ('processando', 'concluido', 'erro')),

    -- Score e Recomendação
    score_geral INTEGER CHECK (score_geral BETWEEN 0 AND 100),
    recomendacao TEXT CHECK (recomendacao IN ('comprar', 'analisar_melhor', 'evitar')),
    justificativa_ia TEXT,

    -- Análise Financeira
    custo_total NUMERIC(15,2),
    custo_aquisicao NUMERIC(15,2),
    custo_itbi NUMERIC(15,2),
    custo_escritura NUMERIC(15,2),
    custo_registro NUMERIC(15,2),
    custo_reforma_estimado NUMERIC(15,2),
    custo_comissoes NUMERIC(15,2),
    custo_desocupacao NUMERIC(15,2),

    -- Projeções
    valor_mercado_estimado NUMERIC(15,2),
    valor_aluguel_estimado NUMERIC(15,2),
    roi_percentual NUMERIC(8,2),
    lucro_liquido NUMERIC(15,2),
    tempo_retorno_meses INTEGER,
    margem_seguranca NUMERIC(8,2),

    -- Comparativos
    comparacao_tesouro JSONB,
    comparacao_cdb JSONB,
    comparativo_cdi NUMERIC(15,2),

    -- Scores Detalhados
    score_localizacao INTEGER CHECK (score_localizacao BETWEEN 0 AND 100),
    score_edital INTEGER CHECK (score_edital BETWEEN 0 AND 100),
    score_matricula INTEGER CHECK (score_matricula BETWEEN 0 AND 100),
    score_financeiro INTEGER CHECK (score_financeiro BETWEEN 0 AND 100),

    -- Análise de Localização
    analise_localizacao JSONB,
    potencial_valorizacao TEXT,
    liquidez VARCHAR(20),

    -- Análise Jurídica
    riscos_edital JSONB,
    ocupacao_detectada BOOLEAN,
    debitos_detectados BOOLEAN,

    -- Análise de Matrícula
    gravames_detectados JSONB,
    irregularidades_matricula JSONB,

    -- Recomendações
    pontos_atencao JSONB,
    proximos_passos JSONB,
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
CREATE INDEX IF NOT EXISTS idx_analises_imovel ON analises_viabilidade(imovel_id);
CREATE INDEX IF NOT EXISTS idx_analises_status ON analises_viabilidade(status);
CREATE INDEX IF NOT EXISTS idx_analises_recomendacao ON analises_viabilidade(recomendacao);
CREATE INDEX IF NOT EXISTS idx_analises_score ON analises_viabilidade(score_geral DESC);
CREATE INDEX IF NOT EXISTS idx_analises_created ON analises_viabilidade(created_at DESC);

-- ============================================
-- 3. TABELA: favoritos
-- Imóveis marcados como favoritos
-- ============================================

CREATE TABLE IF NOT EXISTS favoritos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    imovel_id UUID NOT NULL REFERENCES imoveis_leilao(id) ON DELETE CASCADE,

    notas TEXT,
    prioridade INTEGER DEFAULT 0,
    tags TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(imovel_id)
);

CREATE INDEX IF NOT EXISTS idx_favoritos_prioridade ON favoritos(prioridade DESC);

-- ============================================
-- 4. TABELA: pipeline_execucoes
-- Histórico de execuções do pipeline
-- ============================================

CREATE TABLE IF NOT EXISTS pipeline_execucoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    data_execucao TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) NOT NULL,

    total_analisados INTEGER DEFAULT 0,
    top5_selecionados INTEGER DEFAULT 0,
    recomendados INTEGER DEFAULT 0,

    arquivo_csv TEXT,
    arquivo_pdf TEXT,
    resumo_json JSONB,
    erro TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_data ON pipeline_execucoes(data_execucao DESC);

-- ============================================
-- 5. TRIGGERS
-- ============================================

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers
DROP TRIGGER IF EXISTS update_imoveis_updated_at ON imoveis_leilao;
CREATE TRIGGER update_imoveis_updated_at
    BEFORE UPDATE ON imoveis_leilao
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_analises_updated_at ON analises_viabilidade;
CREATE TRIGGER update_analises_updated_at
    BEFORE UPDATE ON analises_viabilidade
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 6. VIEWS
-- ============================================

-- View: Oportunidades (análises recomendadas)
CREATE OR REPLACE VIEW vw_oportunidades AS
SELECT
    i.id,
    i.codigo_imovel,
    i.endereco,
    i.bairro,
    i.cidade,
    i.tipo_imovel,
    i.valor_minimo,
    i.valor_avaliacao,
    i.desconto,
    i.praca,
    i.link,
    a.score_geral,
    a.recomendacao,
    a.roi_percentual,
    a.lucro_liquido,
    a.justificativa_ia,
    a.pontos_atencao,
    a.created_at as data_analise,
    f.id IS NOT NULL as favorito
FROM imoveis_leilao i
LEFT JOIN LATERAL (
    SELECT * FROM analises_viabilidade
    WHERE imovel_id = i.id AND status = 'concluido'
    ORDER BY created_at DESC
    LIMIT 1
) a ON true
LEFT JOIN favoritos f ON f.imovel_id = i.id
WHERE i.ativo = TRUE
  AND i.situacao = 'disponivel'
  AND a.recomendacao = 'comprar'
ORDER BY a.score_geral DESC NULLS LAST;

-- View: Estatísticas gerais
CREATE OR REPLACE VIEW vw_estatisticas AS
SELECT
    COUNT(*) as total_imoveis,
    COUNT(*) FILTER (WHERE situacao = 'disponivel') as disponiveis,
    AVG(valor_minimo) as valor_medio,
    MIN(valor_minimo) as valor_minimo,
    MAX(valor_minimo) as valor_maximo,
    COUNT(DISTINCT cidade) as cidades
FROM imoveis_leilao
WHERE ativo = TRUE;

-- View: Resumo por cidade
CREATE OR REPLACE VIEW vw_resumo_cidades AS
SELECT
    cidade,
    COUNT(*) as total,
    AVG(valor_minimo)::INTEGER as valor_medio,
    AVG(desconto)::NUMERIC(5,2) as desconto_medio,
    COUNT(*) FILTER (WHERE praca = '2a Praca') as segunda_praca
FROM imoveis_leilao
WHERE ativo = TRUE AND situacao = 'disponivel'
GROUP BY cidade
ORDER BY total DESC;

-- ============================================
-- 7. RLS (Row Level Security) - SIMPLIFICADO
-- ============================================

-- Desabilitar RLS (uso pessoal, não precisa)
ALTER TABLE imoveis_leilao DISABLE ROW LEVEL SECURITY;
ALTER TABLE analises_viabilidade DISABLE ROW LEVEL SECURITY;
ALTER TABLE favoritos DISABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_execucoes DISABLE ROW LEVEL SECURITY;

-- ============================================
-- COMENTÁRIOS
-- ============================================

COMMENT ON TABLE imoveis_leilao IS 'Imóveis de leilão da Caixa - SP até R$ 200k';
COMMENT ON TABLE analises_viabilidade IS 'Análises de viabilidade por IA';
COMMENT ON TABLE favoritos IS 'Imóveis marcados para acompanhamento';
COMMENT ON TABLE pipeline_execucoes IS 'Histórico de execuções do pipeline';
COMMENT ON VIEW vw_oportunidades IS 'Imóveis recomendados para compra';

-- ============================================
-- FIM
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ SCHEMA PESSOAL APLICADO COM SUCESSO';
    RAISE NOTICE '';
    RAISE NOTICE 'Tabelas criadas:';
    RAISE NOTICE '  • imoveis_leilao';
    RAISE NOTICE '  • analises_viabilidade';
    RAISE NOTICE '  • favoritos';
    RAISE NOTICE '  • pipeline_execucoes';
    RAISE NOTICE '';
    RAISE NOTICE 'Views criadas:';
    RAISE NOTICE '  • vw_oportunidades';
    RAISE NOTICE '  • vw_estatisticas';
    RAISE NOTICE '  • vw_resumo_cidades';
    RAISE NOTICE '';
END $$;
