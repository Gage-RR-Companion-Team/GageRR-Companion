import subprocess
import sys
from pathlib import Path


def main():
    app_path = Path(__file__).resolve().parent / "Home.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), *sys.argv[1:]],
        check=True
    )