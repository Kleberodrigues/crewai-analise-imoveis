"""
Classe base para scrapers de leilao de imoveis
Implementa logica comum usando Playwright para web scraping
"""

from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, Page
import asyncio
import random
import re
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseLeilaoScraper(ABC):
    """
    Classe base abstrata para scrapers de sites de leilao.
    Cada site deve implementar sua propria subclasse.
    """

    # Constantes a serem sobrescritas pelas subclasses
    FONTE_NOME: str = "base"
    BASE_URL: str = ""

    # Filtros padrao para leiloes extrajudiciais
    FILTROS_PADRAO = {
        "tipo_leilao": "extrajudicial",
        "tipo_imovel": "apartamento",
        "praca": "2a",
        "modalidade": ["venda_online", "venda_direta"],
        "estado": "SP",
        "preco_max": 200000
    }

    # Configuracoes do browser
    BROWSER_CONFIG = {
        "headless": True,
        "slow_mo": 100,  # ms entre acoes
    }

    # User agents para rotacao
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Inicializa o scraper.

        Args:
            headless: Se True, executa browser sem interface grafica
            timeout: Timeout padrao para operacoes em ms
        """
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.imoveis_coletados: List[Dict] = []
        self.erros: List[Dict] = []

    async def iniciar(self) -> None:
        """Inicia o browser Playwright"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.BROWSER_CONFIG["slow_mo"]
            )

            # Cria contexto com user agent aleatorio
            context = await self.browser.new_context(
                user_agent=random.choice(self.USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="pt-BR"
            )

            self.page = await context.new_page()
            self.page.set_default_timeout(self.timeout)

            logger.info(f"[{self.FONTE_NOME}] Browser iniciado com sucesso")

        except Exception as e:
            logger.error(f"[{self.FONTE_NOME}] Erro ao iniciar browser: {e}")
            raise

    async def finalizar(self) -> None:
        """Fecha o browser e libera recursos"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            logger.info(f"[{self.FONTE_NOME}] Browser finalizado")

        except Exception as e:
            logger.error(f"[{self.FONTE_NOME}] Erro ao finalizar browser: {e}")

    async def delay_aleatorio(self, min_ms: int = 500, max_ms: int = 2000) -> None:
        """Aguarda um tempo aleatorio para evitar deteccao"""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def scroll_pagina(self, vezes: int = 5, delay_entre: int = 1000) -> None:
        """
        Faz scroll na pagina para carregar conteudo lazy-loaded

        Args:
            vezes: Numero de scrolls
            delay_entre: Delay entre scrolls em ms
        """
        for i in range(vezes):
            await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(delay_entre / 1000)

    async def esperar_elemento(self, seletor: str, timeout: int = None) -> bool:
        """
        Espera um elemento aparecer na pagina

        Args:
            seletor: Seletor CSS ou XPath
            timeout: Timeout em ms (usa padrao se None)

        Returns:
            True se elemento encontrado, False caso contrario
        """
        try:
            await self.page.wait_for_selector(seletor, timeout=timeout or self.timeout)
            return True
        except:
            return False

    def extrair_preco(self, texto: str) -> float:
        """
        Extrai valor numerico de texto com preco
        Ex: "R$ 120.000,00" -> 120000.0
        """
        if not texto:
            return 0.0

        # Remove R$, espacos e converte formato brasileiro
        texto_limpo = re.sub(r'[R$\s]', '', texto)
        texto_limpo = texto_limpo.replace('.', '').replace(',', '.')

        try:
            return float(texto_limpo)
        except:
            return 0.0

    def extrair_numero(self, texto: str) -> int:
        """Extrai primeiro numero inteiro de um texto"""
        if not texto:
            return 0

        match = re.search(r'\d+', texto)
        return int(match.group()) if match else 0

    def extrair_area(self, texto: str) -> float:
        """
        Extrai area em m2 de texto
        Ex: "65m²" ou "65 m2" -> 65.0
        """
        if not texto:
            return 0.0

        match = re.search(r'(\d+[.,]?\d*)\s*m[²2]?', texto, re.IGNORECASE)
        if match:
            area_str = match.group(1).replace(',', '.')
            return float(area_str)
        return 0.0

    def calcular_desconto(self, preco: float, avaliacao: float) -> float:
        """Calcula percentual de desconto"""
        if avaliacao <= 0 or preco <= 0:
            return 0.0
        return round((1 - preco / avaliacao) * 100, 1)

    def normalizar_imovel(self, dados_raw: Dict) -> Dict:
        """
        Normaliza dados do imovel para formato padrao do pipeline.

        Args:
            dados_raw: Dados brutos extraidos do site

        Returns:
            Dicionario normalizado
        """
        preco = dados_raw.get('preco', 0)
        avaliacao = dados_raw.get('valor_avaliacao', 0)

        # Calcula desconto se nao fornecido
        desconto = dados_raw.get('desconto')
        if desconto is None and avaliacao > 0:
            desconto = self.calcular_desconto(preco, avaliacao)

        # Determina praca baseado no desconto
        praca = dados_raw.get('praca', '')
        if not praca and desconto:
            praca = "2a Praca" if desconto >= 30 else "1a Praca"

        return {
            # Identificacao
            "id_imovel": str(dados_raw.get('id_imovel', '')),
            "fonte": self.FONTE_NOME,

            # Localizacao
            "endereco": dados_raw.get('endereco', ''),
            "bairro": dados_raw.get('bairro', '').upper(),
            "cidade": dados_raw.get('cidade', 'SAO PAULO').upper(),
            "uf": dados_raw.get('uf', 'SP').upper(),

            # Valores
            "preco": float(preco),
            "valor_avaliacao": float(avaliacao),
            "desconto": float(desconto or 0),

            # Caracteristicas
            "tipo_imovel": dados_raw.get('tipo_imovel', 'Apartamento'),
            "area_privativa": float(dados_raw.get('area_privativa', 0)),
            "area_total": float(dados_raw.get('area_total', 0)),
            "quartos": int(dados_raw.get('quartos', 0)),
            "vagas": int(dados_raw.get('vagas', 0)),

            # Leilao
            "praca": praca,
            "modalidade": dados_raw.get('modalidade', 'Venda Online'),
            "data_leilao": dados_raw.get('data_leilao', ''),

            # Links
            "link": dados_raw.get('link', ''),
            "imagens": dados_raw.get('imagens', []),

            # Metadados
            "data_extracao": datetime.now().isoformat(),
            "descricao": dados_raw.get('descricao', '')
        }

    def filtrar_imoveis(self, imoveis: List[Dict], filtros: Dict = None) -> List[Dict]:
        """
        Aplica filtros na lista de imoveis

        Args:
            imoveis: Lista de imoveis normalizados
            filtros: Dicionario de filtros (usa padrao se None)

        Returns:
            Lista filtrada
        """
        filtros = filtros or self.FILTROS_PADRAO
        filtrados = []

        for imovel in imoveis:
            # Filtro de preco maximo
            if filtros.get('preco_max') and imovel['preco'] > filtros['preco_max']:
                continue

            # Filtro de tipo de imovel
            tipo_filtro = filtros.get('tipo_imovel', '').lower()
            if tipo_filtro and tipo_filtro not in imovel.get('tipo_imovel', '').lower():
                continue

            # Filtro de estado
            if filtros.get('estado') and imovel.get('uf') != filtros['estado']:
                continue

            # Filtro de praca (2a praca = desconto >= 30%)
            if filtros.get('praca') == '2a' and imovel.get('desconto', 0) < 30:
                continue

            filtrados.append(imovel)

        logger.info(f"[{self.FONTE_NOME}] Filtrados {len(filtrados)} de {len(imoveis)} imoveis")
        return filtrados

    @abstractmethod
    async def coletar_listagem(self) -> List[Dict]:
        """
        Coleta lista de imoveis da pagina de listagem.
        Deve ser implementado por cada subclasse.

        Returns:
            Lista de dicionarios com dados basicos dos imoveis
        """
        pass

    @abstractmethod
    async def coletar_detalhes(self, url: str) -> Dict:
        """
        Coleta detalhes de um imovel especifico.
        Deve ser implementado por cada subclasse.

        Args:
            url: URL da pagina de detalhes do imovel

        Returns:
            Dicionario com dados completos do imovel
        """
        pass

    async def executar(self, coletar_detalhes: bool = True, max_imoveis: int = 50) -> List[Dict]:
        """
        Executa o processo completo de scraping.

        Args:
            coletar_detalhes: Se True, coleta detalhes de cada imovel
            max_imoveis: Limite maximo de imoveis a coletar

        Returns:
            Lista de imoveis normalizados
        """
        inicio = datetime.now()
        logger.info(f"[{self.FONTE_NOME}] Iniciando coleta...")

        try:
            await self.iniciar()

            # Etapa 1: Coletar listagem
            listagem = await self.coletar_listagem()
            logger.info(f"[{self.FONTE_NOME}] {len(listagem)} imoveis encontrados na listagem")

            # Limita quantidade
            listagem = listagem[:max_imoveis]

            # Etapa 2: Coletar detalhes (opcional)
            imoveis = []
            if coletar_detalhes and listagem:
                for i, item in enumerate(listagem):
                    try:
                        url = item.get('link', '')
                        if url:
                            await self.delay_aleatorio(1000, 3000)
                            detalhes = await self.coletar_detalhes(url)
                            # Mescla dados da listagem com detalhes
                            dados_completos = {**item, **detalhes}
                            imovel_normalizado = self.normalizar_imovel(dados_completos)
                            imoveis.append(imovel_normalizado)

                            if (i + 1) % 10 == 0:
                                logger.info(f"[{self.FONTE_NOME}] Progresso: {i + 1}/{len(listagem)}")

                    except Exception as e:
                        logger.warning(f"[{self.FONTE_NOME}] Erro ao coletar detalhes: {e}")
                        self.erros.append({"url": item.get('link'), "erro": str(e)})
            else:
                # Usa apenas dados da listagem
                imoveis = [self.normalizar_imovel(item) for item in listagem]

            # Etapa 3: Filtrar resultados
            imoveis_filtrados = self.filtrar_imoveis(imoveis)

            duracao = (datetime.now() - inicio).total_seconds()
            logger.info(
                f"[{self.FONTE_NOME}] Coleta finalizada: "
                f"{len(imoveis_filtrados)} imoveis em {duracao:.1f}s"
            )

            self.imoveis_coletados = imoveis_filtrados
            return imoveis_filtrados

        except Exception as e:
            logger.error(f"[{self.FONTE_NOME}] Erro na execucao: {e}")
            raise

        finally:
            await self.finalizar()

    def get_estatisticas(self) -> Dict:
        """Retorna estatisticas da coleta"""
        return {
            "fonte": self.FONTE_NOME,
            "total_coletados": len(self.imoveis_coletados),
            "total_erros": len(self.erros),
            "erros": self.erros[:5]  # Primeiros 5 erros
        }
