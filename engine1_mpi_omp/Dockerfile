# --- Estágio 1: O "Builder" ---
# Usamos uma imagem base do Ubuntu que tem as ferramentas de compilação.
# Damos a este estágio o nome "builder".
FROM ubuntu:22.04 AS builder

# Instala todas as dependências necessárias para COMPILAR nosso código
# - build-essential: Contém o gcc, make, etc.
# - mpich: A implementação do MPI.
# - libmpich-dev: Os arquivos de cabeçalho do MPI para compilação.
# - libcurl4-openssl-dev: Os arquivos de cabeçalho do libcurl para compilação.
RUN apt-get update && \
    apt-get install -y build-essential mpich libmpich-dev libcurl4-openssl-dev

# Define o diretório de trabalho dentro da imagem
WORKDIR /app

# Copia apenas o nosso arquivo de código-fonte C para dentro da imagem
COPY engine1_mpi_omp/engine1_servico.c .

# Executa o comando de compilação dentro do contêiner.
# Note que a saída (-o) é um único arquivo executável.
RUN mpicc -fopenmp -o engine1_servico_exec engine1_servico.c -lcurl


# --- Estágio 2: A Imagem Final ---
# Começamos de uma imagem limpa do Ubuntu para manter a imagem final pequena.
FROM ubuntu:22.04

# Instala APENAS as dependências necessárias para EXECUTAR nosso código.
# Não precisamos mais do compilador ou dos pacotes -dev.
# - libgomp1: Biblioteca de runtime do OpenMP.
RUN apt-get update && \
    apt-get install -y mpich libcurl4 libgomp1 && \
    # Limpa o cache do apt para reduzir o tamanho da imagem
    rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia APENAS o executável compilado do estágio "builder" para a nossa imagem final.
COPY --from=builder /app/engine1_servico_exec .

# Define o comando que será executado quando o contêiner iniciar.
# Ele irá iniciar nosso serviço com 2 processos MPI.
CMD ["mpirun", "-np", "2", "./engine1_servico_exec"]