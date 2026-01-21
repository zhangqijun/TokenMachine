"""
Routing strategy service for gateway request routing.
"""
import re
import random
from typing import Optional, List, Dict, Any
from loguru import logger
from sqlalchemy.orm import Session

from backend.models.database import (
    RoutingStrategy, RoutingMode, ApiKeyRouteBinding,
    ModelInstance, InstanceHealth, InstanceHealthStatus
)
from backend.models.schemas import RoutingRule


class RoutingService:
    """Service for routing strategy management and request routing."""

    def __init__(self, db: Session):
        """Initialize routing service."""
        self.db = db
        # Round-robin state for each strategy
        self._round_robin_index: Dict[int, int] = {}

    # ========================================================================
    # Routing Strategy CRUD
    # ========================================================================

    def create_strategy(
        self,
        name: str,
        description: Optional[str],
        mode: RoutingMode,
        rules: List[Dict[str, Any]],
        enable_aggregation: bool = False,
        unified_endpoint: Optional[str] = None,
        response_mode: str = "best"
    ) -> RoutingStrategy:
        """
        Create a new routing strategy.

        Args:
            name: Strategy name
            description: Strategy description
            mode: Routing mode
            rules: Routing rules
            enable_aggregation: Enable API aggregation
            unified_endpoint: Unified endpoint path
            response_mode: Response mode (best/all/custom)

        Returns:
            Created RoutingStrategy instance
        """
        # Check if strategy name already exists
        existing = self.db.query(RoutingStrategy).filter(
            RoutingStrategy.name == name
        ).first()
        if existing:
            raise ValueError(f"Routing strategy '{name}' already exists")

        # Validate rules based on mode
        self._validate_rules(mode, rules)

        strategy = RoutingStrategy(
            name=name,
            description=description,
            mode=mode,
            rules=rules,
            is_enabled=True,
            enable_aggregation=enable_aggregation,
            unified_endpoint=unified_endpoint,
            response_mode=response_mode
        )
        self.db.add(strategy)
        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Created routing strategy '{name}' with mode {mode}")
        return strategy

    def get_strategy(self, strategy_id: int) -> Optional[RoutingStrategy]:
        """Get a routing strategy by ID."""
        return self.db.query(RoutingStrategy).filter(
            RoutingStrategy.id == strategy_id
        ).first()

    def list_strategies(
        self,
        enabled_only: bool = False
    ) -> List[RoutingStrategy]:
        """List all routing strategies."""
        query = self.db.query(RoutingStrategy)
        if enabled_only:
            query = query.filter(RoutingStrategy.is_enabled == True)
        return query.order_by(RoutingStrategy.created_at.desc()).all()

    def update_strategy(
        self,
        strategy_id: int,
        **kwargs
    ) -> Optional[RoutingStrategy]:
        """Update a routing strategy."""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return None

        # Validate rules if provided
        if "rules" in kwargs and "mode" in kwargs:
            self._validate_rules(kwargs["mode"], kwargs["rules"])

        for key, value in kwargs.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Updated routing strategy '{strategy.name}'")
        return strategy

    def delete_strategy(self, strategy_id: int) -> bool:
        """Delete a routing strategy."""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return False

        # Check if strategy is bound to any API keys
        binding_count = self.db.query(ApiKeyRouteBinding).filter(
            ApiKeyRouteBinding.routing_strategy_id == strategy_id
        ).count()
        if binding_count > 0:
            raise ValueError(
                f"Cannot delete strategy with {binding_count} active API key bindings"
            )

        self.db.delete(strategy)
        self.db.commit()

        logger.info(f"Deleted routing strategy '{strategy.name}'")
        return True

    def toggle_strategy(self, strategy_id: int) -> Optional[RoutingStrategy]:
        """Toggle routing strategy enabled status."""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return None

        strategy.is_enabled = not strategy.is_enabled
        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Toggled routing strategy '{strategy.name}' to {strategy.is_enabled}")
        return strategy

    # ========================================================================
    # API Key Binding
    # ========================================================================

    def bind_api_key_strategy(
        self,
        api_key_id: int,
        routing_strategy_id: int,
        traffic_weight: int = 100
    ) -> ApiKeyRouteBinding:
        """
        Bind a routing strategy to an API key.

        Args:
            api_key_id: API key ID
            routing_strategy_id: Routing strategy ID
            traffic_weight: Traffic weight (0-100)

        Returns:
            Created ApiKeyRouteBinding instance
        """
        # Check if binding already exists
        existing = self.db.query(ApiKeyRouteBinding).filter(
            ApiKeyRouteBinding.api_key_id == api_key_id,
            ApiKeyRouteBinding.routing_strategy_id == routing_strategy_id
        ).first()
        if existing:
            # Update weight
            existing.traffic_weight = traffic_weight
            self.db.commit()
            self.db.refresh(existing)
            return existing

        binding = ApiKeyRouteBinding(
            api_key_id=api_key_id,
            routing_strategy_id=routing_strategy_id,
            traffic_weight=traffic_weight
        )
        self.db.add(binding)
        self.db.commit()
        self.db.refresh(binding)

        # Update bound keys count
        self._update_bound_keys_count(routing_strategy_id)

        logger.info(f"Bound API key {api_key_id} to strategy {routing_strategy_id}")
        return binding

    def unbind_api_key_strategy(
        self,
        api_key_id: int,
        routing_strategy_id: int
    ) -> bool:
        """Unbind a routing strategy from an API key."""
        binding = self.db.query(ApiKeyRouteBinding).filter(
            ApiKeyRouteBinding.api_key_id == api_key_id,
            ApiKeyRouteBinding.routing_strategy_id == routing_strategy_id
        ).first()
        if not binding:
            return False

        self.db.delete(binding)
        self.db.commit()

        # Update bound keys count
        self._update_bound_keys_count(routing_strategy_id)

        logger.info(f"Unbound API key {api_key_id} from strategy {routing_strategy_id}")
        return True

    def get_api_key_strategies(self, api_key_id: int) -> List[RoutingStrategy]:
        """Get all routing strategies bound to an API key."""
        bindings = self.db.query(ApiKeyRouteBinding).filter(
            ApiKeyRouteBinding.api_key_id == api_key_id
        ).all()

        strategy_ids = [b.routing_strategy_id for b in bindings]
        return self.db.query(RoutingStrategy).filter(
            RoutingStrategy.id.in_(strategy_ids),
            RoutingStrategy.is_enabled == True
        ).all()

    def _update_bound_keys_count(self, strategy_id: int):
        """Update the bound keys count for a strategy."""
        count = self.db.query(ApiKeyRouteBinding).filter(
            ApiKeyRouteBinding.routing_strategy_id == strategy_id
        ).count()
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.bound_keys_count = count
            self.db.commit()

    # ========================================================================
    # Request Routing
    # ========================================================================

    async def select_instance(
        self,
        api_key_id: int,
        model_name: str
    ) -> Optional[ModelInstance]:
        """
        Select the best model instance based on routing strategy.

        Args:
            api_key_id: API key ID
            model_name: Requested model name

        Returns:
            Selected ModelInstance or None
        """
        # Get routing strategies bound to this API key
        strategies = self.get_api_key_strategies(api_key_id)
        if not strategies:
            logger.warning(f"No routing strategies found for API key {api_key_id}")
            return None

        # Try each strategy in order
        for strategy in strategies:
            instance = await self._route_with_strategy(strategy, model_name)
            if instance:
                return instance

        logger.warning(f"No suitable instance found for model '{model_name}'")
        return None

    async def _route_with_strategy(
        self,
        strategy: RoutingStrategy,
        model_name: str
    ) -> Optional[ModelInstance]:
        """Route a request using a specific strategy."""
        # Get candidate instances based on rules
        candidates = await self._get_candidate_instances(strategy, model_name)
        if not candidates:
            return None

        # Apply routing mode
        if strategy.mode == RoutingMode.SEMANTIC:
            return await self._route_semantic(strategy, candidates)
        elif strategy.mode == RoutingMode.WEIGHT:
            return await self._route_weight(strategy, candidates)
        elif strategy.mode == RoutingMode.ROUND_ROBIN:
            return await self._route_round_robin(strategy, candidates)
        elif strategy.mode == RoutingMode.LEAST_CONN:
            return await self._route_least_conn(candidates)
        else:
            logger.error(f"Unknown routing mode: {strategy.mode}")
            return None

    async def _get_candidate_instances(
        self,
        strategy: RoutingStrategy,
        model_name: str
    ) -> List[ModelInstance]:
        """Get candidate instances based on routing rules."""
        candidates = []

        for rule in strategy.rules:
            rule_obj = RoutingRule(**rule)
            # Check if model name matches pattern
            if re.match(rule_obj.pattern, model_name):
                # Find instance by name
                instance = self.db.query(ModelInstance).filter(
                    ModelInstance.name == rule_obj.target,
                    ModelInstance.status == "running"
                ).first()
                if instance:
                    candidates.append((instance, rule_obj))

        return candidates

    async def _route_semantic(
        self,
        strategy: RoutingStrategy,
        candidates: List[tuple[ModelInstance, RoutingRule]]
    ) -> Optional[ModelInstance]:
        """Semantic routing: select by priority, then check health."""
        # Sort by priority (lower number = higher priority)
        candidates.sort(key=lambda x: x[1].priority)

        for instance, rule in candidates:
            if await self._is_instance_healthy(instance.id):
                return instance

        return None

    async def _route_weight(
        self,
        strategy: RoutingStrategy,
        candidates: List[tuple[ModelInstance, RoutingRule]]
    ) -> Optional[ModelInstance]:
        """Weight routing: select based on weight percentage."""
        # Filter healthy instances
        healthy_candidates = [
            (instance, rule) for instance, rule in candidates
            if await self._is_instance_healthy(instance.id)
        ]
        if not healthy_candidates:
            return None

        # Weighted random selection
        total_weight = sum(rule.weight for _, rule in healthy_candidates)
        if total_weight == 0:
            return None

        rand = random.randint(0, total_weight - 1)
        current = 0
        for instance, rule in healthy_candidates:
            current += rule.weight
            if rand < current:
                return instance

        return healthy_candidates[0][0] if healthy_candidates else None

    async def _route_round_robin(
        self,
        strategy: RoutingStrategy,
        candidates: List[tuple[ModelInstance, RoutingRule]]
    ) -> Optional[ModelInstance]:
        """Round-robin routing."""
        # Filter healthy instances
        healthy_instances = [
            instance for instance, _ in candidates
            if await self._is_instance_healthy(instance.id)
        ]
        if not healthy_instances:
            return None

        # Get current index
        index = self._round_robin_index.get(strategy.id, 0)
        selected = healthy_instances[index % len(healthy_instances)]

        # Increment index
        self._round_robin_index[strategy.id] = (index + 1) % len(healthy_instances)

        return selected

    async def _route_least_conn(
        self,
        strategy: RoutingStrategy,
        candidates: List[tuple[ModelInstance, RoutingRule]]
    ) -> Optional[ModelInstance]:
        """Least connection routing."""
        # Get all healthy instances with queue info
        healthy_instances = []
        for instance, _ in candidates:
            if await self._is_instance_healthy(instance.id):
                health = self.db.query(InstanceHealth).filter(
                    InstanceHealth.model_instance_id == instance.id
                ).first()
                if health:
                    healthy_instances.append((instance, health.queue_depth))
                else:
                    healthy_instances.append((instance, 0))

        if not healthy_instances:
            return None

        # Sort by queue depth (ascending)
        healthy_instances.sort(key=lambda x: x[1])
        return healthy_instances[0][0]

    async def _is_instance_healthy(self, instance_id: int) -> bool:
        """Check if an instance is healthy."""
        health = self.db.query(InstanceHealth).filter(
            InstanceHealth.model_instance_id == instance_id
        ).first()
        if not health:
            return True  # No health info, assume healthy

        return health.status == InstanceHealthStatus.HEALTHY

    # ========================================================================
    # Validation
    # ========================================================================

    def _validate_rules(self, mode: RoutingMode, rules: List[Dict[str, Any]]):
        """Validate routing rules for a specific mode."""
        if not rules:
            raise ValueError("Routing rules cannot be empty")

        for rule in rules:
            if "pattern" not in rule or "target" not in rule:
                raise ValueError("Each rule must have 'pattern' and 'target'")

            # Validate regex pattern
            try:
                re.compile(rule["pattern"])
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{rule['pattern']}': {e}")

            # Validate weight for weight-based routing
            if mode == RoutingMode.WEIGHT:
                weight = rule.get("weight", 100)
                if not 0 <= weight <= 100:
                    raise ValueError(f"Weight must be between 0 and 100, got {weight}")

            # Validate priority
            priority = rule.get("priority", 1)
            if not 1 <= priority <= 10:
                raise ValueError(f"Priority must be between 1 and 10, got {priority}")
