#!/bin/bash

# ==============================================================================
# PLAYBOOK DE PROVISIONAMENTO DA VPS - LAVI (IG-OSINT MANAGER)
# ==============================================================================
# Este script deve rodar diretamente na VPS Ubuntu remota da ByteHosting.
# Ele configura o sistema operacional, instala Docker, define o Firewall e
# agenda a rotina inteligente de backups diários.

# Cores para logs formatados no terminal
GREEN="\e[32m"
YELLOW="\e[33m"
RED="\e[31m"
BLUE="\e[34m"
ENDCOLOR="\e[0m"

# Garante que o script está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERRO] Este script de provisionamento deve rodar como root (sudo).${ENDCOLOR}"
    exit 1
fi

echo -e "${BLUE}[INFO] Iniciando provisionamento do servidor remoto VPS para o Lavi...${ENDCOLOR}"

# 1. Atualização e Upgrades Silenciosos do Sistema
echo -e "${BLUE}[INFO] Atualizando os repositórios e pacotes da VPS...${ENDCOLOR}"
apt-get update && apt-get upgrade -y
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO] Falha ao atualizar pacotes do sistema remoto.${ENDCOLOR}"
    exit 1
fi
echo -e "${GREEN}[SUCESSO] Sistema operacional atualizado com sucesso.${ENDCOLOR}"

# 2. Instalação de Pacotes Essenciais (incluindo sqlite3 para backups seguros)
echo -e "${BLUE}[INFO] Instalando dependências essenciais (curl, git, ufw, sqlite3, tar)...${ENDCOLOR}"
apt-get install -y curl git htop ufw iptables sqlite3 tar ca-certificates gnupg
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO] Falha ao instalar dependências essenciais do sistema.${ENDCOLOR}"
    exit 1
fi
echo -e "${GREEN}[SUCESSO] Dependências instaladas com sucesso.${ENDCOLOR}"

# 3. Instalação Oficial e Estável do Docker e Docker Compose V2
echo -e "${BLUE}[INFO] Configurando chaveiro oficial e repositório do Docker...${ENDCOLOR}"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

echo -e "${BLUE}[INFO] Instalando Docker Engine e plugins oficiais (Docker Compose)...${ENDCOLOR}"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO] Falha ao instalar o Docker Engine.${ENDCOLOR}"
    exit 1
fi
echo -e "${GREEN}[SUCESSO] Docker Engine e Docker Compose instalados com sucesso.${ENDCOLOR}"

# 4. Configuração de Firewall e Hardening SSH com UFW
echo -e "${BLUE}[INFO] Aplicando regras rígidas de segurança no Firewall (UFW)...${ENDCOLOR}"
# Políticas padrões: nega entradas e permite saídas
ufw default deny incoming
ufw default allow outgoing

# Abre portas de produção HTTP e HTTPS externas para o Caddy Proxy
ufw allow 80/tcp
ufw allow 443/tcp

# Hardening da Porta SSH 22: Bloqueia IPs que tentem força bruta com rate limiting nativo
ufw limit 22/tcp

# Ativa o Firewall de forma não interativa e permanente
ufw --force enable
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO] Falha ao ativar o firewall UFW.${ENDCOLOR}"
    exit 1
fi
echo -e "${GREEN}[SUCESSO] Firewall UFW ativo com Rate Limiting ativo na porta 22 (SSH).${ENDCOLOR}"

# 5. Estruturação dos Volumes Físicos Remotos para o Lavi
echo -e "${BLUE}[INFO] Criando árvore de diretórios persistentes no host da VPS...${ENDCOLOR}"
mkdir -p /var/lib/lavi/data
mkdir -p /var/lib/lavi/downloads
mkdir -p /var/lib/lavi/sessions
mkdir -p /var/lib/lavi/backups

# Define permissões adequadas
chmod -R 775 /var/lib/lavi
# Associa as pastas ao grupo docker (se o grupo existir) para permitir manipulação sem quebra de privilégios
getent group docker > /dev/null
if [ $? -eq 0 ]; then
    chown -R root:docker /var/lib/lavi
else
    chown -R root:root /var/lib/lavi
fi
echo -e "${GREEN}[SUCESSO] Volumes persistentes criados em /var/lib/lavi/ com permissões ajustadas.${ENDCOLOR}"

# 6. Escrita do Script de Backup Automatizado no Host
echo -e "${BLUE}[INFO] Escrevendo script inteligente de backup diário em /var/lib/lavi/backup_job.sh...${ENDCOLOR}"
cat << 'EOF' > /var/lib/lavi/backup_job.sh
#!/bin/bash

# Script de backup remoto - Executa dump seguro e compactação com retenção
BACKUP_DIR="/var/lib/lavi/backups"
DATA_DIR="/var/lib/lavi/data"
SESSIONS_DIR="/var/lib/lavi/sessions"
TEMP_DB_BACKUP="/tmp/storage_backup.db"
DATE=$(date +%Y-%m-%d)
BACKUP_FILE="$BACKUP_DIR/backup_lavi_$DATE.tar.gz"

# 1. Garante que a pasta de destino existe
mkdir -p "$BACKUP_DIR"

# 2. Executa cópia/dump seguro com timeout de escrita para evitar bloqueio do SQLite pelo Worker
if [ -f "$DATA_DIR/storage.db" ]; then
    sqlite3 "$DATA_DIR/storage.db" ".timeout 5000" ".backup $TEMP_DB_BACKUP"
    BACKUP_DB_STATUS=$?
else
    BACKUP_DB_STATUS=1
fi

# 3. Compacta o banco de dados seguro e os cookies de sessões ativas do bot
if [ $BACKUP_DB_STATUS -eq 0 ]; then
    # Se o backup do SQLite funcionou, compacta o dump e a pasta de sessões
    tar -czf "$BACKUP_FILE" -C /tmp storage_backup.db -C /var/lib/lavi sessions
    rm -f "$TEMP_DB_BACKUP"
else
    # Caso não haja banco ainda (primeira execução) ou falhe o sqlite3, compacta apenas a pasta de sessões
    tar -czf "$BACKUP_FILE" -C /var/lib/lavi sessions
fi

# 4. Aplica política de retenção estrita: Exclui backups com mais de 7 dias de criação
find "$BACKUP_DIR" -name "backup_lavi_*.tar.gz" -type f -mtime +7 -delete

echo "[BACKUP-LAVI] Backup concluído em $DATE. Retenção de 7 dias validada."
EOF

# Dá permissão de execução ao script de backup
chmod +x /var/lib/lavi/backup_job.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO] Falha ao aplicar permissões no script de backup.${ENDCOLOR}"
    exit 1
fi
echo -e "${GREEN}[SUCESSO] Script de backup gravado e configurado como executável.${ENDCOLOR}"

# 7. Registra o Cron Job Diário para rodar às 02:00 AM
echo -e "${BLUE}[INFO] Registrando o job de backup no agendador de tarefas Cron do host remoto...${ENDCOLOR}"
# Remove job existente para manter o script idempotente
crontab -l 2>/dev/null | grep -v "/var/lib/lavi/backup_job.sh" | crontab -
# Adiciona o novo agendamento
(crontab -l 2>/dev/null; echo "0 2 * * * /bin/bash /var/lib/lavi/backup_job.sh >> /var/log/lavi_backup.log 2>&1") | crontab -
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO] Falha ao registrar o Cron Job.${ENDCOLOR}"
    exit 1
fi
echo -e "${GREEN}[SUCESSO] Cron Job configurado para rodar diariamente às 02:00 AM.${ENDCOLOR}"

echo -e "\n=============================================================================="
echo -e "${GREEN}PROVISIONAMENTO DO SERVIDOR REMOTO CONCLUÍDO COM EXCELÊNCIA!${ENDCOLOR}"
echo -e "=============================================================================="
echo -e "Próximos passos:"
echo -e "1. Clone o repositório do Lavi na VPS (ex: dentro de /app ou pasta do seu usuário)."
echo -e "2. Configure o arquivo de ambiente .env de produção baseado no .env.example."
echo -e "3. Inicie o sistema em produção rodando: ${GREEN}docker compose -f docker-compose.prod.yml up --build -d${ENDCOLOR}"
echo -e "==============================================================================\n"
