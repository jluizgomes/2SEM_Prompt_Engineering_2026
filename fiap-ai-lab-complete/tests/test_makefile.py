import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
ENV_EXAMPLE = ROOT / ".env.example"


class MakefileBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name)
        shutil.copy2(MAKEFILE, self.project / "Makefile")
        shutil.copy2(ENV_EXAMPLE, self.project / ".env.example")
        shutil.copytree(ROOT / "scripts", self.project / "scripts")

    def tearDown(self):
        self.temp_dir.cleanup()

    def make(self, target, *, env=None, check=False):
        command = [
            "make",
            "--no-print-directory",
            "--file",
            str(MAKEFILE),
        ]
        command.extend(target.split())
        return subprocess.run(
            command,
            cwd=self.project,
            env=env or os.environ.copy(),
            text=True,
            capture_output=True,
            check=check,
        )

    def executable(self, name, body):
        path = self.project / "bin" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def test_setup_creates_models_directory_without_gguf(self):
        models = self.project / "models-vazio"

        result = self.make(f"setup MODELS_DIR={models}", check=True)

        self.assertTrue((self.project / ".env").is_file())
        self.assertTrue(models.is_dir())
        self.assertEqual(list(models.glob("*.gguf")), [])
        self.assertIn("GGUF é opcional", result.stdout)

    def test_fresh_up_langfuse_reloads_generated_environment(self):
        bin_dir = self.project / "bin"
        self.executable("docker", "#!/bin/sh\nexit 0\n")
        self.executable("python3", "#!/bin/sh\nexit 0\n")
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"

        result = self.make(f"up-langfuse MODELS_DIR={self.project / 'models'}", env=env)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Langfuse", result.stdout + result.stderr)

    def test_check_langfuse_env_accepts_complete_configuration(self):
        self.make("setup", check=True)

        result = self.make("check-langfuse-env", check=True)

        self.assertIn("Langfuse", result.stdout)


class MakefileValidationTests(unittest.TestCase):
    def test_test_net_forwards_langfuse_credentials(self):
        result = subprocess.run(
            ["make", "--no-print-directory", "--dry-run", "test-net"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("-e LANGFUSE_PUBLIC_KEY", result.stdout)
        self.assertIn("-e LANGFUSE_SECRET_KEY", result.stdout)

    def test_health_fails_when_core_services_are_down(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            shutil.copy2(MAKEFILE, project / "Makefile")
            bin_dir = project / "bin"
            bin_dir.mkdir()
            for name in ("docker", "curl"):
                executable = bin_dir / name
                executable.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
                executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"

            result = subprocess.run(
                ["make", "--no-print-directory", "--file", str(MAKEFILE), "health"],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)

    def test_config_fails_when_any_profile_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            count_file = project / "count"
            docker = project / "docker"
            docker.write_text(
                textwrap.dedent(
                    f"""\
                    #!/bin/sh
                    count=0
                    if [ -f "{count_file}" ]; then count=$(cat "{count_file}"); fi
                    count=$((count + 1))
                    printf '%s' "$count" > "{count_file}"
                    [ "$count" -gt 1 ]
                    """
                ),
                encoding="utf-8",
            )
            docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env["PATH"] = f"{project}{os.pathsep}{env['PATH']}"

            result = subprocess.run(
                ["make", "--no-print-directory", "--file", str(MAKEFILE), "config"],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)

    def test_clean_removes_the_compose_ollama_image_name(self):
        result = subprocess.run(
            ["make", "--no-print-directory", "--dry-run", "clean"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("fiap-ollama:latest", result.stdout)
        self.assertNotIn("fiap-ollama-cpu:latest", result.stdout)


if __name__ == "__main__":
    unittest.main()
