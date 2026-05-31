<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->


# 1. REGRAS GERAIS E ESTRUTURA DE PASTAS (ESTRITAMENTE OBRIGATÓRIO)
- Todo o código do projeto deve seguir a seguinte arquitetura de diretórios e convenções de nomenclatura:
  - `SPEC/`: Diretório obrigatório para armazenar todos os arquivos Markdown de especificações (IG-OSINTManager.md, TwitterOSINT.md, etc.).
  - `app/`: Código-fonte Python deve residir exclusivamente neste diretório.
  - `app/main.py`: Ponto de entrada da aplicação.
  - `app/config.py`: Configurações do sistema.
  - `app/db.py`: Conexão e ORM/modelos do banco de dados.
  - `app/utils/`: Utilitários gerais (logging, criptografia, web scraping).
  - `app/api/`: Endpoints da API FastAPI.
  - `app/services/`: Lógica de negócio e scripts de crawling.
  - `frontend/`: Código-fonte da interface web (HTML/JS/CSS).
  - `data/`: Arquivos de dados gerados (logs, arquivos temporários).
  - `requirements.txt`: Dependências Python.
  - `Dockerfile`: Container Docker.

# 2. DESENVOLVIMENTO DE SOFTWARE E REGRAS DO NEGÓCIO
- **Python**: Utilizar exclusivamente Python 3.10+ com tipagem estática (type hints) e docstrings detalhadas.
- **FastAPI**: A API deve ser construída usando FastAPI, priorizando performance e tipagem.
- **Armazenamento Local**: O banco de dados SQLite e todos os arquivos gerados devem residir exclusivamente dentro do diretório `data/` e ser persistidos via volume Docker.
- **Banco de Dados (FTS5)**: O SQLite deve utilizar tabelas virtuais FTS5 para indexação de texto (legendas, comentários) e tabelas normais para metadados (usuários, posts, sessões).
- **Segurança (Privacidade)**: A aplicação deve ser estritamente local. Não deve haver comunicação com servidores externos (a não ser para o scraping em si). Credenciais (como senhas de Instagram) devem ser tratadas com criptografia simétrica (AES-256-GCM) quando armazenadas em banco.
- **Interface Gráfica**: Interface web deve ser leve e funcional, desenvolvida em HTML/JS/CSS puro, sem frameworks pesados, para facilitar a portabilidade e o entendimento.

# 3. SCRAPING E PRIVACIDADE (ESTRITAMENTE OBRIGATÓRIO PARA PRIVACIDADE)
- **Fontes de Dados**:
  - O scraping deve priorizar o acesso a **perfis privados** ou **contas públicas** que não requerem autenticação. **Nenhum dado de usuários não autenticados deve ser coletado.**
  - O scraping de **perfis não autorizados** ou de conteúdo que requer login prévio deve ser evitado. Se necessário, o scraping deve ser realizado **exclusivamente** com contas que possuam autorização explícita ou permissão legal para acessar o conteúdo.
  - O scraping de **perfis privados** ou de conteúdo protegido por senha é **proibido** sem a permissão explícita do proprietário. A aplicação deve respeitar as configurações de privacidade e os direitos autorais.
  - O scraping de qualquer dado público ou autorizado deve ser realizado de forma ética, respeitando os termos de serviço das plataformas e as leis locais de privacidade de dados.
- **Playwright Stealth**:
  - O Playwright deve ser utilizado em modo stealth (`stealth: true`) para evitar detecção pelo anti-bot da plataforma.
  - O uso de proxies é permitido e recomendado para simular diferentes localizações geográficas.

# 4. GERENCIAMENTO DE SESSÕES E AUTENTICAÇÃO
- **Sessões de Usuário**:
  - As sessões de login (cookies) devem ser gerenciadas de forma segura dentro do diretório `data/sessions/`.
  - Cada arquivo de sessão deve ser nomeado de forma única (ex: `session-seu_usuario_bot.json`).
  - **O login deve ser realizado manualmente pelo usuário ou administrador** através da interface gráfica, fornecendo suas credenciais. O sistema não deve armazenar senhas, apenas os cookies/token gerados pelo login.
  - As sessões devem ser persistidas e reutilizadas para evitar bloqueios e agilizar o scraping.
- **Autenticação de Usuário**:
  - A interface web deve possuir um sistema de autenticação com login e senha para acesso administrativo ao painel.
  - As credenciais de login devem ser armazenadas de forma segura, com senha hasheada (bcrypt ou Argon2).

# 5. WEB SCRAPING DE INSTAGRAM E TWITTER
- **Instagram**:
  - **Stories**: Extração horária (incremental) de stories de perfis públicos e autorizados.
  - **Feed**: Extração incremental de posts do feed (últimas 24h) de perfis públicos e autorizados.
  - **Interação**: Ferramentas para curtidas, comentários (com texto gerado por IA), follow e unfollow em perfis públicos e autorizados.
  - **Botões da Interface Gráfica**:
    - **"Ver stories"**: Coleta stories do(s) bot(s) logado(s) em perfis públicos e autorizados.
    - **"Curti-todos os stories"**: Curte stories (públicos e autorizados) dos perfis logados.
    - **"Descurtir-todos os stories"**: Descurte stories (públicos e autorizados) dos perfis logados.
    - **"Follow-todos"**: Segue contas públicas e autorizadas.
    - **"Unfollow-todos"**: Deixa de seguir contas (públicas e autorizadas).
    - **"Salvar stories"**: Salva stories (públicos e autorizados) dos perfis logados (não interage).
    - **"Fazer login"**: Abre interface para login manual do usuário.
- **Twitter**:
  - **Feed**: Extração de tweets via X API (preferencial) ou scraping stealth.
  - **Interação**: Curtir, retweetar, favoritar e responder tweets (públicos e autorizados).
  - **Sessões**: Gerenciamento de sessões de login para autenticação via cookies.

# 6. ENGENHARIA DE DADOS (DATA ENGINEERING)
- **Engenharia de Dados**: O projeto deve seguir princípios de engenharia de dados, priorizando:
  - **Qualidade de dados**: Validação de dados coletados, tratamento de nulos e padronização de formatos.
  - **Escalabilidade**: Arquitetura que permita o aumento do número de contas monitoradas e do volume de dados.
  - **Performance**: Otimização de queries no SQLite, uso de cache quando apropriado e execução eficiente das requisições de scraping.
  - **Documentação**: Comentários claros no código, README atualizado e documentação da arquitetura.

# 7. EXECUÇÃO E AUTOMAÇÃO (CRON E WORKERS)
- **Cron**: O cron interno (anacron) deve ser responsável por:
  - Execução horária dos scrapers de Stories e Twitter.
  - Execução diária dos scrapers de Feed (Instagram e Twitter).
- **Workers**:
  - Utilizar pool de workers para execução concorrente das tarefas de scraping, otimizando o tempo de execução.

# 8. CONTÊINERIZAÇÃO (DOCKER E DOCKER COMPOSE)
- **Docker**: O container deve:
  - Ser construído a partir de uma imagem base Python com dependências instaladas.
  - Ter permissões de escrita no volume mapeado (`/app/data`).
  - Expôr a porta `8000` para a interface web.
- **Docker Compose**:
  - Deve mapear o volume `data/` para uma pasta local do host.
  - Deve expôr a porta `8000`.
  - Deve ser configurado para restart automático (`restart: always`).
