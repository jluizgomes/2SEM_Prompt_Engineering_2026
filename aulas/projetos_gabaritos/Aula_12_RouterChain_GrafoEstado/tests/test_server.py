import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main

try:
    import server
except ImportError:
    server = None


class RouterFalso:
    def __init__(self):
        self.entrada = None

    def invoke(self, entrada):
        self.entrada = entrada
        return {"categoria": " CÁLCULO ", "resposta": "96"}


class ExercicioFalso:
    def __init__(self):
        self.router = RouterFalso()

    @staticmethod
    def normalizar_categoria(categoria):
        return main.normalizar_categoria(categoria)


@unittest.skipIf(server is None, "FastAPI não está instalado neste ambiente")
class ServerA12Test(unittest.TestCase):
    def test_rotear_delega_ao_router_do_main(self):
        exercicio = ExercicioFalso()
        with patch.object(server, "_get_exercicio", return_value=exercicio):
            resultado = server.rotear(server.PerguntaBody(pergunta="Quanto é 12 vezes 8?"))

        self.assertEqual(
            resultado,
            {
                "tipo": "json",
                "conteudo": {"categoria": "calculo", "resposta": "96"},
            },
        )
        self.assertEqual(exercicio.router.entrada, {"pergunta": "Quanto é 12 vezes 8?"})


if __name__ == "__main__":
    unittest.main()
