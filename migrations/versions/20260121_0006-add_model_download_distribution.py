"""add model download distribution

Revision ID: 006_add_model_download_distribution
Revises: 005_add_gateway_management
Create Date: 2025-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_model_download_distribution'
down_revision = '005_add_gateway_management'
branch_labels = None
depends_on = None


def upgrade():
    """Add model download and distribution tables."""

    # ===========================================================================
    # Step 1: Add new columns to models table
    # ===========================================================================
    op.add_column(
        'models',
        sa.Column('modelscope_repo_id', sa.String(255), nullable=True)
    )
    op.create_index(
        'ix_model_modelscope_repo',
        'models',
        ['modelscope_repo_id']
    )

    op.add_column(
        'models',
        sa.Column('modelscope_revision', sa.String(50), server_default='master', nullable=True)
    )

    op.add_column(
        'models',
        sa.Column('storage_path', sa.String(1024), nullable=True)
    )
    op.create_index(
        'ix_model_storage_path',
        'models',
        ['storage_path']
    )

    op.add_column(
        'models',
        sa.Column('storage_type', sa.String(50), server_default='nfs', nullable=True)
    )

    op.add_column(
        'models',
        sa.Column('download_task_id', sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        'fk_models_download_task',
        'models',
        'model_download_tasks',
        ['download_task_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index(
        'ix_model_download_task_id',
        'models',
        ['download_task_id']
    )

    # ===========================================================================
    # Step 2: Create model_download_tasks table
    # ===========================================================================
    op.create_table(
        'model_download_tasks',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.BigInteger(), nullable=False),
        sa.Column('modelscope_repo_id', sa.String(255), nullable=False),
        sa.Column('modelscope_revision', sa.String(50), server_default='master', nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('current_file', sa.String(512), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('downloaded_files', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_files', sa.Integer(), nullable=True),
        sa.Column('downloaded_bytes', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('total_bytes', sa.BigInteger(), nullable=True),
        sa.Column('download_speed_mbps', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        'ix_download_tasks_status',
        'model_download_tasks',
        ['status']
    )
    op.create_index(
        'ix_download_tasks_model',
        'model_download_tasks',
        ['model_id']
    )
    op.create_index(
        'ix_download_tasks_created_at',
        'model_download_tasks',
        [sa.text('created_at DESC')]
    )

    # ===========================================================================
    # Step 3: Create worker_model_cache table
    # ===========================================================================
    op.create_table(
        'worker_model_cache',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('worker_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.BigInteger(), nullable=False),
        sa.Column('is_cached', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('cache_path', sa.String(1024), nullable=True),
        sa.Column('cache_size_gb', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('last_loaded_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('load_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('sync_status', sa.String(50), server_default='synced', nullable=False),
        sa.Column('last_synced_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['worker_id'], ['workers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('worker_id', 'model_id', name='ix_worker_cache_worker_model')
    )

    op.create_index(
        'ix_worker_cache_worker',
        'worker_model_cache',
        ['worker_id']
    )
    op.create_index(
        'ix_worker_cache_model',
        'worker_model_cache',
        ['model_id']
    )
    op.create_index(
        'ix_worker_cache_cached',
        'worker_model_cache',
        ['is_cached']
    )

    # ===========================================================================
    # Step 4: Create ENUM types
    # ===========================================================================
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE modeldownloadtaskstatus AS ENUM (
                'pending',
                'downloading',
                'completed',
                'failed',
                'cancelled'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE workercachesyncstatus AS ENUM (
                'synced',
                'syncing',
                'outdated'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # ===========================================================================
    # Step 5: Update existing columns to use ENUM
    # ===========================================================================
    op.execute("""
        ALTER TABLE model_download_tasks
        ALTER COLUMN status TYPE modeldownloadtaskstatus
        USING status::modeldownloadtaskstatus
    """)

    op.execute("""
        ALTER TABLE worker_model_cache
        ALTER COLUMN sync_status TYPE workercachesyncstatus
        USING sync_status::workercachesyncstatus
    """)


def downgrade():
    """Rollback model download and distribution tables."""

    # Drop ENUM types first
    op.execute("""
        ALTER TABLE worker_model_cache
        ALTER COLUMN sync_status TYPE VARCHAR(50)
        USING sync_status::text
    """)

    op.execute("""
        ALTER TABLE model_download_tasks
        ALTER COLUMN status TYPE VARCHAR(50)
        USING status::text
    """)

    op.execute('DROP TYPE IF EXISTS workercachesyncstatus')
    op.execute('DROP TYPE IF EXISTS modeldownloadtaskstatus')

    # Drop tables
    op.drop_table('worker_model_cache')
    op.drop_table('model_download_tasks')

    # Drop columns from models table
    op.drop_index('ix_model_download_task_id', 'models')
    op.drop_constraint('fk_models_download_task', 'models')
    op.drop_column('models', 'download_task_id')

    op.drop_column('models', 'storage_type')
    op.drop_index('ix_model_storage_path', 'models')
    op.drop_column('models', 'storage_path')
    op.drop_column('models', 'modelscope_revision')
    op.drop_index('ix_model_modelscope_repo', 'models')
    op.drop_column('models', 'modelscope_repo_id')
