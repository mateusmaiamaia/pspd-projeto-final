#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <string.h>
#include <mpi.h>
#include <omp.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <time.h> // MODIFICAÇÃO: Incluído para obter o timestamp
#include <curl/curl.h>

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


// MODIFICAÇÃO: Nova função para enviar dados para o Elasticsearch
void enviar_metricas(int tam, int cpus, int threads, double t_init, double t_comp, double t_fim, double t_total) {
    CURL *curl;
    CURLcode res;

    curl_global_init(CURL_GLOBAL_ALL);
    curl = curl_easy_init();
    if(curl) {
        char post_data[512];
        // Formata os dados em uma string JSON
        sprintf(post_data, "{\"engine\":\"c_mpi_omp\", \"tam\":%d, \"cpus\":%d, \"threads_per_cpu\":%d, \"time_init\":%.7f, \"time_comp\":%.7f, \"time_final\":%.7f, \"time_total\":%.7f, \"@timestamp\":%ld000}",
                tam, cpus, threads, t_init, t_comp, t_fim, t_total, time(NULL));

        struct curl_slist *headers = NULL;
        headers = curl_slist_append(headers, "Content-Type: application/json");

        // URL do Elasticsearch: http://host:porta/nome_do_indice/_doc
        curl_easy_setopt(curl, CURLOPT_URL, "http://elasticsearch:9200/pspd-metrics/_doc");
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, post_data);

        // Executa a requisição HTTP POST
        res = curl_easy_perform(curl);
        if(res != CURLE_OK) {
            fprintf(stderr, "[Rank 0] Erro ao enviar dados para o Elasticsearch: %s\n", curl_easy_strerror(res));
        } else {
            printf("[Rank 0] Métricas enviadas para o Elasticsearch com sucesso.\n");
        }
        
        curl_easy_cleanup(curl);
        curl_slist_free_all(headers);
    }
    curl_global_cleanup();
}


/// Substitua sua função main inteira por esta versão corrigida
int main(int argc, char *argv[]) {
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);

    int server_fd, new_socket;
    struct sockaddr_in address;
    int addrlen = sizeof(address);
    int port = 8080; 

    if (world_rank == 0) {
        if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
            perror("socket failed");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        
        int opt = 1;
        setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt));

        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(port);
        
        if (bind(server_fd, (struct sockaddr *)&address, sizeof(address))<0) {
            perror("bind failed");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        if (listen(server_fd, 3) < 0) {
            perror("listen");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        printf("Engine 1 (MPI+OpenMP) pronta e escutando na porta %d\n", port);
    }

    while (1) {
        int pow = 0;

        if (world_rank == 0) {
            printf("[Rank 0] Aguardando nova conexão...\n");
            if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen))<0) {
                perror("accept");
                continue; 
            }
            read(new_socket, &pow, sizeof(pow));
            printf("[Rank 0] Conexão recebida. Tarefa: POW = %d\n", pow);
        }

        MPI_Bcast(&pow, 1, MPI_INT, 0, MPI_COMM_WORLD);

        if (pow < 0) {
            if(world_rank == 0) close(new_socket);
            break; 
        }
        
        if (pow < POWMIN || pow > POWMAX) {
            if(world_rank == 0) {
                char error_msg[100];
                sprintf(error_msg, "Erro: Tarefa com POW=%d invalida.", pow);
                write(new_socket, error_msg, strlen(error_msg));
                close(new_socket);
                fprintf(stderr, "%s\n", error_msg);
            }
            continue;
        }

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
            int p_rows = tam/world_size; int p_start_row = 1 + p*p_rows; int p_end_row = p_start_row+p_rows-1; if(p == world_size-1) p_end_row = tam;
            recvcounts[p] = (p_end_row-p_start_row+1)*(tam+2);
            displs[p] = ind2d(p_start_row, 0);
        }
        MPI_Gatherv(&final_grid_local[ind2d(start_row,0)], recvcounts[world_rank], MPI_INT, gather_buffer, recvcounts, displs, MPI_INT, 0, MPI_COMM_WORLD);
        free(recvcounts); free(displs);

        if (world_rank == 0) {
            t_end = wall_time();
            const char* result_text = Correto(gather_buffer, tam) ? "CORRETO" : "ERRADO";
            printf("[Rank 0] Resultado da tarefa: %s\n", result_text);
            
            double t_init = t_comp_start - t_start;
            double t_comp = t_comp_end - t_comp_start;
            double t_final = t_end - t_comp_end;
            double t_total = t_end - t_start;

            // CORREÇÃO: Envia as métricas para o Elasticsearch primeiro
            enviar_metricas(tam, world_size, omp_get_max_threads(), t_init, t_comp, t_final, t_total);

            // CORREÇÃO: Em seguida, envia a resposta para o frontend
            char response_str[256];
            sprintf(response_str, "Resultado: %s. Tempo de Computacao: %.4f segundos.", result_text, t_comp);
            write(new_socket, response_str, strlen(response_str));
            printf("[Rank 0] Resposta enviada para o Socket Server.\n");

            free(gather_buffer);
        }
        
        if (world_rank == 0) {
            close(new_socket); // Fecha a conexão com o cliente
        }

        free(tabulIn);
        free(tabulOut);
        free(final_grid_local);
    }
    
    if(world_rank == 0) close(server_fd);

    MPI_Finalize();
    return 0;
}
