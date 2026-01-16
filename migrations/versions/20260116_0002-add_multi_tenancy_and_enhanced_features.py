"""add multi-tenancy and enhanced features

Revision ID: 002_add_multi_tenancy_and_enhanced_features
Revises: 001_add_server_worker_architecture
Create Date: 2026-01-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_multi_tenancy_and_enhanced_features'
down_revision = '001_add_server_worker_architecture'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================================
    # Create new ENUM types
    # ============================================================================

    # Organization enums
    postgresql.ENUM(name='organizationplan', create_type=True).create(op.get_bind())
    postgresql.ENUM(name='userrole', create_type=True).create(op.get_bind())

    # Cluster/Worker enums
    postgresql.ENUM(name='clusterstatus', create_type=True).create(op.get_bind())
    postgresql.ENUM(name='workerpoolstatus', create_type=True).create(op.get_bind())
    postgresql.ENUM(name='gpuvendor', create_type=True).create(op.get_bind())
    postgresql.ENUM(name='gpudevicestate', create_type=True).create(op.get_bind())

    # Model enums
    postgresql.ENUM(name='modelquantization', create_type=True).create(op.get_bind())
    postgresql.ENUM(name='deploymentenvironment', create_type=True).create(op.get_bind())

    # Billing enums
    postgresql.ENUM(name='invoicestatus', create_type=True).create(op.get_bind())

    # Audit enums
    postgresql.ENUM(name='auditauditaction', create_type=True).create(op.get_bind())
    postgresql.ENUM(name='auditstatus', create_type=True).create(op.get_bind())
    postgresql.ENUM(name='auditresourcetype', create_type=True).create(op.get_bind())

    # ============================================================================
    # Create organizations table
    # ============================================================================
    op.create_table(
        'organizations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('plan', postgresql.ENUM(name='organizationplan'), nullable=False),
        sa.Column('quota_tokens', sa.BigInteger(), nullable=False),
        sa.Column('quota_models', sa.Integer(), nullable=False),
        sa.Column('quota_gpus', sa.Integer(), nullable=False),
        sa.Column('max_workers', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'], unique=True)

    # ============================================================================
    # Alter users table to add organization_id and role
    # ============================================================================
    # Drop existing unique indexes
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')

    # Add new columns
    op.add_column('users', sa.Column('organization_id', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('role', postgresql.ENUM(name='userrole'), nullable=False, server_default='user'))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Drop is_admin column (replaced by role)
    op.drop_column('users', 'is_admin')

    # Create foreign key
    op.create_foreign_key(
        'fk_users_organization', 'users', 'organizations',
        ['organization_id'], ['id'], ondelete='CASCADE'
    )

    # Create composite unique indexes
    op.create_index('ix_user_org_username', 'users', ['organization_id', 'username'], unique=True)
    op.create_index('ix_user_org_email', 'users', ['organization_id', 'email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])

    # ============================================================================
    # Alter api_keys table to add organization_id
    # ============================================================================
    op.add_column('api_keys', sa.Column('organization_id', sa.BigInteger(), nullable=False))

    # Create foreign key
    op.create_foreign_key(
        'fk_api_keys_organization', 'api_keys', 'organizations',
        ['organization_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index('ix_api_keys_org', 'api_keys', ['organization_id'])

    # ============================================================================
    # Alter models table to add quantization
    # ============================================================================
    # Drop old unique index
    op.drop_index('ix_model_name_version', table_name='models')

    # Add quantization column
    op.add_column('models', sa.Column('quantization', postgresql.ENUM(name='modelquantization'), nullable=False, server_default='fp16'))

    # Create new composite unique index
    op.create_index('ix_model_name_version_quant', 'models', ['name', 'version', 'quantization'], unique=True)

    # ============================================================================
    # Alter deployments table to add environment and traffic_weight
    # ============================================================================
    op.add_column('deployments', sa.Column('environment', postgresql.ENUM(name='deploymentenvironment'), nullable=False, server_default='production'))
    op.add_column('deployments', sa.Column('traffic_weight', sa.Integer(), nullable=False, server_default='100'))
    op.create_index('ix_deployments_env', 'deployments', ['environment'])

    # ============================================================================
    # Alter clusters table
    # ============================================================================
    # Drop old table if it exists (for full rebuild)
    # We'll need to add columns: is_default, status, type update

    # Add new columns to clusters
    try:
        op.add_column('clusters', sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'))
        op.add_column('clusters', sa.Column('status', postgresql.ENUM(name='clusterstatus'), nullable=False, server_default='running'))
    except:
        pass  # Column may already exist

    op.create_index('ix_clusters_status', 'clusters', ['status'])

    # ============================================================================
    # Create worker_pools table
    # ============================================================================
    op.create_table(
        'worker_pools',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cluster_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('min_workers', sa.Integer(), nullable=False),
        sa.Column('max_workers', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM(name='workerpoolstatus'), nullable=False),
        sa.Column('config', postgresql.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['cluster_id'], ['clusters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_worker_pools_cluster', 'worker_pools', ['cluster_id'])

    # ============================================================================
    # Alter workers table
    # ============================================================================
    # Add new columns to workers
    try:
        op.add_column('workers', sa.Column('pool_id', sa.Integer(), nullable=True))
        op.add_column('workers', sa.Column('port', sa.Integer(), nullable=False, server_default='8080'))
        op.add_column('workers', sa.Column('labels', postgresql.JSON()))
        op.add_column('workers', sa.Column('status_json', postgresql.JSON(), nullable=True))
        op.add_column('workers', sa.Column('last_status_update_at', sa.TIMESTAMP(), nullable=True))
        # Update ip to nullable and cluster_id to not nullable
        op.alter_column('workers', 'ip', nullable=True)
        op.alter_column('workers', 'cluster_id', nullable=False)
    except:
        pass  # Columns may already exist

    # Create foreign key for pool_id
    try:
        op.create_foreign_key(
            'fk_workers_pool', 'workers', 'worker_pools',
            ['pool_id'], ['id'], ondelete='SET NULL'
        )
        op.create_index('ix_workers_pool', 'workers', ['pool_id'])
    except:
        pass

    # Update cluster_id foreign key to CASCADE
    try:
        op.drop_constraint('fk_workers_cluster_id', 'workers', type_='foreignkey')
        op.create_foreign_key(
            'fk_workers_cluster', 'workers', 'clusters',
            ['cluster_id'], ['id'], ondelete='CASCADE'
        )
    except:
        pass

    # ============================================================================
    # Create gpu_devices table (detailed GPU tracking)
    # ============================================================================
    op.create_table(
        'gpu_devices',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('worker_id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('vendor', postgresql.ENUM(name='gpuvendor')),
        sa.Column('index', sa.Integer(), nullable=False),
        sa.Column('core_total', sa.Integer()),
        sa.Column('core_utilization_rate', sa.DECIMAL(precision=5, scale=2)),
        sa.Column('memory_total', sa.BigInteger()),
        sa.Column('memory_used', sa.BigInteger()),
        sa.Column('memory_allocated', sa.BigInteger()),
        sa.Column('memory_utilization_rate', sa.DECIMAL(precision=5, scale=2)),
        sa.Column('temperature', sa.DECIMAL(precision=5, scale=2)),
        sa.Column('state', postgresql.ENUM(name='gpudevicestate'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['worker_id'], ['workers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_gpu_device_worker_uuid', 'gpu_devices', ['worker_id', 'uuid'], unique=True)
    op.create_index('ix_gpu_devices_worker', 'gpu_devices', ['worker_id'])
    op.create_index('ix_gpu_devices_state', 'gpu_devices', ['state'])

    # ============================================================================
    # Alter model_instances table to add deployment_id and endpoint
    # ============================================================================
    try:
        op.add_column('model_instances', sa.Column('deployment_id', sa.BigInteger(), nullable=False))
        op.add_column('model_instances', sa.Column('endpoint', sa.String(length=255), nullable=True))
    except:
        pass

    # Create foreign key for deployment_id
    try:
        op.create_foreign_key(
            'fk_model_instances_deployment', 'model_instances', 'deployments',
            ['deployment_id'], ['id'], ondelete='CASCADE'
        )
        op.create_index('ix_model_instances_deployment', 'model_instances', ['deployment_id'])
    except:
        pass

    # Update worker_id foreign key to CASCADE
    try:
        op.drop_constraint('fk_model_instances_worker_id', 'model_instances', type_='foreignkey')
        op.create_foreign_key(
            'fk_model_instances_worker', 'model_instances', 'workers',
            ['worker_id'], ['id'], ondelete='CASCADE'
        )
    except:
        pass

    # ============================================================================
    # Create invoices table
    # ============================================================================
    op.create_table(
        'invoices',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', postgresql.ENUM(name='invoicestatus'), nullable=False),
        sa.Column('period_start', sa.TIMESTAMP(), nullable=False),
        sa.Column('period_end', sa.TIMESTAMP(), nullable=False),
        sa.Column('tokens_used', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoices_org', 'invoices', ['organization_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])

    # ============================================================================
    # Create audit_logs table
    # ============================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('organization_id', sa.BigInteger(), nullable=True),
        sa.Column('action', postgresql.ENUM(name='auditauditaction'), nullable=False),
        sa.Column('resource_type', postgresql.ENUM(name='auditresourcetype')),
        sa.Column('resource_id', sa.BigInteger()),
        sa.Column('resource_name', sa.String(length=255)),
        sa.Column('ip_address', sa.String(length=45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('status', postgresql.ENUM(name='auditstatus'), nullable=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_user', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_org', 'audit_logs', ['organization_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_created', 'audit_logs', ['created_at'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    postgresql.ENUM(name='auditstatus').drop(op.get_bind())
    postgresql.ENUM(name='auditresourcetype').drop(op.get_bind())
    postgresql.ENUM(name='auditauditaction').drop(op.get_bind())

    op.drop_table('invoices')
    postgresql.ENUM(name='invoicestatus').drop(op.get_bind())

    op.drop_table('gpu_devices')
    postgresql.ENUM(name='gpudevicestate').drop(op.get_bind())
    postgresql.ENUM(name='gpuvendor').drop(op.get_bind())

    # Revert model_instances changes
    try:
        op.drop_constraint('fk_model_instances_worker', 'model_instances', type_='foreignkey')
        op.create_foreign_key(
            'fk_model_instances_worker_id', 'model_instances', 'workers',
            ['worker_id'], ['id'], ondelete='CASCADE'
        )
        op.drop_index('ix_model_instances_deployment', table_name='model_instances')
        op.drop_constraint('fk_model_instances_deployment', 'model_instances', type_='foreignkey')
        op.drop_column('model_instances', 'deployment_id')
        op.drop_column('model_instances', 'endpoint')
    except:
        pass

    # Revert workers changes
    try:
        op.drop_index('ix_workers_pool', table_name='workers')
        op.drop_constraint('fk_workers_pool', 'workers', type_='foreignkey')
        op.drop_column('workers', 'pool_id')
        op.drop_column('workers', 'port')
        op.drop_column('workers', 'labels')
        op.drop_column('workers', 'status_json')
        op.drop_column('workers', 'last_status_update_at')
        op.alter_column('workers', 'ip', nullable=False)
        op.alter_column('workers', 'cluster_id', nullable=True)
    except:
        pass

    op.drop_table('worker_pools')
    postgresql.ENUM(name='workerpoolstatus').drop(op.get_bind())

    # Revert clusters changes
    try:
        op.drop_index('ix_clusters_status', table_name='clusters')
        op.drop_column('clusters', 'status')
        op.drop_column('clusters', 'is_default')
    except:
        pass
    postgresql.ENUM(name='clusterstatus').drop(op.get_bind())

    # Revert deployments changes
    op.drop_index('ix_deployments_env', table_name='deployments')
    op.drop_column('deployments', 'traffic_weight')
    op.drop_column('deployments', 'environment')
    postgresql.ENUM(name='deploymentenvironment').drop(op.get_bind())

    # Revert models changes
    op.drop_index('ix_model_name_version_quant', table_name='models')
    op.drop_column('models', 'quantization')
    op.create_index('ix_model_name_version', 'models', ['name', 'version'], unique=True)
    postgresql.ENUM(name='modelquantization').drop(op.get_bind())

    # Revert api_keys changes
    op.drop_index('ix_api_keys_org', table_name='api_keys')
    op.drop_constraint('fk_api_keys_organization', 'api_keys', type_='foreignkey')
    op.drop_column('api_keys', 'organization_id')

    # Revert users changes
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_user_org_email', table_name='users')
    op.drop_index('ix_user_org_username', table_name='users')
    op.drop_constraint('fk_users_organization', 'users', type_='foreignkey')
    op.drop_column('users', 'is_active')
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False))
    op.drop_column('users', 'role')
    op.drop_column('users', 'organization_id')
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    postgresql.ENUM(name='userrole').drop(op.get_bind())

    op.drop_table('organizations')
    postgresql.ENUM(name='organizationplan').drop(op.get_bind())
