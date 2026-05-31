from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from app.db import execute_query, execute_write
from app.api.auth import get_current_admin
from app.services.scraper_service import InstagramScraper
from app.utils.logging_setup import logger

router = APIRouter(prefix="/api/targets", tags=["targets"])

# Schemas Pydantic
class TargetCreateRequest(BaseModel):
    username: str
    download_feed: int = 1
    download_stories: int = 1
    download_comments: int = 0
    download_likes: int = 0
    check_frequency_hours: int = 24
    is_active: int = 1

class TargetUpdateRequest(BaseModel):
    download_feed: Optional[int]
    download_stories: Optional[int]
    download_comments: Optional[int]
    download_likes: Optional[int]
    check_frequency_hours: Optional[int]
    is_active: Optional[int]

class TargetResponse(BaseModel):
    id: int
    username: str
    download_feed: int
    download_stories: int
    download_comments: int
    download_likes: int
    check_frequency_hours: int
    is_active: int
    last_scraped_at: str | None
    created_at: str

@router.get("", response_model=List[TargetResponse])
def list_targets(current_user: str = Depends(get_current_admin)):
    """
    Lista todos os alvos cadastrados.
    """
    rows = execute_query(
        """
        SELECT id, username, download_feed, download_stories, download_comments, 
               download_likes, check_frequency_hours, is_active, last_scraped_at, created_at 
        FROM scraping_targets ORDER BY username
        """
    )
    targets = []
    for row in rows:
        targets.append({
            "id": row["id"],
            "username": row["username"],
            "download_feed": row["download_feed"],
            "download_stories": row["download_stories"],
            "download_comments": row["download_comments"],
            "download_likes": row["download_likes"],
            "check_frequency_hours": row["check_frequency_hours"],
            "is_active": row["is_active"],
            "last_scraped_at": row["last_scraped_at"],
            "created_at": row["created_at"]
        })
    return targets

@router.post("", response_model=TargetResponse)
def create_target(data: TargetCreateRequest, current_user: str = Depends(get_current_admin)):
    """
    Cadastra um novo alvo para raspagem periódica no SQLite.
    """
    # Remove @ se o usuário digitou
    username = data.username.replace("@", "").strip().lower()
    
    # Verifica se já está cadastrado
    exists = execute_query("SELECT 1 FROM scraping_targets WHERE username = ?", (username,))
    if exists:
        raise HTTPException(status_code=400, detail="Alvo já cadastrado.")

    last_id = execute_write(
        """
        INSERT INTO scraping_targets (username, download_feed, download_stories, download_comments, download_likes, check_frequency_hours, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (username, data.download_feed, data.download_stories, data.download_comments, data.download_likes, data.check_frequency_hours, data.is_active)
    )

    row = execute_query("SELECT * FROM scraping_targets WHERE id = ?", (last_id,))[0]
    return {
        "id": row["id"],
        "username": row["username"],
        "download_feed": row["download_feed"],
        "download_stories": row["download_stories"],
        "download_comments": row["download_comments"],
        "download_likes": row["download_likes"],
        "check_frequency_hours": row["check_frequency_hours"],
        "is_active": row["is_active"],
        "last_scraped_at": row["last_scraped_at"],
        "created_at": row["created_at"]
    }

@router.put("/{target_id}", response_model=TargetResponse)
def update_target(target_id: int, data: TargetUpdateRequest, current_user: str = Depends(get_current_admin)):
    """
    Atualiza as flags e parâmetros de monitoramento do alvo.
    """
    rows = execute_query("SELECT 1 FROM scraping_targets WHERE id = ?", (target_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Alvo não encontrado.")

    # Constrói a query de update dinamicamente com base nas opções fornecidas
    update_fields = []
    params = []
    
    for field, value in data.dict(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        params.append(value)
        
    if not update_fields:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar informado.")

    params.append(datetime.now().isoformat())
    params.append(target_id)
    
    execute_write(
        f"UPDATE scraping_targets SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?",
        tuple(params)
    )

    row = execute_query("SELECT * FROM scraping_targets WHERE id = ?", (target_id,))[0]
    return {
        "id": row["id"],
        "username": row["username"],
        "download_feed": row["download_feed"],
        "download_stories": row["download_stories"],
        "download_comments": row["download_comments"],
        "download_likes": row["download_likes"],
        "check_frequency_hours": row["check_frequency_hours"],
        "is_active": row["is_active"],
        "last_scraped_at": row["last_scraped_at"],
        "created_at": row["created_at"]
    }

@router.delete("/{target_id}")
def delete_target(target_id: int, current_user: str = Depends(get_current_admin)):
    """
    Remove o alvo do banco de dados (cascade deletará posts dele).
    """
    rows = execute_query("SELECT username FROM scraping_targets WHERE id = ?", (target_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Alvo não encontrado.")
    
    username = rows[0]["username"]
    execute_write("DELETE FROM scraping_targets WHERE id = ?", (target_id,))
    return {"message": f"Alvo @{username} removido do monitoramento."}

def run_manual_scraping(bot_username: str, target_username: str, job_type: str):
    """
    Função auxiliar executada em background pelo worker assíncrono do FastAPI.
    """
    try:
        logger.info(f"Iniciando raspagem manual de {job_type} para @{target_username} usando bot @{bot_username}...")
        scraper = InstagramScraper(bot_username)
        if job_type == "STORIES":
            scraper.scrape_stories(target_username)
        elif job_type == "FEED":
            scraper.scrape_feed(target_username)
    except Exception as e:
        logger.error(f"Erro na raspagem manual em background: {e}")

@router.post("/{target_id}/scrape")
def trigger_scrape(target_id: int, job_type: str, background_tasks: BackgroundTasks, current_user: str = Depends(get_current_admin)):
    """
    Dispara manualmente uma tarefa de raspagem (STORIES ou FEED) em background.
    Rotaciona bots ativos para encontrar um operacional.
    """
    rows = execute_query("SELECT username FROM scraping_targets WHERE id = ?", (target_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Alvo não encontrado.")
    target_username = rows[0]["username"]

    # Seleciona um bot ativo da fila
    bots = execute_query("SELECT username FROM instagram_bots WHERE status = 'ACTIVE' LIMIT 1")
    if not bots:
        raise HTTPException(status_code=400, detail="Não há contas bot ativas disponíveis para processar a requisição.")
    bot_username = bots[0]["username"]

    if job_type not in ["STORIES", "FEED"]:
        raise HTTPException(status_code=400, detail="Tipo de job inválido. Use STORIES ou FEED.")

    # Adiciona a tarefa à fila do FastAPI em background
    background_tasks.add_task(run_manual_scraping, bot_username, target_username, job_type)

    return {"message": f"Job de {job_type} disparado com sucesso para @{target_username} em background usando bot @{bot_username}."}
