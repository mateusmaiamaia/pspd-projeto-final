import time
import sys
import requests
import json
from datetime import datetime
import os
from pyspark.sql import SparkSession

def enviar_metricas_spark(tam, cpus, threads, t_comp):
    """Envia métricas para o Elasticsearch."""
    print("Enviando métricas para o Elasticsearch...")
    url = "http://localhost:9200/pspd-metrics/_doc"
    
    metricas = {
        "engine": "apache_spark",
        "tam": tam,
        "cpus": cpus,
        "threads_per_cpu": threads,
        "time_init": 0,
        "time_comp": t_comp,
        "time_final": 0,
        "time_total": t_comp,
        "@timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    
    try:
        response = requests.post(url, json=metricas, timeout=5)
        response.raise_for_status()
        print("Métricas enviadas com sucesso.")
    except Exception as e:
        print(f"Erro ao enviar métricas: {e}")

def get_neighbors(cell):
    """Gera vizinhos de uma célula."""
    r, c = cell
    return [((r + i, c + j), 1) 
            for i in (-1, 0, 1) 
            for j in (-1, 0, 1) 
            if not (i == 0 and j == 0)]

def run_spark_engine(pow_value):
    tam = 1 << pow_value
    generations = 4 * (tam - 3)
    
    # Configuração robusta do Spark
    spark = SparkSession.builder \
        .appName(f"JogoDaVida_Spark_tam{tam}") \
        .config("spark.driver.memory", "8g") \
        .config("spark.executor.memory", "8g") \
        .config("spark.memory.fraction", "0.8") \
        .config("spark.memory.storageFraction", "0.3") \
        .config("spark.cleaner.periodicGC.interval", "1min") \
        .config("spark.checkpoint.compress", "true") \
        .config("spark.default.parallelism", 16) \
        .getOrCreate()
    
    sc = spark.sparkContext
    sc.setCheckpointDir("/tmp/spark-checkpoints")  # Diretório para checkpointing
    
    print(f"--- Iniciando simulação para tam={tam}, {generations} gerações ---")
    
    # Glider inicial
    initial_glider = [(1, 2), (2, 3), (3, 1), (3, 2), (3, 3)]
    live_cells_rdd = sc.parallelize(initial_glider, 16).cache()

    start_time = time.time()
    
    for gen in range(generations):
        # 1. Calcular vizinhos
        neighbor_counts_rdd = live_cells_rdd.flatMap(get_neighbors) \
                                         .reduceByKey(lambda a, b: a + b) \
                                         .cache()
        
        # 2. Identificar nascimentos
        births = neighbor_counts_rdd.filter(lambda x: x[1] == 3) \
                                  .map(lambda x: x[0]) \
                                  .subtract(live_cells_rdd) \
                                  .cache()
        
        # 3. Identificar sobreviventes
        survivors = neighbor_counts_rdd.filter(lambda x: x[1] in (2, 3)) \
                                     .map(lambda x: x[0]) \
                                     .intersection(live_cells_rdd) \
                                     .cache()
        
        # 4. Combinar resultados
        live_cells_rdd = survivors.union(births).repartition(16).cache()
        
        # Checkpointing periódico para evitar stack overflow
        if gen % 50 == 0:
            live_cells_rdd.checkpoint()
            live_cells_rdd.count()  # Força a materialização do checkpoint
        
        # Limpeza de RDDs temporários
        neighbor_counts_rdd.unpersist()
        births.unpersist()
        survivors.unpersist()
        
        # Progresso
        if (gen + 1) % 100 == 0:
            print(f"Geração {gen + 1}/{generations} concluída")

    # Resultado final
    final_count = live_cells_rdd.count()
    end_time = time.time()
    
    print("\n--- Resultados ---")
    print(f"Células vivas: {final_count} (esperado: 5)")
    print(f"Tempo total: {end_time - start_time:.2f} segundos")
    
    enviar_metricas_spark(tam, sc.defaultParallelism, 1, end_time - start_time)
    spark.stop()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: spark-submit --driver-memory 8G --executor-memory 8G engine2_spark.py <pow>")
        sys.exit(1)
    
    try:
        pow_val = int(sys.argv[1])
        if not (3 <= pow_val <= 12):  # Reduzido o limite máximo para 12 (4096x4096)
            raise ValueError("O valor de 'pow' deve estar entre 3 e 12.")
        run_spark_engine(pow_val)
    except ValueError as e:
        print(f"Erro: {e}")
        sys.exit(1)