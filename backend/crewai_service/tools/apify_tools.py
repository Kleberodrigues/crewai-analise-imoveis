"""
Tools de Integracao com Apify - Portal Zuk Scraper
"""

import os
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
# Removido decorador @tool para permitir chamada direta
# from crewai_tools import tool
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuracao Apify
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "apify/web-scraper")  # Seu Actor ID

# URL base da API Apify
APIFY_API_BASE = "https://api.apify.com/v2"


def get_apify_headers() -> Dict:
    """Headers para API Apify"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APIFY_TOKEN}"
    }


def run_apify_zuk_scraper(
    estado: str = "sp",
    max_items: int = 100,
    wait_for_finish: bool = True,
    timeout_secs: int = 600
) -> Dict:
    """
    Executa o Actor do Portal Zuk na Apify para coletar imoveis em leilao.

    Args:
        estado: Estado para filtrar (default: sp)
        max_items: Maximo de imoveis a coletar
        wait_for_finish: Aguardar conclusao
        timeout_secs: Timeout em segundos

    Returns:
        Dict com status e dados coletados
    """
    if not APIFY_TOKEN:
        return {"status": "error", "error": "APIFY_TOKEN nao configurado"}

    # Input do Actor (configuracao do usuario)
    actor_input = {
        "browserLog": False,
        "closeCookieModals": False,
        "debugLog": False,
        "downloadCss": True,
        "downloadMedia": True,
        "headless": True,
        "ignoreCorsAndCsp": False,
        "ignoreSslErrors": False,
        "keepUrlFragments": False,
        "launcher": "chromium",
        "linkSelector": ".card-property-image-wrapper a",
        "pageFunction": """async function pageFunction({ request, page, log, enqueueLinks, pushData }) {
    // PÁGINA DE LISTAGEM - São Paulo apenas
    if (request.url.includes('/leilao') && request.userData.label !== 'DETAIL') {
        try {
            log.info('📜 Iniciando scroll (FILTRO: São Paulo - SP)');

            await page.waitForLoadState('domcontentloaded');
            await page.waitForTimeout(5000);

            // Scroll agressivo
            await page.evaluate(async () => {
                for (let i = 0; i < 20; i++) {
                    window.scrollBy(0, 1000);
                    await new Promise(r => setTimeout(r, 800));
                }
            });

            await page.waitForTimeout(3000);
            log.info('✅ Scroll concluído');

            // Busca links de imóveis com múltiplos padrões
            const links = await page.evaluate(() => {
                const allLinks = Array.from(document.querySelectorAll('a'))
                    .map(el => ({
                        href: el.href,
                        text: el.textContent.toLowerCase()
                    }))
                    .filter(item => {
                        const href = item.href;
                        const text = item.text;

                        const validUrl = href && href.includes('portalzuk.com.br') &&
                            (href.includes('/imovel/') ||
                             href.includes('/imoveis/') ||
                             href.length > 60);

                        const isSP = text.includes('são paulo') ||
                                     text.includes('/ sp') ||
                                     text.includes('sp -') ||
                                     text.includes('sp/') ||
                                     text.includes('sp,');

                        return validUrl && isSP;
                    })
                    .map(item => item.href);

                return [...new Set(allLinks)];
            });

            log.info(`🔗 Imóveis de SP encontrados: ${links.length}`);

            if (links.length > 0) {
                await enqueueLinks({
                    urls: links,
                    userData: { label: 'DETAIL' }
                });
                log.info(`✅ ${links.length} imóveis de SP enfileirados`);
            }

        } catch (error) {
            log.error(`❌ Erro: ${error.message}`);
        }
    }

    // PÁGINA DE DETALHES - Apenas SP
    if (request.userData.label === 'DETAIL') {
        try {
            log.info(`🏠 Processando: ${request.url}`);

            await page.waitForLoadState('domcontentloaded');
            await page.waitForTimeout(2000);

            const data = await page.evaluate(() => {
                const getText = (selector) => {
                    const el = document.querySelector(selector);
                    return el ? el.innerText.trim() : '';
                };

                const pageText = document.body.innerText;

                // Extrai valores
                const valores = [];
                const valorMatches = pageText.match(/R\\$\\s*[\\d.,]+/g);
                if (valorMatches) valores.push(...valorMatches);

                // Extrai datas
                const datas = [];
                const dataMatches = pageText.match(/\\d{2}\\/\\d{2}\\/\\d{4}/g);
                if (dataMatches) datas.push(...dataMatches);

                // Tipo
                const titulo = getText('h1');
                let tipo = '';
                const tLower = titulo.toLowerCase();
                if (tLower.includes('apartamento')) tipo = 'Apartamento';
                else if (tLower.includes('casa')) tipo = 'Casa';
                else if (tLower.includes('sobrado')) tipo = 'Sobrado';
                else tipo = 'Outro';

                // Estado
                let estado = '';
                if (pageText.includes('/ SP') || pageText.includes('SP -')) estado = 'SP';

                return {
                    titulo: titulo,
                    tipo: tipo,
                    estado: estado,
                    endereco: getText('[class*="endereco"]') || getText('[class*="address"]'),
                    valores: valores,
                    datas: datas,
                    imagens: Array.from(document.querySelectorAll('img'))
                        .map(img => img.src)
                        .filter(src => src && !src.includes('data:image'))
                        .slice(0, 10),
                    url: window.location.href,
                    dataExtracao: new Date().toISOString()
                };
            });

            if (data.estado !== 'SP') {
                log.warning(`⚠️ Imóvel NÃO é de SP. Pulando...`);
                return;
            }

            log.info(`✅ ${data.tipo} em SP: ${data.titulo.substring(0, 50)}`);
            await pushData(data);
            log.info(`💾 Salvo!`);

        } catch (error) {
            log.error(`❌ Erro: ${error.message}`);
        }
    }
}""",
        "proxyConfiguration": {
            "useApifyProxy": True
        },
        "respectRobotsTxtFile": True,
        "startUrls": [
            {
                "url": f"https://www.portalzuk.com.br/leilao-de-imoveis/u/todos-imoveis/{estado}"
            }
        ],
        "useChrome": False,
        "waitUntil": "networkidle"
    }

    try:
        # Inicia o Actor
        logger.info(f"Iniciando Apify Actor para estado: {estado}")

        run_url = f"{APIFY_API_BASE}/acts/{APIFY_ACTOR_ID}/runs"

        response = requests.post(
            run_url,
            headers=get_apify_headers(),
            json=actor_input,
            timeout=30
        )

        if response.status_code != 201:
            return {
                "status": "error",
                "error": f"Falha ao iniciar Actor: {response.status_code}",
                "details": response.text
            }

        run_data = response.json()
        run_id = run_data["data"]["id"]
        logger.info(f"Actor iniciado. Run ID: {run_id}")

        if not wait_for_finish:
            return {
                "status": "started",
                "run_id": run_id,
                "message": "Actor iniciado em background"
            }

        # Aguarda conclusao
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout_secs:
                return {
                    "status": "timeout",
                    "run_id": run_id,
                    "elapsed_secs": elapsed
                }

            # Verifica status
            status_url = f"{APIFY_API_BASE}/actor-runs/{run_id}"
            status_response = requests.get(
                status_url,
                headers=get_apify_headers(),
                timeout=30
            )

            if status_response.status_code == 200:
                status_data = status_response.json()["data"]
                run_status = status_data.get("status")

                logger.info(f"Status: {run_status} ({int(elapsed)}s)")

                if run_status == "SUCCEEDED":
                    # Busca resultados
                    dataset_id = status_data.get("defaultDatasetId")
                    items = get_apify_dataset_items(dataset_id)

                    return {
                        "status": "success",
                        "run_id": run_id,
                        "dataset_id": dataset_id,
                        "total_items": len(items),
                        "items": items,
                        "elapsed_secs": int(elapsed)
                    }

                elif run_status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    return {
                        "status": "failed",
                        "run_id": run_id,
                        "run_status": run_status,
                        "elapsed_secs": int(elapsed)
                    }

            time.sleep(10)  # Aguarda 10s antes de verificar novamente

    except Exception as e:
        logger.error(f"Erro ao executar Actor: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def get_apify_dataset_items(dataset_id: str, limit: int = 1000) -> List[Dict]:
    """
    Busca items de um dataset Apify
    """
    try:
        url = f"{APIFY_API_BASE}/datasets/{dataset_id}/items"
        params = {"limit": limit}

        response = requests.get(
            url,
            headers=get_apify_headers(),
            params=params,
            timeout=60
        )

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Erro ao buscar dataset: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Erro ao buscar dataset: {str(e)}")
        return []


def get_apify_run_results(run_id: str) -> Dict:
    """
    Busca resultados de uma execucao anterior do Actor.

    Args:
        run_id: ID da execucao

    Returns:
        Dict com status e items
    """
    try:
        status_url = f"{APIFY_API_BASE}/actor-runs/{run_id}"
        response = requests.get(
            status_url,
            headers=get_apify_headers(),
            timeout=30
        )

        if response.status_code != 200:
            return {"status": "error", "error": f"Run nao encontrada: {run_id}"}

        status_data = response.json()["data"]
        run_status = status_data.get("status")

        if run_status != "SUCCEEDED":
            return {
                "status": "pending",
                "run_status": run_status
            }

        dataset_id = status_data.get("defaultDatasetId")
        items = get_apify_dataset_items(dataset_id)

        return {
            "status": "success",
            "run_id": run_id,
            "total_items": len(items),
            "items": items
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def parse_zuk_imovel(raw_data: Dict) -> Dict:
    """
    Parseia dados brutos do Portal Zuk para formato padrao.

    Args:
        raw_data: Dados brutos do scraper

    Returns:
        Dict com dados normalizados
    """
    try:
        titulo = raw_data.get("titulo", "")
        valores = raw_data.get("valores", [])
        datas = raw_data.get("datas", [])

        # Extrai valores numericos
        def parse_valor(valor_str: str) -> float:
            try:
                # Remove R$, pontos e troca virgula por ponto
                clean = valor_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
                return float(clean)
            except:
                return 0.0

        valores_float = [parse_valor(v) for v in valores if v]
        valores_float = [v for v in valores_float if v > 0]

        # Identifica valores (avaliacao geralmente e maior, lance e menor)
        valor_avaliacao = max(valores_float) if valores_float else 0
        valor_lance = min(valores_float) if valores_float else 0

        # Calcula desconto
        desconto = 0
        if valor_avaliacao > 0 and valor_lance > 0:
            desconto = ((valor_avaliacao - valor_lance) / valor_avaliacao) * 100

        # Extrai endereco do titulo ou campo
        endereco = raw_data.get("endereco", "")
        if not endereco and " - " in titulo:
            partes = titulo.split(" - ")
            if len(partes) > 1:
                endereco = partes[1]

        # Extrai bairro e cidade
        bairro = ""
        cidade = "SAO PAULO"  # Default para SP

        if endereco:
            partes = endereco.split(",")
            if len(partes) >= 2:
                bairro = partes[-2].strip() if len(partes) > 2 else partes[0].strip()

        # Extrai area do titulo
        area = 0
        import re
        area_match = re.search(r'(\d+[\.,]?\d*)\s*m[²2]', titulo.lower())
        if area_match:
            area = float(area_match.group(1).replace(',', '.'))

        # Extrai quartos
        quartos = 0
        quartos_match = re.search(r'(\d+)\s*(?:quarto|dorm|qto)', titulo.lower())
        if quartos_match:
            quartos = int(quartos_match.group(1))

        # Determina praca pelo desconto
        praca = "2a Praca" if desconto > 30 else "1a Praca"

        return {
            "id_imovel": raw_data.get("url", "").split("/")[-1] or f"zuk_{hash(raw_data.get('url', ''))}",
            "titulo": titulo,
            "tipo_imovel": raw_data.get("tipo", "Apartamento"),
            "endereco": endereco,
            "bairro": bairro.upper(),
            "cidade": cidade,
            "estado": "SP",
            "area_privativa": area,
            "quartos": quartos,
            "vagas": 0,
            "valor_avaliacao": valor_avaliacao,
            "preco": valor_lance,  # Valor minimo lance
            "desconto": round(desconto, 2),
            "praca": praca,
            "datas_leilao": datas,
            "imagens": raw_data.get("imagens", []),
            "link": raw_data.get("url", ""),
            "fonte": "portal_zuk",
            "data_extracao": raw_data.get("dataExtracao", datetime.now().isoformat())
        }

    except Exception as e:
        logger.error(f"Erro ao parsear imovel: {str(e)}")
        return {"error": str(e), "raw": raw_data}


def filter_zuk_imoveis(
    imoveis: List[Dict],
    preco_max: float = 150000,
    tipo: str = "Apartamento",
    desconto_min: float = 30
) -> Dict:
    """
    Filtra imoveis do Portal Zuk por criterios.

    Args:
        imoveis: Lista de imoveis parseados
        preco_max: Preco maximo
        tipo: Tipo de imovel
        desconto_min: Desconto minimo (para 2a praca)

    Returns:
        Dict com imoveis filtrados e estatisticas
    """
    filtrados = []

    for imovel in imoveis:
        # Verifica erro no parse
        if "error" in imovel:
            continue

        # Filtro de preco
        if imovel.get("preco", 0) > preco_max:
            continue

        # Filtro de tipo
        if tipo and imovel.get("tipo_imovel", "").lower() != tipo.lower():
            continue

        # Filtro de desconto (2a praca)
        if imovel.get("desconto", 0) < desconto_min:
            continue

        filtrados.append(imovel)

    # Ordena por desconto
    filtrados.sort(key=lambda x: x.get("desconto", 0), reverse=True)

    stats = {
        "total_original": len(imoveis),
        "total_filtrado": len(filtrados),
        "taxa_filtragem": f"{(len(filtrados)/len(imoveis)*100):.1f}%" if imoveis else "0%",
        "preco_medio": sum(i.get("preco", 0) for i in filtrados) / len(filtrados) if filtrados else 0,
        "desconto_medio": sum(i.get("desconto", 0) for i in filtrados) / len(filtrados) if filtrados else 0,
        "filtros": {
            "preco_max": preco_max,
            "tipo": tipo,
            "desconto_min": desconto_min
        }
    }

    return {
        "imoveis": filtrados,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }


# Exemplo de uso
if __name__ == "__main__":
    # Testa execucao (requer APIFY_TOKEN)
    if APIFY_TOKEN:
        result = run_apify_zuk_scraper(estado="sp", wait_for_finish=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result.get("status") == "success":
            # Parseia cada imovel
            parsed = [parse_zuk_imovel(item) for item in result.get("items", [])]
            print(f"\nTotal parseados: {len(parsed)}")

            # Filtra
            filtered = filter_zuk_imoveis(parsed)
            print(f"Total filtrados: {filtered['stats']['total_filtrado']}")
    else:
        print("APIFY_TOKEN nao configurado")
