"""
API FastAPI para análise de imóveis de leilão usando CrewAI
Sistema com 5 agentes especializados hierárquicos
"""

import os
import time
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from supabase import create_client, Client
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da aplicação
app = FastAPI(title="CrewAI Análise de Imóveis", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pxymmcmksyekkjptqblp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuração LLM
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Models
class ImovelData(BaseModel):
    id: str | None = None
    codigo_imovel: str | None = None
    endereco: str
    bairro: str | None = None
    cidade: str
    estado: str | None = "SP"
    regiao_sp: str | None = None
    zona_sp: str | None = None
    tipo_imovel: str | None = None
    area_total: float | None = None
    quartos: int | None = None
    banheiros: int | None = None
    valor_avaliacao: float | None = None
    valor_minimo: float
    tipo_leilao: str | None = None
    link_edital: str | None = None
    observacoes: str | None = None
    situacao: str | None = "disponivel"

# Copiar todas as funções de agentes e tasks do main.py original aqui
# (criar_analista_financeiro, criar_analista_localizacao, etc.)

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "crewai-analise-imoveis",
        "version": "1.0.0",
        "endpoints": ["/healthz", "/health", "/analisar"]
    }

@app.get("/healthz")
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"ok": True, "status": "healthy"}

@app.post("/analisar")
async def analisar_imovel(dados_imovel: ImovelData):
    """
    Endpoint principal: recebe dados do imóvel e retorna análise completa
    """
    try:
        tempo_inicio = time.time()
        logger.info(f"Iniciando análise do imóvel: {dados_imovel.codigo_imovel}")

        # Converter para dict
        dados_dict = dados_imovel.dict()

        # Criar e executar Crew
        # TODO: Implementar lógica do CrewAI aqui
        # crew = criar_crew_analise(dados_dict)
        # resultado = crew.kickoff()

        # Mock temporário
        resultado = {
            "score_geral": 75,
            "recomendacao": "analisar_melhor",
            "justificativa_ia": "Análise em desenvolvimento"
        }

        tempo_fim = time.time()
        tempo_processamento = int(tempo_fim - tempo_inicio)

        logger.info(f"Análise concluída em {tempo_processamento}s")

        resposta = {
            "imovel_id": dados_imovel.id,
            "codigo_imovel": dados_imovel.codigo_imovel,
            "status": "concluido",
            "tempo_processamento_segundos": tempo_processamento,
            "analise": resultado
        }

        return resposta

    except Exception as e:
        logger.error(f"Erro ao processar análise: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
