"""
Script de teste para os web scrapers de leilao
Testa cada scraper individualmente
"""

import asyncio
import sys
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar scrapers
from scrapers import (
    ZukScraper,
    SuperbidScraper,
    MegaLeiloesScraper,
    FrazaoScraper,
    BiasiScraper
)


async def testar_scraper(scraper_class, nome: str, max_imoveis: int = 5):
    """Testa um scraper individual"""
    print(f"\n{'='*60}")
    print(f"Testando: {nome}")
    print(f"{'='*60}")

    scraper = None
    try:
        # Inicializa scraper (headless=False para debug visual)
        scraper = scraper_class(headless=True)
        await scraper.iniciar()

        print(f"[{nome}] Browser iniciado...")

        # Coleta listagem
        print(f"[{nome}] Coletando listagem...")
        imoveis = await scraper.coletar_listagem()

        print(f"[{nome}] Total coletado: {len(imoveis)} imoveis")

        # Mostra primeiros resultados
        for i, imovel in enumerate(imoveis[:max_imoveis]):
            print(f"\n  [{i+1}] {imovel.get('id_imovel', 'N/A')}")
            print(f"      Preco: R$ {imovel.get('preco', 0):,.2f}")
            print(f"      Endereco: {imovel.get('endereco', 'N/A')[:50]}...")
            print(f"      Cidade: {imovel.get('cidade', 'N/A')}")
            print(f"      Link: {imovel.get('link', 'N/A')[:60]}...")

        # Filtra por preco
        filtrados = [i for i in imoveis if i.get('preco', 0) <= 200000 and i.get('preco', 0) > 0]
        print(f"\n[{nome}] Filtrados (ate R$ 200k): {len(filtrados)} imoveis")

        return {
            "scraper": nome,
            "status": "OK",
            "total": len(imoveis),
            "filtrados": len(filtrados),
            "amostra": imoveis[:3]
        }

    except Exception as e:
        logger.error(f"[{nome}] Erro: {e}")
        return {
            "scraper": nome,
            "status": "ERRO",
            "erro": str(e)
        }

    finally:
        if scraper:
            await scraper.finalizar()


async def testar_todos():
    """Testa todos os scrapers"""
    print("\n" + "="*60)
    print("TESTE DOS WEB SCRAPERS DE LEILAO")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    scrapers = [
        (ZukScraper, "Portal Zuk"),
        (SuperbidScraper, "Superbid"),
        (MegaLeiloesScraper, "Mega Leiloes"),
        (FrazaoScraper, "Frazao Leiloes"),
        (BiasiScraper, "Biasi Leiloes"),
    ]

    resultados = []

    for scraper_class, nome in scrapers:
        try:
            resultado = await testar_scraper(scraper_class, nome)
            resultados.append(resultado)
        except Exception as e:
            logger.error(f"Erro fatal em {nome}: {e}")
            resultados.append({
                "scraper": nome,
                "status": "ERRO FATAL",
                "erro": str(e)
            })

        # Delay entre scrapers
        print(f"\n[Aguardando 5s antes do proximo scraper...]")
        await asyncio.sleep(5)

    # Resumo final
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)

    total_coletados = 0
    total_filtrados = 0

    for r in resultados:
        status_icon = "✅" if r["status"] == "OK" else "❌"
        print(f"\n{status_icon} {r['scraper']}: {r['status']}")
        if r["status"] == "OK":
            print(f"   Total: {r['total']} | Filtrados: {r['filtrados']}")
            total_coletados += r.get("total", 0)
            total_filtrados += r.get("filtrados", 0)
        else:
            print(f"   Erro: {r.get('erro', 'Desconhecido')}")

    print(f"\n{'='*60}")
    print(f"TOTAL GERAL: {total_coletados} imoveis coletados")
    print(f"TOTAL FILTRADOS (ate R$ 200k): {total_filtrados} imoveis")
    print(f"{'='*60}")

    return resultados


async def testar_um(nome_scraper: str):
    """Testa apenas um scraper especifico"""
    scrapers_map = {
        "zuk": (ZukScraper, "Portal Zuk"),
        "superbid": (SuperbidScraper, "Superbid"),
        "mega": (MegaLeiloesScraper, "Mega Leiloes"),
        "frazao": (FrazaoScraper, "Frazao Leiloes"),
        "biasi": (BiasiScraper, "Biasi Leiloes"),
    }

    nome_lower = nome_scraper.lower()
    if nome_lower not in scrapers_map:
        print(f"Scraper '{nome_scraper}' nao encontrado.")
        print(f"Opcoes: {', '.join(scrapers_map.keys())}")
        return None

    scraper_class, nome = scrapers_map[nome_lower]
    return await testar_scraper(scraper_class, nome, max_imoveis=10)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Testa scraper especifico
        scraper_nome = sys.argv[1]
        asyncio.run(testar_um(scraper_nome))
    else:
        # Testa todos
        asyncio.run(testar_todos())
