"""Add ICD10.search_terms and trigram index.

Revision ID: 9b1c2d3e4f5a
Revises: 7c3e1a9b6f2d
Create Date: 2026-02-13

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b1c2d3e4f5a"
down_revision = "7c3e1a9b6f2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("icd10", sa.Column("search_terms", sa.Text(), nullable=True))

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Keep pg_trgm enabled for fast wildcard and similarity lookups.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Replace the previous description-only trigram index with a multicolumn index that supports
    # fast wildcard + similarity search across both description and clinician-curated search_terms.
    try:
        op.drop_index("ix_icd10_description_trgm", table_name="icd10")
    except Exception:
        pass

    op.create_index(
        "ix_icd10_desc_terms_trgm",
        "icd10",
        ["description", "search_terms"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={
            "description": "gin_trgm_ops",
            "search_terms": "gin_trgm_ops",
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("ix_icd10_desc_terms_trgm", table_name="icd10")

        op.create_index(
            "ix_icd10_description_trgm",
            "icd10",
            ["description"],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        )

    op.drop_column("icd10", "search_terms")
