"""add gateway management

Revision ID: 005_add_gateway_management
Revises: 004_add_backend_engines_table
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_gateway_management'
down_revision = '004_add_backend_engines_table'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================================
    # Create Gateway ENUM types
    # ============================================================================

    # Routing mode enum
    postgresql.ENUM(name='routingmode', create_type=True).create(op.get_bind())

    # Instance health status enum
    postgresql.ENUM(name='instancehealthstatus', create_type=True).create(op.get_bind())

    # Failover event type enum
    postgresql.ENUM(name='failovereventtype', create_type=True).create(op.get_bind())

    # ============================================================================
    # Create routing_strategies table
    # ============================================================================
    op.create_table(
        'routing_strategies',
        sa.Column('id', postgresql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('mode', postgresql.ENUM(name='routingmode'), nullable=False),
        sa.Column('rules', postgresql.JSON(), nullable=False, server_default='[]'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('enable_aggregation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('unified_endpoint', sa.String(), nullable=True),
        sa.Column('response_mode', sa.String(), nullable=True),
        sa.Column('bound_keys_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('today_requests', postgresql.BIGINT(), nullable=False, server_default='0'),
        sa.Column('p95_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='routing_strategies_pkey'),
        sa.UniqueConstraint('name', name='routing_strategies_name_key'),
        keep_existing=True
    )
    op.create_index('ix_routing_strategies_is_enabled', 'routing_strategies', ['is_enabled'])
    op.create_index('ix_routing_strategies_mode', 'routing_strategies', ['mode'])

    # ============================================================================
    # Create api_key_route_bindings table
    # ============================================================================
    op.create_table(
        'api_key_route_bindings',
        sa.Column('id', postgresql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', postgresql.BIGINT(), nullable=False),
        sa.Column('routing_strategy_id', postgresql.BIGINT(), nullable=False),
        sa.Column('traffic_weight', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], name='api_key_route_bindings_api_key_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['routing_strategy_id'], ['routing_strategies.id'], name='api_key_route_bindings_routing_strategy_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='api_key_route_bindings_pkey'),
        sa.UniqueConstraint('api_key_id', 'routing_strategy_id', name='api_key_route_bindings_api_key_id_routing_strategy_id_key'),
        keep_existing=True
    )
    op.create_index('ix_api_key_route_bindings_api_key_id', 'api_key_route_bindings', ['api_key_id'])
    op.create_index('ix_api_key_route_bindings_routing_strategy_id', 'api_key_route_bindings', ['routing_strategy_id'])

    # ============================================================================
    # Create gateway_configs table
    # ============================================================================
    op.create_table(
        'gateway_configs',
        sa.Column('id', postgresql.BIGINT(), autoincrement=True, nullable=False),
        # Load balancing config
        sa.Column('enable_dynamic_lb', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('schedule_strategy', sa.String(), nullable=False, server_default='queue'),
        sa.Column('queue_threshold', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('response_threshold', sa.Integer(), nullable=False, server_default='5000'),
        sa.Column('gpu_threshold', sa.Integer(), nullable=False, server_default='95'),
        # Health check config
        sa.Column('enable_failover', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('check_method', sa.String(), nullable=False, server_default='active'),
        sa.Column('check_interval', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('timeout', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('fail_threshold', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('response_time_threshold', sa.Integer(), nullable=False, server_default='5000'),
        sa.Column('error_rate_threshold', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('queue_depth_threshold', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('auto_recover', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('recover_threshold', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='gateway_configs_pkey'),
        keep_existing=True
    )

    # Insert default config
    op.execute("""
        INSERT INTO gateway_configs (
            enable_dynamic_lb, schedule_strategy, queue_threshold, response_threshold, gpu_threshold,
            enable_failover, check_method, check_interval, timeout, fail_threshold,
            response_time_threshold, error_rate_threshold, queue_depth_threshold,
            auto_recover, recover_threshold
        ) VALUES (
            true, 'queue', 50, 5000, 95,
            true, 'active', 10, 5, 3,
            5000, 10, 100,
            true, 3
        )
    """)

    # ============================================================================
    # Create instance_health table
    # ============================================================================
    op.create_table(
        'instance_health',
        sa.Column('id', postgresql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('model_instance_id', postgresql.BIGINT(), nullable=False),
        sa.Column('status', postgresql.ENUM(name='instancehealthstatus'), nullable=False),
        sa.Column('last_check_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('fail_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('consecutive_success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('queue_depth', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('response_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('gpu_utilization', postgresql.DECIMAL(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('error_rate', postgresql.DECIMAL(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['model_instance_id'], ['model_instances.id'], name='instance_health_model_instance_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='instance_health_pkey'),
        sa.UniqueConstraint('model_instance_id', name='instance_health_model_instance_id_key'),
        keep_existing=True
    )
    op.create_index('ix_instance_health_model_instance_id', 'instance_health', ['model_instance_id'])
    op.create_index('ix_instance_health_status', 'instance_health', ['status'])

    # ============================================================================
    # Create failover_events table
    # ============================================================================
    op.create_table(
        'failover_events',
        sa.Column('id', postgresql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('source_instance_id', postgresql.BIGINT(), nullable=True),
        sa.Column('target_instance_id', postgresql.BIGINT(), nullable=True),
        sa.Column('event_type', postgresql.ENUM(name='failovereventtype'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('triggered_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_instance_id'], ['model_instances.id'], name='failover_events_source_instance_id_fkey', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_instance_id'], ['model_instances.id'], name='failover_events_target_instance_id_fkey', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='failover_events_pkey'),
        keep_existing=True
    )
    op.create_index('ix_failover_events_created_at', 'failover_events', ['created_at'])
    op.create_index('ix_failover_events_event_type', 'failover_events', ['event_type'])


def downgrade():
    # Drop tables
    op.drop_table('failover_events')
    op.drop_table('instance_health')
    op.drop_table('gateway_configs')
    op.drop_table('api_key_route_bindings')
    op.drop_table('routing_strategies')

    # Drop ENUM types
    postgresql.ENUM(name='failovereventtype', create_type=False).drop(op.get_bind())
    postgresql.ENUM(name='instancehealthstatus', create_type=False).drop(op.get_bind())
    postgresql.ENUM(name='routingmode', create_type=False).drop(op.get_bind())
