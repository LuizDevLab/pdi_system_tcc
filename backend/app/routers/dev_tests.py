# TODO(remover): rotas apenas para testar papéis e escopo; apagar antes da entrega.
from fastapi import APIRouter, Depends

from app.deps import require_evaluated_scope, require_roles
from app.models import User

router = APIRouter(prefix="/test", tags=["teste (remover)"])


@router.get("/admin-only")
def admin_only(user: User = Depends(require_roles("admin"))):
    return {"ok": True, "user_id": user.id}


@router.get("/evaluated/{user_id}")
def evaluated_scope(user_id: int, user: User = Depends(require_evaluated_scope)):
    return {"ok": True, "evaluated_id": user_id}
