"""
Scraper para o Portal Zuk (portalzuk.com.br)
Leiloes extrajudiciais de imoveis
Com bypass para Cloudflare
"""

import re
import asyncio
import logging
from typing import List, Dict
from .base_scraper import BaseLeilaoScraper

logger = logging.getLogger(__name__)


class ZukScraper(BaseLeilaoScraper):
    """
    Scraper para o Portal Zuk - maior portal de leiloes extrajudiciais do Brasil.
    URL: https://www.portalzuk.com.br
    """

    FONTE_NOME = "portal_zuk"
    BASE_URL = "https://www.portalzuk.com.br"

    # URL de listagem (filtros aplicados depois)
    LISTAGEM_URL = "/leilao-de-imoveis"

    # Seletores CSS atualizados (Dez 2024)
    SELETORES = {
        # Cards de imoveis
        "card_imovel": ".card-property",
        "link_imovel": "a[href*='/imovel/']",
        # Dados do imovel
        "preco": ".card-property-price-value",
        "endereco": ".card-property-address",
        "area": ".card-property-info-label",
        "tipo": ".card-property-price-lote",
        "desconto": ".card-property-price-percent",
        "imagem": ".card-property-image-wrapper img",
        "status": ".card-property-news",
        "favorito_id": ".card-property-favorite",
        "paginacao": ".pagination a, .page-link",
        # Cloudflare
        "cloudflare": "#challenge-running, #cf-wrapper, .cf-browser-verification"
    }

    # Tempo de espera para Cloudflare (segundos)
    CLOUDFLARE_WAIT = 10

    async def _aguardar_cloudflare(self) -> bool:
        """Aguarda Cloudflare challenge ser resolvido"""
        logger.info(f"[{self.FONTE_NOME}] Verificando Cloudflare...")

        for i in range(self.CLOUDFLARE_WAIT):
            # Verifica se ainda esta no challenge
            title = await self.page.title()
            if "Cloudflare" in title or "Attention" in title or "challenge" in title.lower():
                logger.info(f"[{self.FONTE_NOME}] Aguardando Cloudflare... ({i+1}s)")
                await asyncio.sleep(1)
            else:
                logger.info(f"[{self.FONTE_NOME}] Cloudflare passou!")
                return True

        # Verifica se conseguiu passar
        title = await self.page.title()
        if "Cloudflare" in title or "Attention" in title:
            logger.warning(f"[{self.FONTE_NOME}] Cloudflare nao foi resolvido")
            return False

        return True

    async def coletar_listagem(self) -> List[Dict]:
        """
        Coleta lista de imoveis da pagina de listagem do Zuk.
        Faz scroll para carregar conteudo lazy-loaded.
        """
        imoveis = []
        url_completa = f"{self.BASE_URL}{self.LISTAGEM_URL}"

        try:
            logger.info(f"[{self.FONTE_NOME}] Acessando {url_completa}")

            # Acessa a pagina
            await self.page.goto(url_completa, wait_until="domcontentloaded", timeout=60000)

            # Aguarda Cloudflare
            cf_ok = await self._aguardar_cloudflare()
            if not cf_ok:
                logger.error(f"[{self.FONTE_NOME}] Bloqueado pelo Cloudflare")
                return []

            # Delay inicial para pagina carregar
            await self.delay_aleatorio(3000, 5000)

            # Scroll para carregar todos os imoveis (lazy loading)
            logger.info(f"[{self.FONTE_NOME}] Fazendo scroll para carregar conteudo...")
            await self.scroll_pagina(vezes=10, delay_entre=1500)

            # Tenta varios seletores para encontrar cards
            cards = []
            seletores_tentados = self.SELETORES["card_imovel"].split(", ")

            for seletor in seletores_tentados:
                try:
                    cards = await self.page.query_selector_all(seletor)
                    if cards:
                        logger.info(f"[{self.FONTE_NOME}] Seletor '{seletor}': {len(cards)} cards")
                        break
                except:
                    continue

            if not cards:
                # Tenta buscar por links de imoveis diretamente
                links = await self.page.query_selector_all("a[href*='/imovel/']")
                logger.info(f"[{self.FONTE_NOME}] Links de imoveis encontrados: {len(links)}")

                for link in links:
                    try:
                        href = await link.get_attribute("href")
                        if href and '/imovel/' in href:
                            imovel = await self._extrair_de_link(link)
                            if imovel:
                                imoveis.append(imovel)
                    except Exception as e:
                        logger.debug(f"Erro ao extrair link: {e}")
            else:
                logger.info(f"[{self.FONTE_NOME}] {len(cards)} cards encontrados")

                for card in cards:
                    try:
                        imovel = await self._extrair_card(card)
                        if imovel and imovel.get('link'):
                            imoveis.append(imovel)
                    except Exception as e:
                        logger.warning(f"[{self.FONTE_NOME}] Erro ao extrair card: {e}")

            # Tenta paginacao se disponivel
            if len(imoveis) > 0:
                imoveis_paginacao = await self._coletar_paginacao()
                imoveis.extend(imoveis_paginacao)

        except Exception as e:
            logger.error(f"[{self.FONTE_NOME}] Erro na listagem: {e}")

        return imoveis

    async def _extrair_de_link(self, link_elem) -> Dict:
        """Extrai dados basicos de um elemento link"""
        dados = {}
        try:
            href = await link_elem.get_attribute("href")
            if href:
                dados['link'] = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                # Extrai ID do imovel
                match = re.search(r'/imovel/([^/]+)', href)
                if match:
                    dados['id_imovel'] = f"ZUK-{match.group(1)}"

                # Tenta pegar texto do elemento
                texto = await link_elem.inner_text()
                if texto:
                    dados['descricao'] = texto.strip()[:200]

                    # Tenta extrair preco do texto
                    preco_match = re.search(r'R\$\s*([\d.,]+)', texto)
                    if preco_match:
                        dados['preco'] = self.extrair_preco(preco_match.group(0))

                dados['tipo_imovel'] = 'Apartamento'
                dados['uf'] = 'SP'

        except Exception as e:
            logger.debug(f"Erro extraindo de link: {e}")

        return dados if dados.get('link') else None

    async def _extrair_card(self, card) -> Dict:
        """Extrai dados de um card de imovel"""
        dados = {}

        try:
            # Link do imovel (pega href e title)
            link_elem = await card.query_selector(self.SELETORES["link_imovel"])
            if link_elem:
                href = await link_elem.get_attribute("href")
                title = await link_elem.get_attribute("title")
                if href:
                    dados['link'] = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    # ID do imovel extraido da URL (formato: /34707-213734)
                    match = re.search(r'/(\d+-\d+)$', href)
                    if match:
                        dados['id_imovel'] = f"ZUK-{match.group(1)}"
                    # Endereco do title
                    if title:
                        dados['descricao'] = title

            # ID do favorito (backup para ID)
            if not dados.get('id_imovel'):
                fav_elem = await card.query_selector(self.SELETORES["favorito_id"])
                if fav_elem:
                    fav_id = await fav_elem.get_attribute("id")
                    if fav_id:
                        dados['id_imovel'] = f"ZUK-{fav_id}"

            # Preco
            preco_elem = await card.query_selector(self.SELETORES["preco"])
            if preco_elem:
                preco_texto = await preco_elem.inner_text()
                dados['preco'] = self.extrair_preco(preco_texto)

            # Endereco
            endereco_elem = await card.query_selector(self.SELETORES["endereco"])
            if endereco_elem:
                endereco = await endereco_elem.inner_text()
                endereco = endereco.replace('\n', ' ').strip()
                dados['endereco'] = endereco
                self._extrair_localizacao(endereco, dados)

            # Area (pode ter varios, pega o primeiro)
            area_elems = await card.query_selector_all(self.SELETORES["area"])
            for area_elem in area_elems:
                area_texto = await area_elem.inner_text()
                if 'm' in area_texto.lower():
                    dados['area_privativa'] = self.extrair_area(area_texto)
                    # Verifica se eh terreno
                    if 'terreno' in area_texto.lower():
                        dados['tipo_imovel'] = 'Terreno'
                    break

            # Tipo de imovel
            tipo_elem = await card.query_selector(self.SELETORES["tipo"])
            if tipo_elem:
                tipo_texto = await tipo_elem.inner_text()
                dados['tipo_imovel'] = tipo_texto.strip()

            # Desconto
            desconto_elem = await card.query_selector(self.SELETORES["desconto"])
            if desconto_elem:
                desconto_texto = await desconto_elem.inner_text()
                dados['desconto'] = self.extrair_numero(desconto_texto)

            # Imagem
            img_elem = await card.query_selector(self.SELETORES["imagem"])
            if img_elem:
                src = await img_elem.get_attribute("src") or await img_elem.get_attribute("data-src")
                if src:
                    dados['imagens'] = [src]

            # Status (ocupado/desocupado)
            status_elem = await card.query_selector(self.SELETORES["status"])
            if status_elem:
                status_texto = await status_elem.inner_text()
                dados['observacoes'] = status_texto.strip()

            # Define tipo padrao se nao encontrou
            if not dados.get('tipo_imovel'):
                dados['tipo_imovel'] = 'Apartamento'
            dados['modalidade'] = 'Venda Online'
            dados['uf'] = 'SP'

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao extrair dados do card: {e}")

        return dados

    def _extrair_localizacao(self, endereco: str, dados: Dict) -> None:
        """Extrai bairro e cidade do endereco"""
        if not endereco:
            return

        # Padrao comum: "Rua X, 123 - Bairro - Cidade/SP"
        partes = endereco.split(' - ')
        if len(partes) >= 2:
            dados['bairro'] = partes[-2].strip() if len(partes) >= 2 else ''

        # Extrai cidade (antes de /SP ou /RJ)
        match = re.search(r'([^-/]+)/SP', endereco, re.IGNORECASE)
        if match:
            dados['cidade'] = match.group(1).strip().upper()
        else:
            dados['cidade'] = 'SAO PAULO'

        dados['uf'] = 'SP'

    async def _coletar_paginacao(self, max_paginas: int = 5) -> List[Dict]:
        """Coleta imoveis das paginas seguintes"""
        imoveis_extras = []

        for pagina in range(2, max_paginas + 1):
            try:
                # Procura botao de proxima pagina
                next_btn = await self.page.query_selector(self.SELETORES["paginacao"])
                if not next_btn:
                    break

                await next_btn.click()
                await self.delay_aleatorio(2000, 4000)
                await self.scroll_pagina(vezes=5)

                cards = await self.page.query_selector_all(self.SELETORES["card_imovel"])
                for card in cards:
                    imovel = await self._extrair_card(card)
                    if imovel and imovel.get('link'):
                        imoveis_extras.append(imovel)

                logger.info(f"[{self.FONTE_NOME}] Pagina {pagina}: {len(cards)} imoveis")

            except Exception as e:
                logger.debug(f"[{self.FONTE_NOME}] Fim da paginacao: {e}")
                break

        return imoveis_extras

    async def coletar_detalhes(self, url: str) -> Dict:
        """
        Coleta detalhes completos de um imovel do Zuk.

        Args:
            url: URL da pagina de detalhes

        Returns:
            Dicionario com dados detalhados
        """
        dados = {'link': url}

        try:
            await self.page.goto(url, wait_until="networkidle")
            await self.delay_aleatorio(1500, 3000)

            # Preco atual
            preco_elem = await self.page.query_selector(".preco-atual, .current-price, h2.preco")
            if preco_elem:
                preco_texto = await preco_elem.inner_text()
                dados['preco'] = self.extrair_preco(preco_texto)

            # Valor de avaliacao
            avaliacao_elem = await self.page.query_selector(".valor-avaliacao, .evaluation-price")
            if avaliacao_elem:
                avaliacao_texto = await avaliacao_elem.inner_text()
                dados['valor_avaliacao'] = self.extrair_preco(avaliacao_texto)

            # Endereco completo
            endereco_elem = await self.page.query_selector(".endereco-completo, .full-address, h1")
            if endereco_elem:
                dados['endereco'] = (await endereco_elem.inner_text()).strip()
                self._extrair_localizacao(dados['endereco'], dados)

            # Caracteristicas (area, quartos, vagas)
            caracteristicas = await self.page.query_selector_all(".caracteristica, .feature, .info-item")
            for carac in caracteristicas:
                texto = (await carac.inner_text()).lower()
                if 'm²' in texto or 'metro' in texto:
                    dados['area_privativa'] = self.extrair_area(texto)
                elif 'quarto' in texto or 'dorm' in texto:
                    dados['quartos'] = self.extrair_numero(texto)
                elif 'vaga' in texto or 'garage' in texto:
                    dados['vagas'] = self.extrair_numero(texto)

            # Data do leilao
            data_elem = await self.page.query_selector(".data-leilao, .auction-date")
            if data_elem:
                dados['data_leilao'] = (await data_elem.inner_text()).strip()

            # Descricao
            descricao_elem = await self.page.query_selector(".descricao, .description")
            if descricao_elem:
                dados['descricao'] = (await descricao_elem.inner_text()).strip()[:500]

            # Imagens (ate 10)
            imagens = []
            img_elems = await self.page.query_selector_all(".galeria img, .gallery img, .carousel img")
            for img in img_elems[:10]:
                src = await img.get_attribute("src") or await img.get_attribute("data-src")
                if src and src.startswith('http'):
                    imagens.append(src)
            if imagens:
                dados['imagens'] = imagens

            # Tipo de leilao / praca
            tipo_elem = await self.page.query_selector(".tipo-leilao, .auction-type")
            if tipo_elem:
                tipo_texto = (await tipo_elem.inner_text()).lower()
                if '2' in tipo_texto or 'segunda' in tipo_texto:
                    dados['praca'] = '2a Praca'
                elif '1' in tipo_texto or 'primeira' in tipo_texto:
                    dados['praca'] = '1a Praca'

            # Modalidade
            modalidade_elem = await self.page.query_selector(".modalidade, .sale-type")
            if modalidade_elem:
                dados['modalidade'] = (await modalidade_elem.inner_text()).strip()

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao coletar detalhes de {url}: {e}")

        return dados
