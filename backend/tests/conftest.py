import sys
from pathlib import Path

# Ensure `app` is importable when pytest runs from anywhere in the repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
