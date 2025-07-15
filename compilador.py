import re
import os
import string 

# === 1. Análisis Léxico ===
def analisis_lexico(texto):
    texto = texto.lower()
    palabras = texto.split()
    palabras = [p.strip(string.punctuation) for p in palabras if p.strip(string.punctuation)]  # ✅ Limpiar signos

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
        "aunque", "y", "o", "..."
    }

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
        elif palabra in {"tabla", "tablas", "base", "bases", "entidad", "entidades"}:
            tokens.append(("INDICADOR_ENTIDAD", palabra))
        elif palabra in {"columna", "columnas", "campo", "campos", "atributo", "atributos"}:
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
            # La siguiente PALABRA después de "tabla", "entidad", etc.
            if i + 1 < len(tokens) and tokens[i+1][0] == "PALABRA":
                estructura["entidad"] = tokens[i+1][1]
                i += 1

        elif tipo == "PALABRA" and estructura["entidad"] is None:
            # Asumir la entidad como la primera palabra que parezca sustantivo clave
            estructura["entidad"] = valor

        elif tipo == "CONECTOR" and (valor == "donde" or valor == "que"):
            # Procesar condiciones normalmente
            j = i + 1
            while j < len(tokens):
                if tokens[j][0] == "PALABRA":
                    atributo = tokens[j][1]
                    k = j + 1
                    while k < len(tokens):
                        current_token = tokens[k]
                        if current_token[0] == "OPERADOR":
                            operador = current_token[1]
                            l = k + 1
                            if l < len(tokens) and tokens[l][0] == "PALABRA":
                                valor_condicion = tokens[l][1]
                                estructura["condiciones"].append({
                                    "atributo": atributo,
                                    "operador": operador,
                                    "valor": valor_condicion
                                })
                                j = l
                                i = j
                                break
                        elif current_token[0] == "CONECTOR" and current_token[1] == "y":
                            j = k
                            break
                        k += 1
                    else:
                        j = k
                j += 1
            i = j

                # Nueva heurística para frases como "con edad menor a 48"
        elif valor == "con" and i + 3 < len(tokens):
            if (tokens[i+1][0] == "PALABRA" and
                tokens[i+2][0] == "PALABRA" and
                tokens[i+3][0] == "PALABRA"):

                atributo = tokens[i+1][1]
                posible_operador = tokens[i+2][1]
                posible_valor = tokens[i+3][1]

                operador_normalizado = _reemplazar_operadores_compuestos(posible_operador)

                if operador_normalizado in ["=", ">", "<", ">=", "<=", "!=", "<>"]:
                    estructura["condiciones"].append({
                        "atributo": atributo,
                        "operador": operador_normalizado,
                        "valor": posible_valor
                    })
                    i += 3  # Avanzar después del valor procesado
        # Heurística para frases como "clientes de Lima"
        elif valor == "de" and i > 0 and tokens[i-1][0] == "PALABRA":
            if estructura["entidad"] is None:
                estructura["entidad"] = tokens[i-1][1]
            if i + 1 < len(tokens) and tokens[i+1][0] == "PALABRA":
                estructura["condiciones"].append({
                    "atributo": "dept",  # o "ubicacion", si prefieres
                    "operador": "igual",
                    "valor": tokens[i+1][1].rstrip(".")  # eliminar punto final
                })
                i += 1

        i += 1

    return estructura

# === Función de reemplazo de operadores compuestos ===
def _reemplazar_operadores_compuestos(texto):
    texto = texto.lower()
    mapeo = {
        "mayor o igual que": ">=",
        "menor o igual que": "<=",
        "igual a": "=",
        "igual": "=",    
        "diferente de": "!=",
        "no es": "!="  
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
            op_sql = "igual"
        elif operador_nl_procesado == ">":
            op_sql = "mayor"
        elif operador_nl_procesado == "<":
            op_sql = "menor"
        elif operador_nl_procesado == ">=":
            op_sql = "mayor_o_igual"
        elif operador_nl_procesado == "<=":
            op_sql = "menor_o_igual"
        elif operador_nl_procesado in {"!=", "<>"}:
            op_sql = "diferente"
        else:
            op_sql = "desconocido"

        valor_formateado = valor

        if op_sql != "desconocido":
            condicion_sql.append(f"{atributo} {op_sql} {valor_formateado}")

    return " y ".join(condicion_sql)

# === 4. Generar lenguaje natural final ===
def generar_lenguaje_natural_final(estructura, condiciones_ln):
    if not estructura["entidad"]:
        return "-- No se puede generar consulta en LN: entidad desconocida."

    consulta_ln = f"selecciona * de {estructura['entidad']}"
    if condiciones_ln:
        consulta_ln += f" donde {condiciones_ln}"
    consulta_ln += "."
    return consulta_ln
# === 4b. Generar SQL real ===
def generar_sql(estructura):
    if not estructura["entidad"]:
        return "-- No se puede generar consulta SQL: entidad desconocida."

    sql = f"SELECT * FROM {estructura['entidad']}"
    condiciones = []

    for cond in estructura["condiciones"]:
        atributo = cond["atributo"]
        operador = cond["operador"]
        valor = cond["valor"]

        # Mapeo a operadores SQL
        op_map = {
            "igual": "=",
            "mayor": ">",
            "menor": "<",
            "mayor_o_igual": ">=",
            "menor_o_igual": "<=",
            "diferente": "!="
        }

        simbolo = op_map.get(operador, "=")

        # Comillas si no es número
        if valor.replace('.', '', 1).isdigit():
            condiciones.append(f"{atributo} {simbolo} {valor}")
        else:
            condiciones.append(f'{atributo} {simbolo} "{valor}"')

    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)

    sql += ";"
    return sql


# === 5. Principal ===
def compilador_nl2sql_texto(texto):
    print("Texto de entrada:", texto)

    tokens = analisis_lexico(texto)
    print("\nTokens léxicos:")
    for t in tokens:
        print(t)

    estructura = analisis_sintactico(tokens)
    print("\nEstructura sintáctica:")
    print(estructura)

    condiciones_ln = analisis_semantico_mejorado(estructura)
    print("\nCondición en lenguaje natural tras análisis semántico:")
    print(condiciones_ln)

    consulta_ln = generar_lenguaje_natural_final(estructura, condiciones_ln)
    print("\nConsulta en lenguaje natural generada para Gestor:")
    print(consulta_ln)

    consulta_sql = generar_sql(estructura)
    print("\nConsulta SQL generada:")
    print(consulta_sql)

    return consulta_sql

# === Ejecutable ===
if __name__ == "__main__":
    nombre_archivo_transcripcion = "compilador/transcripcion.txt"
    nombre_archivo_para_gestor = "compilador/consulta_para_gestor.txt"

    contenido_transcrito = ""
    if os.path.exists(nombre_archivo_transcripcion):
        try:
            with open(nombre_archivo_transcripcion, "r", encoding="utf-8") as f:
                contenido_transcrito = f.read().strip()
            if not contenido_transcrito:
                print(f"El archivo '{nombre_archivo_transcripcion}' está vacío. No hay consulta para procesar.")
                exit()
        except Exception as e:
            print(f"Error al leer el archivo '{nombre_archivo_transcripcion}': {e}")
            exit()
    else:
        print(f"Error: El archivo '{nombre_archivo_transcripcion}' no se encontró.")
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
