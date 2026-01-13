"""
OpenAI Models API endpoint.
"""
import time
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tokenmachine.api.deps import get_current_db, verify_api_key_auth
from tokenmachine.models.database import ApiKey, Deployment, DeploymentStatus, Model
from tokenmachine.models.schemas import ModelInfo, ModelsListResponse

router = APIRouter(tags=["Models"])


@router.get("/v1/models", response_model=ModelsListResponse)
async def list_models(
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db),
):
    """
    List all available models (OpenAI-compatible).

    Returns only running deployments as available models.
    """
    # Get all running deployments
    deployments = db.query(Deployment).filter(
        Deployment.status == DeploymentStatus.RUNNING
    ).all()

    data = []
    for deployment in deployments:
        model = db.query(Model).filter(Model.id == deployment.model_id).first()
        if model:
            data.append(ModelInfo(
                id=deployment.name,
                object="model",
                created=int(model.created_at.timestamp()),
                owned_by="tokenmachine"
            ))

    return ModelsListResponse(object="list", data=data)
