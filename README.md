# Projeto: Aplicação de Larga Escala com Frameworks Paralelos/Distribuídos

Este projeto, desenvolvido para a disciplina de Programação para Sistemas Paralelos e Distribuídos (PSPD), implementa o "Jogo da Vida" de Conway como uma aplicação de larga escala. O objetivo é construir, implantar e analisar o comportamento de diferentes "motores" de cálculo (engines) sob os requisitos de **performance** e **elasticidade**.

A arquitetura final inclui:
- **Engine 1:** Implementada em C com paralelismo híbrido MPI e OpenMP.
- **Engine 2:** Implementada com Apache Spark (a ser integrada).
- **Socket Server:** Um ponto de entrada de rede que recebe requisições e as delega para a engine correta.
- **Banco de Dados:** Elasticsearch para armazenamento e análise de métricas de performance.
- **Visualização:** Kibana para criar dashboards e gráficos a partir dos dados do Elasticsearch.
- **Orquestração:** Kubernetes para gerenciar todos os serviços como contêineres em um cluster.

## Estrutura do Projeto

```
/
├── 📂 engine1_mpi_omp/      # Código-fonte da Engine 1 (C/MPI/OpenMP)
│   └── 📜 engine1_servico.c
├── 📂 engine2_spark/        # Código-fonte da Engine 2 (PySpark)
│   └── 📜 engine2_spark.py
├── 📂 socket_server/        # Código do servidor principal
│   └── 📜 main_socket_server.py
├── 📂 kubernetes/           # Arquivos de manifesto do Kubernetes (.yaml)
├── 📂 tests/                # Scripts para teste
│   └── 📜 test_client.py
├── 📂 archive/              # Versões antigas do código
├── 📂 bin/                  # Executáveis compilados
│   └── ⚙️ engine1_servico
├── 📄 docker-compose.yml     # Arquivo para iniciar o Elasticsearch e Kibana localmente
└── 📄 README.md              # Este arquivo
```

## Pré-requisitos

Antes de começar, garanta que você tem as seguintes ferramentas instaladas:
- `git`
- `build-essential` (contém `gcc`, `make`, etc.)
- `mpich` e `libmpich-dev`
- `libcurl4-openssl-dev`
- `python3`, `python3-pip`, `python3.12-venv`
- `docker` e `docker-compose-plugin` (`docker compose`)

## Guia de Instalação e Configuração

1.  **Clone o Repositório:**
    ```bash
    git clone [https://github.com/mateusmaiamaia/pspd-projeto-final.git](https://github.com/mateusmaiamaia/pspd-projeto-final.git)
    cd pspd-projeto-final
    ```

2.  **Configure o Ambiente Python:**
    Crie e ative um ambiente virtual.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    *Para instalar as dependências Python necessárias, execute:*
    ```bash
    # (Este passo só é necessário se houver um arquivo requirements.txt)
    # pip install -r requirements.txt 
    ```

3.  **Compile a Engine 1:**
    Use o `mpicc` para compilar o código C, linkando a biblioteca `curl`.
    ```bash
    mpicc -fopenmp -o bin/engine1_servico engine1_mpi_omp/engine1_servico.c -lcurl
    ```

## Como Executar a Aplicação (Estado Atual, sem Spark)

Para rodar o sistema completo, você precisará de **3 terminais abertos** na pasta raiz do projeto.

**➡️ Terminal 1: Iniciar o Banco de Dados**
```bash
docker compose up -d
```
*Isso iniciará o Elasticsearch e o Kibana em segundo plano. Pode levar um minuto.*
*Acesse o Kibana no navegador em: `http://localhost:5601`*

**➡️ Terminal 2: Iniciar a Engine 1 (Serviço C)**
```bash
# Define o número de threads para o OpenMP
export OMP_NUM_THREADS=4

# Inicia o serviço MPI, que ficará escutando na porta 8080
mpirun -np 2 bin/engine1_servico
```
*Este terminal ficará ativo, mostrando os logs da Engine 1.*

**➡️ Terminal 3: Iniciar o Socket Server Principal (Serviço Python)**
```bash
# Ative o ambiente virtual primeiro!
source .venv/bin/activate

# Inicia o servidor principal, que ficará escutando na porta 5000
python3 socket_server/main_socket_server.py
```
*Este terminal também ficará ativo, mostrando os logs do servidor principal.*

## Como Testar

Com os 3 serviços rodando, abra um **quarto terminal** para simular um cliente.

Envie uma requisição para a Engine 1 para calcular o Jogo da Vida para `pow=8`:
```bash
echo "engine1,8" | nc localhost 5000
```
Você verá os logs aparecendo nos terminais da Engine 1 e do Socket Server, e uma nova entrada de dados aparecerá no seu Elasticsearch, visível pelo Kibana.