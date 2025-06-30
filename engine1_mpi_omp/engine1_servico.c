#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <string.h>
#include <mpi.h>
#include <omp.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>

#define ind2d(i,j) (i)*(tam+2)+j
#define POWMIN 3
#define POWMAX 10

#define TAG_DOWN 1
#define TAG_UP 2

int world_rank;
int world_size;

double wall_time(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return(tv.tv_sec + tv.tv_usec/1000000.0);
}

void UmaVida(int* tabulIn, int* tabulOut, int tam, int start_row_local, int end_row_local) {
    int i, j, vizviv;
    #pragma omp parallel for private(j, vizviv)
    for (i = start_row_local; i <= end_row_local; i++) {
        for (j = 1; j <= tam; j++) {
            vizviv = tabulIn[ind2d(i-1,j-1)] + tabulIn[ind2d(i-1,j)] + tabulIn[ind2d(i-1,j+1)] +
                     tabulIn[ind2d(i,j-1)] + tabulIn[ind2d(i,j+1)] + tabulIn[ind2d(i+1,j-1)] +
                     tabulIn[ind2d(i+1,j)] + tabulIn[ind2d(i+1,j+1)];
            if (tabulIn[ind2d(i,j)] && vizviv < 2) tabulOut[ind2d(i,j)] = 0;
            else if (tabulIn[ind2d(i,j)] && vizviv > 3) tabulOut[ind2d(i,j)] = 0;
            else if (!tabulIn[ind2d(i,j)] && vizviv == 3) tabulOut[ind2d(i,j)] = 1;
            else tabulOut[ind2d(i,j)] = tabulIn[ind2d(i,j)];
        }
    }
}

void InitTabul(int* tabulIn, int* tabulOut, int tam) {
    int ij;
    for (ij=0; ij<(tam+2)*(tam+2); ij++) {
        tabulIn[ij] = 0;
        tabulOut[ij] = 0;
    }
    if (world_rank == 0) {
        tabulIn[ind2d(1,2)] = 1; tabulIn[ind2d(2,3)] = 1;
        tabulIn[ind2d(3,1)] = 1; tabulIn[ind2d(3,2)] = 1; tabulIn[ind2d(3,3)] = 1;
    }
}

int Correto(int* tabul, int tam) {
    int ij, cnt = 0;
    for (ij=0; ij<(tam+2)*(tam+2); ij++) cnt += tabul[ij];
    return (cnt==5 && tabul[ind2d(tam-2,tam-1)] && tabul[ind2d(tam-1,tam)] && 
            tabul[ind2d(tam,tam-2)] && tabul[ind2d(tam,tam-1)] && tabul[ind2d(tam,tam)]);
}


// NOVO: A função main foi completamente reestruturada
int main(int argc, char *argv[]) {
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);

    int server_fd, new_socket;
    struct sockaddr_in address;
    int addrlen = sizeof(address);
    int port = 8080; // Porta onde a engine vai escutar

    // NOVO: Bloco de configuração do servidor TCP (executado apenas pelo processo 0)
    if (world_rank == 0) {
        // 1. Cria o descritor do socket
        if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
            perror("socket failed");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        
        // 2. Vincula o socket à porta e endereço
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY; // Escuta em qualquer endereço de rede da máquina
        address.sin_port = htons(port);
        
        if (bind(server_fd, (struct sockaddr *)&address, sizeof(address))<0) {
            perror("bind failed");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        // 3. Coloca o socket em modo de escuta por conexões
        if (listen(server_fd, 3) < 0) {
            perror("listen");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        printf("Engine 1 (MPI+OpenMP) pronta e escutando na porta %d\n", port);
    }

    // NOVO: Loop principal do serviço
    while (1) {
        int pow = 0;

        // NOVO: O processo 0 espera por uma conexão, recebe a tarefa e a distribui
        if (world_rank == 0) {
            printf("[Rank 0] Aguardando nova conexão...\n");
            // 4. Aceita uma nova conexão (bloqueante)
            if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen))<0) {
                perror("accept");
                continue; // Em caso de erro, apenas tenta aceitar a próxima
            }
            // 5. Lê os dados (o valor de `pow`) da conexão
            read(new_socket, &pow, sizeof(pow));
            printf("[Rank 0] Conexão recebida. Tarefa: POW = %d\n", pow);
            close(new_socket); // Fecha a conexão do cliente
        }

        // 6. O processo 0 transmite a tarefa (pow) para todos os outros processos MPI
        MPI_Bcast(&pow, 1, MPI_INT, 0, MPI_COMM_WORLD);

        // Se pow for negativo, encerra o serviço
        if (pow < 0) {
            if(world_rank == 0) printf("Sinal de término recebido. Encerrando engine...\n");
            break; 
        }
        
        // Validação básica da tarefa
        if (pow < POWMIN || pow > POWMAX) {
            if(world_rank == 0) fprintf(stderr, "Tarefa com POW=%d inválida.\n", pow);
            continue;
        }

        // --- INÍCIO DA LÓGICA DO JOGO DA VIDA (A MESMA DE ANTES) ---
        int tam = 1 << pow;
        int generations = 4 * (tam - 3);

        int rows_per_proc = tam / world_size;
        int start_row = 1 + world_rank * rows_per_proc;
        int end_row = start_row + rows_per_proc - 1;
        if (world_rank == world_size - 1) end_row = tam;

        int *tabulIn = (int*) malloc((tam+2)*(tam+2)*sizeof(int));
        int *tabulOut = (int*) malloc((tam+2)*(tam+2)*sizeof(int));
        int *final_grid_local = (int*) malloc((tam+2)*(tam+2)*sizeof(int));

        double t_start, t_comp_start, t_comp_end, t_end;

        if(world_rank == 0) t_start = wall_time();
        InitTabul(tabulIn, tabulOut, tam);
        MPI_Bcast(tabulIn, (tam+2)*(tam+2), MPI_INT, 0, MPI_COMM_WORLD);
        
        MPI_Barrier(MPI_COMM_WORLD);
        if(world_rank == 0) t_comp_start = wall_time();

        for (int i=0; i<generations; i++) {
            int* current_in = (i%2 == 0) ? tabulIn : tabulOut;
            int* current_out = (i%2 == 0) ? tabulOut : tabulIn;
            UmaVida(current_in, current_out, tam, start_row, end_row);
            
            MPI_Request reqs[4] = {MPI_REQUEST_NULL, MPI_REQUEST_NULL, MPI_REQUEST_NULL, MPI_REQUEST_NULL};
            MPI_Status statuses[4];
            int req_count = 0;

            if (world_rank > 0) {
                MPI_Isend(&current_out[ind2d(start_row, 0)], tam+2, MPI_INT, world_rank-1, TAG_UP, MPI_COMM_WORLD, &reqs[req_count++]);
                MPI_Irecv(&current_out[ind2d(start_row-1, 0)], tam+2, MPI_INT, world_rank-1, TAG_DOWN, MPI_COMM_WORLD, &reqs[req_count++]);
            }
            if (world_rank < world_size - 1) {
                MPI_Isend(&current_out[ind2d(end_row, 0)], tam+2, MPI_INT, world_rank+1, TAG_DOWN, MPI_COMM_WORLD, &reqs[req_count++]);
                MPI_Irecv(&current_out[ind2d(end_row+1, 0)], tam+2, MPI_INT, world_rank+1, TAG_UP, MPI_COMM_WORLD, &reqs[req_count++]);
            }
            MPI_Waitall(req_count, reqs, statuses);
            MPI_Barrier(MPI_COMM_WORLD);
        }
        
        int* final_ptr = (generations%2 == 0) ? tabulIn : tabulOut;
        memcpy(final_grid_local, final_ptr, (tam+2)*(tam+2)*sizeof(int));
        MPI_Barrier(MPI_COMM_WORLD);

        if(world_rank == 0) t_comp_end = wall_time();
        
        int* gather_buffer = NULL;
        if(world_rank == 0) {
             gather_buffer = (int*) malloc((tam+2)*(tam+2)*sizeof(int));
             memset(gather_buffer, 0, (tam+2)*(tam+2)*sizeof(int));
        }

        int *recvcounts = (int*)malloc(world_size*sizeof(int));
        int *displs = (int*)malloc(world_size*sizeof(int));
        for(int p=0; p<world_size; ++p){
            int p_rows = tam/world_size;
            int p_start_row = 1 + p*p_rows;
            int p_end_row = p_start_row+p_rows-1;
            if(p == world_size-1) p_end_row = tam;
            recvcounts[p] = (p_end_row-p_start_row+1)*(tam+2);
            displs[p] = ind2d(p_start_row, 0);
        }

        MPI_Gatherv(&final_grid_local[ind2d(start_row,0)], recvcounts[world_rank], MPI_INT, 
                    gather_buffer, recvcounts, displs, MPI_INT, 0, MPI_COMM_WORLD);
        
        free(recvcounts); free(displs);

        if (world_rank == 0) {
            t_end = wall_time();
            if (Correto(gather_buffer, tam)) printf("[Rank 0] Resultado da tarefa: CORRETO\n");
            else printf("[Rank 0] Resultado da tarefa: ERRADO\n");
            
            double t_init = t_comp_start - t_start;
            double t_comp = t_comp_end - t_comp_start;
            double t_final = t_end - t_comp_end;
            double t_total = t_end - t_start;

            printf("[Rank 0] Métricas: tam=%d; cpus=%d; threads/cpu=%d; tempos: init=%7.7f, comp=%7.7f, fim=%7.7f, tot=%7.7f \n",
                   tam, world_size, omp_get_max_threads(), t_init, t_comp, t_final, t_total);
            // NO FUTURO: Aqui você enviaria essas métricas para o Elasticsearch em vez de imprimir.
            free(gather_buffer);
        }

        free(tabulIn);
        free(tabulOut);
        free(final_grid_local);
        // --- FIM DA LÓGICA DO JOGO DA VIDA ---
    }
    
    if(world_rank == 0) close(server_fd);

    MPI_Finalize();
    return 0;
}