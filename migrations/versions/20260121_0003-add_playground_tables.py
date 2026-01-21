"""add playground tables

Revision ID: 003_add_playground_tables
Revises: 002_add_multi_tenancy_and_enhanced_features
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_playground_tables'
down_revision = '002_add_multi_tenancy_and_enhanced_features'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================================
    # Create Playground ENUM types
    # ============================================================================

    # Benchmark enums
    postgresql.ENUM(name='tasktype', create_type=True).create(op.get_bind())
    postgresql.ENUM(name='taskstatus', create_type=True).create(op.get_bind())

    # ============================================================================
    # Create playground_sessions table
    # ============================================================================
    op.create_table(
        'playground_sessions',
        sa.Column('id', postgresql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.BIGINT(), nullable=False),
        sa.Column('deployment_id', postgresql.BIGINT(), autoincrement=False, nullable=True),
        sa.Column('session_name', sa.String(), server_default='Untitled Session', nullable=False),
        sa.Column('model_parameters', postgresql.JSON(), nullable=False),
        sa.Column('input_tokens', postgresql.BIGINT(), server_default='0', nullable=False),
        sa.Column('output_tokens', postgresql.BIGINT(), server_default='0', nullable=False),
        sa.Column('total_cost', postgresql.DECIMAL(precision=10, scale=6), server_default='0.0000', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], name='playground_sessions_deployment_id_fkey', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='playground_sessions_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='playground_sessions_pkey'),
        keep_existing=True
    )
    op.create_index('ix_playground_session_user_id', 'playground_sessions', ['user_id'])
    op.create_index('ix_playground_session_created_at', 'playground_sessions', ['created_at'])

    # ============================================================================
    # Create playground_messages table
    # ============================================================================
    op.create_table(
        'playground_messages',
        sa.Column('id', postgresql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('session_id', postgresql.BIGINT(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('output_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['playground_sessions.id'], name='playground_messages_session_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='playground_messages_pkey'),
        keep_existing=True
    )
    op.create_index('ix_playground_message_session_id', 'playground_messages', ['session_id'])
    op.create_index('ix_playground_message_timestamp', 'playground_messages', ['timestamp'])

    # ============================================================================
    # Create benchmark_tasks table
    # ============================================================================
    op.create_table(
        'benchmark_tasks',
        sa.Column('id', postgresql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.BIGINT(), nullable=False),
        sa.Column('deployment_id', postgresql.BIGINT(), autoincrement=False, nullable=True),
        sa.Column('task_name', sa.String(), nullable=False),
        sa.Column('task_type', postgresql.ENUM(name='tasktype'), nullable=False),
        sa.Column('status', postgresql.ENUM(name='taskstatus'), server_default='pending', nullable=False),
        sa.Column('config', postgresql.JSON(), nullable=False),
        sa.Column('result', postgresql.JSON(), nullable=True),
        sa.Column('output_dir', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('celery_task_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], name='benchmark_tasks_deployment_id_fkey', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='benchmark_tasks_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='benchmark_tasks_pkey'),
        keep_existing=True
    )
    op.create_index('ix_benchmark_task_user_id', 'benchmark_tasks', ['user_id'])
    op.create_index('ix_benchmark_task_status', 'benchmark_tasks', ['status'])
    op.create_index('ix_benchmark_task_created_at', 'benchmark_tasks', ['created_at'])
    op.create_index('ix_benchmark_task_celery_task_id', 'benchmark_tasks', ['celery_task_id'])

    # ============================================================================
    # Create benchmark_datasets table
    # ============================================================================
    op.create_table(
        'benchmark_datasets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dataset_size', sa.Integer(), nullable=True),
        sa.Column('meta_data', postgresql.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='benchmark_datasets_pkey'),
        sa.UniqueConstraint('name', name='benchmark_datasets_name_key'),
        keep_existing=True
    )
    op.create_index('ix_benchmark_dataset_category', 'benchmark_datasets', ['category'])
    op.create_index('ix_benchmark_dataset_name', 'benchmark_datasets', ['name'])


def downgrade():
    # Drop tables
    op.drop_table('benchmark_datasets')
    op.drop_table('benchmark_tasks')
    op.drop_table('playground_messages')
    op.drop_table('playground_sessions')

    # Drop ENUM types
    postgresql.ENUM(name='taskstatus', create_type=False).drop(op.get_bind())
    postgresql.ENUM(name='tasktype', create_type=False).drop(op.get_bind())
