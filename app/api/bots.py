import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from app.db import execute_query, execute_write
from app.api.auth import get_current_admin
from app.services.scraper_service import InstagramScraper
from app.config import SESSION_DIR
from app.utils.logging_setup import logger

router = APIRouter(prefix="/api/bots", tags=["bots"])

# Schemas Pydantic
class BotCreateRequest(BaseModel):
    username: str
    password: str  # Senha é enviada efemeramente e não será gravada no banco de dados

class BotResponse(BaseModel):
    id: int
    username: str
    status: str
    session_file_name: str | None
    last_used_at: str | None
    created_at: str

@router.get("", response_model=List[BotResponse])
def list_bots(current_user: str = Depends(get_current_admin)):
    """
    Lista todos os bots cadastrados no banco de dados.
    """
    rows = execute_query("SELECT id, username, status, session_file_name, last_used_at, created_at FROM instagram_bots ORDER BY username")
    bots = []
    for row in rows:
        bots.append({
            "id": row["id"],
            "username": row["username"],
            "status": row["status"],
            "session_file_name": row["session_file_name"],
            "last_used_at": row["last_used_at"],
            "created_at": row["created_at"]
        })
    return bots

@router.post("")
def create_bot(data: BotCreateRequest, current_user: str = Depends(get_current_admin)):
    """
    Cadastra um bot executando a autenticação via Playwright de forma síncrona.
    A senha NÃO é persistida no SQLite. Apenas a sessão de sucesso é gravada.
    """
    # Verifica se o bot já existe
    exists = execute_query("SELECT 1 FROM instagram_bots WHERE username = ?", (data.username,))
    
    # Executa o login via Playwright
    scraper = InstagramScraper(data.username)
    success = scraper.authenticate(data.password)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Falha na autenticação do Instagram. Verifique o usuário/senha ou resolva o Checkpoint manualmente."
        )

    return {"message": f"Bot @{data.username} autenticado e cadastrado com sucesso!"}

@router.delete("/{username}")
def delete_bot(username: str, current_user: str = Depends(get_current_admin)):
    """
    Remove o bot do SQLite e exclui o arquivo de sessão associado no volume.
    """
    rows = execute_query("SELECT session_file_name FROM instagram_bots WHERE username = ?", (username,))
    if not rows:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
        
    bot = rows[0]
    
    # Exclui o registro do banco de dados
    execute_write("DELETE FROM instagram_bots WHERE username = ?", (username,))
    
    # Exclui o arquivo físico de sessão
    if bot["session_file_name"]:
        session_path = Path(SESSION_DIR) / bot["session_file_name"]
        try:
            if session_path.exists():
                os.remove(session_path)
                logger.info(f"Arquivo de sessão removido: {session_path}")
        except Exception as e:
            logger.error(f"Erro ao remover arquivo de sessão {session_path}: {e}")
            
    return {"message": f"Bot @{username} removido com sucesso."}
