"""
Scrapers de leilao de imoveis
Coleta dados de 5 sites: Zuk, Superbid, Mega Leiloes, Frazao, Biasi
"""

from .base_scraper import BaseLeilaoScraper
from .zuk_scraper import ZukScraper
from .superbid_scraper import SuperbidScraper
from .megaleiloes_scraper import MegaLeiloesScraper
from .frazao_scraper import FrazaoScraper
from .biasi_scraper import BiasiScraper

__all__ = [
    'BaseLeilaoScraper',
    'ZukScraper',
    'SuperbidScraper',
    'MegaLeiloesScraper',
    'FrazaoScraper',
    'BiasiScraper'
]

# Lista de todos os scrapers disponiveis
SCRAPERS_DISPONIVEIS = [
    ZukScraper,
    SuperbidScraper,
    MegaLeiloesScraper,
    FrazaoScraper,
    BiasiScraper
]
