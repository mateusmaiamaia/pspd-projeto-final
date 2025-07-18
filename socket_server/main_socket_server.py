import socket
import threading
import struct
import time
import os # Importa a biblioteca para ler variáveis de ambiente

# --- Configurações ---
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000

# MODIFICAÇÃO: Lê o endereço da Engine 1 a partir de uma variável de ambiente.
# Isso torna nosso código flexível para rodar em Docker e Kubernetes.
# Se a variável não existir, usa 'localhost' como padrão.
ENGINE1_HOST = os.environ.get('ENGINE1_HOST', 'localhost')
ENGINE1_PORT = 8080

# (O resto do arquivo continua igual...)
def handle_client(conn, addr):
    print(f"[Servidor Principal] Nova conexão recebida de {addr}")
    try:
        data = conn.recv(1024).decode('utf-8').strip()
        if not data:
            print(f"[Servidor Principal] Cliente {addr} desconectou sem enviar dados.")
            return

        print(f"[Servidor Principal] Recebido de {addr}: '{data}'")
        parts = data.split(',')
        if len(parts) != 2:
            conn.sendall(b"Erro: Formato da requisicao invalido. Use: engine,parametro (ex: engine1,8)")
            return

        engine_choice = parts[0].strip()
        pow_value = int(parts[1].strip())

        if engine_choice == 'engine1':
            print(f"[Servidor Principal] Encaminhando tarefa (POW={pow_value}) para a Engine 1 em '{ENGINE1_HOST}'...")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as engine_socket:
                    engine_socket.connect((ENGINE1_HOST, ENGINE1_PORT))
                    packed_pow = struct.pack('i', pow_value)
                    engine_socket.sendall(packed_pow)
                print(f"[Servidor Principal] Tarefa enviada para a Engine 1 com sucesso.")
                conn.sendall(b"OK: Tarefa submetida para a Engine 1.")
            except Exception as e:
                print(f"[Servidor Principal] ERRO ao conectar ou enviar para a Engine 1: {e}")
                conn.sendall(b"Erro: Nao foi possivel se comunicar com a Engine 1.")
        else:
            conn.sendall(f"Erro: Engine '{engine_choice}' desconhecida ou nao implementada.".encode('utf-8'))
    except Exception as e:
        print(f"[Servidor Principal] Erro ao lidar com o cliente {addr}: {e}")
    finally:
        print(f"[Servidor Principal] Fechando conexao com {addr}")
        conn.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"Servidor principal escutando em {SERVER_HOST}:{SERVER_PORT}")
    while True:
        conn, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()

if __name__ == "__main__":
    start_server()