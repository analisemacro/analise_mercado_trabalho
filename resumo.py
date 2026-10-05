# Passo 3 da rotina: calcula os numeros do relatorio a partir de
# mercado_trabalho.csv e divulgacoes.csv e grava tudo em resumo.json.
# O relatorio.qmd so le esse resumo; nenhum numero e digitado a mao.
import csv
import json
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def br(x, casas):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def nome_mes(d):
    return f"{MESES[d.month - 1]} de {d.year}"


def trimestre(d):
    inicio = MESES[(d.month - 3) % 12]
    return f"{inicio} a {MESES[d.month - 1]} de {d.year}" if d.month >= 3 \
        else f"{inicio} de {d.year - 1} a {MESES[d.month - 1]} de {d.year}"


def calcular(pasta=PASTA):
    with open(pasta / "mercado_trabalho.csv", encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    with open(pasta / "divulgacoes.csv", encoding="utf-8-sig") as f:
        chegadas = {l["mes_referencia"]: l["data_chegada"] for l in csv.DictReader(f, delimiter=";")}

    datas = [datetime.strptime(l["data"], "%Y-%m-%d") for l in linhas]
    desemp = [float(l["taxa_desemprego"]) for l in linhas]
    rend = [float(l["rendimento_medio_real"]) for l in linhas]

    def var_desemp(i):
        dif = round(desemp[-1] - desemp[i], 1)
        if dif == 0:
            return f"ficou igual ({br(desemp[i], 1)}% em {nome_mes(datas[i])})"
        verbo = "caiu" if dif < 0 else "subiu"
        pontos = "ponto percentual" if abs(dif) <= 1 else "pontos percentuais"
        return f"{verbo} {br(abs(dif), 1)} {pontos} (era {br(desemp[i], 1)}% em {nome_mes(datas[i])})"

    def var_rend(i):
        dif = rend[-1] - rend[i]
        pct = (rend[-1] / rend[i] - 1) * 100
        if round(dif) == 0:
            return f"ficou igual (R$ {br(rend[i], 0)} em {nome_mes(datas[i])})"
        verbo = "subiu" if dif > 0 else "caiu"
        return (f"{verbo} R$ {br(abs(dif), 0)}, ou {br(abs(pct), 1)}% "
                f"(era R$ {br(rend[i], 0)} em {nome_mes(datas[i])})")

    chegada_iso = chegadas.get(linhas[-1]["data"])
    return {
        "mes_iso": linhas[-1]["data"],
        "mes_ref": nome_mes(datas[-1]),
        "tri_ref": trimestre(datas[-1]),
        "inicio": nome_mes(datas[0]),
        "chegada": datetime.strptime(chegada_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
                   if chegada_iso else "não registrada",
        "desemp_ult": br(desemp[-1], 1),
        "desemp_1m": var_desemp(-2),
        "desemp_12m": var_desemp(-13),
        "rend_ult": br(rend[-1], 0),
        "rend_1m": var_rend(-2),
        "rend_12m": var_rend(-13),
    }


def escrever(pasta=PASTA):
    resumo = calcular(pasta)
    (pasta / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    return resumo


if __name__ == "__main__":
    r = escrever()
    print(f"Desemprego {r['desemp_ult']}% e rendimento R$ {r['rend_ult']} em {r['mes_ref']}")
