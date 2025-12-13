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
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "message": "Falha ao baixar arquivo"
            }

    except Exception as e:
        logger.error(f"Erro no download: {str(e)}")
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
        df = pd.read_csv(csv_path, sep=';', encoding='latin-1', on_bad_lines='skip')

        # Normaliza nomes das colunas
        df.columns = [
            'id_imovel', 'uf', 'cidade', 'bairro', 'endereco',
            'preco', 'valor_avaliacao', 'desconto', 'descricao',
            'modalidade', 'link'
        ]

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


# Exemplo de uso
if __name__ == "__main__":
    # Testa download
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
