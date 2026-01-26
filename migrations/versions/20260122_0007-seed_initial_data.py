"""seed initial data

Revision ID: 007_seed_initial_data
Revises: 006_add_model_download_distribution
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '007_seed_initial_data'
down_revision = '006_add_model_download_distribution'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Seed initial data: default organization and admin user."""

    # Get the password hashing function from backend
    # Note: We'll use a pre-computed hash for 'admin123'
    # This is the bcrypt hash for 'admin123'
    admin_password_hash = '$2b$12$wvtERcqnTZa420f1C9knxOzF6nUuB83tlmyb1pcOgzbF0gsmKo9Qe'

    # Insert default organization
    connection = op.get_bind()

    # Insert default organization
    connection.execute(
        sa.text("""
            INSERT INTO organizations (name, plan, quota_tokens, quota_models, quota_gpus, max_workers, created_at, updated_at)
            VALUES ('Default Organization', 'PROFESSIONAL', 1000000, 100, 10, 50, NOW(), NOW())
            RETURNING id
        """)
    )

    # Get the organization_id
    result = connection.execute(
        sa.text("SELECT id FROM organizations WHERE name = 'Default Organization' LIMIT 1")
    )
    org_row = result.fetchone()
    org_id = org_row[0] if org_row else None

    # Insert admin user
    if org_id:
        connection.execute(
            sa.text("""
                INSERT INTO users (username, email, password_hash, organization_id, role, is_active, created_at, updated_at)
                VALUES (:username, :email, :password_hash, :org_id, :role, :is_active, NOW(), NOW())
            """),
            {
                'username': 'admin',
                'email': 'admin@tokenmachine.local',
                'password_hash': admin_password_hash,
                'org_id': org_id,
                'role': 'ADMIN',
                'is_active': True
            }
        )

    print("✓ Seeded initial data:")
    print("  - Organization: Default Organization")
    print("  - Admin user: admin / admin123")


def downgrade() -> None:
    """Remove seeded initial data."""

    connection = op.get_bind()

    # Delete admin user
    connection.execute(
        sa.text("DELETE FROM users WHERE username = 'admin'")
    )

    # Delete default organization
    connection.execute(
        sa.text("DELETE FROM organizations WHERE name = 'Default Organization'")
    )

    print("✓ Removed seeded initial data")
