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

    # URL de listagem - apartamentos em SP
    LISTAGEM_URL = "/imoveis/apartamentos/sp"

    # Parametros de filtro
    FILTROS_URL = {}

    # Seletores CSS - baseado na estrutura real do site
    SELETORES = {
        "card_imovel": ".card",
        "link_imovel": "a",
        "preco": ".card-price, .card-instance-value",
        "endereco": ".card-locality, .card-title",
        "titulo": ".card-title",
        "area": ".card-content [class*='area']",
        "quartos": ".card-content [class*='quarto'], .card-content [class*='dorm']",
        "desconto": ".card-status",
        "avaliacao": ".card-instance-value",
        "imagem": ".card-image img",
        "data_leilao": ".card-first-instance-date, .card-second-instance-date",
        "praca": ".card-instance-title",
        "modalidade": ".card-status",
        "banco": ".card-bank img",
        "paginacao": ".pagination a.next, a[rel='next'], .page-next",
        "total_resultados": ".results-count, .total"
    }

    async def coletar_listagem(self) -> List[Dict]:
        """
        Coleta lista de imoveis da pagina de listagem do Mega Leiloes.
        Implementa paginacao para coletar multiplas paginas.
        """
        imoveis = []
        url_base = f"{self.BASE_URL}{self.LISTAGEM_URL}"

        # Monta URL com filtros (se houver)
        if self.FILTROS_URL:
            params = "&".join([f"{k}={v}" for k, v in self.FILTROS_URL.items()])
            url_completa = f"{url_base}?{params}"
        else:
            url_completa = url_base

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

        # Aguarda cards carregarem
        try:
            await self.page.wait_for_selector(".card", timeout=10000)
        except:
            logger.warning(f"[{self.FONTE_NOME}] Timeout aguardando .card")

        # Busca todos os cards na pagina
        cards = await self.page.query_selector_all(".card")
        logger.info(f"[{self.FONTE_NOME}] {len(cards)} cards encontrados na pagina")

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
            # Link do imovel - busca link com /imoveis/ no href
            link_elem = await card.query_selector("a[href*='/imoveis/']")
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    dados['link'] = href
                    # ID do imovel - extrai codigo X123456 do final da URL
                    match = re.search(r'-x(\d+)', href, re.IGNORECASE)
                    if match:
                        dados['id_imovel'] = f"MEGA-{match.group(1)}"
                    else:
                        # Tenta extrair qualquer numero
                        match = re.search(r'/(\d+)', href)
                        if match:
                            dados['id_imovel'] = f"MEGA-{match.group(1)}"

            # Se nao encontrou link valido, pula este card
            if not dados.get('link'):
                return dados

            # Preco - .card-price
            preco_elem = await card.query_selector(".card-price")
            if preco_elem:
                preco_texto = await preco_elem.inner_text()
                dados['preco'] = self.extrair_preco(preco_texto)

            # Titulo/Endereco - .card-title
            titulo_elem = await card.query_selector(".card-title")
            if titulo_elem:
                titulo = await titulo_elem.inner_text()
                dados['endereco'] = titulo.strip()

            # Localidade - .card-locality
            local_elem = await card.query_selector(".card-locality")
            if local_elem:
                local = await local_elem.inner_text()
                dados['endereco'] = f"{dados.get('endereco', '')} - {local.strip()}"
                self._extrair_localizacao(local, dados)

            # Numero do lote - .card-number
            numero_elem = await card.query_selector(".card-number")
            if numero_elem:
                numero = await numero_elem.inner_text()
                if not dados.get('id_imovel'):
                    dados['id_imovel'] = f"MEGA-{numero.strip()}"

            # Imagem - .card-image img
            img_elem = await card.query_selector(".card-image img")
            if img_elem:
                src = await img_elem.get_attribute("src") or await img_elem.get_attribute("data-src")
                if src:
                    dados['imagens'] = [src]

            # Data do leilao - datas das pracas
            data_elem = await card.query_selector(".card-first-instance-date, .card-second-instance-date")
            if data_elem:
                data_texto = await data_elem.inner_text()
                dados['data_leilao'] = data_texto.strip()

            # Praca - .card-instance-title
            praca_elem = await card.query_selector(".card-instance-title")
            if praca_elem:
                praca_texto = await praca_elem.inner_text()
                if '2' in praca_texto or 'segunda' in praca_texto.lower():
                    dados['praca'] = '2a Praca'
                else:
                    dados['praca'] = '1a Praca'

            # Valor da instancia (praca) - .card-instance-value
            valor_elem = await card.query_selector(".card-instance-value")
            if valor_elem:
                valor_texto = await valor_elem.inner_text()
                valor = self.extrair_preco(valor_texto)
                if valor and not dados.get('preco'):
                    dados['preco'] = valor

            # Banco - .card-bank img (alt text)
            banco_elem = await card.query_selector(".card-bank img")
            if banco_elem:
                banco_alt = await banco_elem.get_attribute("alt")
                if banco_alt:
                    dados['banco'] = banco_alt.strip()

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
