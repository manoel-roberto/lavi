import os
from fastapi import APIRouter, Depends, HTTPException
from app.config import LOG_FILE_PATH
from app.api.auth import get_current_admin

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("")
def read_logs(lines: int = 150, current_user: str = Depends(get_current_admin)):
    """
    Retorna as últimas linhas do arquivo de log operacional do crawler para exibição na UI.
    """
    if not os.path.exists(LOG_FILE_PATH):
        return {"logs": "Nenhum log operacional gravado ainda."}

    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
            # Lê as linhas e retorna apenas as últimas especificadas
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return {"logs": "".join(last_lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logs: {str(e)}")
