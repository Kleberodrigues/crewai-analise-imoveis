-- ============================================
-- Tabela para registrar execucoes do pipeline
-- ============================================

CREATE TABLE IF NOT EXISTS public.pipeline_execucoes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    data_execucao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) NOT NULL,
    total_analisados INTEGER DEFAULT 0,
    top5_selecionados INTEGER DEFAULT 0,
    recomendados INTEGER DEFAULT 0,
    arquivo_csv TEXT,
    arquivo_pdf TEXT,
    resumo_json JSONB,
    erro TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indice para busca por data
CREATE INDEX IF NOT EXISTS idx_pipeline_execucoes_data
ON public.pipeline_execucoes(data_execucao DESC);

-- Indice para busca por status
CREATE INDEX IF NOT EXISTS idx_pipeline_execucoes_status
ON public.pipeline_execucoes(status);

-- RLS (Row Level Security)
ALTER TABLE public.pipeline_execucoes ENABLE ROW LEVEL SECURITY;

-- Politica de leitura publica
DROP POLICY IF EXISTS "Permitir leitura publica" ON public.pipeline_execucoes;
CREATE POLICY "Permitir leitura publica" ON public.pipeline_execucoes
    FOR SELECT USING (true);

-- Politica de insercao
DROP POLICY IF EXISTS "Permitir insercao" ON public.pipeline_execucoes;
CREATE POLICY "Permitir insercao" ON public.pipeline_execucoes
    FOR INSERT WITH CHECK (true);
