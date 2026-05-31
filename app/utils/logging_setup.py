import logging
import sys
from logging.handlers import RotatingFileHandler
from app.config import LOG_FILE_PATH

def setup_logger(name: str = "ig_osint") -> logging.Logger:
    """
    Configura e retorna um Logger que grava logs no console (stdout) e em um arquivo rotativo.
    """
    logger = logging.getLogger(name)
    
    # Se o logger já tiver handlers, retorna para evitar duplicidade
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler para o Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para o arquivo (com rotação automática de 5MB, máximo 3 arquivos de backup)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Erro ao inicializar o file handler de log: {e}", file=sys.stderr)

    return logger

# Instância global de logging
logger = setup_logger()
