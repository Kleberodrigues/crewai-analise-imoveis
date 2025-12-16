"""
Testes de integração com Supabase
"""

import pytest
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

@pytest.fixture
def supabase_client():
    """Fixture para cliente Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        pytest.skip("SUPABASE_URL/SUPABASE_SERVICE_KEY não configurados")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def test_supabase_connection(supabase_client):
    """Testa conexão com Supabase"""
    # Tentar buscar 1 imóvel
    result = supabase_client.table('imoveis_leilao').select("*").limit(1).execute()
    assert result.data is not None

def test_buscar_imoveis_disponiveis(supabase_client):
    """Testa busca de imóveis disponíveis"""
    result = supabase_client.table('imoveis_leilao').select("*").eq('situacao', 'disponivel').limit(10).execute()

    assert result.data is not None
    assert len(result.data) > 0
    assert all(imovel['situacao'] == 'disponivel' for imovel in result.data)

def test_buscar_imoveis_por_cidade(supabase_client):
    """Testa busca de imóveis por cidade"""
    result = supabase_client.table('imoveis_leilao').select("*").ilike('cidade', '%São Paulo%').limit(10).execute()

    assert result.data is not None
    # Pode não ter resultados se não houver imóveis em São Paulo

def test_buscar_imoveis_por_faixa_preco(supabase_client):
    """Testa busca de imóveis por faixa de preço"""
    result = supabase_client.table('imoveis_leilao').select("*").lte('valor_minimo', 150000).limit(10).execute()

    assert result.data is not None
    if len(result.data) > 0:
        assert all(imovel['valor_minimo'] <= 150000 for imovel in result.data)

def test_schema_imoveis_leilao(supabase_client):
    """Testa schema da tabela imoveis_leilao"""
    result = supabase_client.table('imoveis_leilao').select("*").limit(1).execute()

    if len(result.data) > 0:
        imovel = result.data[0]
        # Verificar campos essenciais
        assert 'id' in imovel
        assert 'codigo_imovel' in imovel
        assert 'endereco' in imovel
        assert 'cidade' in imovel
        assert 'valor_minimo' in imovel
        assert 'tipo_imovel' in imovel

def test_criar_e_deletar_analise(supabase_client):
    """Testa criação e deleção de análise"""
    # Buscar um imóvel para testar
    imoveis = supabase_client.table('imoveis_leilao').select("id").limit(1).execute()

    if len(imoveis.data) == 0:
        pytest.skip("Nenhum imóvel disponível para teste")

    imovel_id = imoveis.data[0]['id']

    # Criar análise de teste
    analise_data = {
        'imovel_id': imovel_id,
        'status': 'processando',
        'score_geral': 0
    }

    insert_result = supabase_client.table('analises_viabilidade').insert(analise_data).execute()

    assert insert_result.data is not None
    assert len(insert_result.data) > 0

    analise_id = insert_result.data[0]['id']

    # Deletar análise de teste
    delete_result = supabase_client.table('analises_viabilidade').delete().eq('id', analise_id).execute()

    assert delete_result.data is not None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
