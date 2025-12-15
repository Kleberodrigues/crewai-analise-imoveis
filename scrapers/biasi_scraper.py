"""
Scraper para o Biasi Leiloes (biasileiloes.com.br)
Leiloes extrajudiciais de imoveis - Santander, Itau, Banco Inter
"""

import re
import logging
from typing import List, Dict
from .base_scraper import BaseLeilaoScraper

logger = logging.getLogger(__name__)


class BiasiScraper(BaseLeilaoScraper):
    """
    Scraper para o Biasi Leiloes - leiloeiro oficial de bancos.
    URL: https://www.biasileiloes.com.br

    Parceiros: Santander (381 imoveis), Itau (120), Banco Inter (15)
    Similar ao Frazao - multiplas URLs por banco
    """

    FONTE_NOME = "biasi_leiloes"
    BASE_URL = "https://www.biasileiloes.com.br"

    # URLs por banco parceiro
    URLS_BANCOS = [
        "/santander?uf=SP&tipo=apartamento",
        "/itau?uf=SP&tipo=apartamento",
        "/banco-inter?uf=SP&tipo=apartamento",
    ]

    # Seletores CSS
    SELETORES = {
        "card_imovel": ".leilao-card, .imovel-item, .property-card, .auction-item, [class*='leilao']",
        "link_imovel": "a[href*='/leilao/'], a[href*='/imovel/'], a.ver-mais",
        "preco": ".preco, .valor, .lance-minimo, .price",
        "endereco": ".endereco, .local, .localizacao, .address",
        "area": ".area, .metros, .m2",
        "quartos": ".quartos, .dormitorios, .dorms",
        "desconto": ".desconto, .economia, .discount",
        "avaliacao": ".avaliacao, .valor-avaliado, .valor-mercado",
        "imagem": "img.foto, img.thumb, img.imovel-img",
        "data_leilao": ".data, .data-leilao, .encerramento",
        "praca": ".praca, .etapa, .rodada",
        "modalidade": ".modalidade, .tipo-venda",
        "banco": ".banco, .parceiro, .instituicao",
        "paginacao": ".pagination a.next, .pagina-seguinte, button.next"
    }

    async def coletar_listagem(self) -> List[Dict]:
        """
        Coleta lista de imoveis de todas as URLs de bancos parceiros.
        Itera por Santander, Itau e Banco Inter.
        """
        todos_imoveis = []

        for url_banco in self.URLS_BANCOS:
            try:
                banco = self._extrair_nome_banco(url_banco)
                url_completa = f"{self.BASE_URL}{url_banco}"

                logger.info(f"[{self.FONTE_NOME}] Coletando {banco}: {url_completa}")
                imoveis_banco = await self._coletar_por_banco(url_completa, banco)
                todos_imoveis.extend(imoveis_banco)

                logger.info(f"[{self.FONTE_NOME}] {banco}: {len(imoveis_banco)} imoveis")

                # Delay entre bancos
                await self.delay_aleatorio(3000, 5000)

            except Exception as e:
                logger.error(f"[{self.FONTE_NOME}] Erro ao coletar {url_banco}: {e}")

        return todos_imoveis

    def _extrair_nome_banco(self, url: str) -> str:
        """Extrai nome do banco da URL"""
        url_lower = url.lower()
        if 'santander' in url_lower:
            return 'Santander'
        elif 'itau' in url_lower:
            return 'Itau'
        elif 'inter' in url_lower:
            return 'Banco Inter'
        return 'Desconhecido'

    async def _coletar_por_banco(self, url: str, banco: str) -> List[Dict]:
        """Coleta imoveis de uma URL especifica de banco"""
        imoveis = []

        try:
            await self.page.goto(url, wait_until="networkidle")
            await self.delay_aleatorio(2000, 3500)

            # Scroll para carregar conteudo
            await self.scroll_pagina(vezes=6, delay_entre=1000)

            # Coleta primeira pagina
            imoveis_pagina = await self._extrair_pagina(banco)
            imoveis.extend(imoveis_pagina)

            # Paginacao (maximo 4 paginas por banco)
            for pagina in range(2, 5):
                try:
                    next_btn = await self.page.query_selector(self.SELETORES["paginacao"])
                    if not next_btn:
                        # Tenta parametro na URL
                        url_pagina = f"{url}&pagina={pagina}"
                        await self.page.goto(url_pagina, wait_until="networkidle")
                    else:
                        await next_btn.click()

                    await self.delay_aleatorio(2000, 4000)
                    await self.scroll_pagina(vezes=4)

                    imoveis_pagina = await self._extrair_pagina(banco)
                    if not imoveis_pagina:
                        break

                    imoveis.extend(imoveis_pagina)
                    logger.info(f"[{self.FONTE_NOME}] {banco} Pagina {pagina}: {len(imoveis_pagina)} imoveis")

                except Exception as e:
                    logger.debug(f"[{self.FONTE_NOME}] Fim paginacao {banco}: {e}")
                    break

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao coletar banco {banco}: {e}")

        return imoveis

    async def _extrair_pagina(self, banco: str) -> List[Dict]:
        """Extrai imoveis da pagina atual"""
        imoveis = []

        await self.esperar_elemento(self.SELETORES["card_imovel"])
        cards = await self.page.query_selector_all(self.SELETORES["card_imovel"])

        for card in cards:
            try:
                imovel = await self._extrair_card(card, banco)
                if imovel and imovel.get('link'):
                    imoveis.append(imovel)
            except Exception as e:
                logger.warning(f"[{self.FONTE_NOME}] Erro ao extrair card: {e}")

        return imoveis

    async def _extrair_card(self, card, banco: str) -> Dict:
        """Extrai dados de um card de imovel"""
        dados = {'banco': banco}

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
                        banco_prefixo = banco[:3].upper()
                        dados['id_imovel'] = f"BIASI-{banco_prefixo}-{id_match}"

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
            dados['modalidade'] = 'Venda Online'

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
        Coleta detalhes completos de um imovel do Biasi.

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
            preco_elem = await self.page.query_selector(".preco-atual, .valor-lance, .lance-minimo")
            if preco_elem:
                preco_texto = await preco_elem.inner_text()
                dados['preco'] = self.extrair_preco(preco_texto)

            # Valor de avaliacao
            avaliacao_elem = await self.page.query_selector(".valor-avaliacao, .avaliado, .mercado")
            if avaliacao_elem:
                avaliacao_texto = await avaliacao_elem.inner_text()
                dados['valor_avaliacao'] = self.extrair_preco(avaliacao_texto)

            # Endereco completo
            endereco_elem = await self.page.query_selector(".endereco-completo, h1, .titulo")
            if endereco_elem:
                dados['endereco'] = (await endereco_elem.inner_text()).strip()
                self._extrair_localizacao(dados['endereco'], dados)

            # Caracteristicas
            caracteristicas = await self.page.query_selector_all(".caracteristica, .info, .detalhe, .spec")
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
            descricao_elem = await self.page.query_selector(".descricao, .description")
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

            # Banco (se nao foi setado)
            if 'banco' not in dados:
                banco_elem = await self.page.query_selector(".banco, .parceiro")
                if banco_elem:
                    dados['banco'] = (await banco_elem.inner_text()).strip()

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao coletar detalhes de {url}: {e}")

        return dados
