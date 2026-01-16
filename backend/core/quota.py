"""
Quota manager for multi-tenant resource management.
"""
from typing import Tuple, Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from datetime import datetime, timedelta
from decimal import Decimal

from models.database import (
    Organization, APIKey, User, Deployment, Worker,
    OrganizationPlan, UserRole
)
from fastapi import HTTPException


class QuotaManager:
    """Manager for enforcing multi-tenant quotas."""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # API Key Quota Checks
    # ========================================================================

    def check_api_key_quota(
        self,
        api_key_id: int,
        tokens_needed: int = 0
    ) -> Tuple[bool, str]:
        """
        Check if an API key can fulfill a request.

        Args:
            api_key_id: API Key ID
            tokens_needed: Number of tokens required (for pre-check)

        Returns:
            Tuple of (allowed: bool, message: str)
        """
        api_key = self.db.query(APIKey).filter(
            APIKey.id == api_key_id
        ).first()

        if not api_key:
            return False, "API key not found"

        if not api_key.is_active:
            return False, "API key is inactive"

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return False, "API key has expired"

        # Check token quota (if tokens needed)
        if tokens_needed > 0:
            remaining = api_key.quota_tokens - api_key.tokens_used
            if remaining < tokens_needed:
                return False, f"Insufficient quota: {remaining} tokens remaining, {tokens_needed} required"

        # Check organization quota
        org = self.db.query(Organization).filter(
            Organization.id == api_key.organization_id
        ).first()

        if not org:
            return False, "Organization not found"

        # Calculate organization total usage
        total_used = self.db.query(
            func.sum(APIKey.tokens_used)
        ).filter(
            APIKey.organization_id == org.id
        ).scalar() or 0

        org_remaining = org.quota_tokens - total_used
        if org_remaining < tokens_needed:
            return False, f"Organization quota exceeded: {org_remaining} tokens remaining"

        return True, "OK"

    def check_api_key_rate_limit(
        self,
        api_key_id: int,
        window_seconds: int = 60,
        max_requests: int = 60
    ) -> Tuple[bool, str]:
        """
        Check API key rate limit.

        Args:
            api_key_id: API Key ID
            window_seconds: Time window in seconds
            max_requests: Maximum requests per window

        Returns:
            Tuple of (allowed: bool, message: str)
        """
        from models.database import UsageLog

        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)

        request_count = self.db.query(UsageLog).filter(
            and_(
                UsageLog.api_key_id == api_key_id,
                UsageLog.created_at >= cutoff
            )
        ).count()

        if request_count >= max_requests:
            return False, f"Rate limit exceeded: {request_count} requests in last {window_seconds}s"

        return True, "OK"

    # ========================================================================
    # Organization Quota Checks
    # ========================================================================

    def check_organization_quota(
        self,
        organization_id: int,
        resource_type: str,
        additional_count: int = 1
    ) -> Tuple[bool, str]:
        """
        Check if organization can add more resources.

        Args:
            organization_id: Organization ID
            resource_type: Type of resource (models, gpus, workers, deployments)
            additional_count: Number of additional resources

        Returns:
            Tuple of (allowed: bool, message: str)
        """
        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()

        if not org:
            return False, "Organization not found"

        if resource_type == "models":
            current = self.db.query(Deployment).filter(
                Deployment.model_id.in_(
                    self.db.query(Deployment.model_id).filter(
                        # Count unique models deployed by this org
                    ).distinct()
                )
            ).count()
            # Simplified - just count deployments
            current = self.db.query(func.count(func.distinct(Deployment.model_id))).join(
                APIKey, Deployment.id == APIKey.id
            ).filter(
                APIKey.organization_id == organization_id
            ).scalar() or 0

            quota = org.quota_models
            if current + additional_count > quota:
                return False, f"Model quota exceeded: {current}/{quota} models deployed"

        elif resource_type == "workers":
            current = self.db.query(Worker).join(
                Cluster, Worker.cluster_id == Cluster.id
            ).filter(
                Cluster.id == organization_id  # Assuming org owns clusters
            ).count()

            quota = org.max_workers
            if current + additional_count > quota:
                return False, f"Worker quota exceeded: {current}/{quota} workers used"

        elif resource_type == "gpus":
            current = self.db.query(func.sum(Worker.gpu_count)).join(
                Cluster, Worker.cluster_id == Cluster.id
            ).filter(
                Cluster.id == organization_id
            ).scalar() or 0

            quota = org.quota_gpus
            if current + additional_count > quota:
                return False, f"GPU quota exceeded: {current}/{quota} GPUs used"

        return True, "OK"

    # ========================================================================
    # Quota Information
    # ========================================================================

    def get_quota_info(self, organization_id: int) -> Dict[str, Any]:
        """
        Get comprehensive quota information for an organization.

        Args:
            organization_id: Organization ID

        Returns:
            Dictionary with quota information
        """
        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Calculate total usage across all API keys
        total_used = self.db.query(
            func.sum(APIKey.tokens_used)
        ).filter(
            APIKey.organization_id == organization_id
        ).scalar() or 0

        # Count active API keys
        active_keys = self.db.query(func.count(APIKey.id)).filter(
            and_(
                APIKey.organization_id == organization_id,
                APIKey.is_active == True
            )
        ).scalar() or 0

        # Count deployments (simplified)
        deployments_count = self.db.query(func.count(func.distinct(Deployment.model_id))).join(
            UsageLog, Deployment.id == UsageLog.deployment_id
        ).join(
            APIKey, UsageLog.api_key_id == APIKey.id
        ).filter(
            APIKey.organization_id == organization_id
        ).scalar() or 0

        # Count users
        users_count = self.db.query(func.count(User.id)).filter(
            User.organization_id == organization_id
        ).scalar() or 0

        # Calculate usage percentage
        usage_percentage = 0
        if org.quota_tokens > 0:
            usage_percentage = min(100, int(total_used / org.quota_tokens * 100))

        # Get plan limits
        plan_limits = self._get_plan_limits(org.plan)

        return {
            "organization_id": organization_id,
            "name": org.name,
            "plan": org.plan.value if hasattr(org.plan, 'value') else str(org.plan),
            "quotas": {
                "tokens": {
                    "limit": org.quota_tokens,
                    "used": int(total_used),
                    "remaining": max(0, org.quota_tokens - int(total_used)),
                    "usage_percentage": usage_percentage
                },
                "models": {
                    "limit": org.quota_models,
                    "used": deployments_count,
                    "remaining": max(0, org.quota_models - deployments_count)
                },
                "gpus": {
                    "limit": org.quota_gpus,
                    "used": 0,  # Need to calculate actual usage
                    "remaining": org.quota_gpus
                },
                "workers": {
                    "limit": org.max_workers,
                    "used": 0,  # Need to calculate actual usage
                    "remaining": org.max_workers
                },
                "api_keys": {
                    "limit": plan_limits.get("max_api_keys", 10),
                    "used": active_keys,
                    "remaining": max(0, plan_limits.get("max_api_keys", 10) - active_keys)
                },
                "users": {
                    "limit": plan_limits.get("max_users", 5),
                    "used": users_count,
                    "remaining": max(0, plan_limits.get("max_users", 5) - users_count)
                }
            }
        }

    def get_api_key_quota_info(self, api_key_id: int) -> Dict[str, Any]:
        """
        Get quota information for a specific API key.

        Args:
            api_key_id: API Key ID

        Returns:
            Dictionary with quota information
        """
        api_key = self.db.query(APIKey).filter(
            APIKey.id == api_key_id
        ).first()

        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        remaining = api_key.quota_tokens - api_key.tokens_used
        usage_percentage = 0
        if api_key.quota_tokens > 0:
            usage_percentage = int(api_key.tokens_used / api_key.quota_tokens * 100)

        return {
            "api_key_id": api_key_id,
            "key_prefix": api_key.key_prefix,
            "name": api_key.name,
            "organization_id": api_key.organization_id,
            "tokens": {
                "quota": api_key.quota_tokens,
                "used": api_key.tokens_used,
                "remaining": max(0, remaining),
                "usage_percentage": usage_percentage
            },
            "is_active": api_key.is_active,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None
        }

    # ========================================================================
    # Plan Management
    # ========================================================================

    def _get_plan_limits(self, plan: OrganizationPlan) -> Dict[str, int]:
        """Get resource limits for a plan."""
        limits = {
            OrganizationPlan.FREE: {
                "max_api_keys": 2,
                "max_users": 2,
            },
            OrganizationPlan.PROFESSIONAL: {
                "max_api_keys": 10,
                "max_users": 10,
            },
            OrganizationPlan.ENTERPRISE: {
                "max_api_keys": -1,  # Unlimited
                "max_users": -1,  # Unlimited
            }
        }
        return limits.get(plan, {})

    def can_upgrade_plan(
        self,
        organization_id: int,
        new_plan: OrganizationPlan
    ) -> Tuple[bool, str]:
        """
        Check if organization can upgrade to a new plan.

        Args:
            organization_id: Organization ID
            new_plan: Target plan

        Returns:
            Tuple of (allowed: bool, message: str)
        """
        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()

        if not org:
            return False, "Organization not found"

        current_plan = org.plan
        plan_order = [OrganizationPlan.FREE, OrganizationPlan.PROFESSIONAL, OrganizationPlan.ENTERPRISE]

        try:
            current_index = plan_order.index(current_plan)
            new_index = plan_order.index(new_plan)

            if new_index < current_index:
                return False, f"Cannot downgrade from {current_plan.value} to {new_plan.value}"

            return True, "OK"
        except ValueError:
            return False, "Invalid plan"

    def upgrade_plan(
        self,
        organization_id: int,
        new_plan: OrganizationPlan,
        new_quotas: Optional[Dict[str, int]] = None
    ) -> bool:
        """
        Upgrade an organization to a new plan.

        Args:
            organization_id: Organization ID
            new_plan: Target plan
            new_quotas: Optional custom quota overrides

        Returns:
            True if upgraded successfully

        Raises:
            ValueError: If upgrade is not allowed
        """
        allowed, message = self.can_upgrade_plan(organization_id, new_plan)
        if not allowed:
            raise ValueError(message)

        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()

        # Default plan quotas
        plan_quotas = {
            OrganizationPlan.FREE: {
                "quota_tokens": 10000,
                "quota_models": 1,
                "quota_gpus": 1,
                "max_workers": 2
            },
            OrganizationPlan.PROFESSIONAL: {
                "quota_tokens": 1000000,
                "quota_models": 10,
                "quota_gpus": 8,
                "max_workers": 10
            },
            OrganizationPlan.ENTERPRISE: {
                "quota_tokens": 100000000,
                "quota_models": -1,  # Unlimited
                "quota_gpus": -1,  # Unlimited
                "max_workers": -1  # Unlimited
            }
        }

        quotas = plan_quotas.get(new_plan, {})
        if new_quotas:
            quotas.update(new_quotas)

        org.plan = new_plan
        for key, value in quotas.items():
            if value > 0:  # Only update if not unlimited
                setattr(org, key, value)

        self.db.commit()
        return True

    # ========================================================================
    # RBAC Authorization
    # ========================================================================

    def check_permission(
        self,
        user_id: int,
        resource_type: str,
        action: str,
        resource_id: Optional[int] = None
    ) -> bool:
        """
        Check if a user has permission to perform an action.

        Args:
            user_id: User ID
            resource_type: Type of resource (model, deployment, etc.)
            action: Action (create, read, update, delete)
            resource_id: Optional specific resource ID

        Returns:
            True if user has permission
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Admins have all permissions
        if user.role == UserRole.ADMIN:
            return True

        # Readonly users can only read
        if user.role == UserRole.READONLY:
            return action == "read"

        # Regular users can create and read
        if user.role == UserRole.USER:
            if action in ["create", "read"]:
                return True

            # For update/delete, check resource ownership
            if action in ["update", "delete"] and resource_id:
                return self._check_resource_ownership(user_id, resource_type, resource_id)

        return False

    def _check_resource_ownership(
        self,
        user_id: int,
        resource_type: str,
        resource_id: int
    ) -> bool:
        """Check if user owns a resource."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        org_id = user.organization_id

        if resource_type == "api_key":
            resource = self.db.query(APIKey).filter(
                and_(APIKey.id == resource_id, APIKey.user_id == user_id)
            ).first()
            return resource is not None

        # For other resources in the same organization
        return True
