#include "gestor.h"
#include <cstring>
#include <fstream>
#include <iostream>

char ruta[100] = "/home/ubuntu20/5semestre-2025A/nnnlllpppp222/compilador";
char NArchivo[100] = "";
char nombreConsulta[100] = "";
char contenido[1000] = "";

char analisis[100][100]; 
int tamano = 0;

bool usarJoin = false;
char tabla_join[MAX_LEN] = "";
char columnas_registro_join[MAX_COLS][MAX_LEN];
char T_Datos_join[MAX_COLS][MAX_LEN];
int num_columnas_registro_join = 0;

char condicion_join_col1[MAX_LEN] = "";
char condicion_join_col2[MAX_LEN] = "";
char condicion_join_op[MAX_LEN] = "";
bool usar_condicion_join = false;

// Streams
std::ifstream archivoEntrada;
std::ofstream archivoSalida;
std::fstream archivoRelaciones;

void registrarConsulta(const char consulta[200]) {
    strncpy(contenido, consulta, sizeof(contenido) - 1);
    contenido[sizeof(contenido) - 1] = '\0';
}

const char* obtenerNombreArchivo()  {
    return NArchivo;
}

const char* obtenerNombreConsulta()  {
    return nombreConsulta;
}

const char* obtenerRutaBase()  {
    return ruta;
}

std::ifstream& obtenerArchivoEntrada() {
    return archivoEntrada;
}

std::ofstream& obtenerArchivoSalida() {
    return archivoSalida;
}

std::fstream& obtenerArchivoRelaciones() {
    return archivoRelaciones;
}

void establecerNombreArchivo(const char nombre[100]) {
    strncpy(NArchivo, nombre, sizeof(NArchivo) - 1);
    NArchivo[sizeof(NArchivo) - 1] = '\0';
}

void establecerNombreConsulta(const char nombre[100]) {
    strncpy(nombreConsulta, nombre, sizeof(nombreConsulta) - 1);
    nombreConsulta[sizeof(nombreConsulta) - 1] = '\0';
}

void establecerRutaBase(const char nuevaRuta[100]) {
    strncpy(ruta, nuevaRuta, sizeof(ruta) - 1);
    ruta[sizeof(ruta) - 1] = '\0';
}

void establecerTamano(int nuevoTamano) {
    tamano = nuevoTamano;
}

int obtenerTamano()  {
    return tamano;
}

void establecerAnalisis(char (&nuevoAnalisis)[100][100]) {
    memcpy(analisis, nuevoAnalisis, sizeof(analisis));
}

typedef char AnalisisArray[100];
AnalisisArray* obtenerAnalisis() {
    return analisis;
}

const char* ARCHIVO_CONSULTA_ENTRADA = "consulta_para_gestor.txt";

void leerEntrada() {
    std::cout << "Intentando leer consulta del archivo: " << ARCHIVO_CONSULTA_ENTRADA << std::endl;
    std::ifstream archivoConsulta(ARCHIVO_CONSULTA_ENTRADA);

    if (archivoConsulta.is_open()) {
        std::string linea;
        std::getline(archivoConsulta, linea); // Lee la primera (y única) línea del archivo

        if (!linea.empty()) {
            // Copia la línea leída al buffer 'contenido' global
            strncpy(contenido, linea.c_str(), sizeof(contenido) - 1);
            contenido[sizeof(contenido) - 1] = '\0'; // Asegura la terminación nula
            std::cout << "Consulta leída del archivo: \"" << contenido << "\"" << std::endl;
            registrarConsulta(contenido); // Registra la consulta en el sistema del gestor
        } else {
            std::cerr << "El archivo '" << ARCHIVO_CONSULTA_ENTRADA << "' está vacío." << std::endl;
            contenido[0] = '\0'; // Limpiar el contenido si el archivo está vacío
        }
        archivoConsulta.close();
    } else {
        std::cerr << "Error: No se pudo abrir el archivo '" << ARCHIVO_CONSULTA_ENTRADA << "'." << std::endl;
        std::cerr << "Asegúrate de que 'compilador.py' lo haya generado y esté en el mismo directorio." << std::endl;
        contenido[0] = '\0'; // Limpiar el contenido en caso de error
    }
}

char columnas_seleccionadas[MAX_COLS][MAX_LEN];
char columnas_registro[MAX_COLS][MAX_LEN];
char condiciones_col[MAX_COLS][MAX_LEN];
char condiciones_val[MAX_COLS][MAX_LEN];
char condiciones_op[MAX_COLS][MAX_LEN];
char T_Datos[MAX_COLS][MAX_LEN];

int num_columnas_seleccionadas = 0;
int num_columnas_registro = 0;
int numCondiciones = 0;
int indices[MAX_COLS];

bool usarCondiciones = false;
bool error_columna = false;

bool esOperadorValido(const char* op) {
    const char* operadores_validos[] = { "=", "<", ">", "<=", ">=", "!=", "<>" };
    for (int i = 0; i < 7; i++) {
        if (strcmp(op, operadores_validos[i]) == 0) {
            return true;
        }
    }
    return false;
}

int convertirAEntero(char str[]) {
    int num = 0, signo = 1, i = 0;
    if (str[0] == '-') {
        signo = -1;
        i = 1;
    }
    for (; i < strlen(str); i++) {
        num = num * 10 + (str[i] - '0');
    }
    return num * signo;
}

bool esEntero(const char* palabra) {
    int i = 0;
    if (palabra[0] == '-' || palabra[0] == '+') i++;
    if (palabra[i] == '\0') return false;
    for (; palabra[i] != '\0'; i++) {
        if (!isdigit(palabra[i])) return false;
    }
    return true;
}

bool esValorValido(const char* val) {
    int len = strlen(val);
    if (len >= 2 && val[0] == '\'' && val[len - 1] == '\'') {
        return true;
    }
    return esEntero(val) || esFlotante(val);
}


bool esFlotante(const char* palabra) {
    int i = 0;
    bool puntoEncontrado = false;

    if (palabra[0] == '-' || palabra[0] == '+') i++;
    if (palabra[i] == '\0') return false;

    for (; palabra[i] != '\0'; i++) {
        if (palabra[i] == '.') {
            if (puntoEncontrado) return false;
            puntoEncontrado = true;
        } else if (!isdigit(palabra[i])) {
            return false;
        }
    }
    return true;
}

int validarTamano() {
    if (contenido[0] == '\0') {
        std::cout << "La consulta está vacía.\n";
        return 1;
    }

    int palabras = 0;
    bool enPalabra = false;

    for (int i = 0; contenido[i] != '\0'; i++) {
        if (contenido[i] != ' ' && !enPalabra) {
            enPalabra = true;
            palabras++;
        } else if (contenido[i] == ' ') {
            enPalabra = false;
        }
    }

    establecerTamano(palabras);

    if (palabras > MAX_ANALISIS) {
        std::cout << "La consulta excede el tamaño máximo permitido.\n";
        return 1;
    }

    return palabras;
}

void procesarConsulta() {
    char palabra[MAX_LEN] = "";
    char analisis_local[MAX_ANALISIS][MAX_LEN] = {0};
    int analisis_index = 0;
    int palabra_len = 0;

    for (int j = 0; contenido[j] != '\0'; j++) {
        if (contenido[j] != ' ') {
            if (palabra_len < MAX_LEN - 1) {
                palabra[palabra_len++] = contenido[j];
                palabra[palabra_len] = '\0';
            }
        } else {
            if (palabra_len > 0) {
                strcpy(analisis_local[analisis_index++], palabra);
                palabra_len = 0;
                palabra[0] = '\0';
            }
        }
    }

    if (palabra_len > 0) {
        strcpy(analisis_local[analisis_index++], palabra);
    }

    establecerAnalisis(analisis_local);  // Copia interna asumida
    establecerTamano(analisis_index);

    for (int j = 0; j < analisis_index; j++) {
        if (strcmp(analisis_local[j], "|") == 0) {
            if (j + 1 < analisis_index) {
                establecerNombreConsulta(analisis_local[j + 1]);
            }
            break;
        }
    }
}

void analizarCondiciones() {
    usarCondiciones = false;
    numCondiciones = 0;

    char (*analisis_local)[MAX_LEN] = obtenerAnalisis();
    int tam = obtenerTamano();

    for (int i = 0; i < tam; i++) {
        if (strcmp(analisis_local[i], "WHERE") == 0) {
            usarCondiciones = true;
            i++; // Avanzar al primer token luego de "WHERE"

            while (i + 2 < tam && numCondiciones < MAX_COLS) {
                char* col = analisis_local[i++];
                char* op = analisis_local[i++];
                char* val = analisis_local[i++];

                if (!esOperadorValido(op)) {
                    std::cout << "Operador inválido: " << op << std::endl;
                    error_columna = true;
                    break;
                }
                if (!esValorValido(val)) {
                    std::cout << "Valor inválido: " << val << std::endl;
                    error_columna = true;
                    break;
                }

                strcpy(condiciones_col[numCondiciones], col);
                strcpy(condiciones_op[numCondiciones], op);
                strcpy(condiciones_val[numCondiciones], val);
                numCondiciones++;

                if (i < tam && strcmp(analisis_local[i], "&") == 0) {
                    i++; // Saltar el &
                } else {
                    break;
                }
            }
            break;
        }
    }
}

void analizarComandos() {
    num_columnas_seleccionadas = 0;
    // Resetear variables de JOIN
    usarJoin = false;
    strcpy(tabla_join, "");
    num_columnas_registro_join = 0;
    usar_condicion_join = false;
    strcpy(condicion_join_col1, "");
    strcpy(condicion_join_col2, "");
    strcpy(condicion_join_op, "");


    int i = 0;
    while (i < tamano) {
        if (strcmp(analisis[i], "SELECT") == 0) {
            i++;
            if (strcmp(analisis[i], "*") == 0) {
                // Si es SELECT *, se procesará en seleccionar()
                num_columnas_seleccionadas = -1; // Indicador de todas las columnas
                i++;
            } else {
                while (i < tamano && strcmp(analisis[i], "FROM") != 0 && strcmp(analisis[i], "JOIN") != 0 && strcmp(analisis[i], "|") != 0) {
                    if (num_columnas_seleccionadas < MAX_COLS) {
                        strncpy(columnas_seleccionadas[num_columnas_seleccionadas], analisis[i], MAX_LEN - 1);
                        columnas_seleccionadas[num_columnas_seleccionadas][MAX_LEN - 1] = '\0';
                        num_columnas_seleccionadas++;
                    } else {
                        std::cerr << "Advertencia: Demasiadas columnas seleccionadas, se truncará.\n";
                        break;
                    }
                    i++;
                }
            }
        } else if (strcmp(analisis[i], "FROM") == 0) {
            i++;
            if (i < tamano && strcmp(analisis[i], "WHERE") != 0 && strcmp(analisis[i], "JOIN") != 0 && strcmp(analisis[i], "|") != 0) {
                strncpy(NArchivo, analisis[i], sizeof(NArchivo) - 1);
                NArchivo[sizeof(NArchivo) - 1] = '\0';
                i++;
            }
        } else if (strcmp(analisis[i], "JOIN") == 0) { // <--- Nuevo manejo para JOIN
            usarJoin = true;
            i++; // Saltar "join"
            // El formato es: SELECT ... FROM tabla1 JOIN tabla2 ON tabla1.col = tabla2.col
            // O tu formato: SELECT ... FROM tabla1 JOIN col1 col2 FROM tabla2 WHERE ...
            // Para simplificar, asumiremos: SELECT ... FROM tabla1 JOIN tabla2 ON col_tabla1 = col_tabla2
            // O un JOIN simple por tablas, y la condición de unión está en el WHERE.

            // Para tu formato propuesto (select ... from clientes join id dept from empleados WHERE ...):
            // Esto es más como un SELECT DE COLUMNAS ESPECÍFICAS DE LA SEGUNDA TABLA en el JOIN.
            // Es menos común que un JOIN clásico "ON", pero lo implementaremos como tal.
            // Esto significa que las columnas 'id' y 'dept' en tu ejemplo no son la condición de JOIN,
            // sino columnas adicionales a seleccionar de la tabla de la derecha.

            // Si el siguiente token es una columna, asumimos que es el inicio de la selección de columnas para el JOIN.
            // Esto es diferente de un JOIN ON.
            // Para tu ejemplo: "join id dept from empleados"
            // Tendremos que analizar las columnas 'id' y 'dept' para la tabla de la derecha.

            // Si el siguiente token es "FROM", entonces la palabra anterior fue el nombre de la tabla
            // Si no, asumimos que son columnas a seleccionar de la tabla derecha.
            // Vamos a simplificar y esperar: JOIN <nombre_tabla_derecha> [ON <condicion_join>]
            // Si el "ON" no está, asumimos que la condición de JOIN vendrá del WHERE (si la hay y la podemos interpretar)

            // Simplificación inicial: esperar 'JOIN <nombre_tabla>'
            if (i < tamano && strcmp(analisis[i], "ON") != 0 && strcmp(analisis[i], "WHERE") != 0 && strcmp(analisis[i], "|") != 0) {
                strncpy(tabla_join, analisis[i], sizeof(tabla_join) - 1);
                tabla_join[sizeof(tabla_join) - 1] = '\0';
                i++;
            }
            // Después del nombre de la tabla de JOIN, podría venir un 'ON'
            if (i < tamano && strcmp(analisis[i], "ON") == 0) {
                usar_condicion_join = true;
                i++; // Saltar "on"
                if (i + 2 < tamano) { // Esperar col1 op col2
                    strncpy(condicion_join_col1, analisis[i], sizeof(condicion_join_col1) - 1);
                    condicion_join_col1[sizeof(condicion_join_col1) - 1] = '\0';
                    i++;
                    strncpy(condicion_join_op, analisis[i], sizeof(condicion_join_op) - 1);
                    condicion_join_op[sizeof(condicion_join_op) - 1] = '\0';
                    i++;
                    strncpy(condicion_join_col2, analisis[i], sizeof(condicion_join_col2) - 1);
                    condicion_join_col2[sizeof(condicion_join_col2) - 1] = '\0';
                    i++;
                } else {
                    std::cerr << "Error de sintaxis en la condición ON del JOIN.\n";
                    usar_condicion_join = false; // Desactivar si la sintaxis es incorrecta
                }
            }


        } else if (strcmp(analisis[i], "WHERE") == 0) {
            usarCondiciones = true;
            i++;
        } else if (strcmp(analisis[i], "|") == 0) {
            i++;
            if (i < tamano) {
                strncpy(nombreConsulta, analisis[i], sizeof(nombreConsulta) - 1);
                nombreConsulta[sizeof(nombreConsulta) - 1] = '\0';
                i++;
            }
        }
        else {
            i++; // Mover al siguiente token si no es un comando reconocido en esta fase
        }
    }
}

void imprimirArbolSemantico() {
    std::cout << "\n--- Árbol Semántico de la Consulta ---\n";
    std::cout << "Consulta Original: \"" << contenido << "\"\n\n";

    std::cout << "Comando Principal: SELECT\n";

    // Columnas Seleccionadas
    std::cout << "  Columnas Seleccionadas:\n";
    if (num_columnas_seleccionadas > 0) {
        for (int i = 0; i < num_columnas_seleccionadas; ++i) {
            std::cout << "    - " << columnas_seleccionadas[i] << "\n";
        }
    } else {
        std::cout << "    (Ninguna o SELECT *)\n"; // Asumiendo que '*' se manejaría internamente
    }

    // Tabla Principal
    std::cout << "\n  Desde Tabla: " << NArchivo << "\n";

    // JOIN
    if (usarJoin) {
        std::cout << "\n  Operación JOIN:\n";
        std::cout << "    Tipo: JOIN\n";
        std::cout << "    Tabla Unida: " << tabla_join << "\n";
        if (usar_condicion_join) {
            std::cout << "    Condición ON: " << condicion_join_col1 << " " << condicion_join_op << " " << condicion_join_col2 << "\n";
        } else {
            std::cout << "    Condición ON: (No especificada o implícita)\n";
        }
    }

    // Condiciones WHERE
    if (usarCondiciones) {
        std::cout << "\n  Condiciones WHERE:\n";
        for (int i = 0; i < numCondiciones; ++i) {
            std::cout << "    - Columna: " << condiciones_col[i]
                      << ", Operador: " << condiciones_op[i]
                      << ", Valor: " << condiciones_val[i] << "\n";
        }
    } else {
        std::cout << "\n  Condiciones WHERE: (Ninguna)\n";
    }

    std::cout << "\n--- Fin del Árbol Semántico ---\n";
}


void validarArchivo() {
    char ruta_entrada[200];
    // Construye la ruta del archivo de entrada
    snprintf(ruta_entrada, sizeof(ruta_entrada), "%s/tablas/%s.txt", obtenerRutaBase(), obtenerNombreArchivo());

    // Abre el archivo de entrada
    obtenerArchivoEntrada().open(ruta_entrada);
    if (!obtenerArchivoEntrada().is_open()) {
        std::cout << "No Disponible --> " << obtenerNombreArchivo() << ".txt" << std::endl;
        return;
    }

    // Si el nombre de la consulta está vacío, lo generamos automáticamente
    if (strlen(obtenerNombreConsulta()) == 0) {
        char nombre_generado[100];
        snprintf(nombre_generado, sizeof(nombre_generado), "Consulta_%s", obtenerNombreArchivo());
        establecerNombreConsulta(nombre_generado);
    }

    char ruta_salida[200];
    // Construye la ruta del archivo de salida basado en el nombre de la consulta
    snprintf(ruta_salida, sizeof(ruta_salida), "%s/%s.txt", obtenerRutaBase(), obtenerNombreConsulta());

    // Abre el archivo de salida
    obtenerArchivoSalida().open(ruta_salida);
    if (!obtenerArchivoSalida().is_open()) {
        std::cout << "Error al crear o abrir el archivo de salida.\n";
        obtenerArchivoEntrada().close(); // Cierra el archivo de entrada abierto previamente
        return;
    }

    std::cout << "Archivo creado con éxito.\n";
}

// Helper function para cargar el esquema de una tabla
bool cargarEsquemaTabla(const char* nombre_tabla, char columnas[][MAX_LEN], char tipos[][MAX_LEN], int& num_cols) {
    std::ifstream archivo_rel_lectura;
    char ruta_relaciones[200];
    snprintf(ruta_relaciones, sizeof(ruta_relaciones), "%s/relaciones_tablas.txt", obtenerRutaBase());
    archivo_rel_lectura.open(ruta_relaciones);

    if (!archivo_rel_lectura.is_open()) {
        std::cerr << "Error: No se pudo abrir el archivo de relaciones para cargar esquema de '" << nombre_tabla << "'.\n";
        return false;
    }

    char linea[500];
    bool tabla_encontrada = false;
    while (archivo_rel_lectura.getline(linea, sizeof(linea))) {
        char temp_linea[500];
        strncpy(temp_linea, linea, sizeof(temp_linea) - 1);
        temp_linea[sizeof(temp_linea) - 1] = '\0';

        char* saveptr = nullptr;
        char* token = mi_strtok(temp_linea, "#", &saveptr);
        if (token != nullptr && strcmp(token, nombre_tabla) == 0) {
            tabla_encontrada = true;
            num_cols = 0;
            token = mi_strtok(nullptr, "#", &saveptr); // Saltar el nombre de la tabla
            while (token != nullptr && num_cols < MAX_COLS) {
                strncpy(columnas[num_cols], token, MAX_LEN - 1);
                columnas[num_cols][MAX_LEN - 1] = '\0';

                token = mi_strtok(nullptr, "#", &saveptr); // Obtener tipo de dato
                if (token != nullptr) {
                    strncpy(tipos[num_cols], token, MAX_LEN - 1);
                    tipos[num_cols][MAX_LEN - 1] = '\0';
                } else {
                    std::cerr << "Error: Esquema incompleto para columna " << columnas[num_cols] << " en " << nombre_tabla << ".\n";
                    archivo_rel_lectura.close();
                    return false;
                }
                num_cols++;
                token = mi_strtok(nullptr, "#", &saveptr);
            }
            break; // Tabla encontrada y procesada
        }
    }
    archivo_rel_lectura.close();
    if (!tabla_encontrada) {
        std::cerr << "Error: La tabla '" << nombre_tabla << "' no se encontró en relaciones_tablas.txt\n";
        return false;
    }
    return true;
}


void seleccionar() {
    error_columna = false;
    num_columnas_registro = 0; // Reset para la tabla principal/izquierda

    // Cargar esquema de la tabla principal (izquierda)
    if (!cargarEsquemaTabla(NArchivo, columnas_registro, T_Datos, num_columnas_registro)) {
        error_columna = true; // Si no se encuentra la tabla principal
        return;
    }

    if (usarJoin) {
        // Cargar esquema de la tabla de JOIN (derecha)
        if (!cargarEsquemaTabla(tabla_join, columnas_registro_join, T_Datos_join, num_columnas_registro_join)) {
            error_columna = true; // Si no se encuentra la tabla de JOIN
            return;
        }

        // Si es SELECT *, combinar todas las columnas de ambas tablas
        if (num_columnas_seleccionadas == -1) { // SELECT *
            num_columnas_seleccionadas = 0;
            // Añadir columnas de la tabla izquierda
            for (int i = 0; i < num_columnas_registro; ++i) {
                if (num_columnas_seleccionadas < MAX_COLS) {
                    snprintf(columnas_seleccionadas[num_columnas_seleccionadas], MAX_LEN, "%s.%s", NArchivo, columnas_registro[i]);
                    // T_Datos y indices se rellenarán dinámicamente en ingresar
                    indices[num_columnas_seleccionadas] = i; // Mapea a columna de tabla izquierda
                    num_columnas_seleccionadas++;
                }
            }
            // Añadir columnas de la tabla derecha
            for (int i = 0; i < num_columnas_registro_join; ++i) {
                if (num_columnas_seleccionadas < MAX_COLS) {
                    snprintf(columnas_seleccionadas[num_columnas_seleccionadas], MAX_LEN, "%s.%s", tabla_join, columnas_registro_join[i]);
                    // T_Datos y indices se rellenarán dinámicamente en ingresar
                    indices[num_columnas_seleccionadas] = i + num_columnas_registro; // Mapea a columna de tabla derecha (offset)
                                                                                       // IMPORTANTE: Este offset es solo para distinguir las columnas,
                                                                                       // los tipos reales se obtendrán de T_Datos_join en 'ingresar'.
                                                                                       // Esto es un parche, se necesitará un mejor manejo de índices combinados.
                    num_columnas_seleccionadas++;
                }
            }
        } else {
            // Si hay columnas específicas seleccionadas, validar que existan en ALGUNA de las tablas
            char temp_columnas_seleccionadas[MAX_COLS][MAX_LEN];
            int temp_num_cols_sel = 0;

            for (int i = 0; i < num_columnas_seleccionadas; ++i) {
                bool encontrada = false;
                // Buscar en la tabla izquierda
                for (int j = 0; j < num_columnas_registro; ++j) {
                    if (strcmp(columnas_seleccionadas[i], columnas_registro[j]) == 0) {
                        snprintf(temp_columnas_seleccionadas[temp_num_cols_sel], MAX_LEN, "%s.%s", NArchivo, columnas_seleccionadas[i]);
                        indices[temp_num_cols_sel] = j; // Indice de la tabla izquierda
                        temp_num_cols_sel++;
                        encontrada = true;
                        break;
                    }
                }
                // Si no se encontró en la tabla izquierda, buscar en la tabla derecha
                if (!encontrada) {
                    for (int j = 0; j < num_columnas_registro_join; ++j) {
                        if (strcmp(columnas_seleccionadas[i], columnas_registro_join[j]) == 0) {
                            snprintf(temp_columnas_seleccionadas[temp_num_cols_sel], MAX_LEN, "%s.%s", tabla_join, columnas_seleccionadas[i]);
                            indices[temp_num_cols_sel] = j + num_columnas_registro; // Indice de la tabla derecha (con offset para distinguir)
                            temp_num_cols_sel++;
                            encontrada = true;
                            break;
                        }
                    }
                }
                if (!encontrada) {
                    std::cerr << "Error: Columna '" << columnas_seleccionadas[i] << "' no encontrada en ninguna de las tablas.\n";
                    error_columna = true;
                    return;
                }
            }
            // Copiar las columnas seleccionadas con prefijo de tabla
            num_columnas_seleccionadas = temp_num_cols_sel;
            for(int i = 0; i < num_columnas_seleccionadas; ++i) {
                strncpy(columnas_seleccionadas[i], temp_columnas_seleccionadas[i], MAX_LEN - 1);
                columnas_seleccionadas[i][MAX_LEN - 1] = '\0';
            }
        }
    } else { // No hay JOIN, lógica existente
        // Validar columnas seleccionadas contra la tabla principal
        if (num_columnas_seleccionadas == -1) { // SELECT *
            num_columnas_seleccionadas = num_columnas_registro;
            for (int i = 0; i < num_columnas_registro; ++i) {
                strncpy(columnas_seleccionadas[i], columnas_registro[i], MAX_LEN - 1);
                columnas_seleccionadas[i][MAX_LEN - 1] = '\0';
                indices[i] = i;
            }
        } else {
            char temp_cols_sel[MAX_COLS][MAX_LEN]; // Para almacenar las columnas validadas
            int temp_num_cols_sel = 0;

            for (int i = 0; i < num_columnas_seleccionadas; ++i) {
                bool encontrada = false;
                for (int j = 0; j < num_columnas_registro; ++j) {
                    if (strcmp(columnas_seleccionadas[i], columnas_registro[j]) == 0) {
                        strncpy(temp_cols_sel[temp_num_cols_sel], columnas_seleccionadas[i], MAX_LEN - 1);
                        temp_cols_sel[temp_num_cols_sel][MAX_LEN-1] = '\0';
                        indices[temp_num_cols_sel] = j;
                        temp_num_cols_sel++;
                        encontrada = true;
                        break;
                    }
                }
                if (!encontrada) {
                    std::cerr << "Error: Columna '" << columnas_seleccionadas[i] << "' no encontrada en la tabla '" << NArchivo << "'.\n";
                    error_columna = true;
                    return;
                }
            }
            num_columnas_seleccionadas = temp_num_cols_sel;
            for(int i = 0; i < num_columnas_seleccionadas; ++i) {
                strncpy(columnas_seleccionadas[i], temp_cols_sel[i], MAX_LEN - 1);
                columnas_seleccionadas[i][MAX_LEN - 1] = '\0';
            }
        }
    }

    // Validación de la condición de JOIN (si existe)
    if (usar_condicion_join) {
        bool col1_found = false;
        bool col2_found = false;
        char tipo_col1[MAX_LEN] = "";
        char tipo_col2[MAX_LEN] = "";

        // Buscar col1 en tabla izquierda
        for (int i = 0; i < num_columnas_registro; ++i) {
            if (strcmp(condicion_join_col1, columnas_registro[i]) == 0) {
                strcpy(tipo_col1, T_Datos[i]);
                col1_found = true;
                break;
            }
        }
        // Buscar col1 en tabla derecha (si el nombre es calificado, ej. tabla.col)
        if (!col1_found && strchr(condicion_join_col1, '.') != NULL) {
             char temp_col_name[MAX_LEN];
             char temp_table_name[MAX_LEN];
             strncpy(temp_table_name, condicion_join_col1, strchr(condicion_join_col1, '.') - condicion_join_col1);
             temp_table_name[strchr(condicion_join_col1, '.') - condicion_join_col1] = '\0';
             strcpy(temp_col_name, strchr(condicion_join_col1, '.') + 1);

             if (strcmp(temp_table_name, NArchivo) == 0) {
                 for (int i = 0; i < num_columnas_registro; ++i) {
                     if (strcmp(temp_col_name, columnas_registro[i]) == 0) {
                         strcpy(tipo_col1, T_Datos[i]);
                         col1_found = true;
                         break;
                     }
                 }
             } else if (strcmp(temp_table_name, tabla_join) == 0) {
                 for (int i = 0; i < num_columnas_registro_join; ++i) {
                     if (strcmp(temp_col_name, columnas_registro_join[i]) == 0) {
                         strcpy(tipo_col1, T_Datos_join[i]);
                         col1_found = true;
                         break;
                     }
                 }
             }
        } else if (!col1_found) { // Si no se encuentra y no está calificado, error
            std::cerr << "Error: Columna '" << condicion_join_col1 << "' de condición ON no encontrada en tabla principal.\n";
            error_columna = true;
            return;
        }


        // Buscar col2 en tabla derecha
        for (int i = 0; i < num_columnas_registro_join; ++i) {
            if (strcmp(condicion_join_col2, columnas_registro_join[i]) == 0) {
                strcpy(tipo_col2, T_Datos_join[i]);
                col2_found = true;
                break;
            }
        }
         // Buscar col2 en tabla izquierda (si el nombre es calificado, ej. tabla.col)
        if (!col2_found && strchr(condicion_join_col2, '.') != NULL) {
             char temp_col_name[MAX_LEN];
             char temp_table_name[MAX_LEN];
             strncpy(temp_table_name, condicion_join_col2, strchr(condicion_join_col2, '.') - condicion_join_col2);
             temp_table_name[strchr(condicion_join_col2, '.') - condicion_join_col2] = '\0';
             strcpy(temp_col_name, strchr(condicion_join_col2, '.') + 1);

             if (strcmp(temp_table_name, NArchivo) == 0) {
                 for (int i = 0; i < num_columnas_registro; ++i) {
                     if (strcmp(temp_col_name, columnas_registro[i]) == 0) {
                         strcpy(tipo_col2, T_Datos[i]);
                         col2_found = true;
                         break;
                     }
                 }
             } else if (strcmp(temp_table_name, tabla_join) == 0) {
                 for (int i = 0; i < num_columnas_registro_join; ++i) {
                     if (strcmp(temp_col_name, columnas_registro_join[i]) == 0) {
                         strcpy(tipo_col2, T_Datos_join[i]);
                         col2_found = true;
                         break;
                     }
                 }
             }
        } else if (!col2_found) { // Si no se encuentra y no está calificado, error
            std::cerr << "Error: Columna '" << condicion_join_col2 << "' de condición ON no encontrada en tabla de JOIN.\n";
            error_columna = true;
            return;
        }


        if (!col1_found || !col2_found) {
            std::cerr << "Error: Columnas de la condición ON del JOIN no encontradas.\n";
            error_columna = true;
            return;
        }

        // Validar que los tipos de las columnas de JOIN sean compatibles (idealmente idénticos)
        if (strcmp(tipo_col1, tipo_col2) != 0) {
            std::cerr << "Error: Tipos de datos incompatibles para las columnas de JOIN ('"
                      << condicion_join_col1 << "' es " << tipo_col1 << ", '"
                      << condicion_join_col2 << "' es " << tipo_col2 << ").\n";
            error_columna = true;
            return;
        }
        if (strcmp(condicion_join_op, "=") != 0) {
             std::cerr << "Error: El operador de JOIN solo puede ser '=' en esta implementación.\n";
             error_columna = true;
             return;
        }
    }
}

char* mi_strtok(char* str, const char* delimiters, char** saveptr) {
    char* token;

    if (str != nullptr) {
        *saveptr = str;
    }

    if (*saveptr == nullptr) {
        return nullptr;
    }

    // Saltar delimitadores iniciales
    char* start = *saveptr;
    while (*start && strchr(delimiters, *start)) {
        start++;
    }
    if (*start == '\0') {
        *saveptr = nullptr;
        return nullptr;
    }

    // Encontrar fin del token
    token = start;
    char* end = start;
    while (*end && !strchr(delimiters, *end)) {
        end++;
    }

    if (*end) {
        *end = '\0';     // Terminar token
        *saveptr = end + 1;  // Guardar siguiente posición
    } else {
        *saveptr = nullptr;  // No quedan más tokens
    }

    return token;
}

void ingresar() {
    if (error_columna) return;

    // Abrir archivo de la tabla izquierda
    char ruta_archivo_izq[200];
    snprintf(ruta_archivo_izq, sizeof(ruta_archivo_izq), "%s/tablas/%s.txt", obtenerRutaBase(), NArchivo);
    std::ifstream archivo_izq(ruta_archivo_izq);

    if (!archivo_izq.is_open()) {
        std::cerr << "Error: No se pudo abrir el archivo de la tabla principal '" << NArchivo << "'.\n";
        return;
    }

    std::ofstream& archivo_salida_datos = obtenerArchivoSalida();
    if (!archivo_salida_datos.is_open()) {
        std::cerr << "Error: No se pudo abrir el archivo de salida.\n";
        archivo_izq.close();
        return;
    }

    // Variables para las columnas resultantes del JOIN
    char resultado_fila[MAX_COLS * MAX_LEN]; // Buffer para la fila de salida
    int num_resultado_cols; // Número real de columnas en el resultado (contando las seleccionadas)

    // Si hay JOIN
    if (usarJoin) {
        char ruta_archivo_der[200];
        snprintf(ruta_archivo_der, sizeof(ruta_archivo_der), "%s/%s.txt", obtenerRutaBase(), tabla_join);
        std::ifstream archivo_der(ruta_archivo_der);

        if (!archivo_der.is_open()) {
            std::cerr << "Error: No se pudo abrir el archivo de la tabla de JOIN '" << tabla_join << "'.\n";
            archivo_izq.close();
            return;
        }

        char linea_izq[1000];
        while (archivo_izq.getline(linea_izq, sizeof(linea_izq))) {
            char campos_izq[MAX_COLS][MAX_LEN] = {};
            int num_campos_izq = 0;
            char* saveptr_izq = nullptr;
            char* token_izq = mi_strtok(linea_izq, "#", &saveptr_izq);
            while (token_izq != nullptr && num_campos_izq < MAX_COLS) {
                strncpy(campos_izq[num_campos_izq], token_izq, MAX_LEN - 1);
                campos_izq[num_campos_izq][MAX_LEN - 1] = '\0';
                num_campos_izq++;
                token_izq = mi_strtok(nullptr, "#", &saveptr_izq);
            }

            // Para cada línea de la izquierda, leer la tabla derecha desde el principio
            archivo_der.clear(); // Limpiar flags de error
            archivo_der.seekg(0); // Volver al inicio del archivo de la tabla derecha

            char linea_der[1000];
            while (archivo_der.getline(linea_der, sizeof(linea_der))) {
                char campos_der[MAX_COLS][MAX_LEN] = {};
                int num_campos_der = 0;
                char* saveptr_der = nullptr;
                char* token_der = mi_strtok(linea_der, "#", &saveptr_der);
                while (token_der != nullptr && num_campos_der < MAX_COLS) {
                    strncpy(campos_der[num_campos_der], token_der, MAX_LEN - 1);
                    campos_der[num_campos_der][MAX_LEN - 1] = '\0';
                    num_campos_der++;
                    token_der = mi_strtok(nullptr, "#", &saveptr_der);
                }

                // --- EVALUAR CONDICIÓN DE JOIN ---
                bool cumple_join = true;
                if (usar_condicion_join) {
                    int idx_col1 = -1;
                    int idx_col2 = -1;
                    char tipo_col_join[MAX_LEN] = "";

                    // Encontrar índice y tipo de col1 (puede ser de izq o der, si está calificado)
                    char temp_col1_name[MAX_LEN];
                    char temp_tbl1_name[MAX_LEN];
                    strcpy(temp_col1_name, condicion_join_col1);
                    strcpy(temp_tbl1_name, NArchivo); // Asumir tabla izquierda por defecto

                    char* dot_pos1 = strchr(condicion_join_col1, '.');
                    if (dot_pos1 != NULL) {
                        strncpy(temp_tbl1_name, condicion_join_col1, dot_pos1 - condicion_join_col1);
                        temp_tbl1_name[dot_pos1 - condicion_join_col1] = '\0';
                        strcpy(temp_col1_name, dot_pos1 + 1);
                    }

                    if (strcmp(temp_tbl1_name, NArchivo) == 0) {
                        for (int i = 0; i < num_columnas_registro; ++i) {
                            if (strcmp(temp_col1_name, columnas_registro[i]) == 0) {
                                idx_col1 = i;
                                strcpy(tipo_col_join, T_Datos[i]);
                                break;
                            }
                        }
                    } else if (strcmp(temp_tbl1_name, tabla_join) == 0) {
                        for (int i = 0; i < num_columnas_registro_join; ++i) {
                            if (strcmp(temp_col1_name, columnas_registro_join[i]) == 0) {
                                idx_col1 = i; // Este índice es relativo a campos_der
                                strcpy(tipo_col_join, T_Datos_join[i]);
                                break;
                            }
                        }
                    }

                    // Encontrar índice y tipo de col2 (puede ser de izq o der, si está calificado)
                    char temp_col2_name[MAX_LEN];
                    char temp_tbl2_name[MAX_LEN];
                    strcpy(temp_col2_name, condicion_join_col2);
                    strcpy(temp_tbl2_name, tabla_join); // Asumir tabla derecha por defecto

                    char* dot_pos2 = strchr(condicion_join_col2, '.');
                    if (dot_pos2 != NULL) {
                        strncpy(temp_tbl2_name, condicion_join_col2, dot_pos2 - condicion_join_col2);
                        temp_tbl2_name[dot_pos2 - condicion_join_col2] = '\0';
                        strcpy(temp_col2_name, dot_pos2 + 1);
                    }

                    if (strcmp(temp_tbl2_name, NArchivo) == 0) {
                        for (int i = 0; i < num_columnas_registro; ++i) {
                            if (strcmp(temp_col2_name, columnas_registro[i]) == 0) {
                                idx_col2 = i; // Este índice es relativo a campos_izq
                                break;
                            }
                        }
                    } else if (strcmp(temp_tbl2_name, tabla_join) == 0) {
                        for (int i = 0; i < num_columnas_registro_join; ++i) {
                            if (strcmp(temp_col2_name, columnas_registro_join[i]) == 0) {
                                idx_col2 = i;
                                break;
                            }
                        }
                    }

                    if (idx_col1 != -1 && idx_col2 != -1) {
                        char* val1 = (strcmp(temp_tbl1_name, NArchivo) == 0) ? campos_izq[idx_col1] : campos_der[idx_col1];
                        char* val2 = (strcmp(temp_tbl2_name, NArchivo) == 0) ? campos_izq[idx_col2] : campos_der[idx_col2];

                        // Asumiendo solo '=' para JOIN
                        // Lógica de comparación de tipos (similar a la del WHERE que ya corregiste)
                        // Asegúrate de que tipo_col_join esté correcto aquí.
                        // Usaremos el tipo de la primera columna para la comparación
                        char tipo_actual_str[MAX_LEN];
                        strcpy(tipo_actual_str, tipo_col_join);
                        for(int i = 0; tipo_actual_str[i]; i++){
                          tipo_actual_str[i] = tolower(tipo_actual_str[i]);
                        }

                        if (strcmp(tipo_actual_str, "int") == 0) {
                            if (esEntero(val1) && esEntero(val2)) {
                                if (!(convertirAEntero(val1) == convertirAEntero(val2))) cumple_join = false;
                            } else {
                                cumple_join = false; // Tipos no coinciden o no son válidos
                            }
                        } else if (strcmp(tipo_actual_str, "float") == 0) {
                            if (esFlotante(val1) && esFlotante(val2)) {
                                if (!(atof(val1) == atof(val2))) cumple_join = false;
                            } else {
                                cumple_join = false;
                            }
                        } else if (strcmp(tipo_actual_str, "str") == 0 || strcmp(tipo_actual_str, "string") == 0) {
                            if (!(strcmp(val1, val2) == 0)) cumple_join = false;
                        } else {
                            cumple_join = false; // Tipo desconocido
                        }
                    } else {
                        cumple_join = false; // No se encontraron ambas columnas de JOIN
                    }
                }

                if (cumple_join) {
                    // --- EVALUAR CONDICIONES WHERE ADICIONALES (si las hay) ---
                    bool cumple_condiciones_WHERE = true;
                    if (usarCondiciones) {
                        for (int c = 0; c < numCondiciones && cumple_condiciones_WHERE; ++c) {
                            char* valor_celda_WHERE = nullptr;
                            char tipo_columna_WHERE[MAX_LEN] = "";
                            int idx_col_WHERE = -1;

                            // Buscar la columna de la condición WHERE en la tabla izquierda
                            for(int i=0; i < num_columnas_registro; ++i){
                                if(strcmp(condiciones_col[c], columnas_registro[i]) == 0){
                                    idx_col_WHERE = i;
                                    valor_celda_WHERE = campos_izq[i];
                                    strcpy(tipo_columna_WHERE, T_Datos[i]);
                                    break;
                                }
                            }
                            // Si no está en la izquierda, buscar en la derecha
                            if(idx_col_WHERE == -1){
                                for(int i=0; i < num_columnas_registro_join; ++i){
                                    if(strcmp(condiciones_col[c], columnas_registro_join[i]) == 0){
                                        idx_col_WHERE = i;
                                        valor_celda_WHERE = campos_der[i];
                                        strcpy(tipo_columna_WHERE, T_Datos_join[i]);
                                        break;
                                    }
                                }
                            }

                            if (valor_celda_WHERE != nullptr) {
                                char* operador = condiciones_op[c];
                                char* valor_cond = condiciones_val[c];
                                char tipo_actual_str[MAX_LEN];
                                strcpy(tipo_actual_str, tipo_columna_WHERE);
                                for(int i = 0; tipo_actual_str[i]; i++){
                                  tipo_actual_str[i] = tolower(tipo_actual_str[i]);
                                }

                                if (strcmp(tipo_actual_str, "int") == 0) {
                                    if (esEntero(valor_celda_WHERE) && esEntero(valor_cond)) {
                                        int val_celda_int = convertirAEntero(valor_celda_WHERE);
                                        int val_cond_int = convertirAEntero(valor_cond);
                                        if (strcmp(operador, "=") == 0) { if (!(val_celda_int == val_cond_int)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, "<") == 0) { if (!(val_celda_int < val_cond_int)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, ">") == 0) { if (!(val_celda_int > val_cond_int)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, "<=") == 0) { if (!(val_celda_int <= val_cond_int)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, ">=") == 0) { if (!(val_celda_int >= val_cond_int)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, "!=") == 0 || strcmp(operador, "<>") == 0) { if (!(val_celda_int != val_cond_int)) cumple_condiciones_WHERE = false; }
                                    } else { cumple_condiciones_WHERE = false; }
                                } else if (strcmp(tipo_actual_str, "float") == 0) {
                                    if (esFlotante(valor_celda_WHERE) && esFlotante(valor_cond)) {
                                        double val_celda_float = atof(valor_celda_WHERE);
                                        double val_cond_float = atof(valor_cond);
                                        if (strcmp(operador, "=") == 0) { if (!(val_celda_float == val_cond_float)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, "<") == 0) { if (!(val_celda_float < val_cond_float)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, ">") == 0) { if (!(val_celda_float > val_cond_float)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, "<=") == 0) { if (!(val_celda_float <= val_cond_float)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, ">=") == 0) { if (!(val_celda_float >= val_cond_float)) cumple_condiciones_WHERE = false; }
                                        else if (strcmp(operador, "!=") == 0 || strcmp(operador, "<>") == 0) { if (!(val_celda_float != val_cond_float)) cumple_condiciones_WHERE = false; }
                                    } else { cumple_condiciones_WHERE = false; }
                                } else if (strcmp(tipo_actual_str, "str") == 0 || strcmp(tipo_actual_str, "string") == 0) {
                                    char temp_valor_cond[MAX_LEN];
                                    strncpy(temp_valor_cond, valor_cond, MAX_LEN -1);
                                    temp_valor_cond[MAX_LEN -1] = '\0';
                                    int len = strlen(temp_valor_cond);
                                    if (len >= 2 && temp_valor_cond[0] == '\'' && temp_valor_cond[len - 1] == '\'') {
                                        temp_valor_cond[len - 1] = '\0';
                                        memmove(temp_valor_cond, temp_valor_cond + 1, len - 1);
                                    }
                                    if (strcmp(operador, "=") == 0) { if (!(strcmp(valor_celda_WHERE, temp_valor_cond) == 0)) cumple_condiciones_WHERE = false; }
                                    else if (strcmp(operador, "!=") == 0 || strcmp(operador, "<>") == 0) { if (!(strcmp(valor_celda_WHERE, temp_valor_cond) != 0)) cumple_condiciones_WHERE = false; }
                                    else { std::cerr << "Advertencia: Operador '" << operador << "' no soportado para tipo STRING en WHERE.\n"; cumple_condiciones_WHERE = false; }
                                } else { cumple_condiciones_WHERE = false; }
                            } else {
                                // Columna de WHERE no encontrada en ninguna de las tablas del JOIN
                                cumple_condiciones_WHERE = false;
                                std::cerr << "Error: Columna '" << condiciones_col[c] << "' en WHERE no encontrada en las tablas del JOIN.\n";
                            }
                        }
                    }

                    // Si cumple JOIN y WHERE, construir la fila de salida
                    if (cumple_condiciones_WHERE) {
                        resultado_fila[0] = '\0'; // Reiniciar la fila
                        num_resultado_cols = 0;
                        for (int i = 0; i < num_columnas_seleccionadas; ++i) {
                            char temp_col_name[MAX_LEN];
                            char temp_table_name[MAX_LEN];
                            strcpy(temp_col_name, columnas_seleccionadas[i]);
                            char* dot_pos = strchr(columnas_seleccionadas[i], '.');

                            char* valor_a_agregar = nullptr;

                            if (dot_pos != NULL) { // Columna calificada (ej. clientes.nombre)
                                strncpy(temp_table_name, columnas_seleccionadas[i], dot_pos - columnas_seleccionadas[i]);
                                temp_table_name[dot_pos - columnas_seleccionadas[i]] = '\0';
                                strcpy(temp_col_name, dot_pos + 1);

                                if (strcmp(temp_table_name, NArchivo) == 0) {
                                    for(int k=0; k < num_campos_izq; ++k){
                                        if(strcmp(temp_col_name, columnas_registro[k]) == 0){
                                            valor_a_agregar = campos_izq[k];
                                            break;
                                        }
                                    }
                                } else if (strcmp(temp_table_name, tabla_join) == 0) {
                                    for(int k=0; k < num_campos_der; ++k){
                                        if(strcmp(temp_col_name, columnas_registro_join[k]) == 0){
                                            valor_a_agregar = campos_der[k];
                                            break;
                                        }
                                    }
                                }
                            } else { // Columna no calificada, buscar en ambas tablas (preferencia a la izquierda)
                                for(int k=0; k < num_campos_izq; ++k){
                                    if(strcmp(temp_col_name, columnas_registro[k]) == 0){
                                        valor_a_agregar = campos_izq[k];
                                        break;
                                    }
                                }
                                if(valor_a_agregar == nullptr){ // No encontrada en izquierda, buscar en derecha
                                    for(int k=0; k < num_campos_der; ++k){
                                        if(strcmp(temp_col_name, columnas_registro_join[k]) == 0){
                                            valor_a_agregar = campos_der[k];
                                            break;
                                        }
                                    }
                                }
                            }


                            if (valor_a_agregar != nullptr) {
                                if (num_resultado_cols > 0) strcat(resultado_fila, "#");
                                strcat(resultado_fila, valor_a_agregar);
                                num_resultado_cols++;
                            } else {
                                // Error si una columna seleccionada no se encontró en ninguna tabla
                                std::cerr << "Error: Columna '" << columnas_seleccionadas[i] << "' no encontrada para la salida del JOIN.\n";
                                // Considerar si esto debe detener la ejecución o escribir un valor nulo
                            }
                        }
                        if (num_resultado_cols > 0) {
                            archivo_salida_datos << resultado_fila << std::endl;
                        }
                    }
                }
            }
        }
        archivo_der.close(); // Cerrar la tabla de la derecha
    } else {
        // --- LÓGICA EXISTENTE PARA SIN JOIN ---
        char linea_datos[1000];
        while (archivo_izq.getline(linea_datos, sizeof(linea_datos))) {
            char campos[MAX_COLS][MAX_LEN] = {};
            int num_campos = 0;
            char* saveptr = nullptr;
            char* token = mi_strtok(linea_datos, "#", &saveptr);
            while (token != nullptr && num_campos < MAX_COLS) {
                strncpy(campos[num_campos], token, MAX_LEN - 1);
                campos[num_campos][MAX_LEN - 1] = '\0';
                num_campos++;
                token = mi_strtok(nullptr, "#", &saveptr);
            }

            bool cumple_condiciones = true;
            if (usarCondiciones) {
                for (int c = 0; c < numCondiciones && cumple_condiciones; ++c) {
                    int idx_col = -1;
                    for (int cr = 0; cr < num_columnas_registro; ++cr) {
                        if (strcmp(columnas_registro[cr], condiciones_col[c]) == 0) {
                            idx_col = cr;
                            break;
                        }
                    }

                    if (idx_col != -1 && idx_col < num_campos) {
                        char* valor_celda = campos[idx_col];
                        char* operador = condiciones_op[c];
                        char* valor_cond = condiciones_val[c];
                        char* tipo_columna_str = T_Datos[idx_col];
                        for(int i = 0; tipo_columna_str[i]; i++){
                          tipo_columna_str[i] = tolower(tipo_columna_str[i]);
                        }

                        if (strcmp(tipo_columna_str, "int") == 0) {
                            if (esEntero(valor_celda) && esEntero(valor_cond)) {
                                int val_celda_int = convertirAEntero(valor_celda);
                                int val_cond_int = convertirAEntero(valor_cond);
                                if (strcmp(operador, "=") == 0) { if (!(val_celda_int == val_cond_int)) cumple_condiciones = false; }
                                else if (strcmp(operador, "<") == 0) { if (!(val_celda_int < val_cond_int)) cumple_condiciones = false; }
                                else if (strcmp(operador, ">") == 0) { if (!(val_celda_int > val_cond_int)) cumple_condiciones = false; }
                                else if (strcmp(operador, "<=") == 0) { if (!(val_celda_int <= val_cond_int)) cumple_condiciones = false; }
                                else if (strcmp(operador, ">=") == 0) { if (!(val_celda_int >= val_cond_int)) cumple_condiciones = false; }
                                else if (strcmp(operador, "!=") == 0 || strcmp(operador, "<>") == 0) { if (!(val_celda_int != val_cond_int)) cumple_condiciones = false; }
                            } else { cumple_condiciones = false; }
                        } else if (strcmp(tipo_columna_str, "float") == 0) {
                             if (esFlotante(valor_celda) && esFlotante(valor_cond)) {
                                double val_celda_float = atof(valor_celda);
                                double val_cond_float = atof(valor_cond);
                                if (strcmp(operador, "=") == 0) { if (!(val_celda_float == val_cond_float)) cumple_condiciones = false; }
                                else if (strcmp(operador, "<") == 0) { if (!(val_celda_float < val_cond_float)) cumple_condiciones = false; }
                                else if (strcmp(operador, ">") == 0) { if (!(val_celda_float > val_cond_float)) cumple_condiciones = false; }
                                else if (strcmp(operador, "<=") == 0) { if (!(val_celda_float <= val_cond_float)) cumple_condiciones = false; }
                                else if (strcmp(operador, ">=") == 0) { if (!(val_celda_float >= val_cond_float)) cumple_condiciones = false; }
                                else if (strcmp(operador, "!=") == 0 || strcmp(operador, "<>") == 0) { if (!(val_celda_float != val_cond_float)) cumple_condiciones = false; }
                            } else { cumple_condiciones = false; }
                        }
                        else if (strcmp(tipo_columna_str, "str") == 0 || strcmp(tipo_columna_str, "string") == 0) {
                            char temp_valor_cond[MAX_LEN];
                            strncpy(temp_valor_cond, valor_cond, MAX_LEN -1);
                            temp_valor_cond[MAX_LEN -1] = '\0';
                            int len = strlen(temp_valor_cond);
                            if (len >= 2 && temp_valor_cond[0] == '\'' && temp_valor_cond[len - 1] == '\'') {
                                temp_valor_cond[len - 1] = '\0';
                                memmove(temp_valor_cond, temp_valor_cond + 1, len - 1);
                            }
                            if (strcmp(operador, "=") == 0) { if (!(strcmp(valor_celda, temp_valor_cond) == 0)) cumple_condiciones = false; }
                            else if (strcmp(operador, "!=") == 0 || strcmp(operador, "<>") == 0) { if (!(strcmp(valor_celda, temp_valor_cond) != 0)) cumple_condiciones = false; }
                            else { std::cerr << "Advertencia: Operador '" << operador << "' no soportado para tipo STRING.\n"; cumple_condiciones = false; }
                        } else {
                            std::cerr << "Advertencia: Tipo de columna desconocido: " << tipo_columna_str << std::endl;
                            cumple_condiciones = false;
                        }
                    } else {
                        cumple_condiciones = false;
                    }
                }
            }

            if (cumple_condiciones) {
                resultado_fila[0] = '\0';
                num_resultado_cols = 0;
                for (int i = 0; i < num_columnas_seleccionadas; ++i) {
                    if (num_resultado_cols > 0) strcat(resultado_fila, "#");
                    strcat(resultado_fila, campos[indices[i]]);
                    num_resultado_cols++;
                }
                if (num_resultado_cols > 0) {
                    archivo_salida_datos << resultado_fila << std::endl;
                }
            }
        }
    }
    archivo_izq.close();

    // Abrir relaciones_tablas.txt en modo de añadir para registrar la nueva consulta
    std::fstream archivo_rel_escritura;
    char ruta_relaciones[200];
    snprintf(ruta_relaciones, sizeof(ruta_relaciones), "%s/tablas/relaciones_tablas.txt", obtenerRutaBase());

    archivo_rel_escritura.open(ruta_relaciones, std::ios::app);
    if (!archivo_rel_escritura.is_open()) {
        std::cerr << "Error: No se pudo abrir relaciones_tablas.txt para escritura.\n";
        return;
    }

    archivo_rel_escritura << obtenerNombreConsulta();

    // Lógica para escribir el esquema de la tabla de resultado
    // Basado en las columnas_seleccionadas y sus tipos originales
    for (int i = 0; i < num_columnas_seleccionadas; ++i) {
        char col_name[MAX_LEN];
        char table_prefix[MAX_LEN] = "";
        char* dot_pos = strchr(columnas_seleccionadas[i], '.');
        if (dot_pos != NULL) { // Si la columna está calificada (ej. tabla.columna)
            strncpy(table_prefix, columnas_seleccionadas[i], dot_pos - columnas_seleccionadas[i]);
            table_prefix[dot_pos - columnas_seleccionadas[i]] = '\0';
            strcpy(col_name, dot_pos + 1);
        } else { // Columna no calificada
            strcpy(col_name, columnas_seleccionadas[i]);
        }

        char tipo_columna_salida[MAX_LEN] = "";
        bool tipo_encontrado = false;

        // Buscar el tipo en la tabla izquierda
        for (int j = 0; j < num_columnas_registro; ++j) {
            if (strcmp(col_name, columnas_registro[j]) == 0) {
                if (dot_pos == NULL || strcmp(table_prefix, NArchivo) == 0) { // Si no está calificada o es de la tabla izquierda
                    strcpy(tipo_columna_salida, T_Datos[j]);
                    tipo_encontrado = true;
                    break;
                }
            }
        }

        // Si no se encontró o si está calificada y es de la tabla derecha
        if (!tipo_encontrado && usarJoin) {
            for (int j = 0; j < num_columnas_registro_join; ++j) {
                if (strcmp(col_name, columnas_registro_join[j]) == 0) {
                    if (dot_pos == NULL || strcmp(table_prefix, tabla_join) == 0) { // Si no está calificada o es de la tabla derecha
                        strcpy(tipo_columna_salida, T_Datos_join[j]);
                        tipo_encontrado = true;
                        break;
                    }
                }
            }
        }
        if (tipo_encontrado) {
             archivo_rel_escritura << "#" << columnas_seleccionadas[i] << "#" << tipo_columna_salida;
        } else {
            // Esto es un caso de error si no se encontró el tipo de una columna seleccionada
            std::cerr << "Advertencia: Tipo de dato no encontrado para columna '" << columnas_seleccionadas[i] << "'. Se omitirá en el esquema de salida.\n";
        }
    }
    archivo_rel_escritura << std::endl;
    archivo_rel_escritura.close();

    std::cout << "Consulta ejecutada y guardada correctamente.\n";
}

void abrirRelacion(bool leer) {
    char ruta_relacion[200];
    snprintf(ruta_relacion, sizeof(ruta_relacion), "%s/tablas/relaciones_tablas.txt", obtenerRutaBase());

    if (leer) {
        obtenerArchivoRelaciones().open(ruta_relacion, std::ios::in);
    } else {
        obtenerArchivoRelaciones().open(ruta_relacion, std::ios::app);
    }

    if (!obtenerArchivoRelaciones().is_open()) {
        std::cerr << "Error al abrir " << ruta_relacion << std::endl;
    }
}




