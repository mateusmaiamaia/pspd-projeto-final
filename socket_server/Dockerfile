# Usa uma imagem Python oficial e leve como base
FROM python:3.12-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de dependências para o contêiner
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do nosso servidor para o contêiner
COPY socket_server/main_socket_server.py .

# MODIFICAÇÃO AQUI: Copia a pasta de templates para dentro do contêiner
COPY socket_server/templates /app/templates

# Expõe a porta 5000, que o servidor usa
EXPOSE 5000

# Define o comando para executar o servidor quando o contêiner iniciar
CMD ["python3", "-u", "main_socket_server.py"]