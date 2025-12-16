"""
Agentes CrewAI v2 - Analise de Leilao de Imoveis Caixa
Pipeline completo com 6 agentes especializados
"""

import os
from typing import Dict, List, Optional
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import logging

# Importa tools customizadas
from tools.data_tools import download_csv_caixa, parse_csv_imoveis, filter_imoveis
from tools.calc_tools import calc_itbi, calc_cartorio, calc_irpf, calc_custos_totais
from tools.score_tools import (
    calc_score_edital, calc_score_matricula, calc_score_localizacao,
    calc_score_financeiro, calc_score_liquidez, calc_score_oportunidade,
    classificar_recomendacao
)
from tools.output_tools import generate_csv_report, generate_pdf_report, generate_summary_csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuracao LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0.2,
    api_key=OPENAI_API_KEY
)

# LLM economico para tarefas simples
llm_fast = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    api_key=OPENAI_API_KEY
)


# ==================== AGENTES ====================

def criar_agente_coletor() -> Agent:
    """
    Agent 1: Coletor de Dados
    Responsavel por baixar CSV e filtrar imoveis
    """
    return Agent(
        role="Especialista em Coleta de Dados Imobiliarios",
        goal="""Baixar lista atualizada de imoveis da Caixa e filtrar por criterios:
        - Preco ate R$ 150.000
        - Tipo: Apartamento
        - 2a Praca (maior desconto)
        - Cidades: Sao Paulo Capital ou Litoral Paulista""",
        backstory="""Voce e um especialista em coleta e processamento de dados imobiliarios.
        Conhece profundamente o sistema de leiloes da Caixa Economica Federal e sabe
        identificar oportunidades baseado em criterios objetivos.

        Seu trabalho e garantir que a base de dados esteja sempre atualizada (2x por semana)
        e que apenas imoveis que atendam aos criterios sejam processados.""",
        verbose=True,
        llm=llm_fast,
        tools=[download_csv_caixa, parse_csv_imoveis, filter_imoveis],
        allow_delegation=False
    )


def criar_agente_analista_edital() -> Agent:
    """
    Agent 2: Analista de Edital
    Extrai e analisa informacoes juridicas do edital
    """
    return Agent(
        role="Advogado Especialista em Editais de Leilao",
        goal="""Analisar editais de leilao identificando:
        - Status de ocupacao do imovel
        - Debitos que serao transferidos (IPTU, condominio)
        - Riscos juridicos e clausulas restritivas
        - Prazos e condicoes de pagamento
        - Comissao do leiloeiro""",
        backstory="""Voce e um advogado com 15 anos de experiencia em leiloes judiciais
        e extrajudiciais da Caixa Economica Federal em Sao Paulo.

        Ja analisou mais de 2.000 editais e conhece todos os riscos e armadilhas.
        Seu objetivo e proteger o investidor identificando problemas ANTES da arrematacao.

        Voce atribui um score de 0-100 ao edital:
        - 90-100: Muito seguro, baixo risco
        - 70-89: Bom, riscos gerenciaveis
        - 50-69: Atencao necessaria
        - 30-49: Riscos significativos
        - 0-29: Evitar""",
        verbose=True,
        llm=llm,
        tools=[calc_score_edital],
        allow_delegation=False
    )


def criar_agente_analista_matricula() -> Agent:
    """
    Agent 3: Analista de Matricula
    Analisa situacao registral do imovel
    """
    return Agent(
        role="Registrador Imobiliario Especialista",
        goal="""Analisar matriculas de imoveis identificando:
        - Gravames (hipotecas, penhoras, usufrutos)
        - Quais gravames sao extintos no leilao
        - Quais gravames sao transferidos ao arrematante
        - Irregularidades e divergencias
        - Valor estimado dos onus""",
        backstory="""Voce e um oficial de registro de imoveis com 12 anos de experiencia
        em analise de matriculas e certidoes.

        Conhece profundamente a legislacao registral e sabe exatamente quais gravames
        sao eliminados no leilao e quais representam risco para o arrematante.

        Voce classifica matriculas como:
        - Limpa (90-100): Sem pendencias relevantes
        - Regular (50-89): Gravames gerenciaveis
        - Problematica (0-49): Riscos significativos""",
        verbose=True,
        llm=llm,
        tools=[calc_score_matricula],
        allow_delegation=False
    )


def criar_agente_pesquisador_mercado() -> Agent:
    """
    Agent 4: Pesquisador de Mercado
    Pesquisa precos de mercado e condominio
    """
    return Agent(
        role="Analista de Mercado Imobiliario",
        goal="""Pesquisar e estimar:
        - Preco por m2 na regiao (ZapImoveis, VivaReal)
        - Valor de mercado do imovel
        - Valor do condominio mensal
        - IPTU estimado
        - Aluguel potencial
        - Liquidez da regiao (tempo medio de venda)""",
        backstory="""Voce e um corretor de imoveis com 10 anos de atuacao em Sao Paulo
        e litoral paulista. Conhece profundamente o mercado de cada bairro.

        Voce sabe onde pesquisar precos reais e tem acesso a dados de transacoes
        recentes. Suas estimativas sao conservadoras e realistas.

        Para cada imovel, voce fornece:
        - Preco de mercado estimado
        - Faixa de variacao (+/- 10%)
        - Fontes consultadas
        - Tempo medio de venda na regiao""",
        verbose=True,
        llm=llm,
        tools=[calc_score_localizacao, calc_score_liquidez],
        allow_delegation=False
    )


def criar_agente_calculador() -> Agent:
    """
    Agent 5: Calculador de Custos
    Calcula todos os custos de aquisicao e venda
    """
    return Agent(
        role="Contador Especialista em Transacoes Imobiliarias",
        goal="""Calcular com precisao todos os custos:

        AQUISICAO:
        - Valor de arrematacao
        - Comissao leiloeiro (5%)
        - ITBI (3% SP Capital, 2% litoral)
        - Escritura e registro
        - Certidoes
        - Honorarios advocaticios
        - Custos de desocupacao (se aplicavel)
        - Debitos do edital
        - Reforma estimada

        MANUTENCAO (6 meses):
        - Condominio
        - IPTU
        - Luz/agua
        - Seguro

        VENDA:
        - Comissao corretor (6%)
        - IRPF ganho de capital

        RESULTADO:
        - Lucro liquido
        - ROI percentual
        - ROI mensal
        - Margem de seguranca
        - Comparativo com CDI""",
        backstory="""Voce e um contador especializado em transacoes imobiliarias com
        20 anos de experiencia. Conhece todas as tabelas de custos de Sao Paulo.

        Seus calculos sao SEMPRE conservadores - voce prefere superestimar custos
        e subestimar ganhos para proteger o investidor.

        Voce nunca esquece de nenhum custo, por menor que seja.""",
        verbose=True,
        llm=llm,
        tools=[calc_itbi, calc_cartorio, calc_irpf, calc_custos_totais],
        allow_delegation=False
    )


def criar_agente_decisor() -> Agent:
    """
    Agent 6: Decisor/Revisor Senior
    Consolida analises e da recomendacao final
    """
    return Agent(
        role="Investidor Imobiliario Senior",
        goal="""Consolidar todas as analises e fornecer:
        - Score geral ponderado (0-100)
        - Recomendacao: COMPRAR, ANALISAR_MELHOR ou EVITAR
        - Nivel de risco: BAIXO, MEDIO ou ALTO
        - Justificativa clara
        - Pontos de atencao
        - Proximos passos praticos
        - Comparativo com investimentos tradicionais""",
        backstory="""Voce e um investidor imobiliario com 25 anos de experiencia e
        mais de 300 imoveis arrematados em leiloes. Ja ganhou e perdeu dinheiro.

        Voce recebe as analises de 5 especialistas (coletor, edital, matricula,
        mercado, custos) e consolida tudo em uma decisao final.

        Voce e MUITO criterioso:
        - Score >= 75: COMPRAR (oportunidade clara)
        - Score 50-74: ANALISAR_MELHOR (potencial mas precisa validar)
        - Score < 50: EVITAR (risco alto)

        Voce protege o investidor de mas decisoes e destaca apenas
        oportunidades reais. Prefere perder um bom negocio a recomendar um ruim.

        Para cenario de 6 meses, voce considera:
        - Tempo de desocupacao (se aplicavel)
        - Reforma minima necessaria
        - Marketing e venda
        - Margem de seguranca de 10% no preco de venda""",
        verbose=True,
        llm=llm,
        tools=[calc_score_oportunidade, classificar_recomendacao, generate_csv_report, generate_pdf_report],
        allow_delegation=True
    )


# ==================== TASKS ====================

def criar_task_coleta(agent: Agent, estado: str = "SP") -> Task:
    """Task de coleta e filtragem de dados"""
    return Task(
        description=f"""
        1. Verifique se o CSV do estado {estado} precisa ser atualizado (2x por semana)
        2. Se necessario, baixe o CSV atualizado do site da Caixa
        3. Parse o CSV extraindo todos os campos
        4. Filtre os imoveis pelos criterios:
           - Preco <= R$ 150.000
           - Tipo = Apartamento
           - Praca = 2a Praca
           - Cidades = Sao Paulo Capital + Litoral Paulista

        Retorne a lista de imoveis filtrados com estatisticas.
        """,
        agent=agent,
        expected_output="Lista de imoveis filtrados em formato JSON com estatisticas de filtragem"
    )


def criar_task_analise_edital(agent: Agent, imovel: Dict) -> Task:
    """Task de analise do edital"""
    return Task(
        description=f"""
        Analise o edital do imovel:
        - Codigo: {imovel.get('id_imovel')}
        - Endereco: {imovel.get('endereco')}
        - Link: {imovel.get('link')}
        - Observacoes disponiveis: {imovel.get('descricao', 'N/A')}

        Identifique:
        1. Status de ocupacao (ocupado/desocupado/nao_informado)
        2. Debitos de IPTU e condominio
        3. Comissao do leiloeiro
        4. Riscos juridicos
        5. Score do edital (0-100)

        IMPORTANTE: Se nao houver informacoes suficientes, assuma cenario
        conservador (ocupado, debitos medios de R$ 10.000).
        """,
        agent=agent,
        expected_output="JSON com analise do edital incluindo ocupacao, debitos, riscos e score"
    )


def criar_task_analise_matricula(agent: Agent, imovel: Dict) -> Task:
    """Task de analise da matricula"""
    return Task(
        description=f"""
        Analise a situacao registral do imovel:
        - Codigo: {imovel.get('id_imovel')}
        - Endereco: {imovel.get('endereco')}

        Identifique:
        1. Possiveis gravames (hipotecas sao geralmente extintas no leilao CEF)
        2. Gravames que podem ser transferidos
        3. Valor estimado dos onus
        4. Irregularidades potenciais
        5. Score da matricula (0-100)

        IMPORTANTE: Sem acesso a matricula real, faca estimativa conservadora
        baseada em padroes de leiloes da Caixa.
        """,
        agent=agent,
        expected_output="JSON com analise da matricula incluindo gravames e score"
    )


def criar_task_pesquisa_mercado(agent: Agent, imovel: Dict) -> Task:
    """Task de pesquisa de mercado"""
    return Task(
        description=f"""
        Pesquise valores de mercado para:
        - Endereco: {imovel.get('endereco')}
        - Bairro: {imovel.get('bairro')}
        - Cidade: {imovel.get('cidade')}
        - Tipo: {imovel.get('tipo_imovel', 'Apartamento')}
        - Area: {imovel.get('area_privativa', 50)} m2

        Forneca:
        1. Preco por m2 na regiao
        2. Valor de mercado estimado
        3. Condominio mensal estimado
        4. IPTU mensal estimado
        5. Aluguel potencial
        6. Liquidez da regiao (tempo medio de venda)
        7. Score de localizacao (0-100)
        8. Score de liquidez (0-100)

        Use conhecimento sobre bairros de SP e litoral paulista.
        """,
        agent=agent,
        expected_output="JSON com valores de mercado, condominio, liquidez e scores"
    )


def criar_task_calculo_custos(agent: Agent, imovel: Dict, mercado: Dict, edital: Dict, matricula: Dict) -> Task:
    """Task de calculo de custos"""
    return Task(
        description=f"""
        Calcule todos os custos para cenario de venda em 6 meses:

        DADOS DO IMOVEL:
        - Valor arrematacao: R$ {imovel.get('preco', 0):,.2f}
        - Cidade: {imovel.get('cidade')}
        - Area: {imovel.get('area_privativa', 50)} m2

        DADOS DO EDITAL:
        - Ocupacao: {edital.get('ocupacao', 'nao_informado')}
        - Debitos: R$ {edital.get('total_debitos', 0):,.2f}
        - Comissao leiloeiro: {edital.get('comissao_leiloeiro_pct', 5)}%

        DADOS DA MATRICULA:
        - Gravames transferidos: R$ {matricula.get('valor_gravames', 0):,.2f}

        DADOS DE MERCADO:
        - Valor mercado: R$ {mercado.get('valor_mercado_estimado', 0):,.2f}
        - Condominio mensal: R$ {mercado.get('condominio_mensal', 0):,.2f}
        - IPTU mensal: R$ {mercado.get('iptu_mensal', 0):,.2f}

        CALCULE:
        1. Todos os custos de aquisicao detalhados
        2. Custos de manutencao por 6 meses
        3. Custos de venda
        4. Lucro liquido
        5. ROI total e mensal
        6. Margem de seguranca
        7. Comparativo com CDI

        Use preco de venda = 95% do valor de mercado (desconto para venda rapida)
        """,
        agent=agent,
        expected_output="JSON completo com todos os custos, ROI e comparativos"
    )


def criar_task_decisao_final(
    agent: Agent,
    imovel: Dict,
    edital: Dict,
    matricula: Dict,
    mercado: Dict,
    custos: Dict
) -> Task:
    """Task de decisao final"""
    return Task(
        description=f"""
        CONSOLIDACAO FINAL - CENARIO 6 MESES

        IMOVEL: {imovel.get('endereco')} - {imovel.get('bairro')}, {imovel.get('cidade')}
        VALOR: R$ {imovel.get('preco', 0):,.2f} ({imovel.get('desconto', 0):.1f}% desconto)

        SCORES RECEBIDOS:
        - Edital: {edital.get('score', 0)}/100
        - Matricula: {matricula.get('score', 0)}/100
        - Localizacao: {mercado.get('score_localizacao', 0)}/100
        - Liquidez: {mercado.get('score_liquidez', 0)}/100

        RESULTADO FINANCEIRO (6 meses):
        - Investimento Total: R$ {custos.get('investimento_total_6m', 0):,.2f}
        - Lucro Liquido: R$ {custos.get('lucro_liquido', 0):,.2f}
        - ROI: {custos.get('roi_total', 0):.1f}%
        - Margem Seguranca: {custos.get('margem_seguranca', 0):.1f}%

        SUA TAREFA:
        1. Calcule o score geral ponderado:
           - Edital: 20%
           - Matricula: 20%
           - Localizacao: 25%
           - Financeiro (ROI): 25%
           - Liquidez: 10%

        2. Determine recomendacao:
           - COMPRAR: score >= 75 E ROI > 50% E margem > 30%
           - ANALISAR_MELHOR: score 50-74 OU condicoes parciais
           - EVITAR: score < 50 OU riscos criticos

        3. Classifique o risco (BAIXO/MEDIO/ALTO)

        4. Escreva justificativa clara (2-3 paragrafos)

        5. Liste 3-5 pontos de atencao

        6. Liste 3-5 proximos passos praticos

        7. Gere CSV e PDF com a analise completa
        """,
        agent=agent,
        expected_output="JSON com score geral, recomendacao, justificativa, e caminhos dos arquivos CSV/PDF gerados"
    )


# ==================== CREW ====================

def criar_crew_analise_completa(imoveis: List[Dict]) -> Crew:
    """
    Cria Crew completo para analise de multiplos imoveis
    """
    # Cria agentes
    coletor = criar_agente_coletor()
    analista_edital = criar_agente_analista_edital()
    analista_matricula = criar_agente_analista_matricula()
    pesquisador = criar_agente_pesquisador_mercado()
    calculador = criar_agente_calculador()
    decisor = criar_agente_decisor()

    # Tasks serao criadas dinamicamente para cada imovel
    tasks = []

    for imovel in imoveis:
        # Analises paralelas
        task_edital = criar_task_analise_edital(analista_edital, imovel)
        task_matricula = criar_task_analise_matricula(analista_matricula, imovel)
        task_mercado = criar_task_pesquisa_mercado(pesquisador, imovel)

        tasks.extend([task_edital, task_matricula, task_mercado])

    # Crew hierarquico com decisor como manager
    crew = Crew(
        agents=[
            coletor,
            analista_edital,
            analista_matricula,
            pesquisador,
            calculador,
            decisor
        ],
        tasks=tasks,
        process=Process.hierarchical,
        manager_llm=llm,
        verbose=True
    )

    return crew


def analisar_imovel_individual(imovel: Dict) -> Dict:
    """
    Analisa um unico imovel de forma sequencial
    Retorna resultado completo
    """
    logger.info(f"Iniciando analise: {imovel.get('id_imovel')}")

    # 1. Analise do Edital
    analista_edital = criar_agente_analista_edital()
    task_edital = criar_task_analise_edital(analista_edital, imovel)

    # 2. Analise da Matricula
    analista_matricula = criar_agente_analista_matricula()
    task_matricula = criar_task_analise_matricula(analista_matricula, imovel)

    # 3. Pesquisa de Mercado
    pesquisador = criar_agente_pesquisador_mercado()
    task_mercado = criar_task_pesquisa_mercado(pesquisador, imovel)

    # Crew para analises paralelas
    crew_analises = Crew(
        agents=[analista_edital, analista_matricula, pesquisador],
        tasks=[task_edital, task_matricula, task_mercado],
        process=Process.sequential,
        verbose=True
    )

    resultado_analises = crew_analises.kickoff()

    # 4. Calculo de Custos (depende das analises anteriores)
    # ... processamento do resultado

    # 5. Decisao Final
    # ... consolidacao

    return resultado_analises


# ==================== EXECUCAO ====================

if __name__ == "__main__":
    # Teste com imovel exemplo
    imovel_teste = {
        "id_imovel": "8787718781523",
        "endereco": "Rua Exemplo, 123 Apto 45",
        "bairro": "VILA MARIANA",
        "cidade": "SAO PAULO",
        "tipo_imovel": "Apartamento",
        "area_privativa": 65,
        "quartos": 2,
        "vagas": 1,
        "preco": 120000,
        "valor_avaliacao": 200000,
        "desconto": 40,
        "praca": "2a Praca",
        "link": "https://venda-imoveis.caixa.gov.br/...",
        "descricao": "Apartamento desocupado em bom estado"
    }

    resultado = analisar_imovel_individual(imovel_teste)
    print(resultado)
