import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import AskQuestionRequest, AskQuestionResponse
from app.services.rag_service import RAGService

router = APIRouter(tags=["AI / RAG"])


@router.post(
    "/projects/{project_id}/ask",
    response_model=AskQuestionResponse,
    summary="Evidence-grounded question answering with source citations",
)
def ask_question(
    project_id: uuid.UUID,
    data: AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AskQuestionResponse:
    return RAGService.ask_question(db, current_user, project_id, data)
