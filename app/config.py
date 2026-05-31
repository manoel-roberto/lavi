import os
import secrets
from pathlib import Path

# Diretório base da aplicação
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurações do Banco de Dados e Diretórios de Armazenamento
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "storage.db"))
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", str(BASE_DIR / "data" / "downloads"))
SESSION_DIR = os.getenv("SESSION_DIR", str(BASE_DIR / "data" / "sessions"))
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", str(BASE_DIR / "data" / "crawler.log"))

# Garante que os diretórios necessários existam
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(SESSION_DIR).mkdir(parents=True, exist_ok=True)
Path(LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

# Configurações Administrativas do Painel
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin_lavi_2026")

# Chave Secreta para Assinatura de Tokens JWT
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Gera uma chave persistente ou aleatória temporária
    SECRET_KEY = secrets.token_hex(32)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas para o painel administrativo local
