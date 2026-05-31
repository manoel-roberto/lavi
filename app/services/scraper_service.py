import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from playwright.sync_api import sync_playwright, BrowserContext, Page
from playwright_stealth import stealth_sync

from app.config import SESSION_DIR, DOWNLOAD_DIR
from app.db import execute_write, execute_query
from app.utils.logging_setup import logger

class InstagramScraper:
    def __init__(self, bot_username: str):
        self.bot_username = bot_username
        self.session_file = Path(SESSION_DIR) / f"session-{bot_username}.json"
        self.db_bot_id = self._get_bot_id()

    def _get_bot_id(self) -> Optional[int]:
        rows = execute_query("SELECT id FROM instagram_bots WHERE username = ?", (self.bot_username,))
        return rows[0]["id"] if rows else None

    def _apply_jitter(self, min_sec: float = 10.0, max_sec: float = 25.0):
        """
        Aplica o atraso aleatório (jitter) para mimetizar comportamento humano.
        """
        delay = random.uniform(min_sec, max_sec)
        logger.info(f"Aplicando jitter delay de {delay:.2f} segundos...")
        time.sleep(delay)

    def _cooldown(self):
        """
        Aplica uma pausa de descanso prolongada.
        """
        cooldown_time = random.uniform(120.0, 300.0)
        logger.info(f"Cooldown ativo. Descansando por {cooldown_time:.2f} segundos...")
        time.sleep(cooldown_time)

    def _check_soft_block(self, page: Page) -> bool:
        """
        Verifica se a página atual exibe indícios de bloqueio ou desafio de segurança.
        """
        content = page.content().lower()
        indicators = [
            "login • instagram",
            "autenticação",
            "checkpoint",
            "suspeitamos de um comportamento automatizado",
            "tente novamente mais tarde",
            "restrição de conta",
            "confirmar sua identidade",
            "verify your account"
        ]
        
        # Se a URL contiver /accounts/login/ ou /challenge/
        if "/accounts/login/" in page.url or "/challenge/" in page.url:
            return True

        for indicator in indicators:
            if indicator in content:
                return True
                
        return False

    def authenticate(self, password_efemera: str) -> bool:
        """
        Realiza o login manual interativo enviando a senha efemeramente.
        Salva o arquivo de sessão JSON e atualiza o banco de dados.
        """
        logger.info(f"Iniciando tentativa de login para o bot: {self.bot_username}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            stealth_sync(page)

            try:
                page.goto("https://www.instagram.com/accounts/login/")
                page.wait_for_timeout(3000)

                # Preenche credenciais
                page.fill("input[name='username']", self.bot_username)
                page.wait_for_timeout(random.uniform(800, 1500))
                page.fill("input[name='password']", password_efemera)
                page.wait_for_timeout(random.uniform(500, 1200))
                
                # Clica em entrar
                page.click("button[type='submit']")
                
                # Aguarda navegação ou confirmação de sucesso
                # Esperamos até 15 segundos para redirecionamento pós-login
                success = False
                for _ in range(30):
                    page.wait_for_timeout(500)
                    # Verifica se o cookie sessionid foi gerado e se não estamos mais na página de login
                    cookies = context.cookies()
                    has_session = any(c['name'] == 'sessionid' for c in cookies)
                    if has_session and "/accounts/login/" not in page.url:
                        success = True
                        break
                    if self._check_soft_block(page):
                        logger.warning(f"Bot {self.bot_username} detectou bloqueio ou checkpoint durante o login.")
                        break

                if success:
                    # Salva cookies e estado do navegador
                    state = context.storage_state()
                    with open(self.session_file, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=4)
                    
                    logger.info(f"Login efetuado com sucesso! Sessão salva em {self.session_file}")
                    
                    # Atualiza ou cria bot no banco de dados
                    now = datetime.now().isoformat()
                    execute_write(
                        """
                        INSERT INTO instagram_bots (username, status, session_file_name, last_used_at)
                        VALUES (?, 'ACTIVE', ?, ?)
                        ON CONFLICT(username) DO UPDATE SET
                        status = 'ACTIVE', session_file_name = ?, last_used_at = ?, updated_at = ?
                        """,
                        (self.bot_username, self.session_file.name, now, self.session_file.name, now, now)
                    )
                    return True
                else:
                    logger.error(f"Falha ao realizar login para o bot: {self.bot_username}. Verifique credenciais ou checkpoint.")
                    return False
            except Exception as e:
                logger.error(f"Erro inesperado durante autenticação: {e}")
                return False
            finally:
                browser.close()

    def scrape_stories(self, target_username: str) -> Dict[str, Any]:
        """
        Coleta os stories ativos do alvo (últimas 24h) de forma incremental.
        """
        logger.info(f"Bot {self.bot_username} iniciando coleta de STORIES de: {target_username}")
        result = {"status": "SUCCESS", "items_scraped": 0, "error": None}
        started_at = datetime.now().isoformat()
        
        if not self.session_file.exists():
            result.update({"status": "FAILED", "error": "Sessão expirada ou inexistente. Faça login novamente."})
            self._log_history("STORIES", target_username, result, started_at)
            return result

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                # Carrega o contexto com a sessão salva
                context = browser.new_context(
                    storage_state=str(self.session_file),
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                stealth_sync(page)

                # Acessa os stories do alvo
                page.goto(f"https://www.instagram.com/stories/{target_username}/")
                page.wait_for_timeout(4000)

                if self._check_soft_block(page):
                    self._handle_soft_block("STORIES", target_username, started_at)
                    result.update({"status": "FAILED", "error": "Soft Block detectado pelo Instagram."})
                    return result

                # Verifica se há stories ativos na página (ou se o usuário não tem stories)
                if "/stories/" not in page.url:
                    logger.info(f"O alvo {target_username} não possui stories ativos no momento.")
                    result.update({"status": "SUCCESS", "items_scraped": 0})
                    self._log_history("STORIES", target_username, result, started_at)
                    return result

                # Pasta de download do target
                target_dir = Path(DOWNLOAD_DIR) / f"@{target_username}" / "stories"
                target_dir.mkdir(parents=True, exist_ok=True)

                # Navega pelos stories clicando em avançar
                max_stories = 20  # Evita loops infinitos
                scraped_count = 0
                
                for i in range(max_stories):
                    # Procura tags de imagem ou vídeo do story atual
                    # No Instagram, a tag de vídeo tem a tag <video> e a imagem tem <img alt="Foto do story de...">
                    video_element = page.query_selector("video")
                    img_element = page.query_selector("img[alt*='story']")

                    story_id = f"story_{int(time.time())}_{i}"
                    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    
                    if video_element:
                        src = video_element.get_attribute("src")
                        if src:
                            file_path = target_dir / f"{timestamp_str}_{story_id}.mp4"
                            # Baixa o vídeo síncrono
                            self._download_file(page, src, file_path)
                            scraped_count += 1
                    elif img_element:
                        src = img_element.get_attribute("src")
                        if src:
                            file_path = target_dir / f"{timestamp_str}_{story_id}.jpg"
                            # Baixa a imagem
                            self._download_file(page, src, file_path)
                            scraped_count += 1

                    # Aplica jitter rápido antes de passar ao próximo
                    self._apply_jitter(1.5, 3.5)

                    # Tenta clicar no botão de avançar ("Próximo")
                    # O botão de avançar geralmente tem a classe correspondente ou aria-label "Avançar"
                    next_btn = page.query_selector("button[aria-label='Avançar'], button[aria-label='Next']")
                    if next_btn:
                        next_btn.click()
                        page.wait_for_timeout(2000)
                    else:
                        # Se não há botão de avançar, os stories acabaram ou fomos redirecionados
                        break

                    # Se saiu da rota de stories, finalizou
                    if f"/stories/{target_username}" not in page.url:
                        break

                result.update({"status": "SUCCESS", "items_scraped": scraped_count})
                self._log_history("STORIES", target_username, result, started_at)
                
            except Exception as e:
                logger.error(f"Erro ao raspar stories de {target_username}: {e}")
                result.update({"status": "FAILED", "error": str(e)})
                self._log_history("STORIES", target_username, result, started_at)
            finally:
                browser.close()

        return result

    def scrape_feed(self, target_username: str) -> Dict[str, Any]:
        """
        Coleta as últimas postagens do Feed/Reels de forma incremental diária.
        Pára assim que encontra o primeiro post já baixado na rodada anterior.
        """
        logger.info(f"Bot {self.bot_username} iniciando coleta de FEED de: {target_username}")
        result = {"status": "SUCCESS", "items_scraped": 0, "error": None}
        started_at = datetime.now().isoformat()

        if not self.session_file.exists():
            result.update({"status": "FAILED", "error": "Sessão expirada. Refaça o login interativo."})
            self._log_history("FEED", target_username, result, started_at)
            return result

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    storage_state=str(self.session_file),
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                stealth_sync(page)

                # Navega para o perfil do alvo
                page.goto(f"https://www.instagram.com/{target_username}/")
                page.wait_for_timeout(5000)

                if self._check_soft_block(page):
                    self._handle_soft_block("FEED", target_username, started_at)
                    result.update({"status": "FAILED", "error": "Soft Block detectado."})
                    return result

                # Seleciona as tags de âncora que apontam para posts (/p/ ou /reel/)
                post_links = page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
                urls = []
                for link in post_links:
                    href = link.get_attribute("href")
                    if href:
                        full_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                        if full_url not in urls:
                            urls.append(full_url)

                logger.info(f"Encontrados {len(urls)} links de posts de feed na página do perfil.")

                target_dir = Path(DOWNLOAD_DIR) / f"@{target_username}" / "feed"
                target_dir.mkdir(parents=True, exist_ok=True)

                scraped_count = 0
                target_id = self._get_target_id(target_username)

                for url in urls:
                    # Extrai o shortcode do post da URL
                    # Exemplo de URL: https://www.instagram.com/p/C7p2XYZ123/
                    shortcode = url.split("/p/")[-1].split("/reel/")[-1].replace("/", "").strip()

                    # Verifica se o post já foi raspado anteriormente no banco
                    exists = execute_query("SELECT 1 FROM instagram_posts WHERE post_id = ?", (shortcode,))
                    if exists:
                        # TARGET MANAGEMENT: Pára imediatamente ao encontrar o primeiro post antigo persistido
                        logger.info(f"Post {shortcode} já cadastrado no banco de dados. Interrompendo coleta incremental.")
                        break

                    # Acessa o post individualmente para coletar legenda, comentários e mídia
                    page.goto(url)
                    page.wait_for_timeout(4000)

                    if self._check_soft_block(page):
                        self._handle_soft_block("FEED", target_username, started_at)
                        result.update({"status": "PARTIAL_BLOCK", "items_scraped": scraped_count, "error": "Soft Block durante a navegação interna de posts."})
                        return result

                    # Extrai legenda
                    caption_element = page.query_selector("h1")  # Normalmente a legenda está na primeira tag h1
                    caption = caption_element.inner_text() if caption_element else ""

                    # Extrai quantidade de curtidas se visível
                    likes = 0
                    likes_element = page.query_selector("section a span, section span span")
                    if likes_element:
                        try:
                            likes_text = likes_element.inner_text().replace(".", "").replace(",", "").strip()
                            likes = int(likes_text) if likes_text.isdigit() else 0
                        except:
                            pass

                    # Tenta baixar a imagem ou o vídeo do post
                    img_elem = page.query_selector("article img")
                    video_elem = page.query_selector("article video")
                    
                    post_type = "IMAGE"
                    media_url = ""
                    local_filename = ""

                    if video_elem:
                        post_type = "VIDEO"
                        media_url = video_elem.get_attribute("src") or ""
                        local_filename = f"{datetime.now().strftime('%Y-%m-%d')}_feed_{shortcode}.mp4"
                    elif img_elem:
                        post_type = "IMAGE"
                        media_url = img_elem.get_attribute("src") or ""
                        local_filename = f"{datetime.now().strftime('%Y-%m-%d')}_feed_{shortcode}.jpg"

                    local_path = target_dir / local_filename if local_filename else None

                    if media_url and local_path:
                        self._download_file(page, media_url, local_path)

                    # Persiste o texto da legenda na tabela de posts do SQLite (gatilho FTS5 fará o índice)
                    taken_at = datetime.now().isoformat() # Usamos data atual como taken_at para o MVP
                    
                    if target_id:
                        execute_write(
                            """
                            INSERT OR IGNORE INTO instagram_posts 
                            (post_id, target_id, post_type, caption, taken_at, like_count, comment_count, media_url, local_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (shortcode, target_id, post_type, caption, taken_at, likes, 0, media_url, str(local_path.relative_to(Path(DOWNLOAD_DIR).parent)))
                        )
                        
                    scraped_count += 1
                    
                    # Salva metadados brutos JSON locais
                    meta_path = target_dir / f"{datetime.now().strftime('%Y-%m-%d')}_feed_{shortcode}_meta.json"
                    meta_data = {
                        "post_id": shortcode,
                        "url": url,
                        "post_type": post_type,
                        "caption": caption,
                        "like_count": likes,
                        "media_url": media_url,
                        "local_path": str(local_path) if local_path else ""
                    }
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta_data, f, indent=4)

                    # Aplica jitter delay antes do próximo post
                    self._apply_jitter(10.0, 25.0)

                result.update({"status": "SUCCESS", "items_scraped": scraped_count})
                self._log_history("FEED", target_username, result, started_at)
                
            except Exception as e:
                logger.error(f"Erro ao raspar feed de {target_username}: {e}")
                result.update({"status": "FAILED", "error": str(e)})
                self._log_history("FEED", target_username, result, started_at)
            finally:
                browser.close()

        return result

    def _download_file(self, page: Page, url: str, dest_path: Path):
        """
        Baixa o arquivo binário da mídia de forma resiliente usando requisição interna da sessão do Playwright.
        """
        try:
            # Obtém cookies do contexto e faz download via API de request do próprio contexto (mantém autenticação se necessário)
            response = page.context.request.get(url)
            if response.status == 200:
                dest_path.write_bytes(response.body())
                logger.info(f"Mídia salva com sucesso em: {dest_path.name}")
            else:
                logger.warning(f"Resposta inesperada ao baixar mídia HTTP {response.status}")
        except Exception as e:
            logger.error(f"Falha ao realizar download da mídia: {e}")

    def _get_target_id(self, target_username: str) -> Optional[int]:
        rows = execute_query("SELECT id FROM scraping_targets WHERE username = ?", (target_username,))
        return rows[0]["id"] if rows else None

    def _handle_soft_block(self, job_type: str, target_username: str, started_at: str):
        """
        Trata o Soft Block desativando o status do bot no banco e salvando logs.
        """
        logger.error(f"Soft Block de segurança detectado para o bot {self.bot_username} ao rodar {job_type}.")
        now = datetime.now().isoformat()
        
        # Altera status do bot para BLOCKED
        execute_write(
            "UPDATE instagram_bots SET status = 'BLOCKED', updated_at = ? WHERE username = ?",
            (now, self.bot_username)
        )
        
        # Loga falha no histórico
        result = {"status": "FAILED", "items_scraped": 0, "error": "Instagram Soft Block/Challenge detected"}
        self._log_history(job_type, target_username, result, started_at)

    def _log_history(self, job_type: str, target_username: str, result: Dict[str, Any], started_at: str):
        """
        Escreve o log de auditoria na tabela extraction_history.
        """
        target_id = self._get_target_id(target_username)
        completed_at = datetime.now().isoformat()
        execute_write(
            """
            INSERT INTO extraction_history (target_id, bot_id, job_type, status, items_scraped, error_message, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (target_id, self.db_bot_id, job_type, result["status"], result["items_scraped"], result["error"], started_at, completed_at)
        )
        
        # Atualiza a data da última raspagem do alvo
        if result["status"] == "SUCCESS" and target_id:
            execute_write(
                "UPDATE scraping_targets SET last_scraped_at = ?, updated_at = ? WHERE id = ?",
                (completed_at, completed_at, target_id)
            )
