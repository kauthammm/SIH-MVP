"""
Rebuild indexes and retrain ML models using cleaned CSV data.
Run: cd d:\\Sih\\krishivoice\\backend && python scripts/rebuild_data_pipeline.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
ML = ROOT / "ml"


def run(cmd: list[str], cwd: Path) -> None:
    print(f"\n>>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    py = sys.executable
    run([py, "scripts/build_tamil_ds_index.py"], BACKEND)
    run([py, "scripts/build_convo_index.py"], BACKEND)
    run([py, "scripts/build_canonical_index.py"], BACKEND)
    run([py, "scripts/build_tamil_decision_index.py"], BACKEND)
    run([py, "scripts/build_tamil_slang_index.py"], BACKEND)
    run([py, "train_soil_crop_model.py"], ML)
    run([py, "train_models.py"], ML)
    run([py, "scripts/analyze_all_datasets.py"], BACKEND)
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
