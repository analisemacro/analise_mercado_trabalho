# Busca no SGS do Banco Central a taxa de desemprego (24369) e o
# rendimento medio real (24382) e grava em mercado_trabalho.csv.
# Se o BCB nao responder, para sem tocar no arquivo existente.
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent
DESTINO = PASTA / "mercado_trabalho.csv"
SERIES = {"taxa_desemprego": 24369, "rendimento_medio_real": 24382}
CABECALHO = "data;taxa_desemprego;rendimento_medio_real"


class ErroColeta(Exception):
    pass


def get_serie(codigo):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json"
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            dados = json.load(resp)
    except Exception as e:
        raise ErroColeta(f"O Banco Central nao respondeu para a serie {codigo} ({e}). Nada foi gravado.")
    if not dados:
        raise ErroColeta(f"A serie {codigo} veio vazia. Nada foi gravado.")
    return {d["data"]: d["valor"] for d in dados}


def montar_linhas(desemprego, rendimento):
    datas = sorted(set(desemprego) | set(rendimento),
                   key=lambda d: datetime.strptime(d, "%d/%m/%Y"))
    linhas = [CABECALHO]
    for dt in datas:
        iso = datetime.strptime(dt, "%d/%m/%Y").strftime("%Y-%m-%d")
        linhas.append(f"{iso};{desemprego.get(dt, '')};{rendimento.get(dt, '')}")
    return linhas


def coletar(destino=DESTINO):
    desemprego = get_serie(SERIES["taxa_desemprego"])
    rendimento = get_serie(SERIES["rendimento_medio_real"])
    linhas = montar_linhas(desemprego, rendimento)
    # Grava primeiro num arquivo temporario e so depois substitui o destino
    destino = Path(destino)
    temp = destino.with_suffix(".tmp")
    temp.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    os.replace(temp, destino)
    return linhas


if __name__ == "__main__":
    try:
        linhas = coletar()
    except ErroColeta as e:
        sys.exit(str(e))
    print(f"Meses gravados: {len(linhas) - 1}")
    print(f"Primeiro: {linhas[1]}")
    print(f"Ultimo:   {linhas[-1]}")
