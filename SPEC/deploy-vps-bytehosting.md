# CONTEXTO DO PROJETO
Estamos finalizando a infraestrutura e a esteira de deploy do projeto Lavi (IG-OSINT Manager). O ambiente de homologação e testes foi definido: o sistema rodará em um servidor VPS Linux (Ubuntu 22.04/24.04 LTS) de baixo custo na plataforma ByteHosting. 

A arquitetura do sistema é baseada em contêineres Docker, utilizando Docker Compose para orquestração, SQLite com extensão FTS5 para armazenamento indexado de dados textuais e volumes Docker vinculados ao host para persistência real e vitalícia de mídias e sessões de bots.

---

# INSTRUÇÃO DE ATUAÇÃO (SÓCRATES GATE & AG-KIT)
Aja como o agente @[devops-engineer], especialista sênior em infraestrutura de TI, segurança de redes e automação de deploy[cite: 3]. Seu objetivo é criar o ecossistema completo de scripts em Bash e arquivos de configuração necessários para preparar a máquina local do desenvolvedor, provisionar o servidor remoto e orquestrar a aplicação em produção[cite: 3].

Você deve seguir estritamente as decisões arquiteturais validadas:
1. GESTÃO DE SESSÃO ZERO-KNOWLEDGE: Nenhuma senha de bot será salva no banco de dados[cite: 3]. O sistema lerá arquivos de sessão de cookies (`session-*.json`) gerados no login manual inicial[cite: 3].
2. SEGURANÇA RESTRITA DE CHAVES: Chaves privadas SSH devem operar obrigatoriamente com permissão 600[cite: 3].
3. CONCORRÊNCIA SEQUENCIAL: O worker executará as tarefas dos robôs um por vez de forma sequencial (Fila FIFO) para evitar banimento por cruzamento de IP de saída no mesmo container[cite: 3].

---

# ENTREGÁVEIS REQUERIDOS

## 1. SCRIPT DE AUTOMAÇÃO LOCAL (`local_setup_ssh.sh`)
Crie um script em Bash voltado para a máquina local do desenvolvedor (Linux/macOS) que realize o seguinte fluxo automático:
- Verifique se a pasta `~/.ssh` existe; se não, crie-a com permissão 700.
- Verifique se a chave privada para a VPS já existe em `~/.ssh/id_lavi_vps`. Se não existir, gere um par de chaves RSA de 4096 bits com o comentário "manoel.lavi.2026"[cite: 3].
- Imprima na tela de forma clara a chave pública (`id_lavi_vps.pub`) e exiba uma instrução passo a passo orientando o usuário a colá-la no painel da ByteHosting durante a criação da VPS[cite: 3].
- Verifique o arquivo `~/.ssh/config`. Se o bloco `Host lavi-vps` não existir, insira-o automaticamente usando um placeholder ou variável para o IP da VPS, configurando o usuário como `root` e apontando o `IdentityFile` para a chave criada[cite: 3].
- Aplique a permissão mandatória `chmod 600` na chave privada e `chmod 644` na pública e no arquivo config[cite: 3].

## 2. PLAYBOOK DE PROVISIONAMENTO DO SERVIDOR (`server_deploy_setup.sh`)
Escreva um script Bash resiliente e idempotente, projetado para ser executado dentro da VPS Ubuntu da ByteHosting assim que o acesso SSH for estabelecido[cite: 3]. O script deve:
- Executar o update e upgrade dos pacotes do sistema de forma silenciosa (`apt-get update && apt-get upgrade -y`).
- Instalar pacotes essenciais do sistema: `curl`, `git`, `htop`, `ufw`, `iptables`.
- Instalar a versão oficial e estável do Docker Engine e do Docker Compose V2 de acordo com o repositório oficial da Docker[cite: 3].
- Configurar o Firewall Nativo (UFW): liberar a porta SSH configurada, liberar a porta da Web UI do Lavi (ex: 8000) e ativar o firewall.
- Criar a árvore de diretórios persistentes no sistema de arquivos do host da VPS para o mapeamento dos volumes Docker[cite: 3]:
  - `/var/lib/lavi/data` (para o banco `storage.db`)[cite: 3]
  - `/var/lib/lavi/downloads` (para mídias baixadas)[cite: 3]
  - `/var/lib/lavi/sessions` (para os arquivos de cookies dos bots)[cite: 3]
- Garantir permissões de leitura e escrita adequadas para que o processo interno do container manipule essas pastas sem quebras de permissão.

## 3. ORQUESTRAÇÃO DE PRODUÇÃO (`docker-compose.prod.yml`)
Forneça o arquivo YAML de orquestração do Docker Compose ajustado para o ambiente de produção da VPS[cite: 3], estruturado com:
- Definição do serviço principal baseado no Dockerfile local[cite: 3].
- Política de reinicialização configurada como `restart: always`[cite: 3].
- Mapeamento estrito dos volumes criados na VPS para os caminhos internos esperados pela aplicação[cite: 3]:
  - `/var/lib/lavi/data` mapeado para o diretório interno do SQLite[cite: 3].
  - `/var/lib/lavi/downloads` mapeado para a pasta de downloads de mídia[cite: 3].
  - `/var/lib/lavi/sessions` mapeado para o repositório de sessões dos bots[cite: 3].
- Declaração das variáveis de ambiente lidas pelo backend (`DATABASE_PATH`, `DOWNLOAD_DIR`, `SESSION_DIR`) apontando para os escopos internos corretos[cite: 3].
- Configuração de segurança para o Painel Administrativo, lendo as credenciais iniciais (`ADMIN_USERNAME` e `ADMIN_PASSWORD`) a partir de variáveis de ambiente baseadas em um arquivo `.env` local (que deve ser explicitamente adicionado ao `.gitignore`)[cite: 3].

---

# REQUISITOS DE SAÍDA DO AGENTE
Gere os scripts com tratamento de erros robustos, utilizando condicionais de verificação (`if [ $? -ne 0 ]`), logs informativos coloridos para o terminal (`echo -e "\e[32m[INFO]...\e[0m"`) e documentação interna clara em português sobre o comportamento de cada bloco de código[cite: 3].