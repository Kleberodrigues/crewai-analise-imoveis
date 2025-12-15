"""
API Flask para análise de imóveis de leilão usando CrewAI
Sistema com 5 agentes especializados hierárquicos
"""

import os
import time
from typing import Dict, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from supabase import create_client, Client
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da aplicação
app = Flask(__name__)
# CORS: permitir configurar origens via env (CORS_ALLOWED_ORIGINS="http://localhost:3000,https://app.example.com")
_allowed = os.getenv("CORS_ALLOWED_ORIGINS")
if _allowed:
    _origins = [o.strip() for o in _allowed.split(',') if o.strip()]
    CORS(app, resources={r"/*": {"origins": _origins}})
else:
    CORS(app)

# Configuração Supabase (com validação de DNS)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = None

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.warning("SUPABASE_URL/SUPABASE_SERVICE_KEY não configurados. API funcionará sem persistência.")
else:
    try:
        import socket
        host = SUPABASE_URL.replace("https://", "").replace("http://", "").split("/")[0]
        socket.setdefaulttimeout(5)
        socket.getaddrinfo(host, 443)
        socket.setdefaulttimeout(None)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Supabase conectado com sucesso")
    except socket.gaierror:
        logging.warning("Supabase DNS não resolvido - projeto pode estar pausado. API funcionará sem persistência.")
    except Exception as e:
        logging.warning(f"Supabase indisponível: {e}. API funcionará sem persistência.")

# Configuração LLM (lazy initialization para não quebrar o startup)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = None

def get_llm():
    """Retorna o LLM, inicializando se necessário"""
    global llm
    if llm is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não configurada")
        llm = ChatOpenAI(model="gpt-4o", temperature=0.2, api_key=OPENAI_API_KEY)
    return llm

# Segurança e controle
API_TOKEN = os.getenv("CREWAI_API_TOKEN")  # Se definido, exige header x-api-key
MAX_BODY_KB = int(os.getenv("MAX_BODY_KB", "256"))
DEBUG_SAFE_ERRORS = os.getenv("CREWAI_DEBUG", "0").lower() in ("1", "true", "yes")

@app.before_request
def _pre_checks():
    # Limitar tamanho do corpo
    cl = request.content_length or 0
    if cl > MAX_BODY_KB * 1024:
        return jsonify({"erro": "Payload muito grande"}), 413
    # Autenticação via token (opcional)
    if API_TOKEN and request.path in ("/analisar", "/test") and request.method in ("POST", "GET"):
        if request.headers.get("x-api-key") != API_TOKEN:
            return jsonify({"erro": "Não autorizado"}), 401

def _normalize_float(v, default=0.0):
    try:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.replace('.', '').replace(',', '.') if ',' in v else v
            return float(s)
        return float(default)
    except Exception:
        return float(default)

def _normalize_result(res):
    import json as _json
    if isinstance(res, str):
        try:
            res = _json.loads(res)
        except Exception:
            res = {"justificativa_ia": res}
    if not isinstance(res, dict):
        res = {}
    out = dict(res)
    numeric_keys = [
        "valor_arrematacao","custo_desocupacao","comissao_leiloeiro","itbi","escritura_registro",
        "taxas_cartoriais","honorarios_advocaticios","total_custos_diretos","iptu_mensal","condominio_mensal",
        "custo_reforma","custos_totais","preco_venda_estimado","comissao_corretor","aluguel_estimado_mensal",
        "lucro_bruto","imposto_renda_lucro","lucro_liquido","roi_percentual","score_geral","score_localizacao",
        "analise_edital_score","analise_matricula_score"
    ]
    for k in numeric_keys:
        if k in out:
            out[k] = _normalize_float(out.get(k, 0.0))
    list_keys = ["pontos_atencao","proximos_passos","analise_edital_riscos","analise_matricula_gravames"]
    for k in list_keys:
        v = out.get(k)
        if v is None:
            out[k] = []
        elif not isinstance(v, list):
            out[k] = [str(v)]
    text_keys = ["justificativa_ia","analise_edital_resumo","analise_matricula_resumo","analise_localizacao_sp"]
    for k in text_keys:
        if k in out and out[k] is not None:
            out[k] = str(out[k])
    rec = str(out.get("recomendacao", "analisar_melhor")).lower()
    if rec not in ("comprar","analisar_melhor","evitar"):
        rec = "analisar_melhor"
    out["recomendacao"] = rec
    return out

# ==================== AGENTES ====================

def criar_analista_financeiro() -> Agent:
    """Agente 1: Analista Financeiro de Imóveis até 200k em SP"""
    return Agent(
        role="Analista Financeiro de Imóveis até 200k em SP",
        goal="Calcular todos os custos diretos e indiretos, impostos, reformas e projetar ROI realista",
        backstory="""Você é um analista financeiro especializado em imóveis de leilão em São Paulo
        com 15 anos de experiência. Você conhece profundamente todos os custos envolvidos em
        arrematação de imóveis: ITBI (2-3% do valor), escritura, registro, taxas cartoriais,
        comissão do leiloeiro (5%), custos de desocupação (R$5.000-R$15.000), honorários
        advocatícios (R$3.000-R$8.000), e custos de reforma média por m² em SP.

        Você também sabe estimar valores de mercado e aluguel baseado na região e tipo de imóvel.
        Seu foco é entregar uma análise financeira conservadora e realista.""",
        verbose=True,
        llm=get_llm(),
        allow_delegation=False
    )

def criar_analista_localizacao() -> Agent:
    """Agente 2: Especialista em Regiões de São Paulo"""
    return Agent(
        role="Especialista em Regiões de São Paulo",
        goal="Avaliar a qualidade da localização, potencial de valorização e liquidez do imóvel",
        backstory="""Você é um corretor de imóveis com 15 anos de atuação em São Paulo,
        conhecendo profundamente todas as regiões da capital e interior. Você sabe avaliar:

        - Zonas de SP (Norte, Sul, Leste, Oeste, Centro): características, valorização, segurança
        - Bairros específicos: infraestrutura, transporte público, comércio, escolas
        - Potencial de valorização nos próximos 5 anos
        - Liquidez do imóvel (facilidade de venda/aluguel)
        - Comparativo de preços por região

        Você atribui um score de 0-100 baseado em critérios objetivos de localização.""",
        verbose=True,
        llm=get_llm(),
        allow_delegation=False
    )

def criar_analista_juridico() -> Agent:
    """Agente 3: Advogado Especialista em Leilões"""
    return Agent(
        role="Advogado Especialista em Leilões da Caixa",
        goal="Analisar edital do leilão, identificar riscos jurídicos e cláusulas importantes",
        backstory="""Você é um advogado especializado em leilões judiciais e extrajudiciais
        com 12 anos de experiência em arrematação de imóveis da Caixa Econômica Federal em SP.

        Você sabe identificar:
        - Riscos de ocupação (imóvel ocupado, desocupado, comercial)
        - Cláusulas restritivas no edital
        - Débitos que serão transferidos ao arrematante
        - Prazos e condições de pagamento
        - Necessidade de ação de imissão de posse
        - Riscos de ação judicial posterior

        Você atribui um score de 0-100 ao edital, onde 100 = muito seguro e 0 = evitar.""",
        verbose=True,
        llm=get_llm(),
        allow_delegation=False
    )

def criar_analista_matricula() -> Agent:
    """Agente 4: Registrador Imobiliário"""
    return Agent(
        role="Registrador Imobiliário Especialista em Análise de Matrículas",
        goal="Analisar matrícula do imóvel, identificar gravames, penhoras e irregularidades",
        backstory="""Você é um registrador de imóveis com 10 anos de experiência em análise
        de matrículas e certidões. Você sabe identificar:

        - Gravames: hipotecas, penhoras, usufrutos, servidões
        - Irregularidades: metragem divergente, construções não averbadas
        - Histórico de propriedade: sucessões, transmissões anteriores
        - Débitos condominiais e IPTU em atraso
        - Situação jurídica atual do imóvel

        Você classifica os gravames como: eliminados no leilão, transferidos ao arrematante,
        ou que exigem ação judicial. Score de 0-100, onde 100 = matrícula limpa.""",
        verbose=True,
        llm=get_llm(),
        allow_delegation=False
    )

def criar_revisor_senior() -> Agent:
    """Agente 5: Investidor Imobiliário Sênior (Revisor Final)"""
    return Agent(
        role="Investidor Imobiliário Sênior",
        goal="Revisar todas as análises e dar recomendação final consolidada",
        backstory="""Você é um investidor imobiliário com 20 anos de experiência e mais de
        200 imóveis arrematados em leilões. Você já ganhou e perdeu dinheiro em leilões e
        sabe exatamente o que funciona e o que não funciona.

        Você recebe as análises dos 4 especialistas (financeiro, localização, jurídico, matrícula)
        e consolida tudo em uma recomendação final objetiva:

        - COMPRAR: Excelente oportunidade, baixo risco, bom retorno
        - ANALISAR MELHOR: Potencial interessante mas precisa validação adicional
        - EVITAR: Alto risco, retorno questionável, problemas identificados

        Você atribui um score geral de 0-100 e lista claramente:
        - Justificativa da recomendação
        - Pontos de atenção principais
        - Próximos passos práticos
        - Comparação com Tesouro Direto e CDB

        Seu objetivo é proteger o investidor de más decisões e destacar as boas oportunidades.""",
        verbose=True,
        llm=get_llm(),
        allow_delegation=True
    )

# ==================== TASKS ====================

def criar_task_analise_financeira(agent: Agent, dados_imovel: Dict) -> Task:
    """Task para análise financeira completa"""
    return Task(
        description=f"""Analise financeiramente este imóvel de leilão:

**DADOS DO IMÓVEL:**
- Código: {dados_imovel.get('codigo_imovel')}
- Endereço: {dados_imovel.get('endereco')}, {dados_imovel.get('bairro')}
- Cidade: {dados_imovel.get('cidade')} - {dados_imovel.get('estado')}
- Tipo: {dados_imovel.get('tipo_imovel')}
- Área Total: {dados_imovel.get('area_total')} m²
- Quartos: {dados_imovel.get('quartos')} | Banheiros: {dados_imovel.get('banheiros')}
- Valor de Avaliação: R$ {dados_imovel.get('valor_avaliacao'):,.2f}
- Valor Mínimo (Lance): R$ {dados_imovel.get('valor_minimo'):,.2f}
- Tipo de Leilão: {dados_imovel.get('tipo_leilao')}
- Observações: {dados_imovel.get('observacoes')}

**SUA TAREFA:**
1. Calcular TODOS os custos diretos:
   - ITBI (2-3% do valor de arrematação)
   - Escritura e Registro (R$ 2.000 - R$ 4.000)
   - Taxas Cartoriais (R$ 500 - R$ 1.500)
   - Comissão do Leiloeiro (5% do valor de arrematação)
   - Custos de Desocupação (se aplicável: R$ 5.000 - R$ 15.000)
   - Honorários Advocatícios (R$ 3.000 - R$ 8.000)

2. Estimar custos mensais:
   - IPTU mensal estimado
   - Condomínio mensal (se aplicável)
   - Custo de reforma (R$/m² * área)

3. Estimar valores de mercado:
   - Preço de venda estimado (após reforma)
   - Comissão de corretor (6% do preço de venda)
   - Aluguel mensal estimado

4. Calcular retorno financeiro:
   - Lucro Bruto = Preço Venda - (Arrematação + Custos Totais)
   - Imposto de Renda sobre Lucro (15-22.5%)
   - Lucro Líquido
   - ROI Percentual = (Lucro Líquido / Investimento Total) * 100

**FORMATO DE SAÍDA (JSON):**
{{
    "valor_arrematacao": float,
    "custo_desocupacao": float,
    "comissao_leiloeiro": float,
    "itbi": float,
    "escritura_registro": float,
    "taxas_cartoriais": float,
    "honorarios_advocaticios": float,
    "total_custos_diretos": float,
    "iptu_mensal": float,
    "condominio_mensal": float,
    "custo_reforma": float,
    "custos_totais": float,
    "preco_venda_estimado": float,
    "comissao_corretor": float,
    "aluguel_estimado_mensal": float,
    "lucro_bruto": float,
    "imposto_renda_lucro": float,
    "lucro_liquido": float,
    "roi_percentual": float
}}

Seja conservador nas estimativas. É melhor subestimar ganhos e superestimar custos.""",
        agent=agent,
        expected_output="JSON estruturado com todos os campos financeiros calculados"
    )

def criar_task_analise_localizacao(agent: Agent, dados_imovel: Dict) -> Task:
    """Task para análise de localização"""
    return Task(
        description=f"""Avalie a localização deste imóvel em São Paulo:

**LOCALIZAÇÃO:**
- Endereço: {dados_imovel.get('endereco')}
- Bairro: {dados_imovel.get('bairro')}
- Cidade: {dados_imovel.get('cidade')}
- Região SP: {dados_imovel.get('regiao_sp')}
- Zona SP: {dados_imovel.get('zona_sp')}
- Tipo: {dados_imovel.get('tipo_imovel')}

**SUA TAREFA:**
1. Avaliar a região/bairro considerando:
   - Infraestrutura (transporte, comércio, escolas, hospitais)
   - Segurança e qualidade de vida
   - Potencial de valorização nos próximos 5 anos
   - Liquidez (facilidade de venda/aluguel)
   - Comparativo com outras regiões de SP

2. Atribuir score de 0-100:
   - 90-100: Excelente localização (Zona Sul, Oeste, bairros nobres)
   - 70-89: Boa localização (regiões consolidadas)
   - 50-69: Localização mediana (em desenvolvimento)
   - 30-49: Localização desafiadora (afastada, infraestrutura limitada)
   - 0-29: Localização ruim (evitar)

**FORMATO DE SAÍDA (JSON):**
{{
    "score_localizacao": int (0-100),
    "analise_localizacao_sp": "Texto detalhado sobre a região, pontos fortes e fracos, potencial de valorização"
}}

Seja realista e considere o perfil do investidor iniciante.""",
        agent=agent,
        expected_output="JSON com score de localização e análise textual"
    )

def criar_task_analise_juridica(agent: Agent, dados_imovel: Dict) -> Task:
    """Task para análise jurídica do edital"""
    return Task(
        description=f"""Analise os aspectos jurídicos deste leilão:

**DADOS DO LEILÃO:**
- Código: {dados_imovel.get('codigo_imovel')}
- Tipo de Leilão: {dados_imovel.get('tipo_leilao')}
- Link Edital: {dados_imovel.get('link_edital')}
- Observações: {dados_imovel.get('observacoes')}
- Situação: {dados_imovel.get('situacao')}

**SUA TAREFA:**
1. Analisar os principais riscos jurídicos:
   - Status de ocupação (ocupado/desocupado)
   - Débitos que serão transferidos
   - Necessidade de ação de imissão de posse
   - Cláusulas restritivas
   - Prazos e condições

2. Identificar riscos específicos:
   - Alto risco: problemas graves que podem inviabilizar
   - Médio risco: requerem atenção mas são gerenciáveis
   - Baixo risco: questões menores

3. Atribuir score de 0-100:
   - 90-100: Edital muito seguro, baixo risco jurídico
   - 70-89: Edital bom, riscos gerenciáveis
   - 50-69: Edital mediano, atenção necessária
   - 30-49: Edital com riscos significativos
   - 0-29: Edital problemático, evitar

**FORMATO DE SAÍDA (JSON):**
{{
    "analise_edital_score": int (0-100),
    "analise_edital_resumo": "Resumo dos principais pontos do edital",
    "analise_edital_riscos": ["risco 1", "risco 2", "risco 3"]
}}

Base sua análise nas observações disponíveis e em padrões comuns de leilões da Caixa.""",
        agent=agent,
        expected_output="JSON com score do edital, resumo e lista de riscos"
    )

def criar_task_analise_matricula(agent: Agent, dados_imovel: Dict) -> Task:
    """Task para análise de matrícula"""
    return Task(
        description=f"""Analise a situação registral deste imóvel:

**IMÓVEL:**
- Código: {dados_imovel.get('codigo_imovel')}
- Endereço: {dados_imovel.get('endereco')}, {dados_imovel.get('bairro')}
- Observações: {dados_imovel.get('observacoes')}

**SUA TAREFA:**
1. Identificar possíveis gravames:
   - Hipotecas (geralmente extintas no leilão)
   - Penhoras
   - Usufrutos
   - Servidões
   - Débitos condominiais

2. Avaliar regularidade:
   - Área construída vs. registrada
   - Situação cadastral
   - Histórico de propriedade

3. Classificar gravames:
   - Extintos no leilão (não são problema)
   - Transferidos ao arrematante (custo adicional)
   - Requerem ação judicial (alto risco)

4. Atribuir score de 0-100:
   - 90-100: Matrícula limpa, sem pendências
   - 70-89: Matrícula boa, pequenos gravames extintos no leilão
   - 50-69: Matrícula com pendências médias
   - 30-49: Matrícula com problemas significativos
   - 0-29: Matrícula problemática, evitar

**FORMATO DE SAÍDA (JSON):**
{{
    "analise_matricula_score": int (0-100),
    "analise_matricula_resumo": "Resumo da situação registral",
    "analise_matricula_gravames": ["gravame 1", "gravame 2"]
}}

Como não temos acesso à matrícula real, baseie-se nas observações e em padrões comuns.""",
        agent=agent,
        expected_output="JSON com score da matrícula, resumo e lista de gravames"
    )

def criar_task_revisao_final(agent: Agent, dados_imovel: Dict) -> Task:
    """Task para revisão final e recomendação"""
    return Task(
        description=f"""Você recebeu as análises de 4 especialistas sobre este imóvel:

**IMÓVEL:**
- {dados_imovel.get('endereco')}, {dados_imovel.get('bairro')} - {dados_imovel.get('cidade')}
- Tipo: {dados_imovel.get('tipo_imovel')}
- Valor Mínimo: R$ {dados_imovel.get('valor_minimo'):,.2f}

**ANÁLISES RECEBIDAS:**
- Análise Financeira (ROI, custos, retorno)
- Análise de Localização (score, potencial)
- Análise Jurídica (riscos do edital)
- Análise de Matrícula (gravames)

**SUA TAREFA:**
1. Consolidar todas as análises em uma visão única

2. Calcular score geral ponderado (0-100):
   - 30% Análise Financeira (ROI)
   - 25% Localização
   - 25% Jurídica (Edital)
   - 20% Matrícula

3. Dar recomendação final:
   - "comprar": Score geral ≥ 70, baixo risco, bom retorno
   - "analisar_melhor": Score 50-69, potencial mas precisa validação
   - "evitar": Score < 50, alto risco ou baixo retorno

4. Criar comparativo com investimentos conservadores:
   - Tesouro Direto (≈10-12% a.a.)
   - CDB (≈12-14% a.a.)

5. Listar claramente:
   - Justificativa da recomendação (2-3 parágrafos)
   - 3-5 pontos de atenção principais
   - 3-5 próximos passos práticos

**FORMATO DE SAÍDA (JSON):**
{{
    "score_geral": int (0-100),
    "recomendacao": "comprar|analisar_melhor|evitar",
    "justificativa_ia": "Texto explicativo da recomendação",
    "pontos_atencao": ["ponto 1", "ponto 2", "ponto 3"],
    "proximos_passos": ["passo 1", "passo 2", "passo 3"],
    "comparacao_tesouro_direto": {{
        "rentabilidade_tesouro_aa": 11.0,
        "rentabilidade_imovel_roi": float,
        "diferenca_percentual": float,
        "analise": "texto comparativo"
    }},
    "comparacao_cdb": {{
        "rentabilidade_cdb_aa": 13.0,
        "rentabilidade_imovel_roi": float,
        "diferenca_percentual": float,
        "analise": "texto comparativo"
    }}
}}

Seja honesto e objetivo. Proteja o investidor de más decisões.""",
        agent=agent,
        expected_output="JSON com recomendação final consolidada",
        context=[
            criar_task_analise_financeira(criar_analista_financeiro(), dados_imovel),
            criar_task_analise_localizacao(criar_analista_localizacao(), dados_imovel),
            criar_task_analise_juridica(criar_analista_juridico(), dados_imovel),
            criar_task_analise_matricula(criar_analista_matricula(), dados_imovel)
        ]
    )

# ==================== CREW ====================

def criar_crew_analise(dados_imovel: Dict) -> Crew:
    """Cria o Crew com todos os agentes e tasks"""

    # Criar agentes
    analista_financeiro = criar_analista_financeiro()
    analista_localizacao = criar_analista_localizacao()
    analista_juridico = criar_analista_juridico()
    analista_matricula = criar_analista_matricula()
    revisor_senior = criar_revisor_senior()

    # Criar tasks
    task_financeira = criar_task_analise_financeira(analista_financeiro, dados_imovel)
    task_localizacao = criar_task_analise_localizacao(analista_localizacao, dados_imovel)
    task_juridica = criar_task_analise_juridica(analista_juridico, dados_imovel)
    task_matricula = criar_task_analise_matricula(analista_matricula, dados_imovel)
    task_revisao = criar_task_revisao_final(revisor_senior, dados_imovel)

    # Criar Crew hierárquico
    crew = Crew(
        agents=[
            analista_financeiro,
            analista_localizacao,
            analista_juridico,
            analista_matricula,
            revisor_senior
        ],
        tasks=[
            task_financeira,
            task_localizacao,
            task_juridica,
            task_matricula,
            task_revisao
        ],
        process=Process.hierarchical,
        manager_llm=get_llm(),
        verbose=True
    )

    return crew

# ==================== API ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "crewai-analise-imoveis",
        "version": "1.0.0"
    })

@app.route('/analisar', methods=['POST'])
def analisar_imovel():
    """
    Endpoint principal: recebe dados do imóvel e retorna análise completa

    Body esperado:
    {
        "codigo_imovel": "SP-12345",
        "endereco": "Rua X, 123",
        ... (todos os campos do imóvel)
    }
    """
    try:
        tempo_inicio = time.time()

        # Validar request
        dados_imovel = request.get_json()
        if not dados_imovel:
            return jsonify({"erro": "Dados do imóvel não fornecidos"}), 400

        logger.info(f"Iniciando análise do imóvel: {dados_imovel.get('codigo_imovel')}")

        # Criar e executar Crew
        crew = criar_crew_analise(dados_imovel)
        resultado = crew.kickoff()
        resultado = _normalize_result(resultado)

        # Processar resultado
        tempo_fim = time.time()
        tempo_processamento = int(tempo_fim - tempo_inicio)

        logger.info(f"Análise concluída em {tempo_processamento}s")

        # Estruturar resposta
        resposta = {
            "imovel_id": dados_imovel.get("id"),
            "codigo_imovel": dados_imovel.get("codigo_imovel"),
            "status": "concluido",
            "tempo_processamento_segundos": tempo_processamento,
            "analise": resultado
        }

        return jsonify(resposta), 200

    except Exception as e:
        logger.error(f"Erro ao processar análise: {str(e)}")
        return jsonify({
            "erro": "Erro interno ao processar análise",
            "detalhes": str(e)
        }), 500

@app.route('/test', methods=['POST', 'GET'])
def test_analise():
    """Endpoint de teste com dados mock (não requer request body)"""
    dados_mock = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "codigo_imovel": "SP-TEST-001",
        "origem": "caixa",
        "endereco": "Rua Exemplo, 123",
        "bairro": "Vila Mariana",
        "cidade": "São Paulo",
        "estado": "SP",
        "regiao_sp": "capital",
        "zona_sp": "sul",
        "tipo_imovel": "Apartamento",
        "area_total": 65.0,
        "quartos": 2,
        "banheiros": 1,
        "valor_avaliacao": 180000.00,
        "valor_minimo": 150000.00,
        "tipo_leilao": "1º Leilão",
        "link_edital": "https://exemplo.com/edital",
        "observacoes": "Imóvel desocupado, em bom estado de conservação",
        "situacao": "disponivel"
    }

    try:
        tempo_inicio = time.time()
        crew = criar_crew_analise(dados_mock)
        resultado = crew.kickoff()
        resultado = _normalize_result(resultado)
        tempo_fim = time.time()
        return jsonify({
            "imovel_id": dados_mock.get("id"),
            "codigo_imovel": dados_mock.get("codigo_imovel"),
            "status": "concluido",
            "tempo_processamento_segundos": int(tempo_fim - tempo_inicio),
            "analise": resultado
        }), 200
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        body = {"erro": "Falha ao executar teste"}
        if DEBUG_SAFE_ERRORS:
            body["detalhes"] = str(e)
        return jsonify(body), 500

# ==================== PIPELINE ENDPOINTS ====================

def _gerar_links_pesquisa_mercado(cidade: str, bairro: str, tipo: str = "apartamento") -> dict:
    """
    Gera links de busca para pesquisa de mercado em portais imobiliários.
    """
    from urllib.parse import quote

    cidade_slug = cidade.lower().replace(" ", "-").replace("sao", "sao")
    bairro_slug = bairro.lower().replace(" ", "-") if bairro else ""

    # Mapeamento de cidades para slugs dos portais
    cidade_map = {
        "SAO PAULO": "sao-paulo",
        "SANTOS": "santos",
        "GUARUJA": "guaruja",
        "PRAIA GRANDE": "praia-grande",
        "SAO VICENTE": "sao-vicente"
    }
    cidade_portal = cidade_map.get(cidade.upper(), cidade_slug)

    return {
        "zapimoveis": f"https://www.zapimoveis.com.br/venda/apartamentos/sp+{cidade_portal}+{bairro_slug}/",
        "vivareal": f"https://www.vivareal.com.br/venda/sp/{cidade_portal}/{bairro_slug}/apartamento_residencial/",
        "quintoandar": f"https://www.quintoandar.com.br/comprar/imovel/{cidade_portal}-sp-brasil/",
        "imovelweb": f"https://www.imovelweb.com.br/apartamentos-venda-{bairro_slug}-{cidade_portal}.html"
    }


def _formatar_detalhe_imovel(ranking: int, imovel: dict) -> str:
    """
    Formata detalhes completos de um imóvel para email.
    Inclui todos os 9 itens solicitados + links de fontes para validação humana.
    """
    # Dados básicos
    id_imovel = str(imovel.get("id_imovel", "N/A")).strip()
    endereco = imovel.get("endereco", "N/A")
    bairro = imovel.get("bairro", "N/A")
    cidade = imovel.get("cidade", "SP")
    preco = imovel.get("preco", 0)
    desconto = imovel.get("desconto", 0)
    link_caixa = imovel.get("link", "")
    tipo_imovel = imovel.get("tipo_imovel", "Apartamento")
    area = imovel.get("area_privativa", 0)
    quartos = imovel.get("quartos", 0)

    # Dados de custos
    custos = imovel.get("custos", {})
    custos_aquisicao = custos.get("custos_aquisicao", {})
    custos_venda = custos.get("custos_venda", {})
    resultado = custos.get("resultado_venda", {})
    investimento_total = custos.get("investimento_total_com_manutencao", 0)

    # Dados de mercado
    mercado = imovel.get("pesquisa_mercado", {})
    preco_m2 = mercado.get("preco_m2", 0)
    condominio = mercado.get("condominio_mensal", 0)
    similares = mercado.get("imoveis_similares", [])
    fonte_mercado = mercado.get("fonte", "base_regional")
    confianca = mercado.get("confianca", "media")

    # Dados da matrícula
    matricula = imovel.get("analise_matricula", {})
    valor_gravames = matricula.get("valor_gravames", 0)
    gravames_extintos = matricula.get("gravames_extintos", [])
    gravames_transferidos = matricula.get("gravames_transferidos", [])

    # Dados do edital
    edital = imovel.get("analise_edital", {})
    ocupacao = edital.get("ocupacao", "desconhecido")
    debitos_iptu = edital.get("debitos_iptu", 0)
    debitos_condo = edital.get("debitos_condominio", 0)
    total_debitos = edital.get("total_debitos", 0)

    # Scores
    scores = imovel.get("scores", {})
    score_geral = scores.get("geral", 0)
    recomendacao = imovel.get("recomendacao", "N/A")
    nivel_risco = imovel.get("nivel_risco", "N/A")

    # ============ GERA LINKS DE FONTES PARA VALIDAÇÃO ============

    # Links de pesquisa de mercado (SEMPRE gerar)
    links_pesquisa = _gerar_links_pesquisa_mercado(cidade, bairro, tipo_imovel)

    # Formata links de imóveis similares encontrados
    links_similares = ""
    if similares:
        for i, sim in enumerate(similares[:3], 1):
            link_sim = sim.get("link", "")
            preco_sim = sim.get("preco", 0)
            area_sim = sim.get("area", 0)
            if link_sim:
                links_similares += f"      {i}. R$ {preco_sim:,.0f} ({area_sim}m²): {link_sim}\n"

    # Formata dívidas da matrícula
    dividas_matricula = ""
    if valor_gravames > 0:
        dividas_matricula = f"R$ {valor_gravames:,.2f} (ATIVO)"
    elif gravames_extintos:
        dividas_matricula = f"EXTINTOS: {', '.join(gravames_extintos[:3])}"
    elif gravames_transferidos:
        dividas_matricula = f"TRANSFERIDOS: {', '.join(gravames_transferidos[:2])}"
    else:
        dividas_matricula = "Nenhum gravame encontrado"

    return f"""
{'='*60}
🏠 #{ranking} - {endereco}
   📍 {bairro} - {cidade} | {tipo_imovel} {area}m² | {quartos} qto(s)
{'='*60}

🔗 LINKS PARA VALIDAÇÃO (CHECK HUMANO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📄 FICHA DO IMÓVEL (Caixa):
      {link_caixa}

   📋 EDITAL DO LEILÃO (mesmo link, aba "Edital"):
      {link_caixa}

   📜 MATRÍCULA: Solicitar no Cartório de Registro de Imóveis
      da comarca de {cidade}. Número do imóvel: {id_imovel}

📊 PESQUISAR VALOR DE MERCADO (faça sua própria pesquisa):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   🔍 ZapImóveis:
      {links_pesquisa['zapimoveis']}

   🔍 VivaReal:
      {links_pesquisa['vivareal']}

   🔍 QuintoAndar:
      {links_pesquisa['quintoandar']}

   🔍 ImovelWeb:
      {links_pesquisa['imovelweb']}

{'   📌 IMÓVEIS SIMILARES ENCONTRADOS:' if links_similares else ''}
{links_similares if links_similares else '      (Nenhum encontrado via API - use os links acima)'}

   💡 FONTE DOS DADOS: {fonte_mercado.upper()} (Confiança: {confianca.upper()})
   💡 Preço/m² usado: R$ {preco_m2:,.2f}

📋 DADOS DO IMÓVEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   • ID Caixa: {id_imovel}
   • Valor Leilão: R$ {preco:,.2f}
   • Desconto: {desconto:.1f}%
   • Área: {area}m²

💰 CUSTOS DE AQUISIÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   1️⃣ Comissão Leiloeiro (5%): R$ {custos_aquisicao.get('comissao_leiloeiro', 0):,.2f}
   2️⃣ Custos Cartório:
      • Escritura: R$ {custos_aquisicao.get('escritura', 0):,.2f}
      • Registro: R$ {custos_aquisicao.get('registro', 0):,.2f}
      • Certidões: R$ {custos_aquisicao.get('certidoes', 0):,.2f}
   3️⃣ ITBI ({3 if cidade.upper() == 'SAO PAULO' else 2}%): R$ {custos_aquisicao.get('itbi', 0):,.2f}
   • Honorários Advogado: R$ {custos_aquisicao.get('honorarios_advogado', 0):,.2f}
   • Custo Desocupação: R$ {custos_aquisicao.get('custo_desocupacao', 0):,.2f}
   • Débitos Edital: R$ {custos_aquisicao.get('debitos_edital', 0):,.2f}
   • Reforma Estimada: R$ {custos_aquisicao.get('custo_reforma', 0):,.2f}
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ▸ TOTAL INVESTIMENTO: R$ {investimento_total:,.2f}

📜 ANÁLISE DA MATRÍCULA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   6️⃣ Gravames/Dívidas: {dividas_matricula}
   • Score Matrícula: {scores.get('matricula', 0)}/100
   ⚠️ IMPORTANTE: Solicitar matrícula atualizada no cartório!

📄 DADOS DO EDITAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   7️⃣ Ocupação: {ocupacao.upper()}
   • Débitos IPTU: R$ {debitos_iptu:,.2f}
   • Débitos Condomínio: R$ {debitos_condo:,.2f}
   • Total Débitos: R$ {total_debitos:,.2f}
   5️⃣ Condomínio Mensal Estimado: R$ {condominio:,.2f}

💸 CUSTOS DE VENDA (cenário 6 meses)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   8️⃣ IRPF Ganho Capital: R$ {custos_venda.get('irpf', 0):,.2f}
   9️⃣ Comissão Corretor (6%): R$ {custos_venda.get('comissao_corretor', 0):,.2f}

📈 RESULTADO PROJETADO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   • Preço Venda Estimado: R$ {resultado.get('preco_venda', 0):,.2f}
   • Lucro Líquido: R$ {resultado.get('lucro_liquido', 0):,.2f}
   • ROI: {resultado.get('roi_total_percentual', 0):.1f}%
   • Margem Segurança: {resultado.get('margem_seguranca_percentual', 0):.1f}%

📊 COMPOSIÇÃO DO SCORE (como chegamos a {score_geral:.0f}/100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   FATOR        | SCORE | BASEADO EM (R$)              | PESO | CONTRIBUIÇÃO
   -------------|-------|------------------------------|------|-------------
   Edital       | {scores.get('edital', 0):5.1f} | Débitos: R$ {total_debitos:>10,.0f}     | 20%  | {scores.get('edital', 0) * 0.20:5.1f} pts
   Matrícula    | {scores.get('matricula', 0):5.1f} | Gravames: R$ {valor_gravames:>8,.0f}    | 20%  | {scores.get('matricula', 0) * 0.20:5.1f} pts
   Localização  | {scores.get('localizacao', 0):5.1f} | Preço/m²: R$ {preco_m2:>8,.0f}    | 25%  | {scores.get('localizacao', 0) * 0.25:5.1f} pts
   Financeiro   | {scores.get('financeiro', 0):5.1f} | Lucro: R$ {resultado.get('lucro_liquido', 0):>10,.0f}    | 25%  | {scores.get('financeiro', 0) * 0.25:5.1f} pts
   Liquidez     | {scores.get('liquidez', 0):5.1f} | Condo: R$ {condominio:>8,.0f}/mês  | 10%  | {scores.get('liquidez', 0) * 0.10:5.1f} pts
   -------------|-------|------------------------------|------|-------------
   TOTAL        |       |                              | 100% | {score_geral:5.1f} pts

   💡 Fatores com maior impacto: Localização (25%) e Financeiro (25%)
   ⚠️ Fator mais fraco: {'Edital' if scores.get('edital', 0) == min(scores.get('edital', 100), scores.get('matricula', 100), scores.get('localizacao', 100), scores.get('financeiro', 100), scores.get('liquidez', 100)) else 'Matrícula' if scores.get('matricula', 0) == min(scores.get('edital', 100), scores.get('matricula', 100), scores.get('localizacao', 100), scores.get('financeiro', 100), scores.get('liquidez', 100)) else 'Localização' if scores.get('localizacao', 0) == min(scores.get('edital', 100), scores.get('matricula', 100), scores.get('localizacao', 100), scores.get('financeiro', 100), scores.get('liquidez', 100)) else 'Financeiro' if scores.get('financeiro', 0) == min(scores.get('edital', 100), scores.get('matricula', 100), scores.get('localizacao', 100), scores.get('financeiro', 100), scores.get('liquidez', 100)) else 'Liquidez'} ({min(scores.get('edital', 100), scores.get('matricula', 100), scores.get('localizacao', 100), scores.get('financeiro', 100), scores.get('liquidez', 100)):.0f}/100)

🎯 SCORE: {score_geral:.0f}/100 | RISCO: {nivel_risco} | RECOMENDAÇÃO: {recomendacao}
"""


@app.route('/pipeline/executar', methods=['POST'])
def executar_pipeline():
    """
    Executa o pipeline completo de análise de imóveis de leilão.
    Coleta dados da Caixa, analisa e gera relatórios top 5.

    Parâmetros opcionais (JSON body):
    {
        "preco_max": 150000,
        "tipo": "Apartamento",
        "quantidade_top": 5
    }
    """
    try:
        from main_pipeline import PipelineLeilao
        import threading

        # Parâmetros opcionais
        params = request.get_json() or {}

        logger.info("Iniciando execução do pipeline via API...")

        # Executa o pipeline
        pipeline = PipelineLeilao()
        resultado = pipeline.executar()

        if resultado.get("status") == "success":
            stats = resultado.get("stats", {})
            top5_data = resultado.get("relatorios", {}).get("top5", {})
            top5_resumo = top5_data.get("resumo", {})
            estatisticas = top5_resumo.get("estatisticas", {})
            analises_completas = top5_data.get("analises_completas", [])

            # Gera detalhes formatados para cada imóvel
            detalhes_imoveis = ""
            for i, imovel in enumerate(analises_completas, 1):
                detalhes_imoveis += _formatar_detalhe_imovel(i, imovel)

            # Mensagem formatada para email com detalhes completos
            email_message = f"""🎉 Pipeline de Leilão executado com SUCESSO!

📊 RESUMO GERAL DA ANÁLISE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total analisados: {stats.get('total_analisado', 0)}
• Top 5 selecionados: {stats.get('top5_selecionados', 0)}
• Recomendados COMPRAR: {stats.get('recomendados', 0)}

📈 MÉDIAS DO TOP 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• ROI Médio: {estatisticas.get('roi_percentual', {}).get('media', 0):.1f}%
• Margem Segurança: {estatisticas.get('margem_seguranca_pct', {}).get('media', 0):.1f}%
• Desconto Médio: {estatisticas.get('desconto_pct', {}).get('media', 0):.1f}%
• Investimento Total: R$ {estatisticas.get('investimento_total', {}).get('total', 0):,.2f}

{'='*60}
📋 DETALHAMENTO COMPLETO DOS 5 MELHORES IMÓVEIS
{'='*60}
{detalhes_imoveis}

📥 DOWNLOAD DOS RELATÓRIOS COMPLETOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• PDF: https://n8n-crewai-leiloes.zq1zp2.easypanel.host/pipeline/download/pdf
• CSV: https://n8n-crewai-leiloes.zq1zp2.easypanel.host/pipeline/download/csv

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Gerado automaticamente pelo Pipeline de Análise de Leilões
"""

            return jsonify({
                "status": "success",
                "message": "Pipeline executado com sucesso",
                "email_message": email_message,
                "stats": stats,
                "relatorios": {
                    "csv_completo": resultado.get("relatorios", {}).get("csv", {}).get("filepath"),
                    "csv_resumo": resultado.get("relatorios", {}).get("summary", {}).get("filepath"),
                    "top5_csv": top5_data.get("csv", {}).get("filepath"),
                    "top5_pdf": top5_data.get("pdf", {}).get("filepath"),
                },
                "top5_resumo": top5_resumo,
                "top5_analises": analises_completas
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Erro na execução do pipeline",
                "error": resultado.get("error"),
                "stats": resultado.get("stats")
            }), 500

    except Exception as e:
        logger.error(f"Erro ao executar pipeline: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Erro interno ao executar pipeline",
            "error": str(e)
        }), 500


@app.route('/pipeline/status', methods=['GET'])
def pipeline_status():
    """Retorna informações sobre o último pipeline executado"""
    from pathlib import Path
    import glob

    output_dir = Path("./output")

    # Busca últimos arquivos top5
    top5_csvs = sorted(output_dir.glob("top5_oportunidades_*.csv"), reverse=True)
    top5_pdfs = sorted(output_dir.glob("top5_oportunidades_*.pdf"), reverse=True)

    return jsonify({
        "status": "ok",
        "output_dir": str(output_dir.absolute()),
        "ultimos_relatorios": {
            "top5_csv": str(top5_csvs[0]) if top5_csvs else None,
            "top5_pdf": str(top5_pdfs[0]) if top5_pdfs else None,
        },
        "total_arquivos_output": len(list(output_dir.glob("*")))
    })


@app.route('/pipeline/download/<tipo>', methods=['GET'])
def download_relatorio(tipo):
    """Download do último relatório gerado (pdf ou csv)"""
    from flask import send_file
    from pathlib import Path

    output_dir = Path("./output")

    if tipo == 'pdf':
        arquivos = sorted(output_dir.glob("top5_oportunidades_*.pdf"), reverse=True)
        mimetype = 'application/pdf'
    elif tipo == 'csv':
        arquivos = sorted(output_dir.glob("top5_oportunidades_*.csv"), reverse=True)
        mimetype = 'text/csv'
    else:
        return jsonify({"error": "Tipo inválido. Use 'pdf' ou 'csv'"}), 400

    if not arquivos:
        return jsonify({"error": f"Nenhum arquivo {tipo} encontrado"}), 404

    return send_file(
        arquivos[0],
        mimetype=mimetype,
        as_attachment=True,
        download_name=arquivos[0].name
    )


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
