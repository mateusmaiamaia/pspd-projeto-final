import time
import sys
from pyspark.sql import SparkSession

def get_neighbors(cell):
    r, c = cell
    # Gera as 8 coordenadas vizinhas
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
    
    print(f"--- Iniciando Engine 2 (Spark Otimizado) para tam={tam}, {generations} gerações ---")
    
    initial_glider = [(1, 2), (2, 3), (3, 1), (3, 2), (3, 3)]
    live_cells_rdd = sc.parallelize(initial_glider)

    start_time = time.time()
    
    for gen in range(generations):
        # Lógica de cálculo otimizada
        neighbor_counts_rdd = live_cells_rdd.flatMap(get_neighbors).reduceByKey(lambda a, b: a + b)
        births_rdd = neighbor_counts_rdd.filter(lambda item: item[1] == 3).subtractByKey(live_cells_rdd.map(lambda c: (c, 1)))
        survivors_rdd = live_cells_rdd.map(lambda c: (c, 1)).join(neighbor_counts_rdd).filter(lambda item: item[1][1] in [2, 3])
        live_cells_rdd = survivors_rdd.map(lambda item: item[0]).union(births_rdd.map(lambda item: item[0]))

        # --- OTIMIZAÇÃO ESSENCIAL COM CACHE ---
        # A cada 50 gerações, materializamos o RDD em memória para quebrar a
        # longa cadeia de dependências, liberando memória.
        if (gen + 1) % 50 == 0:
            live_cells_rdd.cache()
            
            # Uma ação como 'count' é necessária para forçar a execução e o cache.
            # Também serve como um ótimo indicador de progresso durante a execução longa.
            num_cells = live_cells_rdd.count()
            print(f"  Checkpoint da Geração {gen + 1}/{generations}: {num_cells} células vivas.")

    # Ação final para forçar a computação e medir o tempo
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