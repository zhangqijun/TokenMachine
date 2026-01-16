"""create base tables

Revision ID: 000_create_base_tables
Revises:
Create Date: 2026-01-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000_create_base_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create models table (enums will be created automatically by SQLAlchemy)
    op.create_table(
        'models',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('source', postgresql.ENUM('huggingface', 'modelscope', 'local', name='modelsource', create_type=True), nullable=False),
        sa.Column('category', postgresql.ENUM('llm', 'embedding', 'reranker', 'image', 'tts', 'stt', name='modelcategory', create_type=True), nullable=False),
        sa.Column('path', sa.String(length=1024)),
        sa.Column('size_gb', sa.DECIMAL(precision=10, scale=2)),
        sa.Column('status', postgresql.ENUM('downloading', 'ready', 'error', name='modelstatus', create_type=True), nullable=False),
        sa.Column('download_progress', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_models_name', 'models', ['name'])
    op.create_index('ix_models_category', 'models', ['category'])
    op.create_index('ix_models_status', 'models', ['status'])
    op.create_index('ix_model_name_version', 'models', ['name', 'version'], unique=True)

    # Create deployments table
    op.create_table(
        'deployments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', postgresql.ENUM('starting', 'running', 'stopping', 'stopped', 'error', name='deploymentstatus', create_type=True), nullable=False),
        sa.Column('replicas', sa.Integer(), nullable=False),
        sa.Column('gpu_ids', postgresql.JSON()),
        sa.Column('backend', sa.String(length=50), nullable=False),
        sa.Column('config', postgresql.JSON()),
        sa.Column('health_status', postgresql.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_deployments_name', 'deployments', ['name'], unique=True)
    op.create_index('ix_deployments_status', 'deployments', ['status'])
    op.create_index('ix_deployments_model_id', 'deployments', ['model_id'])

    # Create gpus table
    op.create_table(
        'gpus',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gpu_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('memory_total_mb', sa.BigInteger()),
        sa.Column('memory_free_mb', sa.BigInteger()),
        sa.Column('utilization_percent', sa.DECIMAL(precision=5, scale=2)),
        sa.Column('temperature_celsius', sa.DECIMAL(precision=5, scale=2)),
        sa.Column('status', postgresql.ENUM('available', 'in_use', 'error', name='gpustatus', create_type=True), nullable=False),
        sa.Column('deployment_id', sa.BigInteger()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_gpus_gpu_id', 'gpus', ['gpu_id'], unique=True)
    op.create_index('ix_gpus_status', 'gpus', ['status'])
    op.create_index('ix_gpus_deployment_id', 'gpus', ['deployment_id'])

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=10), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('quota_tokens', sa.BigInteger(), nullable=False),
        sa.Column('tokens_used', sa.BigInteger(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP()),
        sa.Column('last_used_at', sa.TIMESTAMP()),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'])

    # Create usage_logs table
    op.create_table(
        'usage_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.BigInteger(), nullable=False),
        sa.Column('deployment_id', sa.BigInteger(), nullable=False),
        sa.Column('model_id', sa.BigInteger(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('latency_ms', sa.Integer()),
        sa.Column('status', postgresql.ENUM('success', 'error', name='usagelogstatus', create_type=True), nullable=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_usage_logs_status', 'usage_logs', ['status'])
    op.create_index('ix_usage_logs_created_at', 'usage_logs', ['created_at'])
    op.create_index('ix_usage_logs_api_key_id', 'usage_logs', ['api_key_id'])
    op.create_index('ix_usage_logs_deployment_id', 'usage_logs', ['deployment_id'])


def downgrade():
    op.drop_table('usage_logs')
    postgresql.ENUM(name='usagelogstatus').drop(op.get_bind())

    op.drop_table('api_keys')

    op.drop_table('gpus')
    postgresql.ENUM(name='gpustatus').drop(op.get_bind())

    op.drop_table('deployments')
    postgresql.ENUM(name='deploymentstatus').drop(op.get_bind())

    op.drop_table('models')
    postgresql.ENUM(name='modelstatus').drop(op.get_bind())
    postgresql.ENUM(name='modelsource').drop(op.get_bind())
    postgresql.ENUM(name='modelcategory').drop(op.get_bind())

    op.drop_table('users')
