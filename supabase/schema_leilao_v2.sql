-- =====================================================
-- SCHEMA SUPABASE - ANALISE LEILAO IMOVEIS CAIXA v2.0
-- =====================================================

-- Extensoes necessarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- TABELA: imoveis_caixa
-- Dados brutos do CSV da Caixa
-- =====================================================
CREATE TABLE IF NOT EXISTS imoveis_caixa (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_imovel VARCHAR(50) UNIQUE NOT NULL,
    uf VARCHAR(2) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    bairro VARCHAR(100),
    endereco TEXT,
    preco DECIMAL(15,2),
    valor_avaliacao DECIMAL(15,2),
    desconto DECIMAL(5,2),
    descricao TEXT,
    modalidade VARCHAR(100),
    link TEXT,
    -- Campos parseados
    tipo_imovel VARCHAR(50),
    area_privativa DECIMAL(10,2),
    area_total DECIMAL(10,2),
    quartos INTEGER DEFAULT 0,
    vagas INTEGER DEFAULT 0,
    praca VARCHAR(20), -- '1a Praca' ou '2a Praca'
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    hash_csv VARCHAR(32), -- Para detectar mudancas
    ativo BOOLEAN DEFAULT TRUE
);

-- Indices para busca rapida
CREATE INDEX IF NOT EXISTS idx_imoveis_cidade ON imoveis_caixa(cidade);
CREATE INDEX IF NOT EXISTS idx_imoveis_preco ON imoveis_caixa(preco);
CREATE INDEX IF NOT EXISTS idx_imoveis_praca ON imoveis_caixa(praca);
CREATE INDEX IF NOT EXISTS idx_imoveis_tipo ON imoveis_caixa(tipo_imovel);
CREATE INDEX IF NOT EXISTS idx_imoveis_ativo ON imoveis_caixa(ativo);

-- =====================================================
-- TABELA: imoveis_filtrados
-- Imoveis que passaram nos filtros (alvos de analise)
-- =====================================================
CREATE TABLE IF NOT EXISTS imoveis_filtrados (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    imovel_id UUID REFERENCES imoveis_caixa(id) ON DELETE CASCADE,
    filtro_aplicado JSONB, -- Criterios usados
    data_filtragem TIMESTAMPTZ DEFAULT NOW(),
    status_analise VARCHAR(20) DEFAULT 'pendente', -- pendente, em_analise, concluido
    prioridade INTEGER DEFAULT 0 -- Para ordenar fila de analise
);

CREATE INDEX IF NOT EXISTS idx_filtrados_status ON imoveis_filtrados(status_analise);

-- =====================================================
-- TABELA: analises_edital
-- Resultado da analise do edital
-- =====================================================
CREATE TABLE IF NOT EXISTS analises_edital (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    imovel_id UUID REFERENCES imoveis_caixa(id) ON DELETE CASCADE,
    -- Dados extraidos
    ocupacao VARCHAR(20) DEFAULT 'nao_informado', -- ocupado, desocupado, nao_informado
    debitos_iptu DECIMAL(15,2) DEFAULT 0,
    debitos_condominio DECIMAL(15,2) DEFAULT 0,
    outros_debitos DECIMAL(15,2) DEFAULT 0,
    total_debitos DECIMAL(15,2) DEFAULT 0,
    comissao_leiloeiro_pct DECIMAL(5,2) DEFAULT 5,
    prazo_pagamento VARCHAR(50),
    data_leilao DATE,
    -- Riscos
    riscos TEXT[], -- Array de riscos identificados
    observacoes TEXT,
    -- Score
    score INTEGER CHECK (score >= 0 AND score <= 100),
    classificacao VARCHAR(20), -- Bom, Regular, Ruim
    -- Metadata
    fonte_dados VARCHAR(50), -- ocr, manual, api
    pdf_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edital_imovel ON analises_edital(imovel_id);
CREATE INDEX IF NOT EXISTS idx_edital_score ON analises_edital(score);

-- =====================================================
-- TABELA: analises_matricula
-- Resultado da analise da matricula
-- =====================================================
CREATE TABLE IF NOT EXISTS analises_matricula (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    imovel_id UUID REFERENCES imoveis_caixa(id) ON DELETE CASCADE,
    -- Dados extraidos
    numero_matricula VARCHAR(50),
    cartorio VARCHAR(200),
    area_registrada DECIMAL(10,2),
    -- Gravames
    gravames_extintos TEXT[], -- Eliminados no leilao
    gravames_transferidos TEXT[], -- Transferidos ao arrematante
    valor_gravames DECIMAL(15,2) DEFAULT 0,
    -- Irregularidades
    irregularidades TEXT[],
    -- Score
    score INTEGER CHECK (score >= 0 AND score <= 100),
    classificacao VARCHAR(20), -- Limpa, Regular, Problematica
    -- Metadata
    fonte_dados VARCHAR(50),
    pdf_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matricula_imovel ON analises_matricula(imovel_id);

-- =====================================================
-- TABELA: pesquisas_mercado
-- Dados de pesquisa de mercado
-- =====================================================
CREATE TABLE IF NOT EXISTS pesquisas_mercado (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    imovel_id UUID REFERENCES imoveis_caixa(id) ON DELETE CASCADE,
    -- Precos
    preco_m2_regiao DECIMAL(15,2),
    valor_mercado_estimado DECIMAL(15,2),
    condominio_mensal DECIMAL(15,2),
    iptu_mensal DECIMAL(15,2),
    aluguel_estimado DECIMAL(15,2),
    -- Liquidez
    liquidez VARCHAR(20), -- alta, media, baixa
    tempo_venda_dias INTEGER,
    demanda_regiao VARCHAR(20),
    -- Fontes
    fontes TEXT[], -- zap, vivareal, olx, etc
    imoveis_comparados INTEGER,
    -- Score
    score_localizacao INTEGER CHECK (score_localizacao >= 0 AND score_localizacao <= 100),
    score_liquidez INTEGER CHECK (score_liquidez >= 0 AND score_liquidez <= 100),
    -- Metadata
    data_pesquisa TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mercado_imovel ON pesquisas_mercado(imovel_id);

-- =====================================================
-- TABELA: analises_custos
-- Calculo de custos detalhado
-- =====================================================
CREATE TABLE IF NOT EXISTS analises_custos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    imovel_id UUID REFERENCES imoveis_caixa(id) ON DELETE CASCADE,
    -- Valor base
    valor_arrematacao DECIMAL(15,2),
    -- Custos aquisicao
    comissao_leiloeiro DECIMAL(15,2),
    itbi DECIMAL(15,2),
    escritura DECIMAL(15,2),
    registro DECIMAL(15,2),
    certidoes DECIMAL(15,2),
    honorarios_advogado DECIMAL(15,2),
    custo_desocupacao DECIMAL(15,2) DEFAULT 0,
    debitos_edital DECIMAL(15,2) DEFAULT 0,
    gravames_matricula DECIMAL(15,2) DEFAULT 0,
    custo_reforma DECIMAL(15,2) DEFAULT 0,
    total_custos_aquisicao DECIMAL(15,2),
    investimento_total DECIMAL(15,2),
    -- Manutencao (cenario 6 meses)
    manutencao_condominio DECIMAL(15,2),
    manutencao_iptu DECIMAL(15,2),
    manutencao_outros DECIMAL(15,2),
    total_manutencao DECIMAL(15,2),
    investimento_total_6m DECIMAL(15,2),
    -- Custos venda
    comissao_corretor DECIMAL(15,2),
    irpf_ganho_capital DECIMAL(15,2),
    total_custos_venda DECIMAL(15,2),
    -- Cenario venda
    preco_venda_estimado DECIMAL(15,2),
    lucro_bruto DECIMAL(15,2),
    lucro_liquido DECIMAL(15,2),
    roi_total DECIMAL(8,2),
    roi_mensal DECIMAL(8,2),
    margem_seguranca DECIMAL(8,2),
    -- Comparativo
    comparativo_cdi DECIMAL(15,2),
    diferenca_vs_cdi DECIMAL(15,2),
    -- Metadata
    meses_cenario INTEGER DEFAULT 6,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_custos_imovel ON analises_custos(imovel_id);
CREATE INDEX IF NOT EXISTS idx_custos_roi ON analises_custos(roi_total);

-- =====================================================
-- TABELA: analises_finais
-- Resultado consolidado da analise
-- =====================================================
CREATE TABLE IF NOT EXISTS analises_finais (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    imovel_id UUID REFERENCES imoveis_caixa(id) ON DELETE CASCADE,
    -- Referencias
    edital_id UUID REFERENCES analises_edital(id),
    matricula_id UUID REFERENCES analises_matricula(id),
    mercado_id UUID REFERENCES pesquisas_mercado(id),
    custos_id UUID REFERENCES analises_custos(id),
    -- Scores
    score_edital INTEGER,
    score_matricula INTEGER,
    score_localizacao INTEGER,
    score_financeiro INTEGER,
    score_liquidez INTEGER,
    score_geral DECIMAL(5,2),
    -- Decisao
    recomendacao VARCHAR(20), -- COMPRAR, ANALISAR_MELHOR, EVITAR
    nivel_risco VARCHAR(20), -- BAIXO, MEDIO, ALTO
    estrelas INTEGER CHECK (estrelas >= 1 AND estrelas <= 5),
    -- Textos
    justificativa TEXT,
    pontos_atencao TEXT[],
    proximos_passos TEXT[],
    -- Status
    status VARCHAR(20) DEFAULT 'ativo', -- ativo, arquivado, arrematado
    notificado BOOLEAN DEFAULT FALSE,
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_final_imovel ON analises_finais(imovel_id);
CREATE INDEX IF NOT EXISTS idx_final_score ON analises_finais(score_geral DESC);
CREATE INDEX IF NOT EXISTS idx_final_recomendacao ON analises_finais(recomendacao);
CREATE INDEX IF NOT EXISTS idx_final_status ON analises_finais(status);

-- =====================================================
-- TABELA: alertas_enviados
-- Historico de notificacoes
-- =====================================================
CREATE TABLE IF NOT EXISTS alertas_enviados (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analise_id UUID REFERENCES analises_finais(id) ON DELETE CASCADE,
    canal VARCHAR(20) NOT NULL, -- whatsapp, telegram, email
    destinatario VARCHAR(100),
    mensagem TEXT,
    status VARCHAR(20) DEFAULT 'enviado', -- enviado, falhou, lido
    erro TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alertas_analise ON alertas_enviados(analise_id);

-- =====================================================
-- TABELA: downloads_csv
-- Historico de downloads do CSV da Caixa
-- =====================================================
CREATE TABLE IF NOT EXISTS downloads_csv (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estado VARCHAR(2) NOT NULL,
    filename VARCHAR(100),
    filepath TEXT,
    hash_arquivo VARCHAR(32),
    total_imoveis INTEGER,
    total_filtrados INTEGER,
    status VARCHAR(20), -- sucesso, falha, sem_mudancas
    erro TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_downloads_estado ON downloads_csv(estado);
CREATE INDEX IF NOT EXISTS idx_downloads_data ON downloads_csv(created_at);

-- =====================================================
-- VIEWS
-- =====================================================

-- View: Oportunidades com score alto
CREATE OR REPLACE VIEW v_oportunidades AS
SELECT
    i.id_imovel,
    i.endereco,
    i.bairro,
    i.cidade,
    i.tipo_imovel,
    i.preco,
    i.valor_avaliacao,
    i.desconto,
    i.praca,
    i.link,
    af.score_geral,
    af.recomendacao,
    af.nivel_risco,
    af.estrelas,
    ac.investimento_total_6m,
    ac.lucro_liquido,
    ac.roi_total,
    ac.margem_seguranca,
    af.justificativa,
    af.created_at as data_analise
FROM imoveis_caixa i
JOIN analises_finais af ON i.id = af.imovel_id
JOIN analises_custos ac ON i.id = ac.imovel_id
WHERE af.status = 'ativo'
    AND af.recomendacao = 'COMPRAR'
ORDER BY af.score_geral DESC;

-- View: Resumo por cidade
CREATE OR REPLACE VIEW v_resumo_cidades AS
SELECT
    cidade,
    COUNT(*) as total_imoveis,
    COUNT(*) FILTER (WHERE praca = '2a Praca') as total_2a_praca,
    AVG(preco) as preco_medio,
    AVG(desconto) as desconto_medio,
    MIN(preco) as preco_minimo,
    MAX(preco) as preco_maximo
FROM imoveis_caixa
WHERE ativo = TRUE
GROUP BY cidade
ORDER BY total_imoveis DESC;

-- =====================================================
-- FUNCOES
-- =====================================================

-- Funcao: Atualiza updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para updated_at
CREATE TRIGGER tr_imoveis_updated
    BEFORE UPDATE ON imoveis_caixa
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_edital_updated
    BEFORE UPDATE ON analises_edital
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_matricula_updated
    BEFORE UPDATE ON analises_matricula
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_custos_updated
    BEFORE UPDATE ON analises_custos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_final_updated
    BEFORE UPDATE ON analises_finais
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Funcao: Busca imoveis por criterios
CREATE OR REPLACE FUNCTION buscar_imoveis(
    p_preco_max DECIMAL DEFAULT 150000,
    p_tipo VARCHAR DEFAULT 'Apartamento',
    p_praca VARCHAR DEFAULT '2a Praca',
    p_cidades TEXT[] DEFAULT ARRAY['SAO PAULO', 'SANTOS', 'GUARUJA', 'PRAIA GRANDE', 'SAO VICENTE']
)
RETURNS TABLE (
    id UUID,
    id_imovel VARCHAR,
    endereco TEXT,
    bairro VARCHAR,
    cidade VARCHAR,
    preco DECIMAL,
    desconto DECIMAL,
    tipo_imovel VARCHAR,
    link TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        i.id_imovel,
        i.endereco,
        i.bairro,
        i.cidade,
        i.preco,
        i.desconto,
        i.tipo_imovel,
        i.link
    FROM imoveis_caixa i
    WHERE i.ativo = TRUE
        AND i.preco <= p_preco_max
        AND i.tipo_imovel = p_tipo
        AND i.praca = p_praca
        AND i.cidade = ANY(p_cidades)
    ORDER BY i.desconto DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- RLS (Row Level Security)
-- =====================================================

-- Habilita RLS nas tabelas principais
ALTER TABLE imoveis_caixa ENABLE ROW LEVEL SECURITY;
ALTER TABLE analises_finais ENABLE ROW LEVEL SECURITY;
ALTER TABLE alertas_enviados ENABLE ROW LEVEL SECURITY;

-- Politica: Leitura publica para imoveis
CREATE POLICY "Imoveis leitura publica" ON imoveis_caixa
    FOR SELECT USING (true);

-- Politica: Analises leitura publica
CREATE POLICY "Analises leitura publica" ON analises_finais
    FOR SELECT USING (true);

-- =====================================================
-- DADOS INICIAIS
-- =====================================================

-- Insere registro de teste
INSERT INTO downloads_csv (estado, filename, status, total_imoveis)
VALUES ('SP', 'Lista_imoveis_SP.csv', 'pendente', 0)
ON CONFLICT DO NOTHING;

-- =====================================================
-- GRANTS
-- =====================================================

-- Para o service_role (backend)
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Para anon (frontend readonly)
GRANT SELECT ON v_oportunidades TO anon;
GRANT SELECT ON v_resumo_cidades TO anon;
GRANT SELECT ON imoveis_caixa TO anon;
GRANT SELECT ON analises_finais TO anon;
