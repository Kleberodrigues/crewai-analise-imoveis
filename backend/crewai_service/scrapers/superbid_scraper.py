"""
Scraper para o Superbid (superbid.net)
Leiloes extrajudiciais de imoveis
"""

import re
import logging
from typing import List, Dict
from .base_scraper import BaseLeilaoScraper

logger = logging.getLogger(__name__)


class SuperbidScraper(BaseLeilaoScraper):
    """
    Scraper para o Superbid - grande portal de leiloes online.
    URL: https://www.superbid.net e https://sold.superbid.net

    Caracteristica: Sistema robusto com filtros via URL
    """

    FONTE_NOME = "superbid"
    BASE_URL = "https://www.superbid.net"
    SOLD_URL = "https://sold.superbid.net"

    # URL de listagem com filtros
    LISTAGEM_URL = "/categorias/imoveis"

    # Parametros de filtro
    FILTROS_URL = {
        "estado": "SP",
        "tipo": "apartamento",
        "ordenacao": "preco_asc"
    }

    # Seletores CSS
    SELETORES = {
        "card_imovel": ".auction-card, .lote-card, .property-card, [data-auction], .card-leilao",
        "link_imovel": "a[href*='/lote/'], a[href*='/auction/'], a.auction-link",
        "preco": ".current-bid, .lance-atual, .preco, .valor",
        "endereco": ".location, .endereco, .address, .local",
        "area": ".area, .metros, .m2, .size",
        "quartos": ".bedrooms, .quartos, .dorms",
        "desconto": ".discount, .desconto, .economia",
        "avaliacao": ".evaluation, .avaliacao, .valor-mercado",
        "imagem": "img.auction-img, img.lote-img, img[src*='auction']",
        "data_leilao": ".end-date, .encerramento, .data-fim",
        "praca": ".round, .praca, .etapa",
        "status": ".status, .estado, .situacao",
        "paginacao": ".pagination a.next, button.next, [aria-label='Next']",
        "total_resultados": ".results-count, .total"
    }

    async def coletar_listagem(self) -> List[Dict]:
        """
        Coleta lista de imoveis do Superbid.
        Tenta tanto superbid.net quanto sold.superbid.net
        """
        todos_imoveis = []

        # Coleta do site principal
        imoveis_principal = await self._coletar_de_url(self.BASE_URL)
        todos_imoveis.extend(imoveis_principal)

        # Delay entre sites
        await self.delay_aleatorio(3000, 5000)

        # Coleta do Sold (leiloes encerrados com venda direta)
        imoveis_sold = await self._coletar_de_url(self.SOLD_URL)
        todos_imoveis.extend(imoveis_sold)

        return todos_imoveis

    async def _coletar_de_url(self, base_url: str) -> List[Dict]:
        """Coleta imoveis de uma base URL especifica"""
        imoveis = []

        # Monta URL com filtros
        params = "&".join([f"{k}={v}" for k, v in self.FILTROS_URL.items()])
        url_completa = f"{base_url}{self.LISTAGEM_URL}?{params}"

        try:
            logger.info(f"[{self.FONTE_NOME}] Acessando {url_completa}")
            await self.page.goto(url_completa, wait_until="networkidle")
            await self.delay_aleatorio(2000, 4000)

            # Scroll para carregar conteudo lazy-loaded
            await self.scroll_pagina(vezes=8, delay_entre=1200)

            # Coleta primeira pagina
            imoveis_pagina = await self._extrair_pagina(base_url)
            imoveis.extend(imoveis_pagina)
            logger.info(f"[{self.FONTE_NOME}] Pagina 1: {len(imoveis_pagina)} imoveis")

            # Paginacao
            for pagina in range(2, 6):
                try:
                    next_btn = await self.page.query_selector(self.SELETORES["paginacao"])
                    if not next_btn:
                        # Tenta URL direta
                        url_pagina = f"{url_completa}&page={pagina}"
                        await self.page.goto(url_pagina, wait_until="networkidle")
                    else:
                        await next_btn.click()

                    await self.delay_aleatorio(2000, 4000)
                    await self.scroll_pagina(vezes=5)

                    imoveis_pagina = await self._extrair_pagina(base_url)
                    if not imoveis_pagina:
                        break

                    imoveis.extend(imoveis_pagina)
                    logger.info(f"[{self.FONTE_NOME}] Pagina {pagina}: {len(imoveis_pagina)} imoveis")

                except Exception as e:
                    logger.debug(f"[{self.FONTE_NOME}] Fim paginacao: {e}")
                    break

        except Exception as e:
            logger.error(f"[{self.FONTE_NOME}] Erro ao coletar {base_url}: {e}")

        return imoveis

    async def _extrair_pagina(self, base_url: str) -> List[Dict]:
        """Extrai imoveis da pagina atual"""
        imoveis = []

        await self.esperar_elemento(self.SELETORES["card_imovel"])
        cards = await self.page.query_selector_all(self.SELETORES["card_imovel"])

        for card in cards:
            try:
                imovel = await self._extrair_card(card, base_url)
                if imovel and imovel.get('link'):
                    imoveis.append(imovel)
            except Exception as e:
                logger.warning(f"[{self.FONTE_NOME}] Erro ao extrair card: {e}")

        return imoveis

    async def _extrair_card(self, card, base_url: str) -> Dict:
        """Extrai dados de um card de imovel"""
        dados = {}

        try:
            # Link do imovel
            link_elem = await card.query_selector(self.SELETORES["link_imovel"])
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    dados['link'] = href if href.startswith('http') else f"{base_url}{href}"
                    # ID do imovel
                    match = re.search(r'/lote/(\d+)|/auction/(\d+)|/(\d+)', href)
                    if match:
                        id_match = match.group(1) or match.group(2) or match.group(3)
                        prefixo = "SOLD" if "sold" in base_url else "SBID"
                        dados['id_imovel'] = f"{prefixo}-{id_match}"

            # Preco
            preco_elem = await card.query_selector(self.SELETORES["preco"])
            if preco_elem:
                preco_texto = await preco_elem.inner_text()
                dados['preco'] = self.extrair_preco(preco_texto)

            # Endereco
            endereco_elem = await card.query_selector(self.SELETORES["endereco"])
            if endereco_elem:
                endereco = await endereco_elem.inner_text()
                dados['endereco'] = endereco.strip()
                self._extrair_localizacao(endereco, dados)

            # Area
            area_elem = await card.query_selector(self.SELETORES["area"])
            if area_elem:
                area_texto = await area_elem.inner_text()
                dados['area_privativa'] = self.extrair_area(area_texto)

            # Quartos
            quartos_elem = await card.query_selector(self.SELETORES["quartos"])
            if quartos_elem:
                quartos_texto = await quartos_elem.inner_text()
                dados['quartos'] = self.extrair_numero(quartos_texto)

            # Desconto
            desconto_elem = await card.query_selector(self.SELETORES["desconto"])
            if desconto_elem:
                desconto_texto = await desconto_elem.inner_text()
                dados['desconto'] = self.extrair_numero(desconto_texto)

            # Valor de avaliacao
            avaliacao_elem = await card.query_selector(self.SELETORES["avaliacao"])
            if avaliacao_elem:
                avaliacao_texto = await avaliacao_elem.inner_text()
                dados['valor_avaliacao'] = self.extrair_preco(avaliacao_texto)

            # Imagem
            img_elem = await card.query_selector(self.SELETORES["imagem"])
            if img_elem:
                src = await img_elem.get_attribute("src") or await img_elem.get_attribute("data-src")
                if src:
                    dados['imagens'] = [src]

            # Data do leilao
            data_elem = await card.query_selector(self.SELETORES["data_leilao"])
            if data_elem:
                data_texto = await data_elem.inner_text()
                dados['data_leilao'] = data_texto.strip()

            # Praca
            praca_elem = await card.query_selector(self.SELETORES["praca"])
            if praca_elem:
                praca_texto = await praca_elem.inner_text()
                if '2' in praca_texto or 'second' in praca_texto.lower():
                    dados['praca'] = '2a Praca'
                else:
                    dados['praca'] = '1a Praca'

            # Status
            status_elem = await card.query_selector(self.SELETORES["status"])
            if status_elem:
                status_texto = (await status_elem.inner_text()).lower()
                if 'venda direta' in status_texto or 'direct' in status_texto:
                    dados['modalidade'] = 'Venda Direta'
                elif 'online' in status_texto:
                    dados['modalidade'] = 'Venda Online'

            # Define tipo
            dados['tipo_imovel'] = 'Apartamento'
            dados['modalidade'] = dados.get('modalidade', 'Venda Online')

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao extrair dados do card: {e}")

        return dados

    def _extrair_localizacao(self, endereco: str, dados: Dict) -> None:
        """Extrai bairro e cidade do endereco"""
        if not endereco:
            return

        partes = endereco.split(' - ')
        if len(partes) >= 2:
            dados['bairro'] = partes[-2].strip() if len(partes) >= 2 else ''

        match = re.search(r'([^-/]+)/SP', endereco, re.IGNORECASE)
        if match:
            dados['cidade'] = match.group(1).strip().upper()
        else:
            # Tenta encontrar cidade de outra forma
            match_cidade = re.search(r'SAO PAULO|SANTOS|CAMPINAS|GUARULHOS|OSASCO', endereco.upper())
            if match_cidade:
                dados['cidade'] = match_cidade.group()
            else:
                dados['cidade'] = 'SAO PAULO'

        dados['uf'] = 'SP'

    async def coletar_detalhes(self, url: str) -> Dict:
        """
        Coleta detalhes completos de um imovel do Superbid.

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
            preco_elem = await self.page.query_selector(".current-price, .preco-atual, .lance-atual, h2.valor")
            if preco_elem:
                preco_texto = await preco_elem.inner_text()
                dados['preco'] = self.extrair_preco(preco_texto)

            # Valor de avaliacao
            avaliacao_elem = await self.page.query_selector(".market-value, .avaliacao, .valor-mercado")
            if avaliacao_elem:
                avaliacao_texto = await avaliacao_elem.inner_text()
                dados['valor_avaliacao'] = self.extrair_preco(avaliacao_texto)

            # Endereco completo
            endereco_elem = await self.page.query_selector(".full-address, .endereco, h1.title, .titulo")
            if endereco_elem:
                dados['endereco'] = (await endereco_elem.inner_text()).strip()
                self._extrair_localizacao(dados['endereco'], dados)

            # Caracteristicas (formato lista ou tabela)
            caracteristicas = await self.page.query_selector_all(".spec-item, .feature, .caracteristica, tr")
            for carac in caracteristicas:
                texto = (await carac.inner_text()).lower()
                if 'm²' in texto or 'metro' in texto or 'area' in texto:
                    dados['area_privativa'] = self.extrair_area(texto)
                elif 'quarto' in texto or 'dorm' in texto or 'bedroom' in texto:
                    dados['quartos'] = self.extrair_numero(texto)
                elif 'vaga' in texto or 'garage' in texto or 'parking' in texto:
                    dados['vagas'] = self.extrair_numero(texto)

            # Data do leilao
            data_elem = await self.page.query_selector(".end-time, .encerramento, .data-fim")
            if data_elem:
                dados['data_leilao'] = (await data_elem.inner_text()).strip()

            # Descricao
            descricao_elem = await self.page.query_selector(".description, .descricao, .about")
            if descricao_elem:
                dados['descricao'] = (await descricao_elem.inner_text()).strip()[:500]

            # Imagens
            imagens = []
            img_elems = await self.page.query_selector_all(".gallery img, .photos img, .carousel img, .slider img")
            for img in img_elems[:10]:
                src = await img.get_attribute("src") or await img.get_attribute("data-src")
                if src and src.startswith('http'):
                    imagens.append(src)
            if imagens:
                dados['imagens'] = imagens

            # Praca/Etapa
            praca_elem = await self.page.query_selector(".auction-round, .praca, .etapa")
            if praca_elem:
                praca_texto = (await praca_elem.inner_text()).lower()
                if '2' in praca_texto or 'second' in praca_texto:
                    dados['praca'] = '2a Praca'
                elif '1' in praca_texto or 'first' in praca_texto:
                    dados['praca'] = '1a Praca'

            # Modalidade
            modalidade_elem = await self.page.query_selector(".sale-type, .modalidade, .tipo-venda")
            if modalidade_elem:
                modalidade_texto = (await modalidade_elem.inner_text()).lower()
                if 'direta' in modalidade_texto or 'direct' in modalidade_texto:
                    dados['modalidade'] = 'Venda Direta'
                else:
                    dados['modalidade'] = 'Venda Online'

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao coletar detalhes de {url}: {e}")

        return dados
