from pathlib import Path
import runpy


ROOT_VALIDATE = Path(__file__).resolve().parents[1] / "validate.py"


if __name__ == "__main__":
    runpy.run_path(str(ROOT_VALIDATE), run_name="__main__")
