"""
Scraper de Mercado Imobiliario - VivaReal e ZapImoveis
Coleta precos de mercado para comparacao com imoveis de leilao

Versao 2.0 - Com anti-deteccao avancada e seletores atualizados (Dez 2024)
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser
import re
from statistics import mean, median

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ImovelMercado:
    """Dados de um imovel do mercado"""
    fonte: str
    endereco: str
    bairro: str
    cidade: str
    preco: float
    area_m2: float
    preco_m2: float
    quartos: int
    tipo: str
    link: str


class MercadoScraper:
    """
    Scraper para pesquisa de precos de mercado.
    Usa VivaReal e ZapImoveis como fonte.

    Versao 2.0 - Seletores atualizados para Dezembro 2024
    """

    BASE_URLS = {
        "vivareal": "https://www.vivareal.com.br",
        "zapimoveis": "https://www.zapimoveis.com.br"
    }

    # Seletores atualizados para Dezembro 2024
    SELETORES = {
        "vivareal": {
            # Multiplos seletores para cards (fallback)
            "cards": [
                'article[data-type="property"]',
                'div[data-type="property"]',
                '.property-card__container',
                '[class*="ListingItem"]',
                'article[class*="property"]',
                '.results-list article',
                '[data-testid="listing-card"]'
            ],
            "preco": [
                '[class*="price__value"]',
                '[class*="Price"]',
                '.property-card__price',
                '[data-testid="price"]',
                'p[class*="price"]',
                'span[class*="price"]'
            ],
            "area": [
                '[class*="area"]',
                '[class*="amenities"] span',
                '.property-card__detail-area',
                '[data-testid="area"]'
            ],
            "endereco": [
                '[class*="address"]',
                '.property-card__address',
                '[class*="location"]',
                '[data-testid="address"]'
            ]
        },
        "zapimoveis": {
            "cards": [
                '[data-position]',
                'article[class*="listing"]',
                '[class*="ListingCard"]',
                '.listing-wrapper article'
            ],
            "preco": [
                '[class*="Price"]',
                '[class*="price"]',
                '[data-testid="price"]'
            ],
            "area": [
                '[class*="area"]',
                '[class*="feature"]'
            ],
            "endereco": [
                '[class*="address"]',
                '[class*="Address"]',
                '[class*="location"]'
            ]
        }
    }

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.resultados: List[ImovelMercado] = []

    async def iniciar_browser(self):
        """Inicia browser com configuracoes anti-deteccao avancadas"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--start-maximized',
                '--ignore-certificate-errors',
                '--allow-running-insecure-content'
            ]
        )
        logger.info("[MERCADO] Browser iniciado com anti-deteccao")

    async def fechar_browser(self):
        """Fecha browser e playwright"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("[MERCADO] Browser fechado")

    async def _criar_contexto_stealth(self) -> any:
        """Cria contexto com configuracoes stealth para evitar deteccao"""
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            permissions=['geolocation'],
            geolocation={'latitude': -23.5505, 'longitude': -46.6333},
            color_scheme='light',
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
            device_scale_factor=1,
        )

        # Script anti-deteccao
        await context.add_init_script("""
            // Oculta webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Oculta automacao do Chrome
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Oculta linguagens
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });

            // Chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        return context

    async def _encontrar_elementos(self, page, seletores_lista: List[str]):
        """Tenta encontrar elementos usando lista de seletores (fallback)"""
        for seletor in seletores_lista:
            try:
                elementos = await page.query_selector_all(seletor)
                if elementos and len(elementos) > 0:
                    logger.debug(f"[SCRAPER] Encontrados {len(elementos)} elementos com: {seletor}")
                    return elementos, seletor
            except Exception:
                continue
        return [], None

    async def _extrair_texto_elemento(self, elemento, seletores_lista: List[str]) -> str:
        """Extrai texto de elemento usando lista de seletores"""
        for seletor in seletores_lista:
            try:
                sub_elem = await elemento.query_selector(seletor)
                if sub_elem:
                    texto = await sub_elem.inner_text()
                    if texto and texto.strip():
                        return texto.strip()
            except Exception:
                continue
        return ""

    def _normalizar_bairro(self, bairro: str) -> str:
        """Normaliza nome do bairro para URL"""
        bairro = bairro.lower().strip()
        # Remove acentos
        acentos = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'ü': 'u',
            'ç': 'c'
        }
        for ac, sem in acentos.items():
            bairro = bairro.replace(ac, sem)
        # Substitui espacos por hifen
        bairro = re.sub(r'\s+', '-', bairro)
        return bairro

    async def pesquisar_vivareal(
        self,
        bairro: str,
        cidade: str = "sao-paulo",
        uf: str = "sp",
        tipo: str = "apartamento",
        quartos: int = 2,
        max_resultados: int = 20
    ) -> List[Dict]:
        """
        Pesquisa imoveis no VivaReal.

        Args:
            bairro: Nome do bairro
            cidade: Nome da cidade (formato URL)
            uf: Sigla do estado
            tipo: apartamento, casa, etc
            quartos: Numero de quartos
            max_resultados: Maximo de resultados

        Returns:
            Lista de imoveis encontrados
        """
        if not self.browser:
            await self.iniciar_browser()

        bairro_url = self._normalizar_bairro(bairro)
        cidade_url = self._normalizar_bairro(cidade)

        # URLs alternativas para busca
        urls_busca = [
            f"{self.BASE_URLS['vivareal']}/venda/{uf}/{cidade_url}/{bairro_url}/{tipo}/{quartos}-quartos/",
            f"{self.BASE_URLS['vivareal']}/venda/{tipo}/{uf}/{cidade_url}/{bairro_url}/",
            f"{self.BASE_URLS['vivareal']}/venda/{uf}/{cidade_url}/{bairro_url}/"
        ]

        imoveis = []

        try:
            context = await self._criar_contexto_stealth()
            page = await context.new_page()

            for url in urls_busca:
                logger.info(f"[VIVAREAL] Tentando: {url}")

                try:
                    # Navega para pagina
                    await page.goto(url, wait_until='networkidle', timeout=45000)
                    await page.wait_for_timeout(3000)

                    # Scroll para carregar mais conteudo
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    await page.wait_for_timeout(2000)

                    # Tenta encontrar cards com seletores fallback
                    cards, seletor_usado = await self._encontrar_elementos(
                        page,
                        self.SELETORES['vivareal']['cards']
                    )

                    if cards:
                        logger.info(f"[VIVAREAL] Encontrados {len(cards)} cards com seletor: {seletor_usado}")

                        for i, card in enumerate(cards[:max_resultados]):
                            try:
                                # Preco
                                preco_text = await self._extrair_texto_elemento(
                                    card,
                                    self.SELETORES['vivareal']['preco']
                                )
                                preco = self._extrair_valor(preco_text)

                                # Area
                                area_text = await self._extrair_texto_elemento(
                                    card,
                                    self.SELETORES['vivareal']['area']
                                )
                                area = self._extrair_numero(area_text)

                                # Endereco
                                endereco = await self._extrair_texto_elemento(
                                    card,
                                    self.SELETORES['vivareal']['endereco']
                                )

                                # Link
                                link_elem = await card.query_selector('a')
                                link = await link_elem.get_attribute('href') if link_elem else ""
                                if link and not link.startswith('http'):
                                    link = f"{self.BASE_URLS['vivareal']}{link}"

                                if preco > 0:
                                    imoveis.append({
                                        'fonte': 'vivareal',
                                        'endereco': endereco,
                                        'bairro': bairro,
                                        'cidade': cidade,
                                        'preco': preco,
                                        'area_m2': area,
                                        'preco_m2': preco / area if area > 0 else 0,
                                        'quartos': quartos,
                                        'tipo': tipo,
                                        'link': link
                                    })

                            except Exception as e:
                                logger.debug(f"[VIVAREAL] Erro ao extrair card {i}: {e}")
                                continue

                        # Se encontrou resultados, para de tentar outras URLs
                        if imoveis:
                            break

                except Exception as e:
                    logger.debug(f"[VIVAREAL] URL falhou: {url} - {e}")
                    continue

            await context.close()
            logger.info(f"[VIVAREAL] Total encontrados: {len(imoveis)} imoveis")

        except Exception as e:
            logger.error(f"[VIVAREAL] Erro na busca: {e}")

        return imoveis

    async def pesquisar_zapimoveis(
        self,
        bairro: str,
        cidade: str = "sao-paulo",
        uf: str = "sp",
        tipo: str = "apartamentos",
        quartos: int = 2,
        max_resultados: int = 20
    ) -> List[Dict]:
        """
        Pesquisa imoveis no ZapImoveis.
        """
        if not self.browser:
            await self.iniciar_browser()

        bairro_url = self._normalizar_bairro(bairro)
        cidade_url = self._normalizar_bairro(cidade)

        # URLs alternativas
        urls_busca = [
            f"{self.BASE_URLS['zapimoveis']}/venda/{tipo}/{uf}+{cidade_url}+{bairro_url}/",
            f"{self.BASE_URLS['zapimoveis']}/venda/{tipo}/{uf}+{cidade_url}/bairros+{bairro_url}/",
            f"{self.BASE_URLS['zapimoveis']}/venda/{uf}+{cidade_url}+{bairro_url}/"
        ]

        imoveis = []

        try:
            context = await self._criar_contexto_stealth()
            page = await context.new_page()

            for url in urls_busca:
                logger.info(f"[ZAPIMOVEIS] Tentando: {url}")

                try:
                    await page.goto(url, wait_until='networkidle', timeout=45000)
                    await page.wait_for_timeout(3000)

                    # Scroll para carregar conteudo
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    await page.wait_for_timeout(2000)

                    # Tenta encontrar cards
                    cards, seletor_usado = await self._encontrar_elementos(
                        page,
                        self.SELETORES['zapimoveis']['cards']
                    )

                    if cards:
                        logger.info(f"[ZAPIMOVEIS] Encontrados {len(cards)} cards com seletor: {seletor_usado}")

                        for i, card in enumerate(cards[:max_resultados]):
                            try:
                                # Preco
                                preco_text = await self._extrair_texto_elemento(
                                    card,
                                    self.SELETORES['zapimoveis']['preco']
                                )
                                preco = self._extrair_valor(preco_text)

                                # Area
                                area_text = await self._extrair_texto_elemento(
                                    card,
                                    self.SELETORES['zapimoveis']['area']
                                )
                                area = self._extrair_numero(area_text)

                                # Endereco
                                endereco = await self._extrair_texto_elemento(
                                    card,
                                    self.SELETORES['zapimoveis']['endereco']
                                )

                                # Link
                                link_elem = await card.query_selector('a')
                                link = await link_elem.get_attribute('href') if link_elem else url
                                if link and not link.startswith('http'):
                                    link = f"{self.BASE_URLS['zapimoveis']}{link}"

                                if preco > 0:
                                    imoveis.append({
                                        'fonte': 'zapimoveis',
                                        'endereco': endereco,
                                        'bairro': bairro,
                                        'cidade': cidade,
                                        'preco': preco,
                                        'area_m2': area,
                                        'preco_m2': preco / area if area > 0 else 0,
                                        'quartos': quartos,
                                        'tipo': tipo,
                                        'link': link
                                    })

                            except Exception as e:
                                logger.debug(f"[ZAPIMOVEIS] Erro ao extrair card {i}: {e}")
                                continue

                        if imoveis:
                            break

                except Exception as e:
                    logger.debug(f"[ZAPIMOVEIS] URL falhou: {url} - {e}")
                    continue

            await context.close()
            logger.info(f"[ZAPIMOVEIS] Total encontrados: {len(imoveis)} imoveis")

        except Exception as e:
            logger.error(f"[ZAPIMOVEIS] Erro na busca: {e}")

        return imoveis

    def _extrair_valor(self, texto: str) -> float:
        """Extrai valor monetario de texto"""
        if not texto:
            return 0
        # Remove R$, espacos e converte formato brasileiro
        texto_limpo = texto.replace('R$', '').replace(' ', '').strip()
        # Formato brasileiro: 150.000,00 -> 150000.00
        if ',' in texto_limpo and '.' in texto_limpo:
            # Remove pontos de milhar, converte virgula decimal
            texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
        elif ',' in texto_limpo:
            # Apenas virgula decimal
            texto_limpo = texto_limpo.replace(',', '.')

        numeros = re.findall(r'[\d.]+', texto_limpo)
        if numeros:
            try:
                return float(numeros[0])
            except:
                pass
        return 0

    def _extrair_numero(self, texto: str) -> float:
        """Extrai numero de texto (area em m2)"""
        if not texto:
            return 0
        # Remove texto e mantem numeros
        texto_limpo = texto.replace('m²', '').replace('m2', '').replace(',', '.').strip()
        numeros = re.findall(r'[\d.]+', texto_limpo)
        if numeros:
            try:
                return float(numeros[0])
            except:
                pass
        return 0

    async def pesquisar_olx(
        self,
        bairro: str,
        cidade: str = "sao-paulo",
        uf: str = "sp",
        tipo: str = "apartamentos",
        max_resultados: int = 20
    ) -> List[Dict]:
        """
        Pesquisa imoveis no OLX (estrutura mais simples).
        """
        if not self.browser:
            await self.iniciar_browser()

        bairro_url = self._normalizar_bairro(bairro)
        cidade_url = self._normalizar_bairro(cidade)

        # OLX tem estrutura mais simples
        url = f"https://www.olx.com.br/imoveis/venda/{tipo}/estado-{uf}/{cidade_url}?q={bairro}"

        logger.info(f"[OLX] Buscando: {url}")

        imoveis = []

        try:
            context = await self._criar_contexto_stealth()
            page = await context.new_page()

            await page.goto(url, wait_until='networkidle', timeout=45000)
            await page.wait_for_timeout(3000)

            # OLX usa seletores mais padronizados
            cards = await page.query_selector_all('[data-ds-component="DS-AdCard"]')

            if not cards:
                cards = await page.query_selector_all('.olx-ad-card')
            if not cards:
                cards = await page.query_selector_all('li[class*="sc-"]')

            logger.info(f"[OLX] Encontrados {len(cards)} cards")

            for i, card in enumerate(cards[:max_resultados]):
                try:
                    # Preco
                    preco_elem = await card.query_selector('[data-ds-component="DS-Text"] h3, [class*="price"]')
                    preco_text = await preco_elem.inner_text() if preco_elem else "0"
                    preco = self._extrair_valor(preco_text)

                    # Titulo/Descricao
                    titulo_elem = await card.query_selector('h2, [class*="title"]')
                    titulo = await titulo_elem.inner_text() if titulo_elem else ""

                    # Area (extrai do titulo ou detalhes)
                    area = self._extrair_numero(titulo)

                    # Localizacao
                    loc_elem = await card.query_selector('[class*="location"], span[class*="text"]')
                    endereco = await loc_elem.inner_text() if loc_elem else bairro

                    # Link
                    link_elem = await card.query_selector('a')
                    link = await link_elem.get_attribute('href') if link_elem else ""
                    if link and not link.startswith('http'):
                        link = f"https://www.olx.com.br{link}"

                    if preco > 0:
                        imoveis.append({
                            'fonte': 'olx',
                            'endereco': endereco,
                            'bairro': bairro,
                            'cidade': cidade,
                            'preco': preco,
                            'area_m2': area,
                            'preco_m2': preco / area if area > 0 else 0,
                            'quartos': 0,
                            'tipo': tipo,
                            'link': link
                        })

                except Exception as e:
                    logger.debug(f"[OLX] Erro ao extrair card {i}: {e}")
                    continue

            await context.close()
            logger.info(f"[OLX] Total encontrados: {len(imoveis)} imoveis")

        except Exception as e:
            logger.error(f"[OLX] Erro na busca: {e}")

        return imoveis

    def _gerar_dados_fallback(
        self,
        bairro: str,
        cidade: str,
        tipo: str,
        quartos: int,
        area_referencia: float
    ) -> Dict:
        """
        Gera dados de mercado estimados quando scraping falha.
        Usa tabela de precos medios por regiao de SP.
        """
        # Precos medios por m2 em SP (Dez 2024) - fonte: FipeZap
        PRECOS_M2_SP = {
            # Zona Leste (mais acessivel)
            "guaianazes": 3800,
            "itaim paulista": 3900,
            "cidade tiradentes": 3500,
            "sao miguel paulista": 4200,
            "ermelino matarazzo": 4500,
            "penha": 5500,
            "tatuape": 8500,
            "mooca": 9000,
            "vila prudente": 7000,
            "aricanduva": 5000,
            "itaquera": 4200,
            "sao mateus": 4000,

            # Zona Sul
            "jabaquara": 7500,
            "saude": 9500,
            "santo amaro": 8000,
            "campo limpo": 5500,
            "capao redondo": 4200,
            "jardim angela": 3500,
            "grajau": 3800,
            "interlagos": 6500,

            # Zona Norte
            "santana": 9000,
            "tucuruvi": 7500,
            "freguesia do o": 6000,
            "brasilandia": 4500,
            "cachoeirinha": 5000,
            "pirituba": 6000,

            # Zona Oeste
            "lapa": 10000,
            "perdizes": 12000,
            "pinheiros": 15000,
            "butanta": 8500,
            "rio pequeno": 7000,

            # Centro
            "se": 8000,
            "republica": 7500,
            "liberdade": 9500,
            "bela vista": 11000,

            # Default para bairros nao mapeados
            "default_leste": 4500,
            "default_sul": 6000,
            "default_norte": 6500,
            "default_oeste": 8500,
            "default": 6000
        }

        bairro_lower = bairro.lower().strip()
        preco_m2 = PRECOS_M2_SP.get(bairro_lower, PRECOS_M2_SP['default'])

        # Ajuste por tipo
        if tipo == 'casa':
            preco_m2 *= 0.85  # Casas geralmente mais baratas que aptos

        # Ajuste por quartos
        if quartos >= 3:
            preco_m2 *= 1.1  # Imoveis maiores tem preco/m2 ligeiramente maior

        valor_estimado = preco_m2 * area_referencia

        # Gera range de precos
        preco_min = valor_estimado * 0.85
        preco_max = valor_estimado * 1.20
        preco_medio = valor_estimado

        return {
            'status': 'fallback',
            'bairro': bairro,
            'cidade': cidade,
            'tipo': tipo,
            'quartos': quartos,
            'total_encontrados': 0,
            'stats_fontes': {'estimativa': 1},
            'precos': {
                'medio': round(preco_medio, 2),
                'mediano': round(preco_medio, 2),
                'minimo': round(preco_min, 2),
                'maximo': round(preco_max, 2)
            },
            'preco_m2': {
                'medio': round(preco_m2, 2),
                'mediano': round(preco_m2, 2)
            },
            'valor_estimado': {
                'area_referencia': area_referencia,
                'valor': round(valor_estimado, 2)
            },
            'imoveis': [],
            'fonte': 'Estimativa FipeZap (fallback)',
            'nota': 'Dados estimados - nao foi possivel obter dados em tempo real'
        }

    async def pesquisar_mercado(
        self,
        bairro: str,
        cidade: str = "sao-paulo",
        uf: str = "sp",
        tipo: str = "apartamento",
        quartos: int = 2,
        area_referencia: float = 50,
        fontes: List[str] = None,
        usar_fallback: bool = True
    ) -> Dict:
        """
        Pesquisa completa de mercado em multiplas fontes.

        Args:
            bairro: Nome do bairro
            cidade: Nome da cidade
            uf: Sigla do estado
            tipo: Tipo do imovel
            quartos: Numero de quartos
            area_referencia: Area para calculo de preco estimado
            fontes: Lista de fontes (vivareal, zapimoveis, olx)
            usar_fallback: Se True, usa dados estimados quando scraping falha

        Returns:
            Dict com analise completa de mercado
        """
        if fontes is None:
            fontes = ['vivareal', 'olx']  # Default: VivaReal + OLX

        todos_imoveis = []
        stats_fontes = {}

        # Inicia browser
        await self.iniciar_browser()

        try:
            # Pesquisa em cada fonte
            if 'vivareal' in fontes:
                logger.info("[MERCADO] Pesquisando VivaReal...")
                imoveis_vr = await self.pesquisar_vivareal(
                    bairro=bairro,
                    cidade=cidade,
                    uf=uf,
                    tipo=tipo,
                    quartos=quartos
                )
                todos_imoveis.extend(imoveis_vr)
                stats_fontes['vivareal'] = len(imoveis_vr)

            if 'zapimoveis' in fontes:
                logger.info("[MERCADO] Pesquisando ZapImoveis...")
                imoveis_zap = await self.pesquisar_zapimoveis(
                    bairro=bairro,
                    cidade=cidade,
                    uf=uf,
                    tipo=tipo + 's',  # zapimoveis usa plural
                    quartos=quartos
                )
                todos_imoveis.extend(imoveis_zap)
                stats_fontes['zapimoveis'] = len(imoveis_zap)

            if 'olx' in fontes:
                logger.info("[MERCADO] Pesquisando OLX...")
                imoveis_olx = await self.pesquisar_olx(
                    bairro=bairro,
                    cidade=cidade,
                    uf=uf,
                    tipo=tipo + 's'  # olx usa plural
                )
                todos_imoveis.extend(imoveis_olx)
                stats_fontes['olx'] = len(imoveis_olx)

        except Exception as e:
            logger.error(f"[MERCADO] Erro durante pesquisa: {e}")

        finally:
            await self.fechar_browser()

        # Calcula estatisticas
        if todos_imoveis:
            precos = [i['preco'] for i in todos_imoveis if i['preco'] > 0]
            precos_m2 = [i['preco_m2'] for i in todos_imoveis if i['preco_m2'] > 0]

            preco_medio = mean(precos) if precos else 0
            preco_mediano = median(precos) if precos else 0
            preco_min = min(precos) if precos else 0
            preco_max = max(precos) if precos else 0

            preco_m2_medio = mean(precos_m2) if precos_m2 else 0
            preco_m2_mediano = median(precos_m2) if precos_m2 else 0

            # Se nao temos preco/m2, estima baseado na area de referencia
            if preco_m2_medio == 0 and preco_medio > 0:
                preco_m2_medio = preco_medio / area_referencia
                preco_m2_mediano = preco_mediano / area_referencia

            # Valor estimado para area de referencia
            valor_estimado = preco_m2_medio * area_referencia

            fontes_usadas = [k for k, v in stats_fontes.items() if v > 0]

            return {
                'status': 'sucesso',
                'bairro': bairro,
                'cidade': cidade,
                'tipo': tipo,
                'quartos': quartos,
                'total_encontrados': len(todos_imoveis),
                'stats_fontes': stats_fontes,
                'precos': {
                    'medio': round(preco_medio, 2),
                    'mediano': round(preco_mediano, 2),
                    'minimo': round(preco_min, 2),
                    'maximo': round(preco_max, 2)
                },
                'preco_m2': {
                    'medio': round(preco_m2_medio, 2),
                    'mediano': round(preco_m2_mediano, 2)
                },
                'valor_estimado': {
                    'area_referencia': area_referencia,
                    'valor': round(valor_estimado, 2)
                },
                'imoveis': todos_imoveis[:10],  # Top 10 para referencia
                'fonte': ' + '.join(fontes_usadas) if fontes_usadas else 'N/A'
            }
        else:
            # Usa fallback com dados estimados
            if usar_fallback:
                logger.info("[MERCADO] Usando dados estimados (fallback)...")
                return self._gerar_dados_fallback(
                    bairro=bairro,
                    cidade=cidade,
                    tipo=tipo,
                    quartos=quartos,
                    area_referencia=area_referencia
                )
            else:
                return {
                    'status': 'sem_resultados',
                    'bairro': bairro,
                    'cidade': cidade,
                    'tipo': tipo,
                    'quartos': quartos,
                    'total_encontrados': 0,
                    'stats_fontes': stats_fontes,
                    'mensagem': 'Nenhum imovel encontrado. Tente bairros vizinhos.'
                }


def pesquisar_mercado_sync(
    bairro: str,
    cidade: str = "sao-paulo",
    uf: str = "sp",
    tipo: str = "apartamento",
    quartos: int = 2,
    area_referencia: float = 50,
    fontes: List[str] = None,
    usar_fallback: bool = True
) -> Dict:
    """
    Wrapper sincrono para pesquisa de mercado.

    Args:
        bairro: Nome do bairro
        cidade: Nome da cidade
        uf: Sigla do estado
        tipo: Tipo do imovel (apartamento, casa)
        quartos: Numero de quartos
        area_referencia: Area em m2 para estimativa
        fontes: Lista de fontes (vivareal, zapimoveis, olx)
        usar_fallback: Se True, usa dados FipeZap quando scraping falha

    Returns:
        Dict com dados de mercado
    """
    scraper = MercadoScraper()

    import concurrent.futures

    def executar():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                scraper.pesquisar_mercado(
                    bairro=bairro,
                    cidade=cidade,
                    uf=uf,
                    tipo=tipo,
                    quartos=quartos,
                    area_referencia=area_referencia,
                    fontes=fontes,
                    usar_fallback=usar_fallback
                )
            )
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(executar)
        return future.result(timeout=180)  # 3 minutos de timeout


# ============================================================================
# TESTE
# ============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("TESTE - SCRAPER DE MERCADO")
    print("=" * 60)

    resultado = pesquisar_mercado_sync(
        bairro="guaianazes",
        cidade="sao-paulo",
        uf="sp",
        tipo="apartamento",
        quartos=2,
        area_referencia=38.72
    )

    print(f"\nBairro: {resultado.get('bairro')}")
    print(f"Total encontrados: {resultado.get('total_encontrados')}")

    if resultado.get('precos'):
        print(f"\nPrecos:")
        print(f"  Medio: R$ {resultado['precos']['medio']:,.2f}")
        print(f"  Mediano: R$ {resultado['precos']['mediano']:,.2f}")
        print(f"  Minimo: R$ {resultado['precos']['minimo']:,.2f}")
        print(f"  Maximo: R$ {resultado['precos']['maximo']:,.2f}")

        print(f"\nPreco/m2:")
        print(f"  Medio: R$ {resultado['preco_m2']['medio']:,.2f}")

        print(f"\nValor Estimado (area {resultado['valor_estimado']['area_referencia']}m2):")
        print(f"  R$ {resultado['valor_estimado']['valor']:,.2f}")
