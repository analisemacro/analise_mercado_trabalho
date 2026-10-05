# Testes do CODIGO da coleta: usam dados de mentira e nao acessam a internet.
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import buscar_dados as bd


def resposta_falsa(conteudo):
    r = mock.MagicMock()
    r.__enter__.return_value.read.return_value = conteudo.encode()
    return r


class TestCodigo(unittest.TestCase):

    def test_codigos_das_series(self):
        """As series pedidas ao BCB sao a 24369 (desemprego) e a 24382 (rendimento)"""
        self.assertEqual(bd.SERIES, {"taxa_desemprego": 24369, "rendimento_medio_real": 24382})

    def test_converte_data(self):
        """A data do BCB (dd/mm/aaaa) vira aaaa-mm-dd sem trocar dia e mes"""
        linhas = bd.montar_linhas({"01/03/2012": "8.0"}, {"01/03/2012": "3077.00"})
        self.assertEqual(linhas[1], "2012-03-01;8.0;3077.00")

    def test_ordem_cronologica(self):
        """Os meses saem em ordem de data, mesmo que cheguem fora de ordem"""
        d = {"01/01/2013": "1", "01/12/2012": "2", "01/02/2012": "3"}
        linhas = bd.montar_linhas(d, d)
        self.assertEqual([l[:7] for l in linhas[1:]], ["2012-02", "2012-12", "2013-01"])

    def test_junta_pelo_mes(self):
        """Cada valor fica na linha do seu proprio mes, na coluna certa"""
        linhas = bd.montar_linhas({"01/01/2020": "11.2", "01/02/2020": "11.6"},
                                  {"01/01/2020": "3400", "01/02/2020": "3390"})
        self.assertEqual(linhas, [bd.CABECALHO, "2020-01-01;11.2;3400", "2020-02-01;11.6;3390"])

    def test_mes_faltando_fica_vazio(self):
        """Se uma serie nao tem um mes, o campo fica vazio (o teste de dados vai acusar)"""
        linhas = bd.montar_linhas({"01/01/2020": "11.2"}, {})
        self.assertEqual(linhas[1], "2020-01-01;11.2;")

    def test_site_fora_do_ar_nao_grava(self):
        """Se o BCB nao responde, a coleta para e o arquivo antigo fica intacto"""
        with tempfile.TemporaryDirectory() as pasta:
            arq = Path(pasta) / "dados.csv"
            arq.write_text("conteudo antigo", encoding="utf-8")
            with mock.patch("urllib.request.urlopen", side_effect=OSError("sem conexao")), \
                 mock.patch("time.sleep"):
                with self.assertRaises(bd.ErroColeta):
                    bd.coletar(arq)
            self.assertEqual(arq.read_text(encoding="utf-8"), "conteudo antigo")

    def test_tenta_de_novo_apos_falha(self):
        """Se o BCB falha uma vez e depois responde, a coleta tenta de novo e grava"""
        json_falso = '[{"data":"01/03/2012","valor":"8.0"}]'
        respostas = [OSError("502 Bad Gateway"), resposta_falsa(json_falso), resposta_falsa(json_falso)]
        with tempfile.TemporaryDirectory() as pasta:
            arq = Path(pasta) / "dados.csv"
            with mock.patch("urllib.request.urlopen", side_effect=respostas) as urlopen, \
                 mock.patch("time.sleep") as espera:
                bd.coletar(arq)
            self.assertEqual(urlopen.call_count, 3)
            espera.assert_called_once_with(bd.ESPERA)
            self.assertTrue(arq.exists())

    def test_serie_vazia_nao_grava(self):
        """Se o BCB devolve uma serie vazia, a coleta para e o arquivo antigo fica intacto"""
        with tempfile.TemporaryDirectory() as pasta:
            arq = Path(pasta) / "dados.csv"
            arq.write_text("conteudo antigo", encoding="utf-8")
            with mock.patch("urllib.request.urlopen", return_value=resposta_falsa("[]")):
                with self.assertRaises(bd.ErroColeta):
                    bd.coletar(arq)
            self.assertEqual(arq.read_text(encoding="utf-8"), "conteudo antigo")

    def test_coleta_completa_grava_arquivo(self):
        """Com respostas validas do BCB, o arquivo e gravado no formato combinado"""
        json_falso = '[{"data":"01/03/2012","valor":"8.0"}]'
        with tempfile.TemporaryDirectory() as pasta:
            arq = Path(pasta) / "dados.csv"
            with mock.patch("urllib.request.urlopen", side_effect=lambda *a, **k: resposta_falsa(json_falso)):
                bd.coletar(arq)
            self.assertEqual(arq.read_text(encoding="utf-8").splitlines(),
                             [bd.CABECALHO, "2012-03-01;8.0;8.0"])
            self.assertFalse(arq.with_suffix(".tmp").exists())


if __name__ == "__main__":
    unittest.main()
