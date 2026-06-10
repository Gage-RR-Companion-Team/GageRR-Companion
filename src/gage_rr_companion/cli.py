import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "download-local-model":
        from gage_rr_companion.cornelius import download_llama_cpp_model

        model_path = download_llama_cpp_model()
        print(f"Downloaded local Cornelius model to: {model_path}")
        return

    app_path = Path(__file__).resolve().parent / "Home.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), *sys.argv[1:]],
        check=True,
    )
