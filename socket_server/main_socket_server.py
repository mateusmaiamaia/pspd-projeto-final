import os
import socket
import struct
import subprocess
import threading
from flask import Flask, render_template, request, jsonify

# --- Inicialização do Flask ---
app = Flask(__name__)

# --- Configurações das Engines ---
ENGINE1_HOST = os.environ.get('ENGINE1_HOST', 'localhost')
ENGINE1_PORT = 8080

def submit_to_engine1(pow_value):
    """Envia uma tarefa para a Engine 1 (C/MPI) e AGUARDA a resposta."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ENGINE1_HOST, ENGINE1_PORT))
            # Envia o valor de POW
            s.sendall(struct.pack('i', pow_value))
            
            # MODIFICAÇÃO: Espera e recebe a resposta da Engine 1
            # O cálculo pode demorar, então definimos um timeout longo
            s.settimeout(60.0) # Timeout de 60 segundos
            response_from_engine = s.recv(1024).decode('utf-8')
            
        return {"status": "success", "message": response_from_engine}
    except socket.timeout:
        return {"status": "error", "message": "Erro: A Engine 1 demorou muito para responder (timeout)."}
    except Exception as e:
        return {"status": "error", "message": f"Erro ao contatar a Engine 1: {e}"}

def submit_to_engine2(pow_value):
    """Inicia um job da Engine 2 (Spark) em um novo processo."""
    try:
        command = [
            'spark-submit',
            '--driver-memory', '2g',
            'engine2_spark/engine2_spark.py',
            str(pow_value)
        ]
        print(f"Executando comando: {' '.join(command)}")
        # Usamos Popen para não bloquear o servidor web enquanto o Spark executa
        subprocess.Popen(command)
        return {"status": "success", "message": f"Job da Engine 2 com POW={pow_value} submetido. Acompanhe o log do terminal para ver o progresso."}
    except Exception as e:
        return {"status": "error", "message": f"Erro ao iniciar a Engine 2: {e}"}

# --- Rotas da Aplicação Web ---

@app.route('/')
def index():
    """Serve a página HTML principal."""
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_job():
    """Recebe a submissão do formulário web."""
    data = request.get_json()
    engine = data.get('engine')
    pow_val = int(data.get('pow'))
    
    response_data = {}

    if engine == 'engine1':
        response_data = submit_to_engine1(pow_val)
    elif engine == 'engine2':
        response_data = submit_to_engine2(pow_val)
    else:
        response_data = {"status": "error", "message": "Engine desconhecida."}
        
    return jsonify(response_data)

if __name__ == '__main__':
    # Inicia o servidor web Flask
    app.run(host='0.0.0.0', port=5000, debug=True)