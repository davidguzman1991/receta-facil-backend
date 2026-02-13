"""Enable pg_trgm and add trigram index for ICD10 search.

Revision ID: 7c3e1a9b6f2d
Revises: 2a6f75e1d479
Create Date: 2026-02-13

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c3e1a9b6f2d"
down_revision = "2a6f75e1d479"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # pg_trgm provides fast similarity and wildcard matching for large text datasets.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index(
        "ix_icd10_description_trgm",
        "icd10",
        ["description"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"description": "gin_trgm_ops"},
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("ix_icd10_description_trgm", table_name="icd10")
