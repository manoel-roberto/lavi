import sqlite3
import contextlib
from typing import Generator, List, Dict, Any, Optional
from app.config import DATABASE_PATH
from app.utils.logging_setup import logger

@contextlib.contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context Manager para gerenciar conexões com o banco de dados SQLite.
    Garante o fechamento de conexão e ativa pragma de chaves estrangeiras.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    finally:
        conn.close()

def init_db() -> None:
    """
    Inicializa as tabelas relacionais do SQLite e a tabela virtual FTS5
    de acordo com as melhores práticas de Engenharia de Software.
    """
    logger.info(f"Inicializando o banco de dados SQLite em: {DATABASE_PATH}")
    
    ddl_queries = [
        # 1. Tabela de Usuários Administrativos do Painel
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            must_change_password INTEGER NOT NULL DEFAULT 1, -- 1 = Sim, 0 = Não
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """,
        
        # 2. Tabela de Contas Bot do Instagram (Apenas estado e cookies de sessão, sem senhas)
        """
        CREATE TABLE IF NOT EXISTS instagram_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'ACTIVE',    -- ACTIVE, BLOCKED, CHALLENGE_PENDING, EXPIRED
            session_file_name TEXT,                   -- Nome do arquivo em data/sessions/
            last_used_at TEXT,                        -- Timestamp ISO 8601 da última utilização
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """,
        
        # 3. Tabela de Alvos (Targets) a serem monitorados
        """
        CREATE TABLE IF NOT EXISTS scraping_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,            -- Ex: 'alvo_username'
            instagram_id TEXT,                        -- ID numérico se conhecido
            download_feed INTEGER NOT NULL DEFAULT 1, -- 0 ou 1
            download_stories INTEGER NOT NULL DEFAULT 1, -- 0 ou 1
            download_comments INTEGER NOT NULL DEFAULT 0, -- 0 ou 1
            download_likes INTEGER NOT NULL DEFAULT 0, -- 0 ou 1
            check_frequency_hours INTEGER DEFAULT 24, -- Frequência do feed (diário = 24h)
            is_active INTEGER NOT NULL DEFAULT 1,     -- Ativo/Inativo (0 ou 1)
            last_scraped_at TEXT,                     -- Timestamp ISO 8601 da última raspagem
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """,
        
        # 4. Histórico de Execuções e Auditoria de Scraping
        """
        CREATE TABLE IF NOT EXISTS extraction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER,
            bot_id INTEGER,
            job_type TEXT NOT NULL,                  -- STORIES, FEED, COMMENTS, LIKES
            status TEXT NOT NULL,                     -- SUCCESS, FAILED, PARTIAL_BLOCK
            items_scraped INTEGER DEFAULT 0,          -- Contagem de itens coletados
            error_message TEXT,                       -- Detalhes de falhas
            started_at TEXT NOT NULL,                 -- Timestamp de início
            completed_at TEXT,                        -- Timestamp de fim
            FOREIGN KEY (target_id) REFERENCES scraping_targets(id) ON DELETE SET NULL,
            FOREIGN KEY (bot_id) REFERENCES instagram_bots(id) ON DELETE SET NULL
        );
        """,
        
        # 5. Tabela de Metadados Básicos dos Posts Raspados
        """
        CREATE TABLE IF NOT EXISTS instagram_posts (
            post_id TEXT PRIMARY KEY,                 -- ID do post (Shortcode)
            target_id INTEGER NOT NULL,
            post_type TEXT NOT NULL,                  -- IMAGE, VIDEO, CAROUSEL, REELS
            caption TEXT,                             -- Legenda
            taken_at TEXT NOT NULL,                   -- Data de postagem
            like_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            media_url TEXT,                           -- CDN original
            local_path TEXT NOT NULL,                 -- Caminho relativo no volume
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (target_id) REFERENCES scraping_targets(id) ON DELETE CASCADE
        );
        """,
        
        # 6. Tabela Virtual FTS5 (Full-Text Search) para legendas de posts e comentários
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
            post_id UNINDEXED,
            target_username,
            caption,
            comments_sample
        );
        """
    ]

    triggers_ddl = [
        # Trigger de Sincronização após INSERÇÃO de post
        """
        CREATE TRIGGER IF NOT EXISTS trg_posts_fts_insert AFTER INSERT ON instagram_posts
        BEGIN
            INSERT INTO posts_fts (post_id, target_username, caption, comments_sample)
            VALUES (
                new.post_id,
                (SELECT username FROM scraping_targets WHERE id = new.target_id),
                new.caption,
                ''
            );
        END;
        """,
        
        # Trigger de Sincronização após EXCLUSÃO de post
        """
        CREATE TRIGGER IF NOT EXISTS trg_posts_fts_delete AFTER DELETE ON instagram_posts
        BEGIN
            DELETE FROM posts_fts WHERE post_id = old.post_id;
        END;
        """
    ]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Executa a criação das tabelas normais e virtuais
        for query in ddl_queries:
            cursor.execute(query)
            
        # Executa a criação dos triggers
        for trigger in triggers_ddl:
            cursor.execute(trigger)
            
        conn.commit()
    logger.info("Banco de dados SQLite inicializado com sucesso.")

def execute_query(query: str, params: tuple = ()) -> List[sqlite3.Row]:
    """
    Executa uma consulta SELECT segura e retorna o resultado como uma lista de linhas.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

def execute_write(query: str, params: tuple = ()) -> int:
    """
    Executa uma operação de escrita (INSERT, UPDATE, DELETE) e retorna o número da última linha alterada/inserida.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid or cursor.rowcount
