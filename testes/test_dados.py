# Testes dos DADOS: conferem o arquivo que a coleta acabou de gravar.
# ARQUIVO_DADOS aponta o arquivo novo; ARQUIVO_ANTERIOR, a versao do mes passado.
import csv
import os
import unittest
from datetime import date, datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent
ARQUIVO = Path(os.environ.get("ARQUIVO_DADOS", PASTA / "mercado_trabalho.csv"))
ANTERIOR = Path(os.environ.get("ARQUIVO_ANTERIOR", PASTA / "mercado_trabalho.csv"))

# Limites folgados: a historia (2012-2026) ficou entre 5,1% e 14,9% de desemprego,
# entre R$ 2.980 e R$ 3.689 de rendimento, e nunca variou mais que 0,7 ponto
# (desemprego) ou 1,8% (rendimento) de um mes para o outro.
DESEMPREGO_MIN, DESEMPREGO_MAX, DESEMPREGO_SALTO = 2.0, 25.0, 2.0
RENDIMENTO_MIN, RENDIMENTO_MAX, RENDIMENTO_SALTO = 1500.0, 6000.0, 0.08
ATRASO_MAX_MESES = 4


def ler(caminho):
    with open(caminho, encoding="utf-8-sig") as f:
        return list(csv.reader(f, delimiter=";"))


def num_mes(d):
    return d.year * 12 + d.month


class TestDados(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tabela = ler(ARQUIVO)
        cls.linhas = cls.tabela[1:]

    def test_cabecalho(self):
        """A primeira linha e data;taxa_desemprego;rendimento_medio_real"""
        self.assertEqual(self.tabela[0], ["data", "taxa_desemprego", "rendimento_medio_real"])

    def test_tres_colunas(self):
        """Toda linha tem exatamente 3 campos"""
        ruins = [i + 2 for i, l in enumerate(self.linhas) if len(l) != 3]
        self.assertEqual(ruins, [], f"linhas com numero errado de campos: {ruins}")

    def test_datas_validas(self):
        """Toda data e uma data real no formato aaaa-mm-01"""
        for l in self.linhas:
            d = datetime.strptime(l[0], "%Y-%m-%d")
            self.assertEqual(d.day, 1, f"data fora do dia 01: {l[0]}")

    def test_inicio_da_serie(self):
        """A serie comeca em marco de 2012, o inicio da PNAD Continua mensal"""
        self.assertEqual(self.linhas[0][0], "2012-03-01")

    def test_meses_sem_buraco_nem_repeticao(self):
        """Os meses sao consecutivos: nenhum faltando, nenhum repetido, nenhum fora de ordem"""
        meses = [num_mes(datetime.strptime(l[0], "%Y-%m-%d")) for l in self.linhas]
        problemas = [self.linhas[i + 1][0] for i in range(len(meses) - 1) if meses[i + 1] - meses[i] != 1]
        self.assertEqual(problemas, [], f"quebra na sequencia de meses antes de: {problemas}")

    def test_sem_valor_vazio(self):
        """Nenhum mes esta sem o desemprego ou sem o rendimento"""
        vazios = [l[0] for l in self.linhas if len(l) == 3 and (not l[1].strip() or not l[2].strip())]
        self.assertEqual(vazios, [], f"meses com valor faltando: {vazios}")

    def test_valores_sao_numeros(self):
        """Os dois valores de cada mes sao numeros (ponto como separador decimal)"""
        for l in self.linhas:
            for v in l[1:]:
                try:
                    float(v)
                except ValueError:
                    self.fail(f"{l[0]}: valor nao numerico '{v}'")

    def test_desemprego_na_faixa(self):
        """O desemprego fica entre 2% e 25% em todos os meses"""
        fora = [(l[0], l[1]) for l in self.linhas if not DESEMPREGO_MIN <= float(l[1]) <= DESEMPREGO_MAX]
        self.assertEqual(fora, [], f"desemprego fora da faixa: {fora}")

    def test_rendimento_na_faixa(self):
        """O rendimento fica entre R$ 1.500 e R$ 6.000 em todos os meses"""
        fora = [(l[0], l[2]) for l in self.linhas if not RENDIMENTO_MIN <= float(l[2]) <= RENDIMENTO_MAX]
        self.assertEqual(fora, [], f"rendimento fora da faixa: {fora}")

    def test_sem_salto_no_desemprego(self):
        """O desemprego nao muda mais de 2 pontos de um mes para o outro"""
        saltos = [self.linhas[i][0] for i in range(1, len(self.linhas))
                  if abs(float(self.linhas[i][1]) - float(self.linhas[i - 1][1])) > DESEMPREGO_SALTO]
        self.assertEqual(saltos, [], f"saltos suspeitos no desemprego em: {saltos}")

    def test_sem_salto_no_rendimento(self):
        """O rendimento nao muda mais de 8% de um mes para o outro"""
        saltos = [self.linhas[i][0] for i in range(1, len(self.linhas))
                  if abs(float(self.linhas[i][2]) / float(self.linhas[i - 1][2]) - 1) > RENDIMENTO_SALTO]
        self.assertEqual(saltos, [], f"saltos suspeitos no rendimento em: {saltos}")

    def test_dados_atualizados(self):
        """O ultimo mes tem no maximo 4 meses de atraso em relacao a hoje"""
        ultimo = datetime.strptime(self.linhas[-1][0], "%Y-%m-%d")
        atraso = num_mes(date.today()) - num_mes(ultimo)
        self.assertLessEqual(atraso, ATRASO_MAX_MESES, f"ultimo mes e {self.linhas[-1][0]}, {atraso} meses atras")
        self.assertGreaterEqual(atraso, 0, f"ultimo mes {self.linhas[-1][0]} esta no futuro")

    def test_nao_perdeu_meses(self):
        """O arquivo novo tem pelo menos tantos meses quanto o do mes anterior"""
        if not ANTERIOR.exists() or ANTERIOR == ARQUIVO:
            self.skipTest("sem versao anterior para comparar")
        antes = len(ler(ANTERIOR)) - 1
        self.assertGreaterEqual(len(self.linhas), antes, f"tinha {antes} meses, agora tem {len(self.linhas)}")

    def test_historico_nao_mudou(self):
        """Os meses que ja existiam continuam com os mesmos valores do arquivo anterior"""
        if not ANTERIOR.exists() or ANTERIOR == ARQUIVO:
            self.skipTest("sem versao anterior para comparar")
        novos = {l[0]: l[1:] for l in self.linhas}
        mudou = [l[0] for l in ler(ANTERIOR)[1:] if l[0] in novos and
                 [float(x) for x in novos[l[0]]] != [float(x) for x in l[1:]]]
        self.assertEqual(mudou, [], f"valores antigos mudaram em: {mudou} (pode ser revisao do IBGE; confira)")


if __name__ == "__main__":
    unittest.main()
