from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from app.db import execute_query
from app.api.auth import get_current_admin

router = APIRouter(prefix="/api/search", tags=["search"])

class SearchResultResponse(Optional[dict]):
    pass

@router.get("")
def search_posts(q: str, current_user: str = Depends(get_current_admin)):
    """
    Realiza busca textual indexada de alta performance via FTS5 no SQLite.
    Pesquisa palavras-chave em legendas de posts e comentários coletados.
    """
    if not q or len(q.strip()) < 2:
        return []

    # Sanitiza a query para o FTS5 do SQLite
    search_query = f"{q.strip()}*"
    
    # Query que une a tabela virtual FTS5 com a tabela original para metadados e caminhos de arquivos
    query = """
        SELECT p.post_id, p.post_type, p.caption, p.taken_at, p.like_count, p.comment_count, 
               p.local_path, f.target_username, f.comments_sample
        FROM posts_fts f
        JOIN instagram_posts p ON f.post_id = p.post_id
        WHERE posts_fts MATCH ?
        ORDER BY p.taken_at DESC
        LIMIT 50
    """
    
    try:
        rows = execute_query(query, (search_query,))
        results = []
        for row in rows:
            results.append({
                "post_id": row["post_id"],
                "target_username": row["target_username"],
                "post_type": row["post_type"],
                "caption": row["caption"],
                "taken_at": row["taken_at"],
                "like_count": row["like_count"],
                "comment_count": row["comment_count"],
                "local_path": row["local_path"],
                "comments_sample": row["comments_sample"]
            })
        return results
    except Exception as e:
        # Se falhar por sintaxe MATCH, tenta busca aproximada usando LIKE como fallback
        fallback_query = """
            SELECT p.post_id, p.post_type, p.caption, p.taken_at, p.like_count, p.comment_count, 
                   p.local_path, t.username as target_username
            FROM instagram_posts p
            JOIN scraping_targets t ON p.target_id = t.id
            WHERE p.caption LIKE ?
            ORDER BY p.taken_at DESC
            LIMIT 50
        """
        like_pattern = f"%{q.strip()}%"
        rows = execute_query(fallback_query, (like_pattern,))
        results = []
        for row in rows:
            results.append({
                "post_id": row["post_id"],
                "target_username": row["target_username"],
                "post_type": row["post_type"],
                "caption": row["caption"],
                "taken_at": row["taken_at"],
                "like_count": row["like_count"],
                "comment_count": row["comment_count"],
                "local_path": row["local_path"],
                "comments_sample": ""
            })
        return results
