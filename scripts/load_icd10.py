import pandas as pd

from app.core.db import Base, SessionLocal, engine
from app.models.icd10 import ICD10

EXCEL_PATH = r"C:\Users\Usuario\Downloads\CODIGOS CIE10.xlsx"


def main() -> None:
    # Crear todas las tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    df = pd.read_excel(EXCEL_PATH)

    db = SessionLocal()
    try:
        for _, row in df.iterrows():
            code = str(row.get("CLAVE", "")).strip()
            description = str(row.get("DESCRIPCIÓN", "")).strip()

            if not code or not description or code.lower() == "nan" or description.lower() == "nan":
                continue

            db.add(ICD10(code=code, description=description))

        db.commit()
    finally:
        db.close()

    print("CIE-10 cargado correctamente")


if __name__ == "__main__":
    main()
