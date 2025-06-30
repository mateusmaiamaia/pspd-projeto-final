# Projeto PSPD - Jogo da Vida em Larga Escala

Este projeto implementa o Jogo da Vida com foco em performance e elasticidade usando MPI, OpenMP, Spark e Kubernetes.

## Como Compilar e Executar
```bash
# Para compilar a Engine 1 (a partir da raiz do projeto):
mpicc -fopenmp -o bin/engine1_servico engine1_mpi_omp/engine1_servico.c

# Para executar os serviços (em terminais separados):
# Terminal 1: Engine 1
export OMP_NUM_THREADS=4 && mpirun -np 2 bin/engine1_servico

# Terminal 2: Socket Server Principal
python3 socket_server/main_socket_server.py
```
