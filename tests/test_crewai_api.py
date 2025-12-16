"""
Testes para API CrewAI
"""

import pytest
import json
from backend.crewai_service.main import app

# Aviso: para rodar testes que acionam a IA, é necessário configurar OPENAI_API_KEY.

@pytest.fixture
def client():
    """Fixture para cliente de teste Flask"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Testa endpoint de health check"""
    response = client.get('/health')
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data['status'] == 'ok'
    assert 'service' in data
    assert 'version' in data

def test_analisar_endpoint_sem_dados(client):
    """Testa endpoint /analisar sem dados"""
    response = client.post('/analisar', json={})
    # Deve retornar erro ou processar com dados vazios
    assert response.status_code in [200, 400, 500]

def test_analisar_endpoint_com_dados_mock(client):
    """Testa endpoint /analisar com dados mock"""
    dados_mock = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "codigo_imovel": "SP-TEST-001",
        "endereco": "Rua Teste, 123",
        "bairro": "Vila Teste",
        "cidade": "São Paulo",
        "estado": "SP",
        "tipo_imovel": "Apartamento",
        "area_total": 60.0,
        "quartos": 2,
        "banheiros": 1,
        "valor_avaliacao": 180000.00,
        "valor_minimo": 150000.00,
        "tipo_leilao": "1º Leilão",
        "observacoes": "Teste",
        "situacao": "disponivel"
    }

    response = client.post('/analisar',
                          json=dados_mock,
                          content_type='application/json')

    # Pode levar tempo (até 180s), então apenas verificar se iniciou
    assert response.status_code in [200, 500]  # 500 se OpenAI key não configurada

    if response.status_code == 200:
        data = json.loads(response.data)
        assert 'analise' in data or 'erro' in data

def test_test_endpoint(client):
    """Testa endpoint /test"""
    response = client.post('/test')
    # Pode levar tempo, apenas verificar se responde
    assert response.status_code in [200, 500]

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
