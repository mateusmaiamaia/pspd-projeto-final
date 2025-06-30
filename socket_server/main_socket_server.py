import socket
import threading
import struct
import time

# --- Configurações do Servidor Principal ---
# Endereço e porta que este servidor vai escutar para receber conexões dos clientes finais
SERVER_HOST = '0.0.0.0'  # Escuta em todas as interfaces de rede
SERVER_PORT = 5000

# --- Configurações para se conectar à Engine 1 (o serviço em C) ---
ENGINE1_HOST = 'localhost'
ENGINE1_PORT = 8080

def handle_client(conn, addr):
    """
    Esta função é executada em uma nova thread para cada cliente que se conecta.
    """
    print(f"[Servidor Principal] Nova conexão recebida de {addr}")
    try:
        # 1. Recebe os dados do cliente final (ex: "engine1,8")
        data = conn.recv(1024).decode('utf-8').strip()
        if not data:
            print(f"[Servidor Principal] Cliente {addr} desconectou sem enviar dados.")
            return

        print(f"[Servidor Principal] Recebido de {addr}: '{data}'")

        # 2. Analisa (parse) a requisição para separar a engine do parâmetro
        parts = data.split(',')
        if len(parts) != 2:
            conn.sendall(b"Erro: Formato da requisicao invalido. Use: engine,parametro (ex: engine1,8)")
            return

        engine_choice = parts[0].strip()
        pow_value = int(parts[1].strip())

        # 3. Decide o que fazer com base na engine escolhida
        if engine_choice == 'engine1':
            # 3a. Se a escolha for a Engine 1, este servidor se torna um *cliente* do serviço C
            print(f"[Servidor Principal] Encaminhando tarefa (POW={pow_value}) para a Engine 1...")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as engine_socket:
                    engine_socket.connect((ENGINE1_HOST, ENGINE1_PORT))
                    
                    # Empacota o inteiro no formato binário que o C espera ('i' para um int C padrão)
                    packed_pow = struct.pack('i', pow_value)
                    
                    engine_socket.sendall(packed_pow)
                
                print(f"[Servidor Principal] Tarefa enviada para a Engine 1 com sucesso.")
                conn.sendall(b"OK: Tarefa submetida para a Engine 1.")

            except Exception as e:
                print(f"[Servidor Principal] ERRO ao conectar ou enviar para a Engine 1: {e}")
                conn.sendall(b"Erro: Nao foi possivel se comunicar com a Engine 1.")

        elif engine_choice == 'engine2':
            # 3b. Lógica para a Engine 2 (Spark) será adicionada aqui no futuro
            print(f"[Servidor Principal] Engine 2 (Spark) selecionada, mas ainda nao implementada.")
            conn.sendall(b"OK: Engine 2 (Spark) ainda nao esta disponivel.")

        else:
            conn.sendall(f"Erro: Engine '{engine_choice}' desconhecida.".encode('utf-8'))

    except Exception as e:
        print(f"[Servidor Principal] Erro ao lidar com o cliente {addr}: {e}")
    finally:
        # 4. Fecha a conexão com o cliente final
        print(f"[Servidor Principal] Fechando conexao com {addr}")
        conn.close()


def start_server():
    """
    Função principal que inicia o servidor e o coloca para escutar por conexões.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite que o endereço seja reutilizado imediatamente
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5) # Escuta por até 5 conexões pendentes
    print(f"Servidor principal escutando em {SERVER_HOST}:{SERVER_PORT}")

    while True:
        # Bloqueia a execução até que uma nova conexão chegue
        conn, addr = server_socket.accept()
        # Cria e inicia uma nova thread para lidar com o cliente recém-conectado
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()

if __name__ == "__main__":
    start_server()