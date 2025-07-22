import re
import os
import string
from datetime import datetime

# === Formatos de fecha compatibles ===
FORMATOS_FECHA = [
    r"\d{4}-\d{2}-\d{2}",              # 2025-07-21
    r"\d{2}/\d{2}/\d{4}",              # 21/07/2025
    r"\d{2}-\d{2}-\d{4}",              # 21-07-2025
    r"\d{1,2} de [a-z]+ de \d{4}"      # 21 de julio de 2025
]

def es_fecha(texto):
    texto = texto.lower()
    for formato in FORMATOS_FECHA:
        if re.fullmatch(formato, texto):
            return True
    return False

def unir_fecha(tokens, inicio):
    partes = []
    i = inicio
    while i < len(tokens):
        partes.append(tokens[i][1])
        posible_fecha = ' '.join(partes)
        if es_fecha(posible_fecha):
            return posible_fecha, i - inicio + 1
        i += 1
    return None, 0

# === Análisis Léxico ===
def analisis_lexico(texto):
    texto = texto.lower()
    palabras = texto.split()
    palabras = [p.strip(string.punctuation) for p in palabras if p.strip(string.punctuation)]

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
        "aunque", "y", "o"
    }

    operadores = {"=", ">", "<", ">=", "<=", "!=", "<>"}

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

def _reemplazar_operadores_compuestos(texto):
    texto = texto.lower()
    mapeo = {
        "mayor o igual que": ">=",
        "menor o igual que": "<=",
        "mayor que": ">",
        "menor que": "<",
        "menor a": "<",
        "igual a": "=",
        "igual": "=",
        "no es": "!=",
        "diferente de": "!="
    }
    for frase, reemplazo in mapeo.items():
        texto = re.sub(r'\b' + re.escape(frase) + r'\b', reemplazo, texto)
    return texto

# === Análisis Sintáctico ===
def analisis_sintactico(tokens):
    estructura = {
        "accion": None,
        "entidad": None,
        "condiciones": []
    }

    i = 0
    while i < len(tokens):
        tipo, valor = tokens[i]

        # Detectar fechas en una sola palabra
        if es_fecha(valor):
            estructura["condiciones"].append({
                "atributo": "fecha",
                "operador": "=",
                "valor": valor
            })
            i += 1
            continue

        # Unir tokens para frases como "21 de julio de 2025"
        if valor == "de" and i > 1 and tokens[i-1][1] == "en":
            fecha, saltos = unir_fecha(tokens, i-1)
            if fecha:
                estructura["condiciones"].append({
                    "atributo": "fecha",
                    "operador": "=",
                    "valor": fecha
                })
                i += saltos
                continue

        # Acción principal
        if tipo == "ACCION" and estructura["accion"] is None:
            estructura["accion"] = valor

        elif tipo == "INDICADOR_ENTIDAD":
            if i + 1 < len(tokens) and tokens[i+1][0] == "PALABRA":
                estructura["entidad"] = tokens[i+1][1]
                i += 1

        elif tipo == "PALABRA" and estructura["entidad"] is None:
            if valor in {"clientes", "productos", "ventas"}:  # tablas válidas
                estructura["entidad"] = valor
            elif valor in {"nombre", "edad", "id", "dept", "precio", "fecha"}:  # atributos válidos
                estructura.setdefault("atributos_mostrar", []).append(valor)


        elif tipo == "CONECTOR" and valor in {"donde", "que"}:
            j = i + 1
            while j < len(tokens) - 2:
                if (
                    tokens[j][0] == "PALABRA" and
                    tokens[j+1][0] == "PALABRA" and
                    tokens[j+2][0] == "PALABRA"
                ):
                    atributo = tokens[j][1]
                    operador_compuesto = f"{tokens[j+1][1]} {tokens[j+2][1]}"
                    operador_normalizado = _reemplazar_operadores_compuestos(operador_compuesto)
                    if operador_normalizado in {"=", ">", "<", ">=", "<=", "!=", "<>"}:
                        if j + 3 < len(tokens):
                            estructura["condiciones"].append({
                                "atributo": atributo,
                                "operador": operador_normalizado,
                                "valor": tokens[j+3][1]
                            })
                            j += 4
                            continue
                j += 1
            i = j
            continue

        elif valor == "con" and i + 4 < len(tokens):
            atributo = tokens[i+1][1]
            posible_operador = f"{tokens[i+2][1]} {tokens[i+3][1]}"
            operador = _reemplazar_operadores_compuestos(posible_operador)
            valor_c = tokens[i+4][1]

            if operador in {"=", ">", "<", ">=", "<=", "!=", "<>"}:
                estructura["condiciones"].append({
                    "atributo": atributo,
                    "operador": operador,
                    "valor": valor_c
                })
                i += 4

        elif valor == "de" and i > 0 and tokens[i-1][0] == "PALABRA":
            if not (i+1 < len(tokens) and es_fecha(tokens[i+1][1])):
                if estructura["entidad"] is None:
                    estructura["entidad"] = tokens[i-1][1]
                if i + 1 < len(tokens) and tokens[i+1][0] == "PALABRA":
                    estructura["condiciones"].append({
                        "atributo": "dept",
                        "operador": "=",
                        "valor": tokens[i+1][1].rstrip(".")
                    })
                    i += 1

        
            # Ej: "cliente llamado Lucia" o "cliente llamada Lucia"
        elif valor in {"llamado","llamados", "llamada"} and i > 0 and tokens[i-1][0] == "PALABRA":
            if estructura["entidad"] is None:
                estructura["entidad"] = tokens[i-1][1]
            if i + 1 < len(tokens):
                estructura["condiciones"].append({
                    "atributo": "nombre",
                    "operador": "=",
                    "valor": tokens[i+1][1]
                })
                i += 1  # Saltar el nombre

        # Ej: "cliente que se llama Pedro"
        elif (valor == "llama" or valor == "llaman") and i >= 2 and tokens[i-1][1] == "se":
            if estructura["entidad"] is None and i >= 3:
                estructura["entidad"] = tokens[i-3][1]
            if i + 1 < len(tokens):
                estructura["condiciones"].append({
                    "atributo": "nombre",
                    "operador": "=",
                    "valor": tokens[i+1][1]
                })
                i += 1
        i += 1

    return estructura

# === Análisis Semántico ===
def analisis_semantico_mejorado(estructura):
    condiciones_ln = []
    operador_map = {
        "=": "igual",
        ">": "mayor",
        "<": "menor",
        ">=": "mayor o igual",
        "<=": "menor o igual",
        "!=": "diferente",
        "<>": "diferente"
    }
    for cond in estructura["condiciones"]:
        atributo = cond["atributo"]
        operador = operador_map.get(cond["operador"], cond["operador"])
        valor = cond["valor"]
        condiciones_ln.append(f"{atributo} {operador} {valor}")
    return " y ".join(condiciones_ln)

# === Generar Consulta en Lenguaje Natural ===
def generar_lenguaje_natural_final(estructura, condiciones_ln):
    if not estructura["entidad"]:
        return "-- No se puede generar consulta en LN: entidad desconocida."
    consulta = f"selecciona * de {estructura['entidad']}"
    if condiciones_ln:
        consulta += f" donde {condiciones_ln}"
    return consulta + "."

# === Generar SQL ===
def generar_sql(estructura):
    if not estructura["entidad"]:
        return "-- No se puede generar consulta SQL: entidad desconocida."
    if "atributos_mostrar" in estructura and estructura["atributos_mostrar"]:
        campos = ", ".join(estructura["atributos_mostrar"])
        sql = f"SELECT {campos} FROM {estructura['entidad']}"
    else:
        sql = f"SELECT * FROM {estructura['entidad']}"

    condiciones = []

    for cond in estructura["condiciones"]:
        atributo = cond["atributo"]
        operador = cond["operador"]
        valor = cond["valor"]

        # Conversión de fecha con formato largo
        if atributo == "fecha" and re.match(r"\d{1,2} de [a-z]+ de \d{4}", valor):
            try:
                fecha_obj = datetime.strptime(valor, "%d de %B de %Y")
                valor = fecha_obj.strftime("%Y-%m-%d")
            except:
                pass
            condiciones.append(f"{atributo} {operador} DATE('{valor}')")
        else:
            if valor.replace(".", "", 1).isdigit():
                condiciones.append(f"{atributo} {operador} {valor}")
            else:
                condiciones.append(f"{atributo} {operador} '{valor}'")

    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    return sql 

# === Compilador Principal ===
def compilador_nl2sql_texto(texto):
    print("Texto de entrada:", texto)
    tokens = analisis_lexico(texto)
    print("\nTokens léxicos:", tokens)

    estructura = analisis_sintactico(tokens)
    print("\nEstructura sintáctica:", estructura)

    condiciones_ln = analisis_semantico_mejorado(estructura)
    print("\nCondición en lenguaje natural:", condiciones_ln)

    consulta_ln = generar_lenguaje_natural_final(estructura, condiciones_ln)
    print("\nConsulta NL:", consulta_ln)

    consulta_sql = generar_sql(estructura)
    print("\nConsulta SQL:", consulta_sql)

    return consulta_sql

# === Main ===
if __name__ == "__main__":
    nombre_archivo_transcripcion = "transcripcion.txt"
    nombre_archivo_para_gestor = "/home/ubuntu20/5semestre-2025A/nnnlllpppp222/compilador/consulta_para_gestor.txt"

    if os.path.exists(nombre_archivo_transcripcion):
        with open(nombre_archivo_transcripcion, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
    else:
        print("⚠ No se encontró el archivo. Usando consulta de ejemplo.")
        contenido = "muéstrame las ventas que se realizaron en 21 de julio de 2025"

    sql_generado = compilador_nl2sql_texto(contenido)
    with open(nombre_archivo_para_gestor, "w", encoding="utf-8") as f:
        f.write(sql_generado)
    print(f"\nConsulta SQL guardada en: {nombre_archivo_para_gestor}")
