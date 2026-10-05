# Rotina mensal: testa o codigo, coleta os dados numa copia de trabalho,
# testa os dados e, so se tudo passar, atualiza o arquivo oficial, os graficos
# gera o relatorio do mes (se ainda nao existir) e atualiza a pagina em docs/.
# Cada teste vai para logs/testes.log com data, hora e resultado.
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


def publicar_site(pasta_relatorio):
    """Copia o relatorio mais recente para docs/, a pasta que o GitHub Pages publica."""
    site = PASTA / "docs"
    site.mkdir(exist_ok=True)
    (site / ".nojekyll").touch()
    shutil.copyfile(pasta_relatorio / "relatorio.html", site / "index.html")
    shutil.copyfile(pasta_relatorio / "relatorio.pdf", site / "relatorio.pdf")
    registrar(f"Site atualizado com o relatorio de {pasta_relatorio.name}")


def registrar(texto):
    linha = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {texto}"
    print(linha)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def parar(motivo, aviso="O arquivo oficial e os graficos NAO foram alterados."):
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


sys.path.insert(0, str(PASTA / "testes"))
sys.path.insert(0, str(PASTA))
registrar("=== Inicio da rotina ===")

registrar("Etapa 1: testes do codigo")
if not rodar_testes("test_codigo"):
    parar("algum teste do codigo falhou.")

registrar("Etapa 2: coleta no Banco Central (copia de trabalho)")
import buscar_dados
try:
    linhas = buscar_dados.coletar(NOVO)
except buscar_dados.ErroColeta as e:
    parar(str(e))
registrar(f"Coleta ok: {len(linhas) - 1} meses, ultimo {linhas[-1]}")

registrar("Etapa 3: testes dos dados")
os.environ["ARQUIVO_DADOS"] = str(NOVO)
os.environ["ARQUIVO_ANTERIOR"] = str(OFICIAL)
if not rodar_testes("test_dados"):
    parar(f"algum teste dos dados falhou. Os dados novos ficaram em {NOVO.name} para conferencia.")

registrar("Etapa 4: atualizando o arquivo oficial")
os.replace(NOVO, OFICIAL)

registrar("Etapa 5: relatorio (graficos)")
if subprocess.run([sys.executable, str(PASTA / "graficos.py")]).returncode != 0:
    parar("erro ao gerar os graficos.", "Os dados ja foram atualizados; so os graficos ficaram para tras.")

registrar("Etapa 6: relatorio do mes")
mes = ultimo_mes(OFICIAL)
anotar_chegada(mes)
destino = RELATORIOS / mes[:7]
if (destino / "relatorio.html").exists() and (destino / "relatorio.pdf").exists():
    registrar(f"Sem dado novo: o relatorio de {mes[:7]} ja existe em {destino.relative_to(PASTA)}")
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
    registrar(f"Relatorio de {mes[:7]} gerado em {destino.relative_to(PASTA)} (HTML e PDF)")

registrar("Etapa 7: pagina do site (pasta docs, publicada pelo GitHub Pages)")
publicar_site(destino)

registrar("=== Rotina concluida: todos os testes passaram ===")
