"""add server-worker architecture

Revision ID: 001_add_server_worker_architecture
Revises:
Create Date: 2025-01-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_server_worker_architecture'
down_revision = '000_create_base_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create clusters table
    op.create_table(
        'clusters',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.Enum('DOCKER', 'KUBERNETES', 'STANDALONE', name='clustertype'), nullable=False),
        sa.Column('config', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_clusters_name', 'clusters', ['name'], unique=True)

    # Create workers table (Server-Worker architecture)
    op.create_table(
        'workers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('cluster_id', sa.BigInteger(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=False),
        sa.Column('ifname', sa.String(length=50), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('NEW', 'REGISTERING', 'READY', 'ALLOCATING', 'BUSY', 'RELEASING', 'UNHEALTHY', 'DRAINING', 'TERMINATED', name='workerstatus'), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=True),
        sa.Column('gpu_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_heartbeat_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cluster_id'], ['clusters.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workers_cluster_id', 'workers', ['cluster_id'], unique=False)
    op.create_index('ix_workers_name', 'workers', ['name'], unique=False)
    op.create_index('ix_workers_status', 'workers', ['status'], unique=False)
    op.create_index('ix_workers_token_hash', 'workers', ['token_hash'], unique=True)
    op.create_index('ix_worker_cluster_name', 'workers', ['cluster_id', 'name'], unique=True)

    # Create model_instances table
    op.create_table(
        'model_instances',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.BigInteger(), nullable=False),
        sa.Column('worker_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('STARTING', 'RUNNING', 'STOPPING', 'STOPPED', 'ERROR', name='modelinstancestatus'), nullable=False),
        sa.Column('backend', sa.String(length=50), nullable=False, server_default='vllm'),
        sa.Column('config', postgresql.JSON(), nullable=True),
        sa.Column('gpu_ids', postgresql.JSON(), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('health_status', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['worker_id'], ['workers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_instances_model_id', 'model_instances', ['model_id'], unique=False)
    op.create_index('ix_model_instances_worker_id', 'model_instances', ['worker_id'], unique=False)
    op.create_index('ix_model_instances_status', 'model_instances', ['status'], unique=False)
    op.create_index('ix_model_instances_name', 'model_instances', ['name'], unique=True)


def downgrade():
    # Drop model_instances table
    op.drop_index('ix_model_instances_name', table_name='model_instances')
    op.drop_index('ix_model_instances_status', table_name='model_instances')
    op.drop_index('ix_model_instances_worker_id', table_name='model_instances')
    op.drop_index('ix_model_instances_model_id', table_name='model_instances')
    op.drop_table('model_instances')

    # Drop workers table
    op.drop_index('ix_worker_cluster_name', table_name='workers')
    op.drop_index('ix_workers_token_hash', table_name='workers')
    op.drop_index('ix_workers_status', table_name='workers')
    op.drop_index('ix_workers_name', table_name='workers')
    op.drop_index('ix_workers_cluster_id', table_name='workers')
    op.drop_table('workers')

    # Drop clusters table
    op.drop_index('ix_clusters_name', table_name='clusters')
    op.drop_table('clusters')
