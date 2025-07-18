import time
import sys
# NOVOS IMPORTS para a integração com Elasticsearch
import requests
import json
from datetime import datetime

from pyspark.sql import SparkSession

# NOVA FUNÇÃO para enviar métricas para o Elasticsearch
def enviar_metricas_spark(tam, cpus, threads, t_comp):
    """
    Envia as métricas de performance da simulação para o Elasticsearch.
    """
    print("Enviando métricas para o Elasticsearch...")
    # URL do serviço elasticsearch. Como o script roda fora do docker, usamos localhost.
    url = "http://localhost:9200/pspd-metrics/_doc"
    
    # Cria um dicionário (JSON) com os dados
    metricas = {
        "engine": "apache_spark",
        "tam": tam,
        "cpus": cpus, # Em modo local, Spark usa os núcleos disponíveis
        "threads_per_cpu": threads, # threads não é um conceito direto no Spark, usamos como placeholder
        "time_init": 0, # O tempo de inicialização é medido no spark-submit, não aqui
        "time_comp": t_comp,
        "time_final": 0,
        "time_total": t_comp,
        "@timestamp": datetime.utcnow().isoformat() + 'Z' # Timestamp no formato correto
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(metricas), timeout=5)
        response.raise_for_status() # Lança um erro se a resposta não for bem-sucedida (status 2xx)
        print("Métricas enviadas para o Elasticsearch com sucesso.")
    except Exception as e:
        print(f"Erro ao enviar dados para o Elasticsearch: {e}")

def get_neighbors(cell):
    """
    Para uma célula viva (r, c), gera uma lista de suas 8 coordenadas vizinhas.
    """
    r, c = cell
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0:
                continue
            yield ((r + i, c + j), 1)

def run_spark_engine(pow_value):
    tam = 1 << pow_value
    generations = 4 * (tam - 3)
    
    spark = SparkSession.builder.appName(f"JogoDaVida_Spark_tam{tam}").getOrCreate()
    sc = spark.sparkContext
    
    print(f"--- Iniciando Engine 2 (Spark Corrigido) para tam={tam}, {generations} gerações ---")
    
    initial_glider = [(1, 2), (2, 3), (3, 1), (3, 2), (3, 3)]
    live_cells_rdd = sc.parallelize(initial_glider)

    start_time = time.time()
    
    for gen in range(generations):
        # Lógica de cálculo otimizada
        neighbor_counts_rdd = live_cells_rdd.flatMap(get_neighbors).reduceByKey(lambda a, b: a + b)
        births_rdd = neighbor_counts_rdd.filter(lambda item: item[1] == 3).subtractByKey(live_cells_rdd.map(lambda c: (c, 1)))
        survivors_rdd = live_cells_rdd.map(lambda c: (c, 1)).join(neighbor_counts_rdd).filter(lambda item: item[1][1] in [2, 3])
        live_cells_rdd = survivors_rdd.map(lambda item: item[0]).union(births_rdd.map(lambda item: item[0]))

        # Otimização de cache para algoritmos iterativos
        if (gen + 1) % 50 == 0:
            live_cells_rdd.cache()
            # Uma ação como 'count' força a materialização do cache
            num_cells = live_cells_rdd.count()
            print(f"  Checkpoint da Geração {gen + 1}/{generations}: {num_cells} células vivas.")
    
    final_live_count = live_cells_rdd.count()
    end_time = time.time()
    
    print("\n--- Simulação Concluída ---")
    print(f"Total de células vivas no final: {final_live_count}")
    
    if final_live_count == 5:
        print("Resultado: CORRETO (contagem de células igual a 5)")
    else:
        print(f"Resultado: ERRADO (contagem de células é {final_live_count}, esperado 5)")
        
    computation_time = end_time - start_time
    print(f"Tempo total de computação Spark: {computation_time:.7f} segundos")
    
    # MODIFICAÇÃO: Chamada para a nova função de envio de métricas
    enviar_metricas_spark(tam, sc.defaultParallelism, 1, computation_time)

    spark.stop()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: spark-submit engine2_spark.py <valor_do_pow>")
        sys.exit(1)
    
    try:
        pow_val = int(sys.argv[1])
        if not (3 <= pow_val <= 16):
             raise ValueError("O valor de 'pow' deve estar entre 3 e 16.")
        run_spark_engine(pow_val)
    except ValueError as e:
        print(f"Erro: Parâmetro inválido. {e}")
        sys.exit(1)