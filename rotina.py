# Rotina mensal em quatro passos, nesta ordem:
#   1. coletar   - baixa as series do BCB para uma copia de trabalho
#   2. testar    - testa o codigo e os dados; so se tudo passar, a copia vira o arquivo oficial
#   3. resumo    - calcula os numeros do relatorio e grava resumo.json
#   4. relatorio - monta o relatorio do mes (HTML e PDF) e atualiza a pagina em docs/
# Uso: "python rotina.py" roda os quatro; "python rotina.py testar" roda so um passo.
# Cada passo e cada teste vao para logs/testes.log com data, hora e resultado.
import os
import shutil
import subprocess
import sys
import unittest
from datetime import date, datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent
OFICIAL = PASTA / "mercado_trabalho.csv"
NOVO = PASTA / "mercado_trabalho_novo.csv"
DIVULGACOES = PASTA / "divulgacoes.csv"
RELATORIOS = PASTA / "relatorios"
LOG = PASTA / "logs" / "testes.log"

sys.path.insert(0, str(PASTA / "testes"))
sys.path.insert(0, str(PASTA))


def registrar(texto):
    linha = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {texto}"
    print(linha, flush=True)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def parar(motivo, aviso="O arquivo oficial e o relatorio NAO foram alterados."):
    registrar(f"ROTINA INTERROMPIDA: {motivo}")
    registrar(aviso)
    sys.exit(1)


class ResultadoComLog(unittest.TextTestResult):
    def _nome(self, teste):
        return teste.shortDescription() or teste.id()

    def addSuccess(self, teste):
        super().addSuccess(teste)
        registrar(f"PASSOU | {self._nome(teste)}")

    def addFailure(self, teste, err):
        super().addFailure(teste, err)
        registrar(f"FALHOU | {self._nome(teste)} | {err[1]}")

    def addError(self, teste, err):
        super().addError(teste, err)
        registrar(f"ERRO   | {self._nome(teste)} | {err[0].__name__}: {err[1]}")

    def addSkip(self, teste, motivo):
        super().addSkip(teste, motivo)
        registrar(f"PULOU  | {self._nome(teste)} | {motivo}")


def rodar_testes(arquivo):
    suite = unittest.defaultTestLoader.loadTestsFromName(arquivo)
    resultado = unittest.TextTestRunner(resultclass=ResultadoComLog, verbosity=0,
                                        stream=open(os.devnull, "w")).run(suite)
    return resultado.wasSuccessful()


def ultimo_mes(arquivo):
    return arquivo.read_text(encoding="utf-8-sig").strip().splitlines()[-1].split(";")[0]


def anotar_chegada(mes):
    """Guarda o dia em que o mes de referencia apareceu pela primeira vez."""
    if not DIVULGACOES.exists():
        DIVULGACOES.write_text("mes_referencia;data_chegada\n", encoding="utf-8")
    if mes not in DIVULGACOES.read_text(encoding="utf-8"):
        with open(DIVULGACOES, "a", encoding="utf-8") as f:
            f.write(f"{mes};{date.today():%Y-%m-%d}\n")
        registrar(f"Mes novo {mes}: chegada anotada em {DIVULGACOES.name}")


def passo_coletar():
    registrar("Passo 1: coletar os dados no Banco Central (copia de trabalho)")
    import buscar_dados
    try:
        linhas = buscar_dados.coletar(NOVO)
    except buscar_dados.ErroColeta as e:
        parar(str(e))
    registrar(f"Coleta ok: {len(linhas) - 1} meses, ultimo {linhas[-1]}")


def passo_testar():
    registrar("Passo 2: testar o codigo e os dados")
    if not NOVO.exists():
        parar("nao ha copia de trabalho para testar; rode o passo 'coletar' antes.")
    if not rodar_testes("test_codigo"):
        parar("algum teste do codigo falhou.")
    os.environ["ARQUIVO_DADOS"] = str(NOVO)
    os.environ["ARQUIVO_ANTERIOR"] = str(OFICIAL)
    if not rodar_testes("test_dados"):
        parar(f"algum teste dos dados falhou. Os dados novos ficaram em {NOVO.name} para conferencia.")
    os.replace(NOVO, OFICIAL)
    anotar_chegada(ultimo_mes(OFICIAL))
    registrar("Todos os testes passaram; mercado_trabalho.csv atualizado")


def passo_resumo():
    registrar("Passo 3: calcular e escrever o resumo")
    import resumo
    r = resumo.escrever()
    registrar(f"Resumo ok: desemprego {r['desemp_ult']}% e rendimento R$ {r['rend_ult']} em {r['mes_ref']}")


def passo_relatorio():
    registrar("Passo 4: montar o relatorio")
    mes = ultimo_mes(OFICIAL)[:7]
    destino = RELATORIOS / mes
    refazer = os.environ.get("REFAZER_RELATORIO", "").lower() == "true"
    if refazer:
        registrar(f"Pedido para refazer o relatorio de {mes}")
    if not refazer and (destino / "relatorio.html").exists() and (destino / "relatorio.pdf").exists():
        registrar(f"Sem dado novo: o relatorio de {mes} ja existe em {destino.relative_to(PASTA)}")
    else:
        quarto = shutil.which("quarto")
        if not quarto:
            parar("o Quarto nao foi encontrado.", "Os dados ja foram atualizados; so o relatorio ficou para tras.")
        destino.mkdir(parents=True, exist_ok=True)
        for formato, extensao in (("html", "html"), ("typst", "pdf")):
            r = subprocess.run([quarto, "render", "relatorio.qmd", "--to", formato], cwd=PASTA,
                               env={**os.environ, "PASTA_DADOS": str(PASTA)},
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                registrar(r.stderr.strip()[-800:])
                parar(f"erro ao gerar o relatorio ({formato}).",
                      "Os dados ja foram atualizados; so o relatorio ficou para tras.")
            os.replace(PASTA / f"relatorio.{extensao}", destino / f"relatorio.{extensao}")
        registrar(f"Relatorio de {mes} gerado em {destino.relative_to(PASTA)} (HTML e PDF)")

    # A pasta docs/ e o que o GitHub Pages publica: sempre o relatorio mais recente
    site = PASTA / "docs"
    site.mkdir(exist_ok=True)
    (site / ".nojekyll").touch()
    shutil.copyfile(destino / "relatorio.html", site / "index.html")
    shutil.copyfile(destino / "relatorio.pdf", site / "relatorio.pdf")
    registrar(f"Pagina do site atualizada com o relatorio de {mes}")


PASSOS = {"coletar": passo_coletar, "testar": passo_testar,
          "resumo": passo_resumo, "relatorio": passo_relatorio}

if __name__ == "__main__":
    pedidos = sys.argv[1:] or list(PASSOS)
    invalidos = [p for p in pedidos if p not in PASSOS]
    if invalidos:
        sys.exit(f"Passo desconhecido: {invalidos}. Use: {', '.join(PASSOS)}")
    registrar(f"=== Inicio: {', '.join(pedidos)} ===")
    for p in pedidos:
        PASSOS[p]()
    registrar(f"=== Fim: {', '.join(pedidos)} concluido(s) ===")
