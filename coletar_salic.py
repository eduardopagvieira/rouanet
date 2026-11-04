"""
Coleta dos projetos da Lei Rouanet pela API de dados abertos do SALIC.

Uso (no terminal, dentro da pasta do projeto):
    python coletar_salic.py            # coleta tudo, retomando de onde parou
    python coletar_salic.py --teste    # baixa só 2 páginas para conferir
    python coletar_salic.py --workers 4  # muda o número de conexões simultâneas (padrão 6)

Saídas:
    dados/brutos/pagina_000000.json    uma página da API por arquivo (dado bruto, nunca editado)
    dados/projetos_salic.csv           todas as páginas juntas numa tabela
"""

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

URL = "http://api.salic.cultura.gov.br/api/v1/projetos/"
POR_PAGINA = 100          # limite máximo aceito pela API
PAUSA = 0.5               # segundos entre requisições, para não sobrecarregar o servidor
TENTATIVAS = 6

PASTA_BRUTOS = Path("dados/brutos")
SAIDA_CSV = Path("dados/projetos_salic.csv")


def baixar_pagina(sessao, offset):
    params = {"format": "json", "limit": POR_PAGINA, "offset": offset}
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            r = sessao.get(URL, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as erro:
            espera = 2 ** tentativa
            print(f"  offset {offset}: falha ({erro}). Nova tentativa em {espera}s")
            time.sleep(espera)
    raise RuntimeError(f"Desisti do offset {offset} depois de {TENTATIVAS} tentativas")


def extrair_registros(resposta):
    """A API devolve os projetos dentro de _embedded.projetos. Aceita também lista pura."""
    if isinstance(resposta, list):
        return resposta
    embutido = resposta.get("_embedded", {})
    for chave in ("projetos", "projeto"):
        if chave in embutido:
            return embutido[chave]
    return []


_local = threading.local()


def nova_sessao():
    sessao = requests.Session()
    sessao.headers["User-Agent"] = "portfolio-rouanet (pesquisa academica)"
    return sessao


def sessao_da_thread():
    if not hasattr(_local, "sessao"):
        _local.sessao = nova_sessao()
    return _local.sessao


def arquivo_da_pagina(offset):
    return PASTA_BRUTOS / f"pagina_{offset:06d}.json"


def obter_pagina(offset, sessao=None):
    """Lê do disco se já baixada; senão baixa e salva (via arquivo temporário, para não deixar JSON pela metade)."""
    arquivo = arquivo_da_pagina(offset)
    if arquivo.exists():                           # retomada: pula o que já foi baixado
        return json.loads(arquivo.read_text(encoding="utf-8"))
    resposta = baixar_pagina(sessao or sessao_da_thread(), offset)
    temporario = arquivo.with_suffix(".tmp")
    temporario.write_text(json.dumps(resposta, ensure_ascii=False), encoding="utf-8")
    temporario.replace(arquivo)
    time.sleep(PAUSA)
    return resposta


def coletar(teste=False, workers=6):
    PASTA_BRUTOS.mkdir(parents=True, exist_ok=True)

    # A primeira página informa o total, o que permite saber de antemão todos os offsets
    primeira = obter_pagina(0, nova_sessao())
    total = primeira.get("total") if isinstance(primeira, dict) else None
    print("Chaves da resposta:", list(primeira.keys()) if isinstance(primeira, dict) else "lista")
    print("Total informado pela API:", total)
    registros = extrair_registros(primeira)
    if registros:
        print("Campos de um projeto:", list(registros[0].keys()))
    if not total:
        raise RuntimeError("A API não informou o total de projetos; não dá para paralelizar.")

    offsets = list(range(POR_PAGINA, total, POR_PAGINA))
    if teste:
        offsets = offsets[:1]
    faltando = [o for o in offsets if not arquivo_da_pagina(o).exists()]
    print(f"{len(offsets) + 1} páginas no total, {len(faltando)} a baixar com {workers} conexões em paralelo")

    feitas = 0
    inicio = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futuros = {executor.submit(obter_pagina, o): o for o in faltando}
        for futuro in as_completed(futuros):
            futuro.result()                        # propaga erro se uma página falhou de vez
            feitas += 1
            if feitas % 20 == 0 or feitas == len(faltando):
                decorrido = time.time() - inicio
                restante = decorrido / feitas * (len(faltando) - feitas)
                print(f"  {feitas}/{len(faltando)} páginas  (~{restante / 60:.1f} min restantes)", flush=True)


def juntar():
    linhas = []
    for arquivo in sorted(PASTA_BRUTOS.glob("pagina_*.json")):
        resposta = json.loads(arquivo.read_text(encoding="utf-8"))
        linhas.extend(extrair_registros(resposta))
    tabela = pd.json_normalize(linhas)
    tabela = tabela.loc[:, ~tabela.columns.str.startswith("_links")]   # descarta links internos da API
    tabela.to_csv(SAIDA_CSV, index=False, encoding="utf-8-sig")
    print(f"{len(tabela)} projetos e {tabela.shape[1]} colunas salvos em {SAIDA_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--teste", action="store_true", help="baixa só 2 páginas")
    parser.add_argument("--workers", type=int, default=6, help="conexões simultâneas (padrão 6)")
    args = parser.parse_args()
    coletar(teste=args.teste, workers=args.workers)
    juntar()
