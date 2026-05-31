import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import ADMIN_USERNAME, ADMIN_PASSWORD, DOWNLOAD_DIR
from app.db import init_db, execute_query, execute_write
from app.utils.crypto import get_password_hash
from app.utils.logging_setup import logger
from app.services.scheduler import scheduler

# Import de roteadores da API
from app.api.auth import router as auth_router
from app.api.bots import router as bots_router
from app.api.targets import router as targets_router
from app.api.search import router as search_router
from app.api.logs import router as logs_router

app = FastAPI(
    title="Lavi API",
    description="API de Gerenciamento do Motor de Coleta e Inteligência do Lavi",
    version="1.0.0"
)

# Configuração de CORS (Habilitado para desenvolvimento)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de rotas da API
app.include_router(auth_router)
app.include_router(bots_router)
app.include_router(targets_router)
app.include_router(search_router)
app.include_router(logs_router)

def setup_admin_user():
    """
    Verifica se existe ao menos um administrador cadastrado no banco.
    Caso contrário, gera o usuário administrador padrão utilizando as variáveis de ambiente.
    """
    rows = execute_query("SELECT id FROM admin_users LIMIT 1")
    if not rows:
        logger.info(f"Nenhum usuário administrador detectado. Criando usuário inicial: {ADMIN_USERNAME}")
        pw_hash = get_password_hash(ADMIN_PASSWORD)
        execute_write(
            "INSERT INTO admin_users (username, password_hash, must_change_password) VALUES (?, ?, 1)",
            (ADMIN_USERNAME, pw_hash)
        )
        logger.info("Usuário administrador inicial provisionado com sucesso. Senha temporária configurada.")

@app.on_event("startup")
def startup_event():
    # Inicializa tabelas e triggers do SQLite
    init_db()
    # Provisiona o administrador inicial
    setup_admin_user()
    # Inicia a execução do scheduler em background
    scheduler.start()
    logger.info("Servidor backend iniciado e scheduler ativo.")

@app.on_event("shutdown")
def shutdown_event():
    # Para o scheduler
    scheduler.stop()
    logger.info("Servidor backend finalizado.")

# Servidor de mídias baixadas (permite carregar imagens/vídeos locais diretamente na UI)
if os.path.exists(DOWNLOAD_DIR):
    app.mount("/media", StaticFiles(directory=DOWNLOAD_DIR), name="media")

# Monta o frontend estático na raiz (deve ser o último a ser montado)
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning(f"Diretório frontend não encontrado em: {frontend_dir}. Rotas HTML estáticas desabilitadas.")
