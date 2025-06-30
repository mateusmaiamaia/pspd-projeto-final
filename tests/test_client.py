import socket
import struct
import sys

# --- Parâmetros ---
HOST = 'localhost'  # O endereço da máquina onde a engine C está rodando
PORT = 8080         # A porta que a engine C está escutando

if len(sys.argv) < 2:
    print(f"Uso: python3 {sys.argv[0]} <valor_do_pow>")
    sys.exit(1)

POW_TO_SEND = int(sys.argv[1])
# ------------------

# Converte o inteiro para bytes para enviar pela rede
# 'i' significa que estamos empacotando um inteiro C padrão
data_to_send = struct.pack('i', POW_TO_SEND)

try:
    # Cria um socket e se conecta ao servidor
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print(f"Conectando a {HOST}:{PORT}...")
        s.connect((HOST, PORT))
        print("Conectado. Enviando tarefa...")
        # Envia os dados
        s.sendall(data_to_send)
        print(f"Tarefa com POW = {POW_TO_SEND} enviada com sucesso.")
except ConnectionRefusedError:
    print(f"Erro: A conexão foi recusada. A engine C está rodando em {HOST}:{PORT}?")
except Exception as e:
    print(f"Ocorreu um erro: {e}")