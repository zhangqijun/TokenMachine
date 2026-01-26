"""
Billing service for token-based billing and invoicing.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case
from datetime import datetime, date, timedelta
from decimal import Decimal

from backend.models.database import (
    APIKey, UsageLog, Invoice, Organization,
    UsageLogStatus, InvoiceStatus
)


# Pricing configuration (per 1K tokens)
PRICING = {
    "input_token": Decimal("0.001"),  # $0.001 per 1K input tokens
    "output_token": Decimal("0.002"),  # $0.002 per 1K output tokens
}


class BillingService:
    """Service for managing token billing and invoicing."""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Usage Recording
    # ========================================================================

    def record_usage(
        self,
        api_key_id: int,
        deployment_id: int,
        model_id: int,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status: UsageLogStatus = UsageLogStatus.SUCCESS,
        error_message: Optional[str] = None
    ) -> UsageLog:
        """
        Record API usage for billing.

        Args:
            api_key_id: API Key ID
            deployment_id: Deployment ID
            model_id: Model ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Request latency in milliseconds
            status: Request status
            error_message: Error message if status is error

        Returns:
            Created UsageLog object
        """
        log = UsageLog(
            api_key_id=api_key_id,
            deployment_id=deployment_id,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message
        )
        self.db.add(log)

        # Update API Key token usage
        api_key = self.db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if api_key:
            total_tokens = input_tokens + output_tokens
            api_key.tokens_used += total_tokens
            api_key.last_used_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(log)

        return log

    # ========================================================================
    # Cost Calculation
    # ========================================================================

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """
        Calculate cost for given tokens.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        input_cost = (Decimal(input_tokens) / Decimal("1000")) * PRICING["input_token"]
        output_cost = (Decimal(output_tokens) / Decimal("1000")) * PRICING["output_token"]
        return input_cost + output_cost

    def get_api_key_cost(self, api_key_id: int) -> Dict[str, Any]:
        """
        Get total cost for an API key.

        Args:
            api_key_id: API Key ID

        Returns:
            Dictionary with cost information
        """
        logs = self.db.query(UsageLog).filter(UsageLog.api_key_id == api_key_id).all()

        total_input_tokens = sum(log.input_tokens for log in logs)
        total_output_tokens = sum(log.output_tokens for log in logs)
        total_tokens = total_input_tokens + total_output_tokens
        total_cost = self.calculate_cost(total_input_tokens, total_output_tokens)

        return {
            "api_key_id": api_key_id,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "total_cost": float(total_cost)
        }

    # ========================================================================
    # Usage Statistics
    # ========================================================================

    def get_usage_stats(
        self,
        organization_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get usage statistics for an organization within a date range.

        Args:
            organization_id: Organization ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Dictionary with usage statistics
        """
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Query usage logs for the organization
        logs = self.db.query(UsageLog).join(APIKey).filter(
            and_(
                APIKey.organization_id == organization_id,
                UsageLog.created_at >= start_datetime,
                UsageLog.created_at <= end_datetime
            )
        ).all()

        # Calculate totals
        total_input_tokens = sum(log.input_tokens for log in logs)
        total_output_tokens = sum(log.output_tokens for log in logs)
        total_tokens = total_input_tokens + total_output_tokens
        total_cost = self.calculate_cost(total_input_tokens, total_output_tokens)

        # Calculate by model
        by_model: Dict[int, Dict[str, Any]] = {}
        for log in logs:
            model_id = log.model_id
            if model_id not in by_model:
                by_model[model_id] = {
                    "model_id": model_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "tokens": 0,
                    "cost": Decimal("0")
                }
            by_model[model_id]["input_tokens"] += log.input_tokens
            by_model[model_id]["output_tokens"] += log.output_tokens
            by_model[model_id]["tokens"] += (log.input_tokens + log.output_tokens)

        # Calculate costs for each model
        for model_id, stats in by_model.items():
            stats["cost"] = self.calculate_cost(
                stats["input_tokens"],
                stats["output_tokens"]
            )

        # Calculate by day
        by_day: Dict[str, Dict[str, Any]] = {}
        for log in logs:
            log_date = log.created_at.date().isoformat()
            if log_date not in by_day:
                by_day[log_date] = {
                    "date": log_date,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "tokens": 0,
                    "cost": Decimal("0"),
                    "requests": 0
                }
            by_day[log_date]["input_tokens"] += log.input_tokens
            by_day[log_date]["output_tokens"] += log.output_tokens
            by_day[log_date]["tokens"] += (log.input_tokens + log.output_tokens)
            by_day[log_date]["requests"] += 1

        # Calculate costs for each day
        for day_stats in by_day.values():
            day_stats["cost"] = float(self.calculate_cost(
                day_stats["input_tokens"],
                day_stats["output_tokens"]
            ))

        # Calculate by API key
        by_api_key: Dict[int, Dict[str, Any]] = {}
        for log in logs:
            key_id = log.api_key_id
            if key_id not in by_api_key:
                api_key = self.db.query(APIKey).filter(APIKey.id == key_id).first()
                by_api_key[key_id] = {
                    "api_key_id": key_id,
                    "key_prefix": api_key.key_prefix if api_key else "",
                    "name": api_key.name if api_key else "",
                    "tokens": 0,
                    "requests": 0
                }
            by_api_key[key_id]["tokens"] += (log.input_tokens + log.output_tokens)
            by_api_key[key_id]["requests"] += 1

        return {
            "organization_id": organization_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "total_cost": float(total_cost),
            "total_requests": len(logs),
            "by_model": list(by_model.values()),
            "by_day": sorted(by_day.values(), key=lambda x: x["date"]),
            "by_api_key": list(by_api_key.values())
        }

    def get_daily_usage(
        self,
        organization_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily usage for the last N days.

        Args:
            organization_id: Organization ID
            days: Number of days to retrieve

        Returns:
            List of daily usage statistics
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        stats = self.get_usage_stats(organization_id, start_date, end_date)
        return stats.get("by_day", [])

    # ========================================================================
    # Invoice Management
    # ========================================================================

    def create_invoice(
        self,
        organization_id: int,
        period_start: date,
        period_end: date
    ) -> Invoice:
        """
        Create an invoice for an organization for a billing period.

        Args:
            organization_id: Organization ID
            period_start: Billing period start
            period_end: Billing period end

        Returns:
            Created Invoice object

        Raises:
            ValueError: If invoice already exists for the period
        """
        # Check if invoice already exists
        existing = self.db.query(Invoice).filter(
            and_(
                Invoice.organization_id == organization_id,
                Invoice.period_start == period_start,
                Invoice.period_end == period_end
            )
        ).first()

        if existing:
            raise ValueError(
                f"Invoice already exists for organization {organization_id} "
                f"from {period_start} to {period_end}"
            )

        # Calculate usage and cost
        stats = self.get_usage_stats(organization_id, period_start, period_end)

        invoice = Invoice(
            organization_id=organization_id,
            amount=Decimal(str(stats["total_cost"])),
            currency="USD",
            status=InvoiceStatus.PENDING,
            period_start=datetime.combine(period_start, datetime.min.time()),
            period_end=datetime.combine(period_end, datetime.max.time()),
            tokens_used=stats["total_tokens"]
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Get an invoice by ID."""
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def list_invoices(
        self,
        organization_id: Optional[int] = None,
        status: Optional[InvoiceStatus] = None
    ) -> List[Invoice]:
        """
        List invoices with optional filtering.

        Args:
            organization_id: Filter by organization
            status: Filter by status

        Returns:
            List of Invoice objects
        """
        query = self.db.query(Invoice)

        if organization_id:
            query = query.filter(Invoice.organization_id == organization_id)
        if status:
            query = query.filter(Invoice.status == status)

        return query.order_by(Invoice.created_at.desc()).all()

    def update_invoice_status(
        self,
        invoice_id: int,
        status: InvoiceStatus
    ) -> Optional[Invoice]:
        """
        Update invoice status.

        Args:
            invoice_id: Invoice ID
            status: New status

        Returns:
            Updated Invoice object or None if not found
        """
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            return None

        invoice.status = status
        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def pay_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """
        Mark an invoice as paid.

        Args:
            invoice_id: Invoice ID

        Returns:
            Updated Invoice object or None if not found
        """
        return self.update_invoice_status(invoice_id, InvoiceStatus.PAID)

    def cancel_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """
        Cancel an invoice.

        Args:
            invoice_id: Invoice ID

        Returns:
            Updated Invoice object or None if not found
        """
        return self.update_invoice_status(invoice_id, InvoiceStatus.CANCELLED)

    # ========================================================================
    # Organization Billing Summary
    # ========================================================================

    def get_organization_billing_summary(
        self,
        organization_id: int
    ) -> Dict[str, Any]:
        """
        Get billing summary for an organization.

        Args:
            organization_id: Organization ID

        Returns:
            Dictionary with billing summary
        """
        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()

        if not org:
            return {}

        # Calculate total used tokens across all API keys
        total_used = self.db.query(
            func.sum(APIKey.tokens_used)
        ).filter(
            APIKey.organization_id == organization_id
        ).scalar() or 0

        # Get unpaid invoices
        unpaid_invoices = self.db.query(Invoice).filter(
            and_(
                Invoice.organization_id == organization_id,
                Invoice.status == InvoiceStatus.PENDING
            )
        ).all()

        unpaid_amount = sum(inv.amount for inv in unpaid_invoices)

        # Get this month's usage
        today = date.today()
        month_start = today.replace(day=1)
        month_usage = self.get_usage_stats(organization_id, month_start, today)

        return {
            "organization_id": organization_id,
            "plan": org.plan.value if hasattr(org.plan, 'value') else str(org.plan),
            "quota_tokens": org.quota_tokens,
            "tokens_used": int(total_used),
            "tokens_remaining": max(0, org.quota_tokens - int(total_used)),
            "usage_percentage": min(100, int(total_used / org.quota_tokens * 100)) if org.quota_tokens > 0 else 0,
            "this_month_cost": month_usage.get("total_cost", 0),
            "this_month_tokens": month_usage.get("total_tokens", 0),
            "unpaid_invoices": len(unpaid_invoices),
            "unpaid_amount": float(unpaid_amount)
        }
