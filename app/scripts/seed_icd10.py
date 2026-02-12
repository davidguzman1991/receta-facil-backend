import csv
import os

from sqlalchemy import select

from app.core.db import Base, SessionLocal, engine
from app.models.icd10 import ICD10


DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "icd10_codes.csv")


def seed_icd10(csv_path: str = DEFAULT_CSV_PATH) -> tuple[int, int]:
    Base.metadata.create_all(bind=engine)

    inserted = 0
    existed = 0

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        db = SessionLocal()
        try:
            for row in reader:
                code = (row.get("code") or "").strip()
                description = (row.get("description") or "").strip()
                if not code or not description:
                    continue

                existing = db.execute(select(ICD10).where(ICD10.code == code)).scalar_one_or_none()
                if existing:
                    existed += 1
                    if existing.description != description:
                        existing.description = description
                    continue

                db.add(ICD10(code=code, description=description))
                inserted += 1

            db.commit()
        finally:
            db.close()

    return inserted, existed


def main() -> None:
    csv_path = os.getenv("ICD10_CSV_PATH", DEFAULT_CSV_PATH)
    inserted, existed = seed_icd10(csv_path=csv_path)
    print(f"ICD10 seed complete. inserted={inserted} existed={existed}")


if __name__ == "__main__":
    main()
