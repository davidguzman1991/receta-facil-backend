import sys
import os
from pathlib import Path

# Add project root to PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import pandas as pd

from sqlalchemy import func, select

from app.core.db import Base, SessionLocal, engine
from app.models.icd10 import ICD10


def main() -> None:
    Base.metadata.create_all(bind=engine)

    BASE_DIR = Path(__file__).resolve().parent.parent
    csv_path = BASE_DIR / "app" / "data" / "icd10_codes.csv"

    db = SessionLocal()
    try:
        existing_count = db.execute(select(func.count()).select_from(ICD10)).scalar_one()
        if existing_count > 0:
            print("ICD10 already loaded. Skipping.")
            return

        print(f"Cargando archivo desde: {csv_path.resolve()}")

        df = pd.read_csv(csv_path, sep=";")

        for _, row in df.iterrows():
            code = str(row["code"]).strip()
            description = str(row["description"]).strip()

            if not code or not description:
                continue

            db.merge(ICD10(code=code, description=description))

        db.commit()
        print("CIE-10 cargado correctamente")
    except Exception as exc:
        db.rollback()
        print(f"Error cargando ICD10: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

