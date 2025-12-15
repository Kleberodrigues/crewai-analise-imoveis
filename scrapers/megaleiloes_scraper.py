"""
Scraper para o Mega Leiloes (megaleiloes.com.br)
Leiloes extrajudiciais de imoveis
"""

import re
import logging
from typing import List, Dict
from .base_scraper import BaseLeilaoScraper

logger = logging.getLogger(__name__)


class MegaLeiloesScraper(BaseLeilaoScraper):
    """
    Scraper para o Mega Leiloes - portal de leiloes com paginacao.
    URL: https://www.megaleiloes.com.br
    """

    FONTE_NOME = "mega_leiloes"
    BASE_URL = "https://www.megaleiloes.com.br"

    # URL de listagem com filtros: apartamento + SP + extrajudicial
    LISTAGEM_URL = "/imoveis/apartamentos"

    # Parametros de filtro
    FILTROS_URL = {
        "estado": "sp",
        "tipo_leilao": "extrajudicial",
        "ordenar": "preco_asc"
    }

    # Seletores CSS
    SELETORES = {
        "card_imovel": ".leilao-card, .imovel-card, .property-item, .auction-item",
        "link_imovel": "a[href*='/leilao/'], a[href*='/imovel/']",
        "preco": ".valor, .preco, .price, .lance-atual",
        "endereco": ".endereco, .local, .address, .localizacao",
        "area": ".area, .metros, .m2, [class*='area']",
        "quartos": ".quartos, .dormitorios, .dorms, [class*='quarto']",
        "desconto": ".desconto, .economia, .discount",
        "avaliacao": ".avaliacao, .valor-avaliado, .valor-mercado",
        "imagem": "img.foto, img.thumbnail, img.imovel",
        "data_leilao": ".data, .data-leilao, .prazo",
        "praca": ".praca, .etapa, .round",
        "modalidade": ".modalidade, .tipo-venda",
        "paginacao": ".pagination a.next, .proxima-pagina, [rel='next']",
        "total_resultados": ".total-resultados, .count, .quantidade"
    }

    async def coletar_listagem(self) -> List[Dict]:
        """
        Coleta lista de imoveis da pagina de listagem do Mega Leiloes.
        Implementa paginacao para coletar multiplas paginas.
        """
        imoveis = []
        url_base = f"{self.BASE_URL}{self.LISTAGEM_URL}"

        # Monta URL com filtros
        params = "&".join([f"{k}={v}" for k, v in self.FILTROS_URL.items()])
        url_completa = f"{url_base}?{params}"

        try:
            logger.info(f"[{self.FONTE_NOME}] Acessando {url_completa}")
            await self.page.goto(url_completa, wait_until="networkidle")
            await self.delay_aleatorio(2000, 4000)

            # Scroll para carregar conteudo
            await self.scroll_pagina(vezes=5, delay_entre=1000)

            # Coleta primeira pagina
            imoveis_pagina = await self._extrair_pagina()
            imoveis.extend(imoveis_pagina)
            logger.info(f"[{self.FONTE_NOME}] Pagina 1: {len(imoveis_pagina)} imoveis")

            # Coleta paginas adicionais
            for pagina in range(2, 6):  # Maximo 5 paginas
                try:
                    # Tenta navegar para proxima pagina
                    next_btn = await self.page.query_selector(self.SELETORES["paginacao"])
                    if not next_btn:
                        # Tenta URL direta com parametro de pagina
                        url_pagina = f"{url_completa}&pagina={pagina}"
                        await self.page.goto(url_pagina, wait_until="networkidle")

                    else:
                        await next_btn.click()

                    await self.delay_aleatorio(2000, 4000)
                    await self.scroll_pagina(vezes=3)

                    imoveis_pagina = await self._extrair_pagina()
                    if not imoveis_pagina:
                        break

                    imoveis.extend(imoveis_pagina)
                    logger.info(f"[{self.FONTE_NOME}] Pagina {pagina}: {len(imoveis_pagina)} imoveis")

                except Exception as e:
                    logger.debug(f"[{self.FONTE_NOME}] Fim da paginacao: {e}")
                    break

        except Exception as e:
            logger.error(f"[{self.FONTE_NOME}] Erro na listagem: {e}")

        return imoveis

    async def _extrair_pagina(self) -> List[Dict]:
        """Extrai imoveis da pagina atual"""
        imoveis = []

        await self.esperar_elemento(self.SELETORES["card_imovel"])
        cards = await self.page.query_selector_all(self.SELETORES["card_imovel"])

        for card in cards:
            try:
                imovel = await self._extrair_card(card)
                if imovel and imovel.get('link'):
                    imoveis.append(imovel)
            except Exception as e:
                logger.warning(f"[{self.FONTE_NOME}] Erro ao extrair card: {e}")

        return imoveis

    async def _extrair_card(self, card) -> Dict:
        """Extrai dados de um card de imovel"""
        dados = {}

        try:
            # Link do imovel
            link_elem = await card.query_selector(self.SELETORES["link_imovel"])
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    dados['link'] = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    # ID do imovel
                    match = re.search(r'/leilao/(\d+)|/imovel/(\d+)|/(\d+)', href)
                    if match:
                        id_match = match.group(1) or match.group(2) or match.group(3)
                        dados['id_imovel'] = f"MEGA-{id_match}"

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
                if '2' in praca_texto or 'segunda' in praca_texto.lower():
                    dados['praca'] = '2a Praca'
                else:
                    dados['praca'] = '1a Praca'

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

        # Padrao: "Endereco - Bairro - Cidade/SP"
        partes = endereco.split(' - ')
        if len(partes) >= 2:
            dados['bairro'] = partes[-2].strip() if len(partes) >= 2 else ''

        # Extrai cidade
        match = re.search(r'([^-/]+)/SP', endereco, re.IGNORECASE)
        if match:
            dados['cidade'] = match.group(1).strip().upper()
        else:
            dados['cidade'] = 'SAO PAULO'

        dados['uf'] = 'SP'

    async def coletar_detalhes(self, url: str) -> Dict:
        """
        Coleta detalhes completos de um imovel do Mega Leiloes.

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
            preco_elem = await self.page.query_selector(".preco-atual, .valor-lance, h2.valor")
            if preco_elem:
                preco_texto = await preco_elem.inner_text()
                dados['preco'] = self.extrair_preco(preco_texto)

            # Valor de avaliacao
            avaliacao_elem = await self.page.query_selector(".valor-avaliacao, .avaliado")
            if avaliacao_elem:
                avaliacao_texto = await avaliacao_elem.inner_text()
                dados['valor_avaliacao'] = self.extrair_preco(avaliacao_texto)

            # Endereco completo
            endereco_elem = await self.page.query_selector(".endereco-completo, h1.titulo, .localizacao")
            if endereco_elem:
                dados['endereco'] = (await endereco_elem.inner_text()).strip()
                self._extrair_localizacao(dados['endereco'], dados)

            # Caracteristicas
            caracteristicas = await self.page.query_selector_all(".caracteristica, .info-item, .detalhe")
            for carac in caracteristicas:
                texto = (await carac.inner_text()).lower()
                if 'm²' in texto or 'metro' in texto or 'area' in texto:
                    dados['area_privativa'] = self.extrair_area(texto)
                elif 'quarto' in texto or 'dorm' in texto:
                    dados['quartos'] = self.extrair_numero(texto)
                elif 'vaga' in texto or 'garage' in texto:
                    dados['vagas'] = self.extrair_numero(texto)

            # Data do leilao
            data_elem = await self.page.query_selector(".data-leilao, .encerramento")
            if data_elem:
                dados['data_leilao'] = (await data_elem.inner_text()).strip()

            # Descricao
            descricao_elem = await self.page.query_selector(".descricao, .description, .sobre")
            if descricao_elem:
                dados['descricao'] = (await descricao_elem.inner_text()).strip()[:500]

            # Imagens
            imagens = []
            img_elems = await self.page.query_selector_all(".galeria img, .fotos img, .carousel img")
            for img in img_elems[:10]:
                src = await img.get_attribute("src") or await img.get_attribute("data-src")
                if src and src.startswith('http'):
                    imagens.append(src)
            if imagens:
                dados['imagens'] = imagens

            # Praca
            praca_elem = await self.page.query_selector(".praca, .etapa")
            if praca_elem:
                praca_texto = (await praca_elem.inner_text()).lower()
                if '2' in praca_texto or 'segunda' in praca_texto:
                    dados['praca'] = '2a Praca'
                elif '1' in praca_texto or 'primeira' in praca_texto:
                    dados['praca'] = '1a Praca'

            # Modalidade
            modalidade_elem = await self.page.query_selector(".modalidade, .tipo-venda")
            if modalidade_elem:
                dados['modalidade'] = (await modalidade_elem.inner_text()).strip()

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao coletar detalhes de {url}: {e}")

        return dados
