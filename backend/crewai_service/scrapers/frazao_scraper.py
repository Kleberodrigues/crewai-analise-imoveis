"""
Scraper para o Frazao Leiloes (frazaoleiloes.com.br)
Leiloes extrajudiciais de imoveis - Multiplos bancos (Itau, Santander, Inter)
"""

import re
import logging
from typing import List, Dict
from .base_scraper import BaseLeilaoScraper

logger = logging.getLogger(__name__)


class FrazaoScraper(BaseLeilaoScraper):
    """
    Scraper para o Frazao Leiloes - agregador de leiloes de varios bancos.
    URL: https://www.frazaoleiloes.com.br

    Caracteristica: Multiplas URLs por banco (Itau, Santander, Banco Inter)
    """

    FONTE_NOME = "frazao_leiloes"
    BASE_URL = "https://www.frazaoleiloes.com.br"

    # URLs por banco - sem filtros complexos para evitar erros
    URLS_BANCOS = [
        "/itau/leiloes",
        "/santander/leiloes",
    ]

    # Seletores CSS - baseado na estrutura real do site (Dez 2024)
    SELETORES = {
        "card_imovel": ".card-format-all, .thumbnail-vitrine-lot",
        "link_imovel": "a.item-photo[href*='/lote/']",
        "preco": ".price-line",
        "endereco": ".item-photo",  # titulo no data-addr ou texto interno
        "titulo": ".inf-lote-address",
        "area": ".inf-lote-icons span, [class*='area']",
        "quartos": "[class*='quarto'], [class*='dorm']",
        "desconto": ".desconto, .percent",
        "avaliacao": ".avaliacao, .valor-avaliacao",
        "imagem": ".photo-lot img",
        "data_leilao": ".inf-leilao-calendar",
        "praca": ".praca, .etapa",
        "modalidade": ".status-tag",
        "banco": ".banco",
        "lote_id": ".lot-favorite",
        "paginacao": ".pagination a.next, a[rel='next'], .page-link"
    }

    async def coletar_listagem(self) -> List[Dict]:
        """
        Coleta lista de imoveis de todas as URLs de bancos.
        Itera por Itau, Santander e Banco Inter.
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

                # Delay entre bancos para evitar bloqueio
                await self.delay_aleatorio(3000, 5000)

            except Exception as e:
                logger.error(f"[{self.FONTE_NOME}] Erro ao coletar {url_banco}: {e}")

        return todos_imoveis

    def _extrair_nome_banco(self, url: str) -> str:
        """Extrai nome do banco da URL"""
        if 'itau' in url.lower():
            return 'Itau'
        elif 'santander' in url.lower():
            return 'Santander'
        elif 'inter' in url.lower():
            return 'Banco Inter'
        return 'Desconhecido'

    async def _coletar_por_banco(self, url: str, banco: str) -> List[Dict]:
        """Coleta imoveis de uma URL especifica de banco"""
        imoveis = []

        try:
            await self.page.goto(url, wait_until="networkidle")
            await self.delay_aleatorio(2000, 3500)

            # Scroll para carregar conteudo
            await self.scroll_pagina(vezes=5, delay_entre=1000)

            # Coleta primeira pagina
            imoveis_pagina = await self._extrair_pagina(banco)
            imoveis.extend(imoveis_pagina)

            # Paginacao
            for pagina in range(2, 4):  # Maximo 3 paginas por banco
                try:
                    next_btn = await self.page.query_selector(self.SELETORES["paginacao"])
                    if not next_btn:
                        break

                    await next_btn.click()
                    await self.delay_aleatorio(2000, 4000)
                    await self.scroll_pagina(vezes=3)

                    imoveis_pagina = await self._extrair_pagina(banco)
                    if not imoveis_pagina:
                        break

                    imoveis.extend(imoveis_pagina)

                except Exception as e:
                    logger.debug(f"[{self.FONTE_NOME}] Fim paginacao {banco}: {e}")
                    break

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao coletar banco {banco}: {e}")

        return imoveis

    async def _extrair_pagina(self, banco: str) -> List[Dict]:
        """Extrai imoveis da pagina atual"""
        imoveis = []

        # Aguarda cards carregarem
        try:
            await self.page.wait_for_selector(".card-format-all, .thumbnail-vitrine-lot", timeout=10000)
        except:
            logger.warning(f"[{self.FONTE_NOME}] Timeout aguardando cards")

        # Busca todos os cards - usando seletores atualizados
        cards = await self.page.query_selector_all(".card-format-all")
        if not cards:
            cards = await self.page.query_selector_all(".thumbnail-vitrine-lot")
        logger.info(f"[{self.FONTE_NOME}] {len(cards)} cards encontrados")

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
            # Link do imovel - busca link com /lote/ no href
            link_elem = await card.query_selector("a.item-photo[href*='/lote/'], a[href*='/lote/']")
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    dados['link'] = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    # ID do imovel - extrai numero do lote
                    match = re.search(r'/lote/(\d+)', href)
                    if match:
                        dados['id_imovel'] = f"FRAZAO-{banco[:3].upper()}-{match.group(1)}"

                    # Endereco do atributo data-addr ou titulo
                    addr = await link_elem.get_attribute("data-addr")
                    if addr:
                        dados['endereco'] = addr.strip()
                        self._extrair_localizacao(addr, dados)

                    # Tipo do imovel do atributo data-tipo
                    tipo = await link_elem.get_attribute("data-tipo")
                    if tipo:
                        dados['tipo_imovel'] = tipo.strip()

            # Preco - usando .price-line
            preco_elem = await card.query_selector(".price-line")
            if preco_elem:
                preco_texto = await preco_elem.inner_text()
                dados['preco'] = self.extrair_preco(preco_texto)

            # Titulo/descricao do imovel
            titulo_elem = await card.query_selector(".inf-lote-address, .card-title")
            if titulo_elem:
                titulo = await titulo_elem.inner_text()
                dados['descricao'] = titulo.strip()
                # Extrai localizacao do titulo se nao tiver endereco
                if not dados.get('endereco'):
                    self._extrair_localizacao(titulo, dados)

            # Area - busca no texto completo do card
            texto_completo = await card.inner_text()
            area_match = re.search(r'(\d+[.,]?\d*)\s*m[²2]', texto_completo)
            if area_match:
                area_str = area_match.group(1).replace(',', '.')
                dados['area_privativa'] = float(area_str)

            # Data do leilao
            data_elem = await card.query_selector(".inf-leilao-calendar")
            if data_elem:
                data_texto = await data_elem.inner_text()
                dados['data_leilao'] = data_texto.strip()

            # ID do lote (backup)
            if not dados.get('id_imovel'):
                lote_elem = await card.query_selector(".lot-favorite")
                if lote_elem:
                    lote_id = await lote_elem.get_attribute("loteid")
                    if lote_id:
                        dados['id_imovel'] = f"FRAZAO-{banco[:3].upper()}-{lote_id}"

            # Imagem
            img_elem = await card.query_selector(".photo-lot img, img")
            if img_elem:
                src = await img_elem.get_attribute("src") or await img_elem.get_attribute("data-src")
                if src and not 'placeholder' in src.lower():
                    dados['imagens'] = [src]

            # Define tipo padrao se nao encontrou
            if not dados.get('tipo_imovel'):
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
        Coleta detalhes completos de um imovel do Frazao.

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
            avaliacao_elem = await self.page.query_selector(".valor-avaliacao, .avaliado, .valor-mercado")
            if avaliacao_elem:
                avaliacao_texto = await avaliacao_elem.inner_text()
                dados['valor_avaliacao'] = self.extrair_preco(avaliacao_texto)

            # Endereco completo
            endereco_elem = await self.page.query_selector(".endereco-completo, h1, .titulo-imovel")
            if endereco_elem:
                dados['endereco'] = (await endereco_elem.inner_text()).strip()
                self._extrair_localizacao(dados['endereco'], dados)

            # Caracteristicas
            caracteristicas = await self.page.query_selector_all(".caracteristica, .info, .detalhe, li")
            for carac in caracteristicas:
                texto = (await carac.inner_text()).lower()
                if 'm²' in texto or 'metro' in texto or 'area' in texto:
                    dados['area_privativa'] = self.extrair_area(texto)
                elif 'quarto' in texto or 'dorm' in texto:
                    dados['quartos'] = self.extrair_numero(texto)
                elif 'vaga' in texto or 'garage' in texto:
                    dados['vagas'] = self.extrair_numero(texto)

            # Data do leilao
            data_elem = await self.page.query_selector(".data-leilao, .encerramento, .prazo")
            if data_elem:
                dados['data_leilao'] = (await data_elem.inner_text()).strip()

            # Descricao
            descricao_elem = await self.page.query_selector(".descricao, .description, .detalhes")
            if descricao_elem:
                dados['descricao'] = (await descricao_elem.inner_text()).strip()[:500]

            # Imagens
            imagens = []
            img_elems = await self.page.query_selector_all(".galeria img, .fotos img, .slider img")
            for img in img_elems[:10]:
                src = await img.get_attribute("src") or await img.get_attribute("data-src")
                if src and src.startswith('http'):
                    imagens.append(src)
            if imagens:
                dados['imagens'] = imagens

            # Praca
            praca_elem = await self.page.query_selector(".praca, .etapa, .rodada")
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

            # Banco (se nao foi setado antes)
            if 'banco' not in dados:
                banco_elem = await self.page.query_selector(".banco, .instituicao")
                if banco_elem:
                    dados['banco'] = (await banco_elem.inner_text()).strip()

        except Exception as e:
            logger.warning(f"[{self.FONTE_NOME}] Erro ao coletar detalhes de {url}: {e}")

        return dados
