#!/bin/bash
# Script para coletar dados de performance da Engine 1 para todos os POWs.

LOG_FILE="engine1_collection.log"

# O comando 'tee -a' imprime a mensagem no terminal E a adiciona ao arquivo de log
echo "Iniciando a coleta de dados de performance para a Engine 1..." | tee $LOG_FILE
echo "Os resultados serão salvos em $LOG_FILE" | tee -a $LOG_FILE
date | tee -a $LOG_FILE

# Loop para todos os valores de POW de 3 a 10
for pow in {3..10}
do
  echo "" | tee -a $LOG_FILE
  echo "------------------------------------------" | tee -a $LOG_FILE
  echo ">> Enviando tarefa para POW = $pow" | tee -a $LOG_FILE
  echo "------------------------------------------" | tee -a $LOG_FILE
  
  # Envia a requisição para o Socket Server e salva a resposta no log
  echo "engine1,$pow" | nc localhost 5000 | tee -a $LOG_FILE
  
  # Pausa para o sistema processar a requisição e para não sobrecarregar
  echo "Aguardando 15 segundos..."
  sleep 15
done

echo "" | tee -a $LOG_FILE
echo "✅ Coleta de dados concluída!" | tee -a $LOG_FILE
echo "Verifique seu dashboard no Kibana para ver os resultados." | tee -a $LOG_FILE