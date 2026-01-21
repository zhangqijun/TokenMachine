"""add backend engines table

Revision ID: 004_add_backend_engines_table
Revises: 003_add_playground_tables
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_backend_engines_table'
down_revision = '003_add_playground_tables'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================================
    # Create Backend Engine ENUM types
    # ============================================================================

    # BackendEngineType enum
    postgresql.ENUM(
        name='backendenginetype',
        create_type=True
    ).create(op.get_bind(), checkfirst=True)

    # BackendEngineStatus enum
    postgresql.ENUM(
        name='backendenginestatus',
        create_type=True
    ).create(op.get_bind(), checkfirst=True)

    # ============================================================================
    # Create backend_engines table
    # ============================================================================
    op.create_table(
        'backend_engines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('engine_type', sa.Enum('vllm', 'sglang', 'llama_cpp', name='backendenginetype'), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('not_installed', 'installing', 'installed', 'error', 'outdated', name='backendenginestatus'), nullable=False, server_default='not_installed'),
        sa.Column('install_path', sa.String(length=1024), nullable=True),
        sa.Column('image_name', sa.String(length=255), nullable=True),
        sa.Column('tarball_path', sa.String(length=1024), nullable=True),
        sa.Column('installed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('config', postgresql.JSON(), nullable=True),
        sa.Column('env_vars', postgresql.JSON(), nullable=True),
        sa.Column('size_mb', sa.Integer(), nullable=True),
        sa.Column('active_deployments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='backend_engines_pkey'),
        keep_existing=True
    )

    # Create indexes
    op.create_index('ix_backend_engines_engine_type', 'backend_engines', ['engine_type'])
    op.create_index('ix_backend_engines_status', 'backend_engines', ['status'])
    op.create_index(
        'ix_backend_engine_type_version',
        'backend_engines',
        ['engine_type', 'version'],
        unique=True
    )


def downgrade():
    # Drop indexes
    op.drop_index('ix_backend_engine_type_version', table_name='backend_engines')
    op.drop_index('ix_backend_engines_status', table_name='backend_engines')
    op.drop_index('ix_backend_engines_engine_type', table_name='backend_engines')

    # Drop table
    op.drop_table('backend_engines')

    # Drop ENUM types
    postgresql.ENUM(name='backendenginestatus', create_type=False).drop(op.get_bind(), checkfirst=False)
    postgresql.ENUM(name='backendenginetype', create_type=False).drop(op.get_bind(), checkfirst=False)
