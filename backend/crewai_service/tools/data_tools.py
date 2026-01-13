"""
Tools de Coleta de Dados - Download e Filtragem de Imoveis Caixa
Download automatico 2x por semana com verificacao de atualizacao
"""

import os
import requests
import pandas as pd
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
# Removido decorador @tool para permitir chamada direta
# from crewai_tools import tool
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuracoes
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
CACHE_FILE = DATA_DIR / "cache_metadata.json"

# Cidades alvo
CIDADES_CAPITAL = ["SAO PAULO"]
CIDADES_LITORAL = [
    "SANTOS", "GUARUJA", "PRAIA GRANDE", "SAO VICENTE", "BERTIOGA",
    "UBATUBA", "CARAGUATATUBA", "ILHABELA", "MONGAGUA", "ITANHAEM",
    "PERUIBE", "CUBATAO", "CANANEIA", "IGUAPE"
]
CIDADES_ALVO = CIDADES_CAPITAL + CIDADES_LITORAL

# URL base Caixa
CAIXA_DOWNLOAD_URL = "https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp"


def get_cache_metadata() -> Dict:
    """Le metadados do cache"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_cache_metadata(metadata: Dict):
    """Salva metadados do cache"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)


def file_hash(filepath: Path) -> str:
    """Calcula hash MD5 do arquivo para detectar mudancas"""
    if not filepath.exists():
        return ""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def needs_update(estado: str, force: bool = False) -> bool:
    """
    Verifica se precisa atualizar o CSV.
    Regras:
    - Se force=True, sempre atualiza
    - Se arquivo nao existe, atualiza
    - Se ultima atualizacao > 3 dias, atualiza (garante 2x por semana)
    - Se e segunda ou quinta-feira, tenta atualizar
    """
    if force:
        return True

    metadata = get_cache_metadata()
    estado_key = f"Lista_imoveis_{estado}"

    if estado_key not in metadata:
        return True

    last_update = datetime.fromisoformat(metadata[estado_key].get("last_update", "2000-01-01"))
    days_since_update = (datetime.now() - last_update).days

    # Atualiza se passou mais de 3 dias
    if days_since_update >= 3:
        return True

    # Atualiza nas segundas e quintas (0=segunda, 3=quinta)
    today = datetime.now().weekday()
    last_update_day = last_update.weekday()

    if today in [0, 3] and last_update_day != today:
        return True

    return False


def download_csv_caixa(estado: str = "SP", force: bool = False) -> Dict:
    """
    Baixa CSV de imoveis da Caixa por estado.
    Verifica automaticamente se precisa atualizar (2x por semana).

    Args:
        estado: Sigla do estado (ex: SP, RJ)
        force: Forca download mesmo se cache recente

    Returns:
        Dict com status, caminho do arquivo e metadados
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"Lista_imoveis_{estado}.csv"
    filepath = DATA_DIR / filename

    # Verifica se precisa atualizar
    if not needs_update(estado, force):
        metadata = get_cache_metadata()
        cached = metadata.get(f"Lista_imoveis_{estado}", {})
        logger.info(f"Usando cache existente: {filepath}")
        return {
            "status": "cached",
            "filepath": str(filepath),
            "last_update": cached.get("last_update"),
            "total_imoveis": cached.get("total_imoveis", 0),
            "hash": cached.get("hash"),
            "message": f"Arquivo em cache (atualizado em {cached.get('last_update')})"
        }

    # Faz download
    try:
        logger.info(f"Baixando CSV para {estado}...")

        # Simula requisicao ao site da Caixa
        # Na pratica, pode precisar de session/cookies
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/csv,application/csv,text/plain",
            "Referer": CAIXA_DOWNLOAD_URL
        }

        # URL de download (pode variar conforme o site)
        download_url = f"{CAIXA_DOWNLOAD_URL}?uf={estado}"

        response = requests.get(download_url, headers=headers, timeout=60)

        if response.status_code == 200:
            # Salva arquivo
            with open(filepath, 'wb') as f:
                f.write(response.content)

            # Conta linhas
            df = pd.read_csv(filepath, sep=';', encoding='latin-1', on_bad_lines='skip')
            total_imoveis = len(df)

            # Atualiza metadata
            new_hash = file_hash(filepath)
            metadata = get_cache_metadata()
            old_hash = metadata.get(f"Lista_imoveis_{estado}", {}).get("hash", "")

            metadata[f"Lista_imoveis_{estado}"] = {
                "last_update": datetime.now().isoformat(),
                "total_imoveis": total_imoveis,
                "hash": new_hash,
                "filesize_kb": filepath.stat().st_size / 1024
            }
            save_cache_metadata(metadata)

            changed = new_hash != old_hash

            return {
                "status": "updated" if changed else "no_changes",
                "filepath": str(filepath),
                "last_update": datetime.now().isoformat(),
                "total_imoveis": total_imoveis,
                "hash": new_hash,
                "changed": changed,
                "message": f"Download concluido: {total_imoveis} imoveis"
            }
        else:
            # Fallback: usa cache existente se disponivel
            if filepath.exists():
                logger.warning(f"Download falhou (HTTP {response.status_code}), usando cache existente")
                metadata = get_cache_metadata()
                cached = metadata.get(f"Lista_imoveis_{estado}", {})
                return {
                    "status": "cached",
                    "filepath": str(filepath),
                    "last_update": cached.get("last_update"),
                    "total_imoveis": cached.get("total_imoveis", 0),
                    "hash": cached.get("hash"),
                    "message": f"Download falhou, usando cache existente"
                }
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "message": "Falha ao baixar arquivo"
            }

    except Exception as e:
        logger.error(f"Erro no download: {str(e)}")
        # Fallback: usa cache existente se disponivel
        if filepath.exists():
            logger.warning(f"Erro no download, usando cache existente: {filepath}")
            metadata = get_cache_metadata()
            cached = metadata.get(f"Lista_imoveis_{estado}", {})
            return {
                "status": "cached",
                "filepath": str(filepath),
                "last_update": cached.get("last_update"),
                "total_imoveis": cached.get("total_imoveis", 0),
                "hash": cached.get("hash"),
                "message": f"Erro no download, usando cache existente"
            }
        return {
            "status": "error",
            "error": str(e),
            "message": "Erro durante download"
        }


def parse_csv_imoveis(csv_path: str) -> List[Dict]:
    """
    Parseia CSV de imoveis da Caixa e normaliza os dados.

    Args:
        csv_path: Caminho do arquivo CSV

    Returns:
        Lista de dicionarios com dados normalizados
    """
    try:
        # Verifica se arquivo existe
        if not Path(csv_path).exists():
            logger.error(f"Arquivo nao encontrado: {csv_path}")
            return []

        # Verifica se o arquivo e HTML (site da Caixa pode retornar HTML ao inves de CSV)
        with open(csv_path, 'r', encoding='latin-1', errors='ignore') as f:
            first_line = f.read(500)
            if '<!DOCTYPE' in first_line or '<html' in first_line.lower():
                logger.error(f"Arquivo contem HTML ao inves de CSV. Site da Caixa requer sessao/cookies.")
                logger.info("Tentando usar dados dos scrapers como fonte alternativa...")
                return []

        # Tenta ler o CSV com diferentes configuracoes
        try:
            df = pd.read_csv(csv_path, sep=';', encoding='latin-1', on_bad_lines='skip')
        except Exception as e1:
            logger.warning(f"Erro com sep=';', tentando com ','...")
            try:
                df = pd.read_csv(csv_path, sep=',', encoding='latin-1', on_bad_lines='skip')
            except Exception as e2:
                logger.error(f"Erro ao ler CSV: {e1}, {e2}")
                return []

        # Verifica se tem colunas suficientes
        if len(df.columns) < 6:
            logger.error(f"CSV com poucas colunas ({len(df.columns)}). Formato invalido.")
            return []

        # Normaliza nomes das colunas (tenta mapear colunas existentes)
        expected_cols = [
            'id_imovel', 'uf', 'cidade', 'bairro', 'endereco',
            'preco', 'valor_avaliacao', 'desconto', 'descricao',
            'modalidade', 'link'
        ]

        # Se tiver 11 colunas, usa mapeamento direto
        if len(df.columns) == 11:
            df.columns = expected_cols
        else:
            # Tenta mapear colunas por nome ou posicao
            logger.warning(f"CSV com {len(df.columns)} colunas (esperado 11). Tentando adaptar...")
            # Usa as colunas existentes e preenche as faltantes
            current_cols = list(df.columns)
            new_cols = expected_cols[:len(current_cols)]
            df.columns = new_cols

        # Limpa espacos
        for col in ['uf', 'cidade', 'bairro', 'endereco', 'modalidade']:
            df[col] = df[col].str.strip()

        # Converte valores numericos
        df['preco'] = pd.to_numeric(
            df['preco'].astype(str).str.replace('.', '').str.replace(',', '.'),
            errors='coerce'
        )
        df['valor_avaliacao'] = pd.to_numeric(
            df['valor_avaliacao'].astype(str).str.replace('.', '').str.replace(',', '.'),
            errors='coerce'
        )
        df['desconto'] = pd.to_numeric(
            df['desconto'].astype(str).str.replace(',', '.'),
            errors='coerce'
        )

        # Extrai dados da descricao
        def parse_descricao(desc: str) -> Dict:
            """Extrai tipo, area, quartos da descricao"""
            result = {
                'tipo_imovel': 'Outro',
                'area_privativa': 0,
                'area_total': 0,
                'quartos': 0,
                'vagas': 0
            }

            if pd.isna(desc):
                return result

            desc = str(desc).lower()

            # Tipo
            if 'apartamento' in desc:
                result['tipo_imovel'] = 'Apartamento'
            elif 'casa' in desc:
                result['tipo_imovel'] = 'Casa'
            elif 'terreno' in desc:
                result['tipo_imovel'] = 'Terreno'
            elif 'sala' in desc or 'comercial' in desc:
                result['tipo_imovel'] = 'Comercial'

            # Area privativa
            import re
            match = re.search(r'(\d+[\.,]?\d*)\s*de\s*[aá]rea\s*privativa', desc)
            if match:
                result['area_privativa'] = float(match.group(1).replace(',', '.'))

            # Area total
            match = re.search(r'(\d+[\.,]?\d*)\s*de\s*[aá]rea\s*total', desc)
            if match:
                result['area_total'] = float(match.group(1).replace(',', '.'))

            # Quartos
            match = re.search(r'(\d+)\s*qto', desc)
            if match:
                result['quartos'] = int(match.group(1))

            # Vagas
            match = re.search(r'(\d+)\s*vaga', desc)
            if match:
                result['vagas'] = int(match.group(1))

            return result

        # Aplica parsing da descricao
        desc_parsed = df['descricao'].apply(parse_descricao)
        df['tipo_imovel'] = desc_parsed.apply(lambda x: x['tipo_imovel'])
        df['area_privativa'] = desc_parsed.apply(lambda x: x['area_privativa'])
        df['area_total'] = desc_parsed.apply(lambda x: x['area_total'])
        df['quartos'] = desc_parsed.apply(lambda x: x['quartos'])
        df['vagas'] = desc_parsed.apply(lambda x: x['vagas'])

        # Identifica 2a praca pelo desconto (geralmente > 30%)
        df['praca'] = df['desconto'].apply(lambda x: '2a Praca' if x and x > 30 else '1a Praca')

        return df.to_dict('records')

    except Exception as e:
        logger.error(f"Erro ao parsear CSV: {str(e)}")
        return []


def filter_imoveis(
    imoveis: List[Dict],
    preco_max: float = 150000,
    tipo: str = "Apartamento",
    praca: str = "2a Praca",
    cidades: Optional[List[str]] = None
) -> Dict:
    """
    Filtra lista de imoveis por criterios.

    Args:
        imoveis: Lista de imoveis parseados
        preco_max: Preco maximo (default: 150000)
        tipo: Tipo de imovel (default: Apartamento)
        praca: 1a ou 2a Praca (default: 2a Praca)
        cidades: Lista de cidades alvo (default: SP + Litoral)

    Returns:
        Dict com imoveis filtrados e estatisticas
    """
    if cidades is None:
        cidades = CIDADES_ALVO

    # Normaliza cidades para uppercase
    cidades = [c.upper() for c in cidades]

    df = pd.DataFrame(imoveis)

    total_original = len(df)

    # Aplica filtros
    filtros_aplicados = []

    # Filtro de preco
    if preco_max > 0:
        df = df[df['preco'] <= preco_max]
        filtros_aplicados.append(f"preco <= R$ {preco_max:,.2f}")

    # Filtro de tipo
    if tipo:
        df = df[df['tipo_imovel'].str.upper() == tipo.upper()]
        filtros_aplicados.append(f"tipo = {tipo}")

    # Filtro de praca
    if praca:
        df = df[df['praca'] == praca]
        filtros_aplicados.append(f"praca = {praca}")

    # Filtro de cidades
    if cidades:
        df = df[df['cidade'].str.upper().isin(cidades)]
        filtros_aplicados.append(f"cidades = {len(cidades)} cidades")

    # Remove duplicatas por ID
    df = df.drop_duplicates(subset=['id_imovel'])

    # Ordena por desconto (maior primeiro)
    df = df.sort_values('desconto', ascending=False)

    imoveis_filtrados = df.to_dict('records')

    # Estatisticas
    stats = {
        "total_original": total_original,
        "total_filtrado": len(imoveis_filtrados),
        "taxa_filtragem": f"{(len(imoveis_filtrados)/total_original*100):.1f}%" if total_original > 0 else "0%",
        "filtros_aplicados": filtros_aplicados,
        "preco_medio": df['preco'].mean() if len(df) > 0 else 0,
        "preco_min": df['preco'].min() if len(df) > 0 else 0,
        "preco_max": df['preco'].max() if len(df) > 0 else 0,
        "desconto_medio": df['desconto'].mean() if len(df) > 0 else 0,
        "cidades_encontradas": df['cidade'].unique().tolist() if len(df) > 0 else []
    }

    return {
        "imoveis": imoveis_filtrados,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }


def check_update_schedule() -> Dict:
    """
    Verifica agenda de atualizacoes e proximo download.

    Returns:
        Dict com status das atualizacoes e proxima data
    """
    metadata = get_cache_metadata()

    # Calcula proxima atualizacao (segunda ou quinta)
    today = datetime.now()
    days_ahead = {
        0: 0,  # Segunda
        1: 2,  # Terca -> Quinta
        2: 1,  # Quarta -> Quinta
        3: 0,  # Quinta
        4: 3,  # Sexta -> Segunda
        5: 2,  # Sabado -> Segunda
        6: 1   # Domingo -> Segunda
    }

    next_update = today + timedelta(days=days_ahead[today.weekday()])
    next_update = next_update.replace(hour=8, minute=0, second=0, microsecond=0)

    estados_status = {}
    for key, data in metadata.items():
        if key.startswith("Lista_imoveis_"):
            estado = key.replace("Lista_imoveis_", "")
            last_update = datetime.fromisoformat(data.get("last_update", "2000-01-01"))
            dias_desde = (today - last_update).days

            estados_status[estado] = {
                "last_update": data.get("last_update"),
                "dias_desde_atualizacao": dias_desde,
                "total_imoveis": data.get("total_imoveis", 0),
                "precisa_atualizar": needs_update(estado)
            }

    return {
        "schedule": "Segunda e Quinta-feira as 08:00",
        "proxima_atualizacao": next_update.isoformat(),
        "hoje": today.isoformat(),
        "estados": estados_status
    }


# ============================================================================
# COLETA MULTI-FONTE - Web Scrapers de Leiloes
# ============================================================================

import asyncio
from typing import Tuple


async def coletar_todas_fontes(
    estado: str = "SP",
    preco_max: float = 200000,
    max_por_fonte: int = 50,
    coletar_detalhes: bool = False
) -> Dict:
    """
    Executa todos os scrapers em paralelo e consolida resultados.

    Args:
        estado: Estado para filtrar (default: SP)
        preco_max: Preco maximo (default: 200000)
        max_por_fonte: Maximo de imoveis por fonte (default: 50)
        coletar_detalhes: Se deve coletar detalhes de cada imovel (mais lento)

    Returns:
        Dict com imoveis consolidados e estatisticas por fonte
    """
    # Verifica se Playwright esta disponivel antes de importar scrapers
    try:
        from playwright.async_api import async_playwright
        # Testa se Chromium esta instalado
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
        logger.info("[MULTI-FONTE] Playwright/Chromium verificado com sucesso")
    except Exception as e:
        logger.error(f"[MULTI-FONTE] Playwright nao disponivel: {e}")
        return {
            "imoveis": [],
            "stats_por_fonte": {},
            "total_bruto": 0,
            "total_unico": 0,
            "duplicatas_removidas": 0,
            "fontes_com_erro": 1,
            "erros": [{"fonte": "playwright", "erro": f"Playwright/Chromium nao disponivel: {str(e)}"}],
            "timestamp": datetime.now().isoformat()
        }

    from scrapers import (
        ZukScraper,
        SuperbidScraper,
        MegaLeiloesScraper,
        FrazaoScraper,
        BiasiScraper
    )

    logger.info(f"[MULTI-FONTE] Iniciando coleta de {5} fontes...")

    scrapers = [
        ("portal_zuk", ZukScraper()),
        ("superbid", SuperbidScraper()),
        ("mega_leiloes", MegaLeiloesScraper()),
        ("frazao_leiloes", FrazaoScraper()),
        # ("biasi_leiloes", BiasiScraper()),  # Desabilitado: muito lento (~7 min) e sem resultados
    ]

    resultados = {}
    todos_imoveis = []
    erros = []

    # Executa scrapers sequencialmente para evitar bloqueio
    for nome_fonte, scraper in scrapers:
        try:
            logger.info(f"[MULTI-FONTE] Coletando {nome_fonte}...")

            imoveis = await scraper.executar(
                coletar_detalhes=coletar_detalhes,
                max_imoveis=max_por_fonte
            )

            # Aplica filtro de preco
            imoveis_filtrados = [
                i for i in imoveis
                if i.get('preco', float('inf')) <= preco_max
            ]

            resultados[nome_fonte] = {
                "total_coletados": len(imoveis),
                "total_filtrados": len(imoveis_filtrados),
                "status": "sucesso"
            }

            todos_imoveis.extend(imoveis_filtrados)
            logger.info(f"[MULTI-FONTE] {nome_fonte}: {len(imoveis_filtrados)} imoveis")

        except Exception as e:
            logger.error(f"[MULTI-FONTE] Erro em {nome_fonte}: {e}")
            resultados[nome_fonte] = {
                "total_coletados": 0,
                "total_filtrados": 0,
                "status": "erro",
                "erro": str(e)
            }
            erros.append({"fonte": nome_fonte, "erro": str(e)})

    # Remove duplicatas (por endereco similar + preco proximo)
    imoveis_unicos = remover_duplicatas_multifonte(todos_imoveis)

    return {
        "imoveis": imoveis_unicos,
        "stats_por_fonte": resultados,
        "total_bruto": len(todos_imoveis),
        "total_unico": len(imoveis_unicos),
        "duplicatas_removidas": len(todos_imoveis) - len(imoveis_unicos),
        "fontes_com_erro": len(erros),
        "erros": erros,
        "timestamp": datetime.now().isoformat()
    }


def remover_duplicatas_multifonte(imoveis: List[Dict]) -> List[Dict]:
    """
    Remove duplicatas entre fontes diferentes.
    Usa endereco normalizado + faixa de preco para identificar duplicatas.
    """
    vistos = set()
    unicos = []

    for imovel in imoveis:
        # Cria chave de deduplicacao
        endereco = imovel.get('endereco', '').lower()
        # Normaliza endereco (remove acentos, espacos extras)
        endereco_norm = ''.join(c for c in endereco if c.isalnum())

        preco = imovel.get('preco', 0)
        # Agrupa precos em faixas de 5000
        faixa_preco = int(preco / 5000) * 5000

        chave = f"{endereco_norm[:50]}_{faixa_preco}"

        if chave not in vistos:
            vistos.add(chave)
            unicos.append(imovel)

    return unicos


def consolidar_todas_fontes(
    imoveis_caixa: List[Dict],
    imoveis_scrapers: List[Dict]
) -> List[Dict]:
    """
    Consolida imoveis da Caixa com imoveis dos scrapers.

    Args:
        imoveis_caixa: Lista de imoveis do CSV da Caixa
        imoveis_scrapers: Lista de imoveis dos web scrapers

    Returns:
        Lista consolidada sem duplicatas
    """
    # Marca fonte nos imoveis da Caixa
    for imovel in imoveis_caixa:
        imovel['fonte'] = 'caixa'

    # Junta todas as listas
    todos = imoveis_caixa + imoveis_scrapers

    # Remove duplicatas
    return remover_duplicatas_multifonte(todos)


def executar_coleta_multifonte_sync(
    estado: str = "SP",
    preco_max: float = 200000,
    incluir_caixa: bool = True,
    max_por_fonte: int = 50
) -> Dict:
    """
    Wrapper sincrono para a coleta multi-fonte.
    Combina Caixa + Web Scrapers.

    Args:
        estado: Estado (default: SP)
        preco_max: Preco maximo
        incluir_caixa: Se deve incluir dados da Caixa
        max_por_fonte: Maximo de imoveis por fonte

    Returns:
        Dict com todos os imoveis consolidados
    """
    imoveis_caixa = []
    stats_caixa = {}

    # 1. Coleta Caixa (se habilitado)
    if incluir_caixa:
        try:
            result = download_csv_caixa(estado, force=False)
            if result["status"] in ["cached", "updated", "no_changes"]:
                imoveis_raw = parse_csv_imoveis(result["filepath"])
                filtrado = filter_imoveis(
                    imoveis_raw,
                    preco_max=preco_max,
                    tipo="Apartamento",
                    praca="2a Praca",
                    cidades=CIDADES_ALVO
                )
                imoveis_caixa = filtrado["imoveis"]
                stats_caixa = {
                    "total": len(imoveis_caixa),
                    "status": "sucesso",
                    "source": result["status"]
                }
        except Exception as e:
            logger.error(f"[COLETA] Erro na Caixa: {e}")
            stats_caixa = {"total": 0, "status": "erro", "erro": str(e)}

    # 2. Coleta Web Scrapers (com fallback se Playwright nao disponivel)
    resultado_scrapers = {
        "imoveis": [],
        "stats_por_fonte": {},
        "duplicatas_removidas": 0,
        "erros": []
    }

    try:
        # Tenta importar e verificar se Playwright esta disponivel
        try:
            from playwright.async_api import async_playwright
            playwright_disponivel = True
        except ImportError:
            playwright_disponivel = False
            logger.warning("[COLETA] Playwright nao instalado - scrapers desabilitados")

        if playwright_disponivel:
            # Usa asyncio.run() que e mais seguro em contextos sincronos
            # Cria nova thread para evitar conflito com event loops existentes
            import concurrent.futures

            def executar_scrapers():
                """Executa scrapers em um novo event loop isolado"""
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        coletar_todas_fontes(
                            estado=estado,
                            preco_max=preco_max,
                            max_por_fonte=max_por_fonte,
                            coletar_detalhes=False
                        )
                    )
                finally:
                    loop.close()

            # Executa em thread separada para evitar conflitos de event loop
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(executar_scrapers)
                resultado_scrapers = future.result(timeout=900)  # 15 min timeout

    except concurrent.futures.TimeoutError:
        logger.error("[COLETA] Timeout nos scrapers (15 min)")
        resultado_scrapers["erros"].append({"fonte": "scrapers", "erro": "Timeout apos 15 minutos"})
    except Exception as e:
        logger.error(f"[COLETA] Erro nos scrapers: {e}")
        resultado_scrapers["erros"].append({"fonte": "scrapers", "erro": str(e)})

    # 3. Consolida
    imoveis_consolidados = consolidar_todas_fontes(
        imoveis_caixa,
        resultado_scrapers["imoveis"]
    )

    # 4. Ordena por desconto
    imoveis_consolidados.sort(
        key=lambda x: x.get('desconto', 0),
        reverse=True
    )

    # Estatisticas finais
    return {
        "imoveis": imoveis_consolidados,
        "stats": {
            "total_consolidado": len(imoveis_consolidados),
            "fonte_caixa": stats_caixa.get("total", 0),
            "fonte_zuk": resultado_scrapers["stats_por_fonte"].get("portal_zuk", {}).get("total_filtrados", 0),
            "fonte_superbid": resultado_scrapers["stats_por_fonte"].get("superbid", {}).get("total_filtrados", 0),
            "fonte_megaleiloes": resultado_scrapers["stats_por_fonte"].get("mega_leiloes", {}).get("total_filtrados", 0),
            "fonte_frazao": resultado_scrapers["stats_por_fonte"].get("frazao_leiloes", {}).get("total_filtrados", 0),
            "fonte_biasi": resultado_scrapers["stats_por_fonte"].get("biasi_leiloes", {}).get("total_filtrados", 0),
            "duplicatas_removidas": resultado_scrapers.get("duplicatas_removidas", 0),
            "erros": resultado_scrapers.get("erros", [])
        },
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# PESQUISA DE MERCADO - VivaReal, ZapImoveis, OLX
# ============================================================================

def pesquisar_mercado(
    bairro: str,
    cidade: str = "sao-paulo",
    uf: str = "sp",
    tipo: str = "apartamento",
    quartos: int = 2,
    area_m2: float = 50.0,
    fontes: List[str] = None,
    usar_scraping: bool = False  # OTIMIZADO: desabilitado por padrao para velocidade
) -> Dict:
    """
    Pesquisa precos de mercado para um bairro especifico.

    MODO RAPIDO (padrao): Usa tabela FipeZap com 50+ bairros de SP (~1ms)
    MODO SCRAPING: Usa VivaReal, ZapImoveis e OLX (~2-5min por imovel)

    Args:
        bairro: Nome do bairro (ex: "guaianazes")
        cidade: Nome da cidade (ex: "sao-paulo")
        uf: Sigla do estado (ex: "sp")
        tipo: Tipo do imovel (apartamento, casa)
        quartos: Numero de quartos
        area_m2: Area do imovel em m2
        fontes: Lista de fontes (vivareal, zapimoveis, olx)
        usar_scraping: Se True, faz scraping real (lento). Default False (rapido).

    Returns:
        Dict com dados de mercado (precos, estatisticas, imoveis comparaveis)
    """
    # MODO RAPIDO: Usa tabela FipeZap diretamente (recomendado)
    if not usar_scraping:
        logger.info(f"[MERCADO] FipeZap rapido: {bairro}, {cidade}")
        return _gerar_estimativa_fipezap(bairro, cidade, tipo, quartos, area_m2)

    # MODO SCRAPING: Busca em tempo real (lento, pode falhar)
    try:
        import sys
        from pathlib import Path

        scrapers_dir = Path(__file__).parent.parent / "scrapers"
        if str(scrapers_dir) not in sys.path:
            sys.path.insert(0, str(scrapers_dir))

        from mercado_scraper import pesquisar_mercado_sync

        logger.info(f"[MERCADO] Scraping: {bairro}, {cidade}-{uf.upper()}")

        resultado = pesquisar_mercado_sync(
            bairro=bairro,
            cidade=cidade,
            uf=uf,
            tipo=tipo,
            quartos=quartos,
            area_referencia=area_m2,
            fontes=fontes,
            usar_fallback=True
        )

        logger.info(f"[MERCADO] Status: {resultado.get('status')}, Fonte: {resultado.get('fonte')}")
        return resultado

    except ImportError as e:
        logger.error(f"[MERCADO] Erro de importacao: {e}")
        return _gerar_estimativa_fipezap(bairro, cidade, tipo, quartos, area_m2)

    except Exception as e:
        logger.error(f"[MERCADO] Erro na pesquisa: {e}")
        return _gerar_estimativa_fipezap(bairro, cidade, tipo, quartos, area_m2)


# Tabela de precos FipeZap por bairro/cidade (Dez 2024)
# Fonte: FipeZap - Indice de precos de imoveis
PRECOS_FIPEZAP_M2 = {
    # === SAO PAULO CAPITAL - ZONA LESTE ===
    "guaianazes": 3800,
    "itaim paulista": 3900,
    "cidade tiradentes": 3500,
    "sao miguel paulista": 4200,
    "sao miguel": 4200,
    "ermelino matarazzo": 4500,
    "penha": 5500,
    "tatuape": 8500,
    "mooca": 9000,
    "vila prudente": 7000,
    "aricanduva": 5000,
    "itaquera": 4200,
    "sao mateus": 4000,
    "vila formosa": 6500,
    "belem": 7000,
    "bras": 6000,
    "pari": 5500,
    "cangaiba": 4800,
    "artur alvim": 4300,
    "jose bonifacio": 4000,
    "jardim helena": 3600,
    "vila jacui": 3800,
    "lajeado": 3700,
    "iguatemi": 3900,
    "jardim iva": 4500,
    "agua rasa": 7500,
    "carrão": 7000,
    "carrao": 7000,
    "vila matilde": 5800,
    "vila ema": 5200,
    "sapopemba": 4000,
    "sao lucas": 5500,
    "vila alpina": 5000,

    # === SAO PAULO CAPITAL - ZONA SUL ===
    "jabaquara": 7500,
    "saude": 9500,
    "santo amaro": 8000,
    "campo limpo": 5500,
    "capao redondo": 4200,
    "jardim angela": 3500,
    "grajau": 3800,
    "interlagos": 6500,
    "cidade dutra": 4500,
    "socorro": 5500,
    "cidade ademar": 4800,
    "pedreira": 4300,
    "jardim sao luis": 4000,
    "parelheiros": 3200,
    "marsilac": 2800,
    "moema": 14000,
    "vila mariana": 12000,
    "ipiranga": 8000,
    "cursino": 7500,
    "sacoma": 6000,
    "vila das merces": 5500,
    "campo belo": 13000,
    "brooklin": 14000,
    "itaim bibi": 16000,
    "vila olimpia": 15000,
    "morumbi": 11000,
    "campo grande": 7000,
    "vila andrade": 8500,
    "jardim angela": 3500,

    # === SAO PAULO CAPITAL - ZONA NORTE ===
    "santana": 9000,
    "tucuruvi": 7500,
    "freguesia do o": 6000,
    "brasilandia": 4500,
    "cachoeirinha": 5000,
    "pirituba": 6000,
    "jaragua": 4500,
    "perus": 4000,
    "anhanguera": 3800,
    "tremembe": 6500,
    "mandaqui": 7000,
    "vila guilherme": 7000,
    "vila maria": 6000,
    "casa verde": 7500,
    "limao": 6500,
    "vila medeiros": 5500,
    "jaçana": 5000,
    "jacana": 5000,
    "horto florestal": 9000,
    "lauzane paulista": 7000,
    "vila nova cachoeirinha": 5500,

    # === SAO PAULO CAPITAL - ZONA OESTE ===
    "lapa": 10000,
    "perdizes": 12000,
    "pinheiros": 15000,
    "butanta": 8500,
    "rio pequeno": 7000,
    "raposo tavares": 5500,
    "jaguare": 7500,
    "vila sonia": 8000,
    "morumbi": 11000,
    "vila leopoldina": 9500,
    "alto de pinheiros": 16000,
    "jardim paulista": 15000,
    "cerqueira cesar": 14000,
    "consolacao": 12000,
    "barra funda": 9000,
    "agua branca": 9500,
    "pompeia": 10000,
    "sumare": 10500,
    "pacaembu": 14000,
    "higienopolis": 13000,

    # === SAO PAULO CAPITAL - CENTRO ===
    "se": 8000,
    "republica": 7500,
    "liberdade": 9500,
    "bela vista": 11000,
    "cambuci": 7000,
    "aclimacao": 10000,
    "santa cecilia": 9000,
    "bom retiro": 6500,
    "luz": 6000,

    # === GRANDE SAO PAULO ===
    "guarulhos": 5500,
    "osasco": 6000,
    "santo andre": 6500,
    "sao bernardo": 7000,
    "sao bernardo do campo": 7000,
    "sao caetano": 9000,
    "sao caetano do sul": 9000,
    "diadema": 5000,
    "maua": 4500,
    "mogi das cruzes": 5000,
    "suzano": 4200,
    "itaquaquecetuba": 3800,
    "ferraz de vasconcelos": 4000,
    "barueri": 7500,
    "carapicuiba": 4500,
    "cotia": 5500,
    "taboao da serra": 5500,
    "embu das artes": 4800,
    "embu": 4800,
    "itapecerica da serra": 4500,
    "francisco morato": 3500,
    "franco da rocha": 3800,
    "caieiras": 4500,
    "aruja": 5500,
    "santana de parnaiba": 7000,
    "jandira": 4800,
    "itapevi": 4200,
    "poa": 4500,

    # === LITORAL PAULISTA ===
    "santos": 8500,
    "guaruja": 6500,
    "praia grande": 5500,
    "sao vicente": 5000,
    "cubatao": 4500,
    "bertioga": 7000,
    "mongagua": 4500,
    "itanhaem": 4200,
    "peruibe": 4000,
    "caraguatatuba": 5500,
    "ubatuba": 6000,
    "ilhabela": 8000,
    "sao sebastiao": 5500,

    # === INTERIOR SP - CIDADES GRANDES ===
    "campinas": 7500,
    "ribeirao preto": 6500,
    "sorocaba": 5500,
    "sao jose dos campos": 6500,
    "jundiai": 6000,
    "piracicaba": 5000,
    "bauru": 4500,
    "limeira": 4500,
    "taubate": 5000,
    "franca": 4000,
    "marilia": 4000,
    "presidente prudente": 3800,
    "sao jose do rio preto": 5000,
    "araraquara": 4500,
    "rio claro": 4500,
    "americana": 5000,
    "indaiatuba": 5500,
    "valinhos": 6000,
    "vinhedo": 7000,
    "atibaia": 5500,
    "braganca paulista": 4500,
    "itu": 4500,
    "salto": 4500,
    "jacarei": 4500,
    "mogi guacu": 4000,
    "mogi mirim": 4000,
    "sumare": 4500,
    "hortolandia": 4200,
    "paulinia": 5500,
    "tatui": 4000,
    "botucatu": 4500,

    # === OUTROS ESTADOS (capitais) ===
    "rio de janeiro": 9000,
    "belo horizonte": 7000,
    "curitiba": 7500,
    "porto alegre": 7000,
    "brasilia": 9000,
    "salvador": 6000,
    "fortaleza": 6500,
    "recife": 6500,
    "manaus": 5500,
    "goiania": 5500,
    "belem": 5000,
    "florianopolis": 9500,
    "vitoria": 7500,
    "natal": 6000,
    "joao pessoa": 5500,
    "maceio": 5500,
    "teresina": 4500,
    "campo grande": 5000,
    "cuiaba": 5000,

    # === DEFAULTS POR REGIAO ===
    "default_sp_leste": 4500,
    "default_sp_sul": 6500,
    "default_sp_norte": 6000,
    "default_sp_oeste": 9000,
    "default_sp_centro": 8000,
    "default_grande_sp": 5500,
    "default_litoral": 5500,
    "default_interior": 5000,
    "default": 5500
}


def _gerar_estimativa_fipezap(
    bairro: str,
    cidade: str,
    tipo: str,
    quartos: int,
    area_m2: float
) -> Dict:
    """
    Gera estimativa de mercado usando tabela FipeZap.
    Mais de 200 bairros/cidades mapeados.
    """
    # Normaliza bairro para busca
    bairro_lower = bairro.lower().strip()
    # Remove caracteres especiais e acentos simples
    bairro_lower = bairro_lower.replace("ã", "a").replace("õ", "o").replace("ç", "c")
    bairro_lower = bairro_lower.replace("á", "a").replace("é", "e").replace("í", "i")
    bairro_lower = bairro_lower.replace("ó", "o").replace("ú", "u").replace("â", "a")
    bairro_lower = bairro_lower.replace("ê", "e").replace("ô", "o")

    # Normaliza cidade
    cidade_lower = cidade.lower().strip()
    cidade_lower = cidade_lower.replace("-", " ").replace("_", " ")
    cidade_lower = cidade_lower.replace("ã", "a").replace("õ", "o").replace("ç", "c")
    cidade_lower = cidade_lower.replace("á", "a").replace("é", "e").replace("í", "i")
    cidade_lower = cidade_lower.replace("ó", "o").replace("ú", "u")

    # Busca preco: primeiro por bairro, depois por cidade
    preco_m2 = PRECOS_FIPEZAP_M2.get(bairro_lower)

    if not preco_m2:
        # Tenta busca parcial no bairro
        for key in PRECOS_FIPEZAP_M2:
            if key in bairro_lower or bairro_lower in key:
                preco_m2 = PRECOS_FIPEZAP_M2[key]
                break

    if not preco_m2:
        # Busca pela cidade
        preco_m2 = PRECOS_FIPEZAP_M2.get(cidade_lower)

    if not preco_m2:
        # Tenta busca parcial na cidade
        for key in PRECOS_FIPEZAP_M2:
            if key in cidade_lower or cidade_lower in key:
                preco_m2 = PRECOS_FIPEZAP_M2[key]
                break

    if not preco_m2:
        # Default
        preco_m2 = PRECOS_FIPEZAP_M2['default']

    # Ajustes por tipo de imovel
    if tipo and tipo.lower() == 'casa':
        preco_m2 *= 0.85  # Casas geralmente mais baratas que aptos
    elif tipo and 'comercial' in tipo.lower():
        preco_m2 *= 0.75  # Comercial ainda mais barato

    # Ajuste por quartos
    if quartos >= 3:
        preco_m2 *= 1.05  # Imoveis maiores tem preco/m2 ligeiramente maior
    elif quartos >= 4:
        preco_m2 *= 1.10

    valor_estimado = preco_m2 * area_m2

    return {
        'status': 'sucesso',
        'bairro': bairro,
        'cidade': cidade,
        'tipo': tipo,
        'quartos': quartos,
        'total_encontrados': 0,
        'stats_fontes': {'fipezap': 1},
        'precos': {
            'medio': round(valor_estimado, 2),
            'mediano': round(valor_estimado, 2),
            'minimo': round(valor_estimado * 0.85, 2),
            'maximo': round(valor_estimado * 1.20, 2)
        },
        'preco_m2': {
            'medio': round(preco_m2, 2),
            'mediano': round(preco_m2, 2)
        },
        'valor_estimado': {
            'area_referencia': area_m2,
            'valor': round(valor_estimado, 2)
        },
        'imoveis': [],
        'fonte': 'FipeZap (tabela local)',
        'nota': 'Precos medios por m2 atualizados Dez 2024'
    }


def _gerar_estimativa_basica(
    bairro: str,
    cidade: str,
    tipo: str,
    quartos: int,
    area_m2: float
) -> Dict:
    """Alias para compatibilidade - usa FipeZap"""
    return _gerar_estimativa_fipezap(bairro, cidade, tipo, quartos, area_m2)


def comparar_imovel_mercado(
    imovel: Dict,
    dados_mercado: Dict
) -> Dict:
    """
    Compara um imovel de leilao com dados de mercado.

    Args:
        imovel: Dados do imovel de leilao
        dados_mercado: Resultado da pesquisa de mercado

    Returns:
        Dict com analise comparativa
    """
    preco_leilao = imovel.get('preco', 0)
    valor_avaliacao = imovel.get('valor_avaliacao', preco_leilao)

    preco_mercado_medio = dados_mercado.get('precos', {}).get('medio', 0)
    preco_mercado_min = dados_mercado.get('precos', {}).get('minimo', 0)

    # Calcula descontos
    desconto_avaliacao = ((valor_avaliacao - preco_leilao) / valor_avaliacao * 100) if valor_avaliacao > 0 else 0
    desconto_mercado = ((preco_mercado_medio - preco_leilao) / preco_mercado_medio * 100) if preco_mercado_medio > 0 else 0

    # Potencial de lucro bruto
    lucro_bruto_potencial = preco_mercado_medio - preco_leilao
    margem_bruta = (lucro_bruto_potencial / preco_leilao * 100) if preco_leilao > 0 else 0

    # Classificacao de oportunidade
    if desconto_mercado >= 40:
        classificacao = "EXCELENTE"
    elif desconto_mercado >= 30:
        classificacao = "MUITO_BOA"
    elif desconto_mercado >= 20:
        classificacao = "BOA"
    elif desconto_mercado >= 10:
        classificacao = "MODERADA"
    else:
        classificacao = "BAIXA"

    return {
        'preco_leilao': preco_leilao,
        'valor_avaliacao': valor_avaliacao,
        'preco_mercado_medio': preco_mercado_medio,
        'preco_mercado_minimo': preco_mercado_min,
        'desconto_vs_avaliacao': round(desconto_avaliacao, 2),
        'desconto_vs_mercado': round(desconto_mercado, 2),
        'lucro_bruto_potencial': round(lucro_bruto_potencial, 2),
        'margem_bruta_pct': round(margem_bruta, 2),
        'classificacao_oportunidade': classificacao,
        'fonte_mercado': dados_mercado.get('fonte', 'N/A'),
        'total_comparaveis': dados_mercado.get('total_encontrados', 0)
    }


# Exemplo de uso
if __name__ == "__main__":
    # Testa download Caixa
    result = download_csv_caixa("SP", force=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["status"] in ["cached", "updated", "no_changes"]:
        # Parseia
        imoveis = parse_csv_imoveis(result["filepath"])
        print(f"\nTotal parseado: {len(imoveis)}")

        # Filtra
        filtrado = filter_imoveis(
            imoveis,
            preco_max=150000,
            tipo="Apartamento",
            praca="2a Praca"
        )
        print(f"\nTotal filtrado: {filtrado['stats']['total_filtrado']}")
        print(json.dumps(filtrado['stats'], indent=2, ensure_ascii=False))

    # Testa coleta multi-fonte (descomente para testar)
    # print("\n" + "="*50)
    # print("Testando coleta multi-fonte...")
    # resultado = executar_coleta_multifonte_sync(
    #     estado="SP",
    #     preco_max=200000,
    #     incluir_caixa=True,
    #     max_por_fonte=10
    # )
    # print(f"Total consolidado: {resultado['stats']['total_consolidado']}")
    # print(json.dumps(resultado['stats'], indent=2, ensure_ascii=False))
