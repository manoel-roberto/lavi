# Lavi

**Lavi** é uma plataforma de inteligência competitiva e extração automatizada de dados públicos do Instagram (Social Listening e OSINT). Projetada com foco em privacidade de dados e evasão anti-ban baseada em boas práticas, a plataforma coleta dados de feeds e stories de perfis públicos monitorados de forma transparente, indexando o conteúdo textual (legendas e comentários) para busca rápida em tempo real.

---

## 🚀 Funcionalidades Principais

* **Gerenciamento de Alvos**: Defina perfis do Instagram concorrentes ou artistas para monitoramento sob demanda ou automatizado.
* **Autenticação Segura de Bots (Sem senhas salvas)**: O sistema não armazena as senhas dos seus bots no banco de dados. Os logins são efetuados efemeramente e as sessões (`cookies/localStorage`) são mantidas localmente em arquivos criptografados de estado.
* **Coleta Inteligente e Automação**:
  * **Stories**: Capturados de hora em hora (incremental) para evitar que expirem.
  * **Feed e Reels**: Varredura diária incremental (últimas 24h) rodando na madrugada.
* **Evasão Anti-ban Avançada**: Utiliza **Playwright Stealth**, simulação de agentes reais, atrasos variáveis aleatórios (*jitter*) entre 10s e 25s por requisição, cooldowns longos e loop sequencial de execução FIFO (um bot por vez) para mitigar detecções de IP.
* **Busca Indexada de Alta Performance (FTS5)**: Utiliza a extensão nativa de busca textual do SQLite para pesquisar palavras-chave instantaneamente em legendas e nos comentários agregados.
* **Visualização Completa de Mídias e Logs**: Painel administrativo com terminal de logs em tempo real e galeria interativa para reprodução de fotos e vídeos coletados localmente.

---

## 📂 Arquitetura de Diretórios

A estrutura de pastas do projeto segue o padrão definido abaixo:

```text
├── SPEC/                  # Especificações técnicas e de engenharia
├── app/                   # Código-fonte Python do Backend
│   ├── api/               # Endpoints REST (FastAPI)
│   ├── services/          # Lógica de Scraping (Playwright) e Scheduler
│   ├── utils/             # Utilitários de criptografia, hash e logs
│   ├── config.py          # Configurações de ambiente do sistema
│   ├── db.py              # Modelagem de dados e triggers FTS5
│   └── main.py            # Ponto de entrada da aplicação
├── data/                  # Volume persistente (Banco de dados, cookies e mídias)
├── frontend/              # Interface Gráfica da SPA (HTML5, Vanilla CSS, JS)
├── Dockerfile             # Configuração da imagem isolada
└── docker-compose.yml     # Orquestração do container
```

---

## 🛠️ Requisitos de Instalação

* **Docker** e **Docker Compose** instalados na máquina hospedeira.

---

## 🏁 Inicialização Rápida

1. **Clone o repositório** (ou acesse a pasta raiz):
   ```bash
   git clone https://github.com/manoel-roberto/lavi.git
   cd lavi
   ```

2. **Inicie o container**:
   ```bash
   docker compose up --build -d
   ```

3. **Acesse a Interface Gráfica**:
   Abra o seu navegador no endereço: [http://localhost:8000](http://localhost:8000)

4. **Credenciais Administrativas Padrão**:
   * **Usuário**: `admin`
   * **Senha**: `admin_lavi_2026`
   *(Ao efetuar o primeiro login, o sistema solicitará obrigatoriamente a troca da senha padrão por uma senha forte pessoal).*

---

## 🔒 Políticas de Privacidade e Segurança

1. **Armazenamento Seguro de Cookies**: Credenciais do painel administrativo são armazenadas utilizando hashes criptográficos fortes (`bcrypt`). As chaves de sessão dos bots do Instagram são guardadas estritamente na pasta mapeada local `./data/sessions/` de forma isolada do banco de dados.
2. **Coleta Ética**: A coleta de dados é restrita a perfis públicos. A ferramenta não requer e não realiza a invasão de perfis privados sem autorização expressa, agindo estritamente como um agregador de dados de escuta social.

---

## 🛢️ Estrutura do Banco de Dados (SQLite FTS5)

O banco de dados armazena os metadados em tabelas relacionais clássicas, enquanto as legendas e comentários de posts são duplicados dinamicamente em uma tabela virtual utilizando triggers automáticos do SQLite:

```sql
-- Tabela virtual de pesquisa rápida
CREATE VIRTUAL TABLE posts_fts USING fts5(
    post_id,
    target_username,
    caption,
    comments_sample
);
```

* **Triggers de inserção e exclusão**: Atualizam a tabela virtual `posts_fts` em tempo real toda vez que um registro de post ou alvo é inserido ou removido.

---

## 🚀 Deploy em Produção (VPS ByteHosting)

Esta seção descreve os passos práticos para implantar o Lavi em um servidor VPS Linux na ByteHosting (ou outro provedor Ubuntu de sua preferência) com segurança criptográfica (SSH), firewall ativo e SSL automatizado pelo Caddy.

### Passo 1: Configuração Local (Na sua máquina local)

1. **Torne o script executável e rode-o**:
   ```bash
   chmod +x local_setup_ssh.sh
   ./local_setup_ssh.sh
   ```
2. **Adicione a chave SSH**:
   * Copie o conteúdo da chave pública exibida no terminal (gerada em `~/.ssh/id_lavi_vps.pub`).
   * Adicione esta chave no painel da **ByteHosting** antes de instanciar a VPS.
3. **Configure o atalho**:
   * Edite seu arquivo local em `~/.ssh/config` e substitua o placeholder `<DIGITE_O_IP_DA_SUA_VPS_AQUI>` pelo IP público real da sua VPS.

---

### Passo 2: Provisionamento da VPS

1. **Acesse a VPS remotamente** usando o atalho criado:
   ```bash
   ssh lavi-vps
   ```
2. **Clone o repositório da aplicação na VPS**:
   ```bash
   git clone https://github.com/manoel-roberto/lavi.git /app/lavi
   cd /app/lavi
   ```
3. **Execute o playbook de provisionamento e hardening**:
   ```bash
   sudo chmod +x server_deploy_setup.sh
   sudo ./server_deploy_setup.sh
   ```
   * *O que este script executa automaticamente:*
     * Atualização do sistema e instalação do SQLite3, Git e utilitários.
     * Instalação oficial estável do Docker Engine e Compose V2.
     * Ativação do Firewall UFW com **rate-limiting na porta SSH (22)** para mitigar ataques de brute-force e liberação de portas web (`80`/`443`).
     * Criação de volumes e atribuição de permissões em `/var/lib/lavi/`.
     * Registro do Cron Job diário (executado às 02:00 AM) para backups compactados com 7 dias de retenção.

---

### Passo 3: Inicialização em Produção

1. **Prepare as variáveis de ambiente**:
   ```bash
   cp .env.example .env
   nano .env
   ```
   * *Configurações obrigatórias:*
     * **`DOMAIN_NAME`**: Preencha com o seu domínio real (ex: `lavi.seu-dominio.com`) apontado para o IP da VPS. O Caddy usará este domínio para obter e renovar o certificado SSL Let's Encrypt de forma automática.
     * **`ADMIN_PASSWORD`** e **`SECRET_KEY`**: Insira chaves fortes e únicas.
2. **Suba o ecossistema Docker**:
   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```
3. **Acesse via HTTPS**:
   Acesse no seu navegador: `https://lavi.seu-dominio.com` (ou domínio correspondente). O Caddy garantirá HTTPS nativo com compressão ativa.

