import threading
import time
from datetime import datetime, timedelta
from app.db import execute_query
from app.services.scraper_service import InstagramScraper
from app.utils.logging_setup import logger

class BackgroundScheduler:
    def __init__(self):
        self._thread = None
        self._running = False
        self._last_stories_run = None
        self._last_feed_run = None

    def start(self):
        """
        Inicia a thread em background do Scheduler.
        """
        if self._running:
            logger.warning("Scheduler em background já está rodando.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="BackgroundScheduler")
        self._thread.start()
        logger.info("Scheduler em background inicializado com sucesso.")

    def stop(self):
        """
        Para o Scheduler de forma segura.
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            logger.info("Scheduler em background finalizado.")

    def _loop(self):
        """
        Loop principal que acorda a cada 60 segundos para avaliar se deve rodar as tarefas.
        """
        logger.info("Iniciando loop do Scheduler em background...")
        
        # Na inicialização, define os horários das últimas execuções para evitar rodar tudo imediatamente
        self._last_stories_run = datetime.now() - timedelta(minutes=55)  # Roda em 5 minutos
        self._last_feed_run = datetime.now() - timedelta(hours=23)       # Roda em 1 hora

        while self._running:
            try:
                now = datetime.now()
                
                # Execução Horária dos Stories (intervalo de 1 hora)
                if not self._last_stories_run or (now - self._last_stories_run) >= timedelta(hours=1):
                    logger.info("Disparando tarefa horária agendada: STORIES")
                    self.run_stories_job()
                    self._last_stories_run = now
                
                # Execução Diária do Feed (intervalo de 24 horas)
                if not self._last_feed_run or (now - self._last_feed_run) >= timedelta(hours=24):
                    logger.info("Disparando tarefa diária agendada: FEED")
                    self.run_feed_job()
                    self._last_feed_run = now

            except Exception as e:
                logger.error(f"Erro no loop do scheduler em background: {e}")
                
            time.sleep(60)  # Aguarda 1 minuto

    def run_stories_job(self):
        """
        Job de coleta de Stories: Roda sequencialmente para todos os alvos e bots ativos.
        """
        active_bots = execute_query("SELECT username FROM instagram_bots WHERE status = 'ACTIVE'")
        active_targets = execute_query("SELECT username FROM scraping_targets WHERE is_active = 1 AND download_stories = 1")

        if not active_bots:
            logger.warning("Nenhum bot ativo cadastrado para rodar o job de STORIES.")
            return
        if not active_targets:
            logger.info("Nenhum alvo de monitoramento ativo para STORIES.")
            return

        logger.info(f"Iniciando raspagem de STORIES para {len(active_targets)} alvos usando {len(active_bots)} bots ativos.")
        
        # Abordagem FIFO sequencial
        bot_index = 0
        for target in active_targets:
            target_username = target["username"]
            
            # Tenta raspar o alvo com o bot atual da fila
            success = False
            while not success and bot_index < len(active_bots):
                bot_username = active_bots[bot_index]["username"]
                
                # Verifica se o bot ainda está ativo antes de instanciar
                bot_status = execute_query("SELECT status FROM instagram_bots WHERE username = ?", (bot_username,))
                if not bot_status or bot_status[0]["status"] != "ACTIVE":
                    bot_index += 1
                    continue

                scraper = InstagramScraper(bot_username)
                res = scraper.scrape_stories(target_username)
                
                if res["status"] == "SUCCESS":
                    success = True
                    # Aplica delay leve de transição entre alvos
                    time.sleep(random.uniform(5.0, 15.0))
                else:
                    logger.warning(f"Bot {bot_username} falhou ao coletar stories de {target_username}. Tentando rotacionar bot...")
                    bot_index += 1  # Rotaciona para o próximo bot da fila se o atual falhar/bloquear

            if bot_index >= len(active_bots):
                logger.error("Todos os bots ativos foram exauridos ou bloqueados. Abortando job de STORIES.")
                break

    def run_feed_job(self):
        """
        Job de coleta de Feed: Roda sequencialmente para todos os alvos e bots ativos.
        """
        active_bots = execute_query("SELECT username FROM instagram_bots WHERE status = 'ACTIVE'")
        active_targets = execute_query("SELECT username FROM scraping_targets WHERE is_active = 1 AND download_feed = 1")

        if not active_bots:
            logger.warning("Nenhum bot ativo cadastrado para rodar o job de FEED.")
            return
        if not active_targets:
            logger.info("Nenhum alvo de monitoramento ativo para FEED.")
            return

        logger.info(f"Iniciando raspagem de FEED para {len(active_targets)} alvos usando {len(active_bots)} bots ativos.")
        
        bot_index = 0
        for target in active_targets:
            target_username = target["username"]
            
            success = False
            while not success and bot_index < len(active_bots):
                bot_username = active_bots[bot_index]["username"]
                
                bot_status = execute_query("SELECT status FROM instagram_bots WHERE username = ?", (bot_username,))
                if not bot_status or bot_status[0]["status"] != "ACTIVE":
                    bot_index += 1
                    continue

                scraper = InstagramScraper(bot_username)
                res = scraper.scrape_feed(target_username)
                
                if res["status"] == "SUCCESS":
                    success = True
                    # Aplica delay de transição entre alvos (cooldown)
                    time.sleep(random.uniform(15.0, 30.0))
                else:
                    logger.warning(f"Bot {bot_username} falhou ao coletar feed de {target_username}. Rotacionando bot...")
                    bot_index += 1

            if bot_index >= len(active_bots):
                logger.error("Todos os bots ativos foram exauridos ou bloqueados. Abortando job de FEED.")
                break

# Instância global do Scheduler
scheduler = BackgroundScheduler()
import random # Garante import local se não herdado
