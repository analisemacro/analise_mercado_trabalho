# Le mercado_trabalho.csv e gera um grafico PNG para cada serie.
import csv
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PASTA = Path(__file__).resolve().parent

datas, desemprego, rendimento = [], [], []
with open(PASTA / "mercado_trabalho.csv", encoding="utf-8-sig") as f:
    for linha in csv.DictReader(f, delimiter=";"):
        datas.append(datetime.strptime(linha["data"], "%Y-%m-%d"))
        desemprego.append(float(linha["taxa_desemprego"]))
        rendimento.append(float(linha["rendimento_medio_real"]))


def grafico(valores, titulo, unidade, formato, arquivo, cor):
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    ax.plot(datas, valores, color=cor, linewidth=2)
    ax.scatter([datas[-1]], [valores[-1]], color=cor, zorder=3)
    ax.annotate(formato(valores[-1]), (datas[-1], valores[-1]),
                xytext=(8, 0), textcoords="offset points", va="center",
                color=cor, fontweight="bold")
    ax.set_title(titulo, loc="left", fontsize=14, fontweight="bold")
    ax.set_ylabel(unidade)
    ax.grid(axis="y", alpha=0.3)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.text(0.01, 0.01, "Fonte: Banco Central do Brasil (SGS) / IBGE, PNAD Contínua",
             fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.03, 0.97, 1))
    fig.savefig(PASTA / arquivo)
    plt.close(fig)


def br(x, casas):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


grafico(desemprego, "Taxa de desemprego no Brasil", "% da força de trabalho",
        lambda v: f"{br(v, 1)}%", "grafico_desemprego.png", "#1f4e79")
grafico(rendimento, "Rendimento médio real do trabalho", "R$ (valores reais)",
        lambda v: f"R$ {br(v, 0)}", "grafico_rendimento.png", "#2a9d8f")
print("Graficos gerados.")
