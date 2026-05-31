from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from app.db import execute_query
from app.api.auth import get_current_admin

router = APIRouter(prefix="/api/posts", tags=["posts"])

class PostResponse(BaseModel):
    post_id: str
    target_id: int
    target_username: str
    post_type: str
    caption: Optional[str]
    taken_at: str
    like_count: int
    comment_count: int
    media_url: Optional[str]
    local_path: str

@router.get("", response_model=List[PostResponse])
def list_posts(
    target_id: Optional[int] = None,
    post_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: str = Depends(get_current_admin)
):
    """
    Retorna uma lista dos posts coletados ordenados por data de forma decrescente.
    Permite filtrar por alvo (target_id) e tipo de mídia.
    """
    query = """
        SELECT p.post_id, p.target_id, t.username as target_username, p.post_type, 
               p.caption, p.taken_at, p.like_count, p.comment_count, p.media_url, p.local_path
        FROM instagram_posts p
        JOIN scraping_targets t ON p.target_id = t.id
    """
    conditions = []
    params = []
    
    if target_id is not None:
        conditions.append("p.target_id = ?")
        params.append(target_id)
        
    if post_type is not None:
        conditions.append("p.post_type = ?")
        params.append(post_type)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY p.taken_at DESC LIMIT ?"
    params.append(limit)
    
    rows = execute_query(query, tuple(params))
    
    posts = []
    for row in rows:
        posts.append({
            "post_id": row["post_id"],
            "target_id": row["target_id"],
            "target_username": row["target_username"],
            "post_type": row["post_type"],
            "caption": row["caption"],
            "taken_at": row["taken_at"],
            "like_count": row["like_count"],
            "comment_count": row["comment_count"],
            "media_url": row["media_url"],
            "local_path": row["local_path"]
        })
    return posts
