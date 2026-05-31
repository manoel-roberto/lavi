#!/bin/bash

# ==============================================================================
# SCRIPT DE CONFIGURAÇÃO SSH LOCAL - LAVI
# ==============================================================================
# Este script deve rodar na máquina local do desenvolvedor (Linux/macOS).
# Ele automatiza a criação do par de chaves SSH seguro e a configuração do atalho SSH.

# Cores para output informativo no terminal
GREEN="\e[32m"
YELLOW="\e[33m"
RED="\e[31m"
BLUE="\e[34m"
ENDCOLOR="\e[0m"

echo -e "${BLUE}[INFO] Iniciando configuração automatizada do SSH local para a VPS do Lavi...${ENDCOLOR}"

SSH_DIR="$HOME/.ssh"
KEY_FILE="$SSH_DIR/id_lavi_vps"
CONFIG_FILE="$SSH_DIR/config"

# 1. Garante a existência do diretório .ssh com as permissões corretas
if [ ! -d "$SSH_DIR" ]; then
    echo -e "${YELLOW}[AVISO] Pasta $SSH_DIR não encontrada. Criando...${ENDCOLOR}"
    mkdir -p "$SSH_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO] Falha ao criar o diretório $SSH_DIR.${ENDCOLOR}"
        exit 1
    fi
    chmod 700 "$SSH_DIR"
fi

# 2. Gera a chave de segurança RSA de 4096 bits se ela não existir
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}[AVISO] Chave SSH privada do Lavi não encontrada em $KEY_FILE. Gerando novo par RSA de 4096 bits...${ENDCOLOR}"
    ssh-keygen -t rsa -b 4096 -C "manoel.lavi.2026" -f "$KEY_FILE" -N ""
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO] Falha ao gerar o par de chaves SSH com ssh-keygen.${ENDCOLOR}"
        exit 1
    fi
    echo -e "${GREEN}[SUCESSO] Chave SSH gerada com sucesso em: $KEY_FILE${ENDCOLOR}"
else
    echo -e "${GREEN}[INFO] Chave SSH existente detectada em $KEY_FILE. Nenhuma chave foi sobrescrita.${ENDCOLOR}"
fi

# 3. Aplica permissões restritas obrigatórias nas chaves geradas
chmod 600 "$KEY_FILE"
chmod 644 "${KEY_FILE}.pub"
echo -e "${GREEN}[INFO] Permissões aplicadas nas chaves SSH (600 para privada, 644 para pública).${ENDCOLOR}"

# 4. Injeta a configuração do host no config do SSH para facilitar acesso
# Verifica se o arquivo de configuração existe, se não, cria
if [ ! -f "$CONFIG_FILE" ]; then
    touch "$CONFIG_FILE"
    chmod 644 "$CONFIG_FILE"
fi

# Verifica se o bloco de Host para a VPS já está configurado no arquivo config
grep -q "Host lavi-vps" "$CONFIG_FILE"
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[AVISO] Atalho 'lavi-vps' não configurado em $CONFIG_FILE. Adicionando bloco padrão...${ENDCOLOR}"
    
    # Injeta a configuração padrão
    cat << EOF >> "$CONFIG_FILE"

# Configuração da VPS de Produção do Lavi
Host lavi-vps
    HostName <DIGITE_O_IP_DA_SUA_VPS_AQUI>
    User root
    IdentityFile ~/.ssh/id_lavi_vps
    IdentitiesOnly yes
EOF
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO] Falha ao injetar a configuração no arquivo $CONFIG_FILE.${ENDCOLOR}"
        exit 1
    fi
    echo -e "${GREEN}[SUCESSO] Configuração do host 'lavi-vps' adicionada a $CONFIG_FILE.${ENDCOLOR}"
else
    echo -e "${GREEN}[INFO] O host 'lavi-vps' já está configurado no seu arquivo de SSH config. Nenhuma alteração foi feita.${ENDCOLOR}"
fi

chmod 644 "$CONFIG_FILE"

# 5. Imprime a chave pública e instrução de uso
echo -e "\n=============================================================================="
echo -e "${GREEN}CHAVE PÚBLICA GERADA COM SUCESSO! CRIE A VPS COM ELA:${ENDCOLOR}"
echo -e "=============================================================================="
cat "${KEY_FILE}.pub"
echo -e "=============================================================================="
echo -e "${BLUE}INSTRUÇÕES DE USO:${ENDCOLOR}"
echo -e "1. Copie todo o conteúdo da chave pública acima (começando por 'ssh-rsa' e terminando com 'manoel.lavi.2026')."
echo -e "2. Vá para o painel da ${YELLOW}ByteHosting${ENDCOLOR} durante a criação/configuração da sua VPS Ubuntu."
echo -e "3. Adicione/Cole esta chave pública nas configurações de chaves SSH autorizadas."
echo -e "4. Edite seu arquivo local em ${YELLOW}~/.ssh/config${ENDCOLOR} e substitua ${YELLOW}<DIGITE_O_IP_DA_SUA_VPS_AQUI>${ENDCOLOR} pelo IP real recebido."
echo -e "5. Acesse o servidor remotamente de forma rápida rodando apenas: ${GREEN}ssh lavi-vps${ENDCOLOR}"
echo -e "==============================================================================\n"
