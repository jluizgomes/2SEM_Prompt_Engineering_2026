import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "ollama" / "entrypoint.sh"


class OllamaBootstrapTests(unittest.TestCase):
    def test_empty_models_directory_keeps_container_alive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            bin_dir = project / "bin"
            models_dir = project / "models"
            bin_dir.mkdir()
            models_dir.mkdir()
            ollama = bin_dir / "ollama"
            ollama.write_text(
                "#!/bin/sh\n"
                "if [ \"${1:-}\" = serve ]; then exit 0; fi\n"
                "if [ \"${1:-}\" = list ]; then printf 'NAME ID SIZE MODIFIED\\n'; exit 0; fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            ollama.chmod(ollama.stat().st_mode | stat.S_IXUSR)
            curl = bin_dir / "curl"
            curl.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
            nvidia = bin_dir / "nvidia-smi"
            nvidia.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            nvidia.chmod(nvidia.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
                    "GGUF_DIR": str(models_dir),
                    "GGUF_FILE": "modelo-que-nao-existe.gguf",
                    "GGUF_MODEL": "modelo-que-nao-existe",
                    "CHAT_MODEL": "modelo-remoto-que-nao-existe",
                    "EMBEDDING_MODEL": "embedding-que-nao-existe",
                    "GUARDRAIL_MODELS": "",
                    "EXTRA_MODELS": "",
                    "EMBEDDING_CONTEXT": "",
                    "OLLAMA_NUM_THREADS": "1",
                }
            )

            result = subprocess.run(
                [str(ENTRYPOINT)],
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Nenhum arquivo .gguf", result.stdout)
            self.assertIn("AVISO: falha ao baixar", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
