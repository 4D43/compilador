import re
import os

# ... (Las secciones de analisis_lexico, analisis_sintactico, analisis_semantico_mejorado, _reemplazar_operadores_compuestos son las mismas) ...

# === 1. Análisis Léxico ===
def analisis_lexico(texto):
    texto = texto.lower()
    palabras = texto.split()

    acciones = {
    "muéstrame", "muestrame", "mostrar", "muestra", "dame", "dámelos", "dámelas",
    "enséñame", "ensename", "quiero", "consultar", "consulta", "ver", "visualizar",
    "verifica", "explora", "lista", "listar", "recupera", "recuperar", "busca",
    "buscar", "obtén", "obtener", "extrae", "extraer", "filtra", "filtrar",
    "accede", "acceder", "selecciona", "seleccionar", "deseo", "necesito"
    }


    cuantificadores = {
        "todos", "todas", "los", "las", "algunos", "algunas", "ninguno", "ninguna",
        "cada", "varios", "cualquier", "cualquiera", "muchos", "muchas", "pocos", "pocas",
        "uno", "una", "el", "la", "este", "esta", "estos", "estas"
    }


    conectores = {
        "que", "donde", "cuyo", "cuyos", "cual", "cuales", "si", "cuando", "mientras",
        "aunque", "y", "o", "..."}

    operadores = {
        "es", "igual", "igual a", "=",
        "mayor que", ">",
        "menor que", "<",
        "mayor o igual que", ">=",
        "menor o igual que", "<=",
        "no es", "diferente de", "!=", "<>"
    }

    tokens = []
    for palabra in palabras:
        if palabra in acciones:
            tokens.append(("ACCION", palabra))
        elif palabra in cuantificadores:
            tokens.append(("CUANTIFICADOR", palabra))
        elif palabra in conectores:
            tokens.append(("CONECTOR", palabra))
        elif palabra in operadores:
            tokens.append(("OPERADOR", palabra))
        elif palabra == "tabla" or palabra == "tablas" or palabra == "base" or palabra == "bases" or palabra == "entidad" or palabra == "entidades":
            tokens.append(("INDICADOR_ENTIDAD", palabra))
        elif palabra == "columna" or palabra == "columnas" or palabra == "campo" or palabra == "campos" or palabra == "atributo" or palabra == "atributos":
            tokens.append(("INDICADOR_ATRIBUTO", palabra))
        else:
            tokens.append(("PALABRA", palabra))
    return tokens

# === 2. Análisis Sintáctico ===
def analisis_sintactico(tokens):
    estructura = {
        "accion": None,
        "entidad": None,
        "condiciones": []
    }

    i = 0
    while i < len(tokens):
        tipo, valor = tokens[i]

        if tipo == "ACCION" and estructura["accion"] is None:
            estructura["accion"] = valor
        elif tipo == "INDICADOR_ENTIDAD":
            # La siguiente PALABRA después de "tabla" o "entidad" es la entidad
            if i + 1 < len(tokens) and tokens[i+1][0] == "PALABRA":
                estructura["entidad"] = tokens[i+1][1]
                i += 1 # Saltar la entidad ya procesada
        elif tipo == "CONECTOR" and (valor == "donde" or valor == "que"):
            # Buscar condiciones después de "donde" o "que"
            j = i + 1
            while j < len(tokens):
                if tokens[j][0] == "PALABRA": # Posible atributo
                    atributo = tokens[j][1]
                    k = j + 1
                    while k < len(tokens): # Revisar todos los tokens subsiguientes para operador y valor
                        current_token = tokens[k]
                        if current_token[0] == "OPERADOR":
                            operador = current_token[1]
                            l = k + 1
                            if l < len(tokens) and tokens[l][0] == "PALABRA": # Valor
                                valor_condicion = tokens[l][1]
                                estructura["condiciones"].append({
                                    "atributo": atributo,
                                    "operador": operador,
                                    "valor": valor_condicion
                                })
                                # Mover j al valor actual para continuar el bucle desde ahí
                                j = l
                                i = j # Asegurarse de que el índice principal también avance
                                break # Salir del bucle interno de operador/valor y continuar con el siguiente token principal
                            else: # Operador sin valor, puede ser el final de la condición o un error
                                break
                        elif current_token[0] == "CONECTOR" and current_token[1] == "y": # Manejar "y" para múltiples condiciones
                            j = k # Mover j al conector "y" para la próxima iteración principal
                            break
                        elif current_token[0] == "PALABRA" and k > j + 1: # Si encontramos otra palabra sin operador, asumimos fin de condición
                            j = k -1 # Para que el bucle principal avance correctamente
                            break
                        k += 1 # Avanzar en los tokens después del atributo
                    else: # Si el bucle while(k) termina sin un break
                        j = k # Mover j para evitar bucle infinito si no se encuentra operador/valor
                j += 1
            i = j # Mover el índice principal al final de las condiciones procesadas
        i += 1
    return estructura

# Función para manejar operadores compuestos como "mayor o igual que"
def _reemplazar_operadores_compuestos(texto):
    texto = texto.lower()
    mapeo = {
        "mayor o igual que": ">=",
        "menor o igual que": "<=",
        "igual a": "=",
        "diferente de": "!="
    }
    for frase, reemplazo in mapeo.items():
        texto = re.sub(r'\b' + re.escape(frase) + r'\b', reemplazo, texto)
    return texto

def analisis_semantico_mejorado(estructura):
    condicion_sql = []
    for cond in estructura["condiciones"]:
        atributo = cond["atributo"]
        operador_nl = cond["operador"]
        valor = cond["valor"]

        operador_nl_procesado = _reemplazar_operadores_compuestos(operador_nl)

        op_sql = ""
        if operador_nl_procesado == "=":
            op_sql = "igual" # Cambiamos a "igual" para que gestor.cpp lo entienda
        elif operador_nl_procesado == ">":
            op_sql = "mayor" # Cambiamos a "mayor"
        elif operador_nl_procesado == "<":
            op_sql = "menor" # Cambiamos a "menor"
        elif operador_nl_procesado == ">=":
            op_sql = "mayor_o_igual" # Nuevo operador para gestor.cpp si lo soporta
        elif operador_nl_procesado == "<=":
            op_sql = "menor_o_igual" # Nuevo operador
        elif operador_nl_procesado == "!=" or operador_nl_procesado == "<>":
            op_sql = "diferente" # Nuevo operador
        else:
            op_sql = "desconocido"

        # No necesitamos formatear el valor con comillas aquí, ya que gestor.cpp lo maneja en su tokenización
        valor_formateado = valor

        if op_sql != "desconocido":
            condicion_sql.append(f"{atributo} {op_sql} {valor_formateado}")

    return " y ".join(condicion_sql) # Unimos con " y " para que gestor.cpp lo entienda

# === 4. Generación de Consulta en Lenguaje Natural para Gestor ===
def generar_lenguaje_natural_final(estructura, condiciones_ln):
    if not estructura["entidad"]:
        return "-- No se puede generar consulta en LN: entidad desconocida."

    # Ejemplo de formato que gestor.cpp parece manejar:
    # "selecciona * de tabla_nombre donde columna operador valor"
    # "selecciona columna1,columna2 de tabla_nombre donde columna operador valor"

    # Simplificamos a SELECT * para la compatibilidad con el ejemplo de gestor.cpp
    # El gestor.cpp actual solo parece usar `SELECT *` para mostrar datos
    # y `ingresar` para la inserción. Asumimos una consulta de selección simple.
    
    consulta_ln = f"selecciona * de {estructura['entidad']}"
    if condiciones_ln:
        consulta_ln += f" donde {condiciones_ln}"
    consulta_ln += "." # Agregamos un punto final o algún terminador si gestor.cpp lo espera

    return consulta_ln

# === 5. Módulo principal ===
def compilador_nl2sql_texto(texto):
    print("Texto de entrada:", texto)

    tokens = analisis_lexico(texto)
    print("\nTokens léxicos:")
    for t in tokens:
        print(t)

    estructura = analisis_sintactico(tokens)
    print("\nEstructura sintáctica:")
    print(estructura)

    # Ahora el análisis semántico genera la parte de las condiciones en lenguaje natural
    condiciones_ln = analisis_semantico_mejorado(estructura)
    print("\nCondición en lenguaje natural tras análisis semántico:")
    print(condiciones_ln)

    # La generación final ahora es en lenguaje natural
    consulta_ln = generar_lenguaje_natural_final(estructura, condiciones_ln)
    print("\nConsulta en lenguaje natural generada para Gestor:")
    print(consulta_ln)

    return consulta_ln

# === Módulo principal con lectura y escritura de archivo ===
if __name__ == "__main__":
    nombre_archivo_transcripcion = "transcripcion.txt" 
    nombre_archivo_para_gestor = "consulta_para_gestor.txt" # Nuevo archivo de salida

    contenido_transcrito = ""
    if os.path.exists(nombre_archivo_transcripcion):
        try:
            with open(nombre_archivo_transcripcion, "r", encoding="utf-8") as f:
                contenido_transcrito = f.read().strip()
            
            if not contenido_transcrito:
                print(f"El archivo '{nombre_archivo_transcripcion}' está vacío. No hay consulta para procesar.")
                exit() # Salir si el archivo está vacío

        except Exception as e:
            print(f"Error al leer el archivo '{nombre_archivo_transcripcion}': {e}")
            exit() # Salir en caso de error de lectura
    else:
        print(f"Error: El archivo '{nombre_archivo_transcripcion}' no se encontró.")
        print("Asegúrate de que 'transcribir_audio.py' se haya ejecutado y generado el archivo.")
        # Ejemplo si no hay archivo de entrada
        contenido_transcrito = "muéstrame todos los datos de la tabla empleados donde edad mayor que 30"
        print(f"Usando consulta de ejemplo: '{contenido_transcrito}'")

    if contenido_transcrito:
        consulta_para_gestor = compilador_nl2sql_texto(contenido_transcrito)
        if consulta_para_gestor:
            try:
                with open(nombre_archivo_para_gestor, "w", encoding="utf-8") as f:
                    f.write(consulta_para_gestor)
                print(f"\nConsulta para Gestor guardada en '{nombre_archivo_para_gestor}'")
            except Exception as e:
                print(f"Error al escribir en el archivo '{nombre_archivo_para_gestor}': {e}")