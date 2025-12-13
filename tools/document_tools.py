"""
Ferramentas para download e análise de documentos de imóveis (matrícula e edital)
Usa GPT-4o Vision para OCR e análise de PDFs escaneados
"""

import os
import re
import logging
import requests
import base64
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Diretório para salvar documentos
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'documentos')
os.makedirs(DOCS_DIR, exist_ok=True)

# Cache de análises
_cache_analises: Dict[str, Dict] = {}


def baixar_matricula(imovel_id: str, estado: str = "SP") -> Optional[str]:
    """
    Baixa a matrícula do imóvel do site da Caixa

    Args:
        imovel_id: ID do imóvel (ex: 1555519290270)
        estado: UF do imóvel (default: SP)

    Returns:
        Caminho do arquivo baixado ou None se falhar
    """
    try:
        # URL padrão da Caixa para matrículas
        url = f"https://venda-imoveis.caixa.gov.br/editais/matricula/{estado}/{imovel_id}.pdf"

        # Nome do arquivo local
        filename = f"matricula_{imovel_id}.pdf"
        filepath = os.path.join(DOCS_DIR, filename)

        # Verifica se já existe
        if os.path.exists(filepath):
            logger.info(f"Matrícula já baixada: {filepath}")
            return filepath

        # Baixa o arquivo
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/pdf'):
            with open(filepath, 'wb') as f:
                f.write(response.content)
            logger.info(f"Matrícula baixada: {filepath} ({len(response.content)} bytes)")
            return filepath
        else:
            logger.warning(f"Matrícula não disponível: {url} (status: {response.status_code})")
            return None

    except Exception as e:
        logger.error(f"Erro ao baixar matrícula {imovel_id}: {e}")
        return None


def pdf_to_images(filepath: str, max_pages: int = 5) -> List[str]:
    """
    Converte páginas do PDF em imagens base64 para enviar ao GPT-4o Vision

    Args:
        filepath: Caminho do PDF
        max_pages: Número máximo de páginas

    Returns:
        Lista de strings base64 das imagens
    """
    images = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)

        for i, page in enumerate(doc):
            if i >= max_pages:
                break

            # Renderiza página como imagem (300 DPI para boa qualidade)
            mat = fitz.Matrix(2, 2)  # 2x zoom = ~144 DPI
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            images.append(b64)

        doc.close()
        logger.info(f"Convertidas {len(images)} páginas do PDF para imagem")

    except Exception as e:
        logger.error(f"Erro ao converter PDF para imagens: {e}")

    return images


def analisar_matricula_com_gpt4(filepath: str) -> Dict[str, Any]:
    """
    Usa GPT-4o Vision para analisar a matrícula do imóvel

    Args:
        filepath: Caminho do PDF da matrícula

    Returns:
        Dicionário com análise estruturada
    """
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY não configurada")
        return {"erro": "API key não configurada"}

    # Converte PDF para imagens
    images = pdf_to_images(filepath, max_pages=5)

    if not images:
        logger.error("Não foi possível converter PDF para imagens")
        return {"erro": "Falha na conversão do PDF"}

    # Monta o prompt para análise
    prompt = """Analise esta matrícula de imóvel e extraia as seguintes informações em formato JSON:

{
    "matricula_numero": "número da matrícula",
    "comarca": "comarca",
    "oficio": "número do ofício",
    "area_privativa_m2": número,
    "area_total_m2": número,
    "endereco": "endereço completo",
    "proprietarios_atuais": ["lista de proprietários atuais"],

    "penhoras": [
        {
            "tipo": "PENHORA",
            "valor": número em reais,
            "credor": "nome do credor",
            "processo": "número do processo",
            "data": "data da averbação"
        }
    ],

    "alienacao_fiduciaria": {
        "existe": true/false,
        "credor": "nome do banco",
        "valor_original": número,
        "consolidada": true/false
    },

    "gravames": [
        {
            "tipo": "tipo do gravame",
            "descricao": "descrição",
            "valor": número ou null
        }
    ],

    "dividas_condominio": {
        "existe": true/false,
        "valor": número,
        "credor": "nome do condomínio"
    },

    "consolidacao_propriedade": {
        "consolidada": true/false,
        "para_quem": "nome de quem ficou a propriedade",
        "valor": número,
        "data": "data da consolidação"
    },

    "riscos_identificados": ["lista de riscos encontrados"],

    "score_risco": número de 0 a 100,
    "classificacao_risco": "BAIXO" ou "MEDIO" ou "ALTO",

    "resumo": "resumo executivo da análise"
}

Seja preciso com os valores monetários. Se não encontrar alguma informação, use null."""

    # Monta as mensagens com as imagens
    content = [{"type": "text", "text": prompt}]

    for img_b64 in images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}",
                "detail": "high"
            }
        })

    # Chama a API do GPT-4o
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1
        }

        logger.info("Enviando matrícula para análise com GPT-4o Vision...")

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            logger.error(f"Erro na API OpenAI: {response.status_code} - {response.text}")
            return {"erro": f"API error: {response.status_code}"}

        result = response.json()
        answer = result["choices"][0]["message"]["content"]

        # Extrai o JSON da resposta
        # Remove possíveis markdown code blocks
        answer = answer.replace("```json", "").replace("```", "").strip()

        try:
            analise = json.loads(answer)
            logger.info(f"Análise concluída - Risco: {analise.get('classificacao_risco', 'N/I')}")
            return analise
        except json.JSONDecodeError:
            logger.warning("Resposta não é JSON válido, retornando texto bruto")
            return {"texto_bruto": answer, "erro": "JSON inválido"}

    except Exception as e:
        logger.error(f"Erro ao chamar GPT-4o: {e}")
        return {"erro": str(e)}


def extrair_texto_pdf(filepath: str) -> str:
    """
    Extrai texto de um arquivo PDF (fallback para PDFs simples)

    Args:
        filepath: Caminho do arquivo PDF

    Returns:
        Texto extraído do PDF
    """
    try:
        import fitz
        text_parts = []
        doc = fitz.open(filepath)
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return '\n'.join(text_parts)
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF {filepath}: {e}")
        return ""


def analisar_matricula(texto: str) -> Dict[str, Any]:
    """
    Analisa o texto da matrícula e extrai informações relevantes

    Args:
        texto: Texto extraído da matrícula

    Returns:
        Dicionário com informações extraídas
    """
    resultado = {
        'matricula_numero': None,
        'comarca': None,
        'oficio': None,
        'area_privativa_m2': None,
        'area_total_m2': None,
        'fracao_ideal': None,
        'proprietarios': [],
        'gravames': [],
        'penhoras': [],
        'alienacao_fiduciaria': None,
        'consolidacao_propriedade': None,
        'dividas_identificadas': [],
        'riscos': [],
        'score_risco': 0,  # 0-100, onde 100 = alto risco
    }

    texto_upper = texto.upper()
    texto_clean = re.sub(r'\s+', ' ', texto)

    # Extrai número da matrícula
    match = re.search(r'matr[íi]cula[:\s]*(\d+[\.\d]*)', texto, re.IGNORECASE)
    if match:
        resultado['matricula_numero'] = match.group(1).replace('.', '')

    # Extrai comarca
    match = re.search(r'comarca[:\s]*([^\n,]+)', texto, re.IGNORECASE)
    if match:
        resultado['comarca'] = match.group(1).strip()

    # Extrai áreas
    match = re.search(r'[áa]rea\s+privativa[:\s=]*(\d+[,\.]\d+)\s*m', texto, re.IGNORECASE)
    if match:
        resultado['area_privativa_m2'] = float(match.group(1).replace(',', '.'))

    match = re.search(r'[áa]rea\s+total[:\s=]*(\d+[,\.]\d+)\s*m', texto, re.IGNORECASE)
    if match:
        resultado['area_total_m2'] = float(match.group(1).replace(',', '.'))

    # === DETECÇÃO DE GRAVAMES E RISCOS ===

    # Penhoras
    penhoras = re.findall(
        r'PENHORA[:\s].*?(?:valor|d[íi]vida)[:\s]*(?:de\s+)?R\$\s*([\d\.,]+)',
        texto, re.IGNORECASE | re.DOTALL
    )
    for valor in penhoras:
        valor_float = float(valor.replace('.', '').replace(',', '.'))
        resultado['penhoras'].append({
            'tipo': 'PENHORA',
            'valor': valor_float
        })
        resultado['dividas_identificadas'].append({
            'tipo': 'Penhora',
            'valor': valor_float
        })

    # Busca por valores de penhora no formato R$ X.XXX,XX
    if 'PENHORA' in texto_upper:
        valores_penhora = re.findall(
            r'PENHORA.*?R\$\s*([\d\.]+[,]\d{2})',
            texto, re.IGNORECASE | re.DOTALL
        )
        for valor in valores_penhora:
            try:
                valor_float = float(valor.replace('.', '').replace(',', '.'))
                if valor_float > 100:  # Ignora valores muito baixos
                    if not any(p['valor'] == valor_float for p in resultado['penhoras']):
                        resultado['penhoras'].append({
                            'tipo': 'PENHORA',
                            'valor': valor_float
                        })
            except:
                pass

    # Alienação Fiduciária
    if 'ALIENA' in texto_upper and 'FIDUCI' in texto_upper:
        match = re.search(
            r'ALIENA[ÇC][ÃA]O\s+FIDUCI[ÁA]RIA.*?d[íi]vida.*?R\$\s*([\d\.,]+)',
            texto, re.IGNORECASE | re.DOTALL
        )
        if match:
            valor = float(match.group(1).replace('.', '').replace(',', '.'))
            resultado['alienacao_fiduciaria'] = {
                'valor_original': valor,
                'credor': 'Caixa Econômica Federal' if 'CAIXA' in texto_upper else 'Desconhecido'
            }

    # Consolidação da Propriedade
    if 'CONSOLIDA' in texto_upper and 'PROPRIEDADE' in texto_upper:
        match = re.search(
            r'CONSOLIDA[ÇC][ÃA]O.*?PROPRIEDADE.*?R\$\s*([\d\.,]+)',
            texto, re.IGNORECASE | re.DOTALL
        )
        valor = None
        if match:
            valor = float(match.group(1).replace('.', '').replace(',', '.'))

        resultado['consolidacao_propriedade'] = {
            'consolidada': True,
            'valor': valor,
            'motivo': 'Não purgação da mora' if 'PURG' in texto_upper else 'Inadimplência'
        }

    # Dívida de Condomínio
    if 'CONDOM' in texto_upper and ('PENHORA' in texto_upper or 'EXECU' in texto_upper):
        match = re.search(
            r'CONDOM[ÍI]NIO.*?R\$\s*([\d\.,]+)',
            texto, re.IGNORECASE | re.DOTALL
        )
        if match:
            valor = float(match.group(1).replace('.', '').replace(',', '.'))
            resultado['dividas_identificadas'].append({
                'tipo': 'Condomínio',
                'valor': valor,
                'observacao': 'Dívida de condomínio averbada na matrícula'
            })

    # Hipoteca
    if 'HIPOTECA' in texto_upper:
        resultado['gravames'].append({
            'tipo': 'HIPOTECA',
            'descricao': 'Hipoteca registrada na matrícula'
        })

    # Indisponibilidade
    if 'INDISPONIBILIDADE' in texto_upper:
        resultado['gravames'].append({
            'tipo': 'INDISPONIBILIDADE',
            'descricao': 'Indisponibilidade de bens averbada'
        })

    # Usufruto
    if 'USUFRUTO' in texto_upper:
        resultado['gravames'].append({
            'tipo': 'USUFRUTO',
            'descricao': 'Usufruto registrado - verificar vigência'
        })

    # Ação judicial
    if 'A[ÇC][ÃA]O' in texto_upper or 'PROCESSO' in texto_upper or 'EXECU[ÇC][ÃA]O' in texto_upper:
        processos = re.findall(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto)
        for proc in processos:
            resultado['gravames'].append({
                'tipo': 'PROCESSO_JUDICIAL',
                'numero': proc
            })

    # === CÁLCULO DO SCORE DE RISCO ===

    score = 0
    riscos = []

    # Penhoras (alto risco)
    if resultado['penhoras']:
        total_penhoras = sum(p['valor'] for p in resultado['penhoras'])
        score += min(40, len(resultado['penhoras']) * 15)
        riscos.append(f"🚨 {len(resultado['penhoras'])} penhora(s) averbada(s) - Total: R$ {total_penhoras:,.2f}")

    # Alienação fiduciária (médio risco se consolidada pela Caixa)
    if resultado['alienacao_fiduciaria']:
        if resultado['consolidacao_propriedade']:
            score += 10  # Menor risco se já consolidada
            riscos.append("⚠️ Alienação fiduciária com propriedade consolidada (Caixa é proprietária)")
        else:
            score += 25
            riscos.append("🚨 Alienação fiduciária ativa")

    # Outros gravames
    for gravame in resultado['gravames']:
        if gravame['tipo'] == 'INDISPONIBILIDADE':
            score += 20
            riscos.append("🚨 Indisponibilidade de bens averbada")
        elif gravame['tipo'] == 'HIPOTECA':
            score += 15
            riscos.append("⚠️ Hipoteca registrada")
        elif gravame['tipo'] == 'USUFRUTO':
            score += 25
            riscos.append("🚨 Usufruto registrado - pode afetar posse")
        elif gravame['tipo'] == 'PROCESSO_JUDICIAL':
            score += 10
            riscos.append(f"⚠️ Processo judicial: {gravame.get('numero', 'N/I')}")

    # Dívidas identificadas
    if resultado['dividas_identificadas']:
        total_dividas = sum(d['valor'] for d in resultado['dividas_identificadas'])
        if total_dividas > 50000:
            score += 20
            riscos.append(f"🚨 Alto valor em dívidas: R$ {total_dividas:,.2f}")
        elif total_dividas > 10000:
            score += 10
            riscos.append(f"⚠️ Dívidas identificadas: R$ {total_dividas:,.2f}")

    resultado['score_risco'] = min(100, score)
    resultado['riscos'] = riscos

    # Classificação do risco
    if score >= 60:
        resultado['classificacao_risco'] = 'ALTO'
    elif score >= 30:
        resultado['classificacao_risco'] = 'MEDIO'
    else:
        resultado['classificacao_risco'] = 'BAIXO'

    return resultado


def analisar_documento_imovel(imovel_id: str, estado: str = "SP", force_download: bool = False, use_gpt4: bool = True) -> Dict[str, Any]:
    """
    Função principal: baixa e analisa a matrícula de um imóvel

    Args:
        imovel_id: ID do imóvel
        estado: UF do imóvel
        force_download: Força novo download mesmo se já existir
        use_gpt4: Se True, usa GPT-4o Vision para análise (recomendado para PDFs escaneados)

    Returns:
        Dicionário com análise completa do documento
    """
    # Verifica cache
    cache_key = f"{estado}_{imovel_id}"
    if cache_key in _cache_analises and not force_download:
        logger.info(f"Usando análise em cache para {imovel_id}")
        return _cache_analises[cache_key]

    resultado = {
        'imovel_id': imovel_id,
        'estado': estado,
        'matricula_disponivel': False,
        'matricula_arquivo': None,
        'analise': None,
        'metodo_analise': None,
        'erro': None,
        'timestamp': datetime.now().isoformat()
    }

    try:
        # Remove arquivo existente se force_download
        if force_download:
            filepath = os.path.join(DOCS_DIR, f"matricula_{imovel_id}.pdf")
            if os.path.exists(filepath):
                os.remove(filepath)

        # Baixa a matrícula
        filepath = baixar_matricula(imovel_id, estado)

        if filepath:
            resultado['matricula_disponivel'] = True
            resultado['matricula_arquivo'] = filepath

            if use_gpt4 and OPENAI_API_KEY:
                # Usa GPT-4o Vision para análise (melhor para PDFs escaneados)
                logger.info(f"Analisando matrícula com GPT-4o Vision...")
                analise_gpt = analisar_matricula_com_gpt4(filepath)

                if analise_gpt and not analise_gpt.get('erro'):
                    # Converte formato GPT-4o para formato padrão do pipeline
                    resultado['analise'] = converter_analise_gpt4(analise_gpt)
                    resultado['analise_gpt4_raw'] = analise_gpt
                    resultado['metodo_analise'] = 'gpt4o_vision'
                else:
                    logger.warning(f"GPT-4o falhou, tentando análise por regex...")
                    # Fallback para análise por regex
                    texto = extrair_texto_pdf(filepath)
                    if texto:
                        resultado['analise'] = analisar_matricula(texto)
                        resultado['metodo_analise'] = 'regex_fallback'
                    else:
                        resultado['erro'] = 'Não foi possível analisar a matrícula'
            else:
                # Análise por regex (para PDFs com texto extraível)
                texto = extrair_texto_pdf(filepath)
                if texto:
                    resultado['analise'] = analisar_matricula(texto)
                    resultado['metodo_analise'] = 'regex'
                else:
                    resultado['erro'] = 'Não foi possível extrair texto do PDF'
        else:
            resultado['erro'] = 'Matrícula não disponível para download'

        # Salva no cache
        _cache_analises[cache_key] = resultado

    except Exception as e:
        resultado['erro'] = str(e)
        logger.error(f"Erro ao analisar documento do imóvel {imovel_id}: {e}")

    return resultado


def converter_analise_gpt4(gpt_analise: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte a análise do GPT-4o para o formato padrão do pipeline

    Args:
        gpt_analise: Resultado da análise do GPT-4o

    Returns:
        Dicionário no formato padrão
    """
    resultado = {
        'matricula_numero': gpt_analise.get('matricula_numero'),
        'comarca': gpt_analise.get('comarca'),
        'oficio': gpt_analise.get('oficio'),
        'area_privativa_m2': gpt_analise.get('area_privativa_m2'),
        'area_total_m2': gpt_analise.get('area_total_m2'),
        'fracao_ideal': None,
        'proprietarios': gpt_analise.get('proprietarios_atuais', []),
        'gravames': [],
        'penhoras': [],
        'alienacao_fiduciaria': None,
        'consolidacao_propriedade': None,
        'dividas_identificadas': [],
        'riscos': gpt_analise.get('riscos_identificados', []),
        'score_risco': gpt_analise.get('score_risco', 0),
        'classificacao_risco': gpt_analise.get('classificacao_risco', 'BAIXO'),
        'resumo': gpt_analise.get('resumo', ''),
    }

    # Converte penhoras
    for p in gpt_analise.get('penhoras', []):
        resultado['penhoras'].append({
            'tipo': p.get('tipo', 'PENHORA'),
            'valor': p.get('valor', 0),
            'credor': p.get('credor'),
            'processo': p.get('processo'),
            'data': p.get('data')
        })
        # Adiciona como dívida identificada
        if p.get('valor'):
            resultado['dividas_identificadas'].append({
                'tipo': 'Penhora',
                'valor': p.get('valor', 0),
                'credor': p.get('credor'),
                'observacao': f"Processo: {p.get('processo', 'N/I')}"
            })

    # Converte alienação fiduciária
    af = gpt_analise.get('alienacao_fiduciaria', {})
    if af and af.get('existe'):
        resultado['alienacao_fiduciaria'] = {
            'valor_original': af.get('valor_original', 0),
            'credor': af.get('credor', 'Desconhecido'),
            'consolidada': af.get('consolidada', False)
        }

    # Converte consolidação
    cp = gpt_analise.get('consolidacao_propriedade', {})
    if cp and cp.get('consolidada'):
        resultado['consolidacao_propriedade'] = {
            'consolidada': True,
            'valor': cp.get('valor'),
            'para_quem': cp.get('para_quem'),
            'data': cp.get('data'),
            'motivo': 'Não purgação da mora'
        }

    # Converte dívidas de condomínio
    dc = gpt_analise.get('dividas_condominio', {})
    if dc and dc.get('existe') and dc.get('valor'):
        resultado['dividas_identificadas'].append({
            'tipo': 'Condomínio',
            'valor': dc.get('valor', 0),
            'credor': dc.get('credor'),
            'observacao': 'Dívida de condomínio averbada'
        })

    # Converte gravames
    for g in gpt_analise.get('gravames', []):
        resultado['gravames'].append({
            'tipo': g.get('tipo', 'GRAVAME'),
            'descricao': g.get('descricao'),
            'valor': g.get('valor')
        })

    return resultado


def calcular_custos_documentacao(analise: Dict[str, Any], valor_imovel: float) -> Dict[str, float]:
    """
    Calcula custos adicionais baseado na análise da matrícula

    Args:
        analise: Resultado da análise da matrícula
        valor_imovel: Valor de compra do imóvel

    Returns:
        Dicionário com custos estimados
    """
    custos = {
        'dividas_matricula': 0,
        'penhoras': 0,
        'regularizacao_estimada': 0,
        'total_custos_documentacao': 0
    }

    if not analise:
        return custos

    # Soma penhoras
    for penhora in analise.get('penhoras', []):
        custos['penhoras'] += penhora.get('valor', 0)

    # Soma dívidas identificadas
    for divida in analise.get('dividas_identificadas', []):
        custos['dividas_matricula'] += divida.get('valor', 0)

    # Estimativa de regularização (advogado, custas judiciais)
    if analise.get('score_risco', 0) >= 60:
        custos['regularizacao_estimada'] = 5000  # R$ 5.000 para casos complexos
    elif analise.get('score_risco', 0) >= 30:
        custos['regularizacao_estimada'] = 2000  # R$ 2.000 para casos médios

    # Adiciona 20% de margem para correção monetária das dívidas
    custos['dividas_matricula'] *= 1.20
    custos['penhoras'] *= 1.20

    custos['total_custos_documentacao'] = (
        custos['dividas_matricula'] +
        custos['penhoras'] +
        custos['regularizacao_estimada']
    )

    return custos


def gerar_relatorio_matricula(analise: Dict[str, Any]) -> str:
    """
    Gera um relatório textual da análise da matrícula

    Args:
        analise: Resultado da análise

    Returns:
        Relatório formatado em texto
    """
    if not analise:
        return "Análise não disponível"

    linhas = [
        "=" * 60,
        "RELATÓRIO DE ANÁLISE DA MATRÍCULA",
        "=" * 60,
        "",
        f"Matrícula: {analise.get('matricula_numero', 'N/I')}",
        f"Comarca: {analise.get('comarca', 'N/I')}",
        f"Área Privativa: {analise.get('area_privativa_m2', 'N/I')} m²",
        f"Área Total: {analise.get('area_total_m2', 'N/I')} m²",
        "",
        "-" * 40,
        "CLASSIFICAÇÃO DE RISCO",
        "-" * 40,
        f"Score: {analise.get('score_risco', 0)}/100",
        f"Classificação: {analise.get('classificacao_risco', 'N/I')}",
        "",
    ]

    # Riscos identificados
    riscos = analise.get('riscos', [])
    if riscos:
        linhas.append("-" * 40)
        linhas.append("RISCOS IDENTIFICADOS")
        linhas.append("-" * 40)
        for risco in riscos:
            linhas.append(f"  {risco}")
        linhas.append("")

    # Penhoras
    penhoras = analise.get('penhoras', [])
    if penhoras:
        linhas.append("-" * 40)
        linhas.append("PENHORAS")
        linhas.append("-" * 40)
        total = 0
        for p in penhoras:
            valor = p.get('valor', 0)
            total += valor
            linhas.append(f"  - {p.get('tipo', 'Penhora')}: R$ {valor:,.2f}")
        linhas.append(f"  TOTAL: R$ {total:,.2f}")
        linhas.append("")

    # Dívidas
    dividas = analise.get('dividas_identificadas', [])
    if dividas:
        linhas.append("-" * 40)
        linhas.append("DÍVIDAS IDENTIFICADAS")
        linhas.append("-" * 40)
        for d in dividas:
            linhas.append(f"  - {d.get('tipo', 'Dívida')}: R$ {d.get('valor', 0):,.2f}")
            if d.get('observacao'):
                linhas.append(f"    Obs: {d['observacao']}")
        linhas.append("")

    # Gravames
    gravames = analise.get('gravames', [])
    if gravames:
        linhas.append("-" * 40)
        linhas.append("OUTROS GRAVAMES")
        linhas.append("-" * 40)
        for g in gravames:
            linhas.append(f"  - {g.get('tipo', 'Gravame')}: {g.get('descricao', g.get('numero', 'N/I'))}")
        linhas.append("")

    # Alienação fiduciária
    af = analise.get('alienacao_fiduciaria')
    if af:
        linhas.append("-" * 40)
        linhas.append("ALIENAÇÃO FIDUCIÁRIA")
        linhas.append("-" * 40)
        linhas.append(f"  Credor: {af.get('credor', 'N/I')}")
        linhas.append(f"  Valor Original: R$ {af.get('valor_original', 0):,.2f}")
        linhas.append("")

    # Consolidação
    cp = analise.get('consolidacao_propriedade')
    if cp:
        linhas.append("-" * 40)
        linhas.append("CONSOLIDAÇÃO DA PROPRIEDADE")
        linhas.append("-" * 40)
        linhas.append(f"  Status: {'Consolidada' if cp.get('consolidada') else 'Não consolidada'}")
        if cp.get('valor'):
            linhas.append(f"  Valor: R$ {cp['valor']:,.2f}")
        linhas.append(f"  Motivo: {cp.get('motivo', 'N/I')}")
        linhas.append("")

    linhas.append("=" * 60)

    return "\n".join(linhas)


# ============================================
# ANÁLISE DE EDITAL (PÁGINA DO IMÓVEL)
# ============================================

def extrair_edital_pagina(imovel_id: str) -> Dict[str, Any]:
    """
    Extrai dados da página do imóvel que funcionam como edital
    Na Venda Online da Caixa, não existe edital PDF separado.
    As informações estão na página do imóvel.

    Args:
        imovel_id: ID do imóvel

    Returns:
        Dicionário com dados do "edital"
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("BeautifulSoup não instalado. Instale: pip install beautifulsoup4")
        return {"erro": "BeautifulSoup não disponível"}

    url = f'https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={imovel_id}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code != 200:
            return {'erro': f'Status {resp.status_code}'}

        soup = BeautifulSoup(resp.text, 'html.parser')
        texto = soup.get_text()

        dados = {
            'imovel_id': imovel_id,
            'titulo': None,
            'valor_avaliacao': None,
            'valor_minimo': None,
            'desconto_percentual': None,
            'tipo_imovel': None,
            'quartos': None,
            'matricula': None,
            'comarca': None,
            'oficio': None,
            'inscricao_imobiliaria': None,
            'area_total': None,
            'area_privativa': None,
            'endereco': None,
            'descricao': None,
            'formas_pagamento': [],
            'aceita_financiamento': False,
            'aceita_fgts': False,
            'regras_condominio': None,
            'limite_condominio_caixa_percentual': None,
            'regras_tributos': None,
            'gravames_matricula': False,
            'regularizacao_comprador': True,
            'ocupado': None,
            'modalidade_venda': 'Venda Online',
        }

        # Titulo do edificio
        h5 = soup.find('h5')
        if h5:
            dados['titulo'] = h5.get_text().strip()

        # Valor de avaliacao
        match = re.search(r'Valor de avalia[çc][ãa]o:\s*R\$\s*([\d\.,]+)', texto)
        if match:
            dados['valor_avaliacao'] = float(match.group(1).replace('.', '').replace(',', '.'))

        # Valor minimo
        match = re.search(r'Valor m[íi]nimo de venda:\s*R\$\s*([\d\.,]+)', texto)
        if match:
            dados['valor_minimo'] = float(match.group(1).replace('.', '').replace(',', '.'))

        # Desconto
        match = re.search(r'desconto de\s*([\d,]+)%', texto)
        if match:
            dados['desconto_percentual'] = float(match.group(1).replace(',', '.'))

        # Tipo imovel
        match = re.search(r'Tipo de im[óo]vel:\s*(\w+)', texto)
        if match:
            dados['tipo_imovel'] = match.group(1)

        # Quartos
        match = re.search(r'Quartos:\s*(\d+)', texto)
        if match:
            dados['quartos'] = int(match.group(1))

        # Matricula
        match = re.search(r'Matr[íi]cula\(?s?\)?:\s*(\d+)', texto)
        if match:
            dados['matricula'] = match.group(1)

        # Comarca
        match = re.search(r'Comarca:\s*([A-Z\s\-]+)', texto)
        if match:
            dados['comarca'] = match.group(1).strip()

        # Oficio
        match = re.search(r'Of[íi]cio:\s*(\d+)', texto)
        if match:
            dados['oficio'] = match.group(1)

        # Inscricao imobiliaria
        match = re.search(r'Inscri[çc][ãa]o imobili[áa]ria:\s*(\d+)', texto)
        if match:
            dados['inscricao_imobiliaria'] = match.group(1)

        # Areas
        match = re.search(r'[ÁA]rea total\s*=\s*([\d,]+)m', texto)
        if match:
            dados['area_total'] = float(match.group(1).replace(',', '.'))

        match = re.search(r'[ÁA]rea privativa\s*=\s*([\d,]+)m', texto)
        if match:
            dados['area_privativa'] = float(match.group(1).replace(',', '.'))

        # Endereco - pega só a primeira linha
        match = re.search(r'Endere[çc]o:\s*([^,]+,[^,]+,[^-]+-[^,]+)', texto)
        if match:
            dados['endereco'] = match.group(1).strip()

        # Descricao do imovel
        match = re.search(r'Descri[çc][ãa]o:\s*([^\.]+\.)', texto)
        if match:
            dados['descricao'] = match.group(1).strip()

        # Formas de pagamento
        if 'Recursos pr' in texto:
            dados['formas_pagamento'].append('Recursos próprios')
        if 'financiamento' in texto.lower():
            dados['formas_pagamento'].append('Financiamento SBPE')
            dados['aceita_financiamento'] = True
        if 'FGTS' in texto:
            dados['formas_pagamento'].append('FGTS')
            dados['aceita_fgts'] = True

        # Regras condominio
        match = re.search(r'Condom[íi]nio:\s*([^\.]+\.)([^\.]+\.)?', texto)
        if match:
            dados['regras_condominio'] = (match.group(1) + (match.group(2) or '')).strip()

        # Limite condominio Caixa
        match = re.search(r'limite de\s*(\d+)%', texto)
        if match:
            dados['limite_condominio_caixa_percentual'] = int(match.group(1))

        # Regras tributos
        if 'Tributos:' in texto:
            match = re.search(r'Tributos:\s*([^\.]+\.)', texto)
            if match:
                dados['regras_tributos'] = match.group(1).strip()

        # Gravames
        if 'gravame' in texto.lower() or 'penhora' in texto.lower() or 'indisponibilidade' in texto.lower():
            dados['gravames_matricula'] = True

        # Regularizacao
        if 'Regulariza' in texto and 'adquirente' in texto.lower():
            dados['regularizacao_comprador'] = True

        # Ocupacao
        if 'ocupado' in texto.lower():
            dados['ocupado'] = True
        elif 'desocupado' in texto.lower():
            dados['ocupado'] = False

        return dados

    except Exception as e:
        logger.error(f"Erro ao extrair edital da página: {e}")
        return {'erro': str(e)}


def analisar_edital_completo(imovel_id: str, estado: str = "SP") -> Dict[str, Any]:
    """
    Análise completa do "edital" combinando:
    1. Dados da página do imóvel
    2. Análise da matrícula (se disponível)
    3. Regras gerais da Venda Online

    Args:
        imovel_id: ID do imóvel
        estado: UF

    Returns:
        Dicionário com análise completa do edital
    """
    resultado = {
        'imovel_id': imovel_id,
        'estado': estado,
        'timestamp': datetime.now().isoformat(),
        'dados_pagina': None,
        'analise_matricula': None,
        'regras_venda_online': None,
        'custos_estimados': {},
        'riscos': [],
        'alertas': [],
        'score_risco_edital': 0,
    }

    # 1. Extrai dados da página do imóvel
    dados_pagina = extrair_edital_pagina(imovel_id)
    resultado['dados_pagina'] = dados_pagina

    if dados_pagina.get('erro'):
        resultado['alertas'].append(f"Erro ao extrair página: {dados_pagina['erro']}")
    else:
        # Analisa regras específicas
        if dados_pagina.get('gravames_matricula'):
            resultado['riscos'].append("Imóvel com gravame/penhora/indisponibilidade na matrícula")
            resultado['score_risco_edital'] += 20

        if dados_pagina.get('regularizacao_comprador'):
            resultado['riscos'].append("Regularização por conta do comprador")
            resultado['score_risco_edital'] += 10

        if dados_pagina.get('ocupado') is True:
            resultado['riscos'].append("Imóvel ocupado - pode haver custos de desocupação")
            resultado['score_risco_edital'] += 15

        # Calcula custos baseados nas regras
        valor_avaliacao = dados_pagina.get('valor_avaliacao', 0)
        valor_minimo = dados_pagina.get('valor_minimo', 0)
        limite_cond = dados_pagina.get('limite_condominio_caixa_percentual', 10)

        resultado['custos_estimados'] = {
            'limite_condominio_comprador': valor_avaliacao * (limite_cond / 100) if valor_avaliacao else None,
            'tributos_responsavel': 'comprador',
            'regularizacao_responsavel': 'comprador' if dados_pagina.get('regularizacao_comprador') else 'caixa',
        }

    # 2. Tenta obter análise da matrícula (se já existir no cache)
    cache_key = f"{estado}_{imovel_id}"
    if cache_key in _cache_analises:
        resultado['analise_matricula'] = _cache_analises[cache_key].get('analise')

    # 3. Regras gerais da Venda Online (resumo)
    resultado['regras_venda_online'] = {
        'tipo_venda': 'Venda Online',
        'prazo_pagamento': '2 dias úteis após proposta aceita',
        'formas_pagamento': ['Recursos próprios', 'Financiamento SBPE', 'FGTS'],
        'comissao_leiloeiro': 'Não há (venda direta)',
        'itbi_responsavel': 'comprador',
        'registro_responsavel': 'comprador',
        'condominio_regra': f'Comprador paga até {dados_pagina.get("limite_condominio_caixa_percentual", 10)}% do valor de avaliação',
        'tributos_regra': 'Comprador assume todos os tributos',
        'desocupacao_regra': 'Comprador assume custos de desocupação se ocupado',
    }

    # Ajusta score baseado na matrícula se disponível
    if resultado.get('analise_matricula'):
        matricula_score = resultado['analise_matricula'].get('score_risco', 0)
        resultado['score_risco_edital'] = max(resultado['score_risco_edital'], matricula_score)

    # Classificação
    if resultado['score_risco_edital'] >= 60:
        resultado['classificacao_risco'] = 'ALTO'
    elif resultado['score_risco_edital'] >= 30:
        resultado['classificacao_risco'] = 'MEDIO'
    else:
        resultado['classificacao_risco'] = 'BAIXO'

    return resultado


def gerar_relatorio_edital(analise: Dict[str, Any]) -> str:
    """
    Gera relatório textual da análise do edital

    Args:
        analise: Resultado da análise do edital

    Returns:
        Relatório formatado
    """
    linhas = [
        "=" * 60,
        "RELATÓRIO DE ANÁLISE DO EDITAL",
        "=" * 60,
        "",
    ]

    dados = analise.get('dados_pagina', {})

    if dados:
        linhas.extend([
            f"Imóvel: {dados.get('titulo', 'N/I')}",
            f"Endereço: {dados.get('endereco', 'N/I')}",
            f"Tipo: {dados.get('tipo_imovel', 'N/I')} - {dados.get('quartos', 'N/I')} quarto(s)",
            f"Área: {dados.get('area_privativa', 'N/I')} m² (privativa) / {dados.get('area_total', 'N/I')} m² (total)",
            "",
            "-" * 40,
            "VALORES",
            "-" * 40,
            f"Avaliação: R$ {dados.get('valor_avaliacao', 0):,.2f}" if dados.get('valor_avaliacao') else "Avaliação: N/I",
            f"Mínimo: R$ {dados.get('valor_minimo', 0):,.2f}" if dados.get('valor_minimo') else "Mínimo: N/I",
            f"Desconto: {dados.get('desconto_percentual', 0):.1f}%" if dados.get('desconto_percentual') else "Desconto: N/I",
            "",
        ])

    linhas.extend([
        "-" * 40,
        "FORMAS DE PAGAMENTO",
        "-" * 40,
    ])
    for forma in dados.get('formas_pagamento', []):
        linhas.append(f"  ✓ {forma}")

    linhas.extend([
        "",
        "-" * 40,
        "REGRAS DE CUSTOS",
        "-" * 40,
        f"Condomínio: {dados.get('regras_condominio', 'N/I')}",
        f"Tributos: {dados.get('regras_tributos', 'N/I')}",
        f"Gravames na matrícula: {'SIM' if dados.get('gravames_matricula') else 'NÃO'}",
        f"Regularização: {'Comprador' if dados.get('regularizacao_comprador') else 'Caixa'}",
        "",
    ])

    # Riscos
    riscos = analise.get('riscos', [])
    if riscos:
        linhas.extend([
            "-" * 40,
            "RISCOS IDENTIFICADOS",
            "-" * 40,
        ])
        for risco in riscos:
            linhas.append(f"  ⚠️ {risco}")
        linhas.append("")

    linhas.extend([
        "-" * 40,
        "CLASSIFICAÇÃO",
        "-" * 40,
        f"Score de Risco: {analise.get('score_risco_edital', 0)}/100",
        f"Classificação: {analise.get('classificacao_risco', 'N/I')}",
        "",
        "=" * 60,
    ])

    return "\n".join(linhas)


# Função de teste
if __name__ == "__main__":
    # Teste com um imóvel específico
    resultado = analisar_documento_imovel("1555519290270", "SP")

    if resultado['analise']:
        print(gerar_relatorio_matricula(resultado['analise']))

        # Calcula custos
        custos = calcular_custos_documentacao(resultado['analise'], 135326.01)
        print("\nCUSTOS ESTIMADOS:")
        for k, v in custos.items():
            print(f"  {k}: R$ {v:,.2f}")

    # Teste análise de edital
    print("\n")
    edital = analisar_edital_completo("1555519290270", "SP")
    print(gerar_relatorio_edital(edital))
