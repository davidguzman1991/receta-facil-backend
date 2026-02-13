import sys
import os

# Add project root to PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import pandas as pd

from app.core.db import Base, SessionLocal, engine
from app.models.icd10 import ICD10


def main() -> None:
    Base.metadata.create_all(bind=engine)

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    csv_path = os.path.join(BASE_DIR, "data", "icd10_codes.csv")

    print(f"Cargando archivo desde: {csv_path}")

    df = pd.read_csv(csv_path, sep=";")

    db = SessionLocal()
    try:
        for _, row in df.iterrows():
            code = str(row["code"]).strip()
            description = str(row["description"]).strip()

            if not code or not description:
                continue

            db.add(ICD10(code=code, description=description))

        db.commit()
    finally:
        db.close()

    print("CIE-10 cargado correctamente")


if __name__ == "__main__":
    main()

