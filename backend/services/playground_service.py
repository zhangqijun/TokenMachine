"""
Playground service for dialogue testing.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.database import PlaygroundSession, PlaygroundMessage
from backend.models.schemas import PlaygroundSessionCreate
from backend.core.config import get_settings
import httpx


# Try to import tiktoken for token counting, fallback to simple counting if not available
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


class PlaygroundService:
    """Dialogue testing service."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        if HAS_TIKTOKEN:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if HAS_TIKTOKEN:
            return len(self.encoding.encode(text))
        else:
            # Simple fallback: count characters / 4 (rough approximation)
            return len(text) // 4

    def create_session(
        self,
        user_id: int,
        data: PlaygroundSessionCreate
    ) -> PlaygroundSession:
        """Create a new dialogue session."""
        session = PlaygroundSession(
            user_id=user_id,
            deployment_id=data.deployment_id,
            session_name=data.session_name,
            model_parameters=data.model_parameters  # Use model_parameters (internal field name)
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def list_sessions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[PlaygroundSession]:
        """Get user's dialogue sessions."""
        return self.db.query(PlaygroundSession)\
            .filter(PlaygroundSession.user_id == user_id)\
            .order_by(PlaygroundSession.updated_at.desc())\
            .offset(skip)\
            .limit(min(limit, 100))\
            .all()

    def get_session(
        self,
        session_id: int,
        user_id: int
    ) -> Optional[PlaygroundSession]:
        """Get session details with messages."""
        return self.db.query(PlaygroundSession)\
            .filter(
                PlaygroundSession.id == session_id,
                PlaygroundSession.user_id == user_id
            )\
            .first()

    def send_message(
        self,
        session_id: int,
        user_id: int,
        content: str
    ) -> PlaygroundMessage:
        """
        Send message and get AI response.

        Process:
        1. Save user message
        2. Call inference API
        3. Save AI response
        4. Update session statistics
        """
        session = self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")

        # 1. Save user message
        user_message = PlaygroundMessage(
            session_id=session_id,
            role="user",
            content=content,
            input_tokens=self._count_tokens(content)
        )
        self.db.add(user_message)

        # 2. Prepare request history (last 10 messages)
        messages = []
        for msg in session.messages[-10:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        messages.append({"role": "user", "content": content})

        # Add system prompt if configured
        if session.model_parameters.get("systemPrompt"):
            messages.insert(0, {
                "role": "system",
                "content": session.model_parameters["systemPrompt"]
            })

        # 3. Call inference API
        try:
            # Get the inference URL from deployment or settings
            if session.deployment:
                # Use deployment endpoint if available
                # For now, use the default inference service URL
                api_url = f"{self.settings.inference_service_url}/v1/chat/completions"
            else:
                api_url = f"{self.settings.inference_service_url}/v1/chat/completions"

            with httpx.Client(timeout=60) as client:
                response = client.post(api_url, json={
                    "model": session.model_parameters.get("model", "default"),
                    "messages": messages,
                    "temperature": session.model_parameters.get("temperature", 0.7),
                    "max_tokens": session.model_parameters.get("maxTokens", 2048),
                    "top_p": session.model_parameters.get("topP", 0.9),
                    "frequency_penalty": session.model_parameters.get("frequencyPenalty", 0.0),
                    "presence_penalty": session.model_parameters.get("presencePenalty", 0.0)
                })
                response.raise_for_status()
                response_data = response.json()

            assistant_content = response_data["choices"][0]["message"]["content"]
            usage = response_data.get("usage", {})

        except Exception as e:
            # For testing/demo: simulate AI response if inference service is not available
            if self.settings.debug:
                assistant_content = f"[Demo Response] I received your message: {content}"
                usage = {
                    "prompt_tokens": user_message.input_tokens,
                    "completion_tokens": self._count_tokens(assistant_content)
                }
            else:
                raise RuntimeError(f"Failed to call inference API: {str(e)}")

        # 4. Save AI response
        assistant_message = PlaygroundMessage(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            output_tokens=usage.get("completion_tokens", self._count_tokens(assistant_content))
        )
        self.db.add(assistant_message)

        # 5. Update session statistics
        session.input_tokens += usage.get("prompt_tokens", user_message.input_tokens)
        session.output_tokens += usage.get("completion_tokens", assistant_message.output_tokens)
        session.total_cost = float((session.input_tokens + session.output_tokens) * self.settings.token_cost_rate)

        self.db.commit()
        self.db.refresh(assistant_message)
        return assistant_message

    def delete_session(self, session_id: int, user_id: int):
        """Delete a dialogue session."""
        session = self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        self.db.delete(session)
        self.db.commit()
