"""
API Flask para Pipeline de Analise de Leiloes
Endpoints para execucao manual, consulta e webhooks
"""

import os
import sys
import json
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Adiciona path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Import do pipeline
from main_pipeline import PipelineLeilao

# Configuracao
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Estado global
pipeline_status = {
    "running": False,
    "last_run": None,
    "last_result": None
}


# ==================== ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "service": "leilao-pipeline",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/status', methods=['GET'])
def status():
    """Status do pipeline"""
    return jsonify({
        "pipeline_running": pipeline_status["running"],
        "last_run": pipeline_status["last_run"],
        "last_result": pipeline_status["last_result"]
    })


@app.route('/run', methods=['POST'])
def run_pipeline():
    """
    Executa pipeline manualmente.

    Body (opcional):
    {
        "force_download": true,
        "skip_zuk": false,
        "max_imoveis": 50
    }
    """
    if pipeline_status["running"]:
        return jsonify({
            "status": "error",
            "message": "Pipeline ja esta em execucao"
        }), 409

    # Inicia em thread separada
    def run_async():
        pipeline_status["running"] = True
        pipeline_status["last_run"] = datetime.now().isoformat()

        try:
            pipeline = PipelineLeilao()
            result = pipeline.executar()
            pipeline_status["last_result"] = result
        except Exception as e:
            pipeline_status["last_result"] = {"error": str(e)}
        finally:
            pipeline_status["running"] = False

    thread = threading.Thread(target=run_async)
    thread.start()

    return jsonify({
        "status": "started",
        "message": "Pipeline iniciado em background",
        "started_at": datetime.now().isoformat()
    })


@app.route('/results', methods=['GET'])
def get_results():
    """
    Retorna ultimos resultados.

    Query params:
    - limit: numero de resultados (default: 20)
    - recomendacao: filtrar por COMPRAR, ANALISAR_MELHOR, EVITAR
    - min_score: score minimo
    """
    limit = request.args.get('limit', 20, type=int)
    recomendacao = request.args.get('recomendacao', None)
    min_score = request.args.get('min_score', 0, type=float)

    # Le ultimo CSV de resultados
    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))

    # Busca arquivo mais recente
    csv_files = list(output_dir.glob("analise_leilao_*.csv"))

    if not csv_files:
        return jsonify({
            "status": "empty",
            "message": "Nenhum resultado encontrado"
        })

    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)

    try:
        import pandas as pd
        df = pd.read_csv(latest_csv, sep=';')

        # Aplica filtros
        if recomendacao:
            df = df[df['recomendacao'] == recomendacao]

        if min_score > 0:
            df = df[df['score_geral'] >= min_score]

        # Ordena por score
        df = df.sort_values('score_geral', ascending=False)

        # Limita
        df = df.head(limit)

        return jsonify({
            "status": "success",
            "total": len(df),
            "arquivo": str(latest_csv),
            "resultados": df.to_dict('records')
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/imovel/<imovel_id>', methods=['GET'])
def get_imovel(imovel_id: str):
    """Retorna detalhes de um imovel especifico"""
    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
    csv_files = list(output_dir.glob("analise_leilao_*.csv"))

    if not csv_files:
        return jsonify({"error": "Nenhum dado encontrado"}), 404

    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)

    try:
        import pandas as pd
        df = pd.read_csv(latest_csv, sep=';')

        imovel = df[df['id_imovel'] == imovel_id]

        if imovel.empty:
            return jsonify({"error": "Imovel nao encontrado"}), 404

        return jsonify({
            "status": "success",
            "imovel": imovel.to_dict('records')[0]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Retorna estatisticas gerais"""
    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
    csv_files = list(output_dir.glob("analise_leilao_*.csv"))

    if not csv_files:
        return jsonify({
            "total_analises": 0,
            "total_arquivos": 0
        })

    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)

    try:
        import pandas as pd
        df = pd.read_csv(latest_csv, sep=';')

        stats = {
            "total_imoveis": len(df),
            "por_recomendacao": df['recomendacao'].value_counts().to_dict(),
            "por_cidade": df['cidade'].value_counts().to_dict(),
            "preco_medio": df['valor_minimo_leilao'].mean(),
            "desconto_medio": df['desconto_percentual'].mean(),
            "roi_medio": df['cenario_roi_percentual'].mean(),
            "score_medio": df['score_geral'].mean(),
            "ultimo_arquivo": str(latest_csv),
            "data_atualizacao": datetime.fromtimestamp(latest_csv.stat().st_mtime).isoformat()
        }

        return jsonify(stats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/webhook/apify', methods=['POST'])
def webhook_apify():
    """
    Webhook para receber notificacoes do Apify quando scraping terminar.
    Configura no Apify: POST para /webhook/apify
    """
    data = request.get_json()

    logger.info(f"Webhook Apify recebido: {data.get('eventType')}")

    if data.get("eventType") == "ACTOR.RUN.SUCCEEDED":
        # Scraping concluido, pode processar resultados
        run_id = data.get("actorRunId")
        logger.info(f"Apify run concluido: {run_id}")

        # Aqui poderia disparar analise automatica
        # ...

    return jsonify({"status": "received"})


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename: str):
    """Download de arquivo de resultado"""
    from flask import send_from_directory

    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
    filepath = output_dir / filename

    if not filepath.exists():
        return jsonify({"error": "Arquivo nao encontrado"}), 404

    return send_from_directory(
        output_dir,
        filename,
        as_attachment=True
    )


@app.route('/files', methods=['GET'])
def list_files():
    """Lista arquivos disponiveis para download"""
    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))

    files = []
    for f in output_dir.glob("*"):
        if f.is_file():
            files.append({
                "name": f.name,
                "size_kb": f.stat().st_size / 1024,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "download_url": f"/download/{f.name}"
            })

    # Ordena por data
    files.sort(key=lambda x: x["modified"], reverse=True)

    return jsonify({
        "total": len(files),
        "files": files
    })


# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    app.run(host='0.0.0.0', port=port, debug=debug)
