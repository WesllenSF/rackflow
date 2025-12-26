# DocRack - Documentação Simples de Racks

Aplicação web simples para documentar racks de rede, equipamentos e conexões físicas. Desenvolvida para rodar localmente ou em servidores Linux (Ubuntu Server), com foco em simplicidade e agilidade.

## Funcionalidades

- **Dashboard**: Visão geral de todos os racks cadastrados.
- **Visualização de Rack**: Layout visual interativo (U por U) dos equipamentos.
- **Gerenciamento de Racks**: Criação e exclusão (com limpeza automática de equipamentos).
- **Gerenciamento de Equipamentos**: Adicionar/Remover equipamentos com altura (U) personalizada.
- **Conexões Físicas**: Documentação de portas e conexões ponto-a-ponto (ex: Switch -> Patch Panel).
- **Autenticação**: Sistema de login seguro para proteger o acesso.
- **Perfil de Usuário**: Alteração de senha e gestão da conta.
- **Tema**: Suporte persistente a modo Claro e Escuro (Dark Mode).

## Credenciais Padrão

Ao iniciar o sistema pela primeira vez, um usuário administrador é criado automaticamente:

- **Usuário:** `admin`
- **Senha:** `admin`

> **Importante:** Recomenda-se alterar a senha imediatamente após o primeiro login acessando o menu "Perfil".

## Instalação no Ubuntu Server

Siga os passos abaixo para instalar e rodar a aplicação em um servidor Ubuntu.

### 1. Pré-requisitos
Instale o Python 3 e o gerenciador de pacotes pip:
```bash
sudo apt update
sudo apt install python3-pip python3-venv git -y
```

### 2. Instalação da Aplicação
Clone o repositório ou copie os arquivos para uma pasta (ex: `/opt/doc_rack`):

```bash
# Exemplo criando a pasta e ajustando permissões (se necessário)
sudo mkdir -p /opt/doc_rack
sudo chown $USER:$USER /opt/doc_rack
cd /opt/doc_rack
# (Copie os arquivos do projeto para cá)
```

### 3. Configuração do Ambiente
Crie um ambiente virtual e instale as dependências:

```bash
# Dentro da pasta /opt/doc_rack
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Rodando a Aplicação
Para testar, você pode rodar diretamente:
```bash
python3 run.py
```
O servidor iniciará na porta **8000**. Acesse: `http://SEU_IP_SERVIDOR:8000`

### 5. Configurando como Serviço (Systemd)
Para que a aplicação inicie automaticamente com o servidor e rode em segundo plano:

1. Edite o arquivo de serviço:
   ```bash
   sudo nano /etc/systemd/system/docrack.service
   ```

2. Cole o conteúdo abaixo (ajuste `User` e `WorkingDirectory` conforme sua instalação):
   ```ini
   [Unit]
   Description=DocRack Web Server
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/opt/doc_rack
   ExecStart=/opt/doc_rack/venv/bin/python run.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   *(Nota: Se o usuário for `root` ou outro, altere o campo `User`)*

3. Ative e inicie o serviço:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable docrack
   sudo systemctl start docrack
   ```

4. Verifique o status:
   ```bash
   sudo systemctl status docrack
   ```

## Estrutura do Projeto

- `app/`: Código fonte da aplicação (Rotas, Modelos, Templates).
- `doc_rack.db`: Banco de dados SQLite (criado automaticamente na primeira execução).
- `requirements.txt`: Lista de dependências Python.
- `run.py`: Script de inicialização do servidor web.
