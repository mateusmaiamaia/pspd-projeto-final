# Usa uma imagem Python oficial e leve como base
FROM python:3.12-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de dependências para o contêiner
# O 'COPY ../requirements.txt' sobe um nível para encontrar o arquivo na raiz do projeto
COPY ../requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do nosso servidor para o contêiner
COPY socket_server/main_socket_server.py .

# Expõe a porta 5000, que o servidor usa
EXPOSE 5000

# Define o comando para executar o servidor quando o contêiner iniciar
CMD ["python3", "-u", "main_socket_server.py"]