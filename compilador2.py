import sys
import os
import re
import string
import json
from datetime import datetime
from difflib import get_close_matches

from Trie import Trie, TrieNode
from fuzzy_dict1 import sincronizar_diccionario, generar_trie_desde_diccionario, crear_prompt_para_whisper
from transcribir_audio import transcribir_audio

import whisper 

# --- 3.1: FASE 1: Análisis Léxico (P1) ---
def analisis_lexico(texto_transcrito):
    """
    FASE 1: ANÁLISIS LÉXICO
    Toma el texto de Whisper, lo limpia y lematiza.
    """
    print(f"\n--- FASE 1: Análisis Léxico (Lematización) ---")
    print(f"(P1) Texto de entrada: '{texto_transcrito}'")
    
    LEMAS = {
        "muéstrame": "mostrar", "dame": "mostrar", "ver": "mostrar",
        "clientes": "cliente", "ventas": "venta", "productos": "producto",
        "cuántos": "cuánto", "cuántas": "cuánto", "cuánta": "cuánto",
        "departamento": "dept", "departamentos": "dept",
        "con": "donde", "en": "donde", "del": "donde", "de": "donde"
    }
    
    texto = texto_transcrito.lower().strip(string.punctuation)
    tokens_originales = texto.split()
    tokens_lematizados = []
    
    for token in tokens_originales:
        token_limpio = token.strip(string.punctuation)
        tokens_lematizados.append(LEMAS.get(token_limpio, token_limpio))
        
    print(f"(P1) Tokens Lematizados: {tokens_lematizados}")
    return tokens_lematizados

# --- 3.2: FASE 2: Análisis Sintáctico ---

# (P1) Define los patrones de consulta (Trie de Estructuras)
PATRONES_TRIE = {
    "mostrar": {
        "los": { "__meta__": {"tipo_siguiente": "ENTIDAD", "accion": "SELECT", "select": "*"} },
        "las": { "__meta__": {"tipo_siguiente": "ENTIDAD", "accion": "SELECT", "select": "*"} },
        "el": { "__meta__": {"tipo_siguiente": "ENTIDAD", "accion": "SELECT", "select": "*"} },
        "la": { "__meta__": {"tipo_siguiente": "ENTIDAD", "accion": "SELECT", "select": "*"} },
        "__meta__": {"tipo_siguiente": "ATRIBUTO", "accion": "SELECT"}
    },
    "cuánto": {
        "__meta__": {"tipo_siguiente": "ENTIDAD", "accion": "COUNT", "select": "COUNT(*)"}
    },
    "ordenar_por": {"columna": "edad", "direccion": "ASC"}
}
CONECTORES_CONDICION = {"donde", "que"} # Simplificado

def analisis_sintactico(tokens_lematizados):
    """
    (SIMULACIÓN DE PERSONA 1)
    FASE 2: ANÁLISIS SINTÁCTICO
    Recorre el Trie simplificado para construir el "Contrato".
    """
    print(f"\n--- FASE 2: Análisis Sintáctico (Parsing) ---")

    estructura_logica = {
        "accion": None,
        "entidad": None,
        "atributos_mostrar": [],
        "condiciones": [],
        "es_incompleta": False
    }

    i = 0
    n = len(tokens_lematizados)

    # -------------------------------
    #  1. ACCIÓN (mostrar / cuánto)
    # -------------------------------
    if i < n and tokens_lematizados[i] in ("mostrar", "cuánto"):
        accion = tokens_lematizados[i]
        i += 1

        if accion == "mostrar":
            estructura_logica["accion"] = "SELECT"
        elif accion == "cuánto":
            estructura_logica["accion"] = "COUNT"
            estructura_logica["atributos_mostrar"].append("COUNT(*)")
    else:
        print("(P1) Error: No se detectó verbo de acción válido.")
        estructura_logica["es_incompleta"] = True
        return estructura_logica

    # ------------------------------------------------
    # 2. ARTÍCULO (puede haber varios: "todos", "los", "las", ...)
    # ------------------------------------------------
    articulos = {"los", "las", "el", "la", "todos", "todas", "todo", "toda"}
    while i < n and tokens_lematizados[i] in articulos:
        i += 1  # saltar cuantos artículos aparezcan seguidos

    # ------------------------------------------------
    # 3. ENTIDAD (cliente, producto, venta, ...)
    # ------------------------------------------------
    if i < n:
        estructura_logica["entidad"] = tokens_lematizados[i]
        i += 1
    else:
        print("(P1) Error: No se encontró entidad.")
        estructura_logica["es_incompleta"] = True
        return estructura_logica

    # ------------------------------------------------
    # 4. CONDICIONES (opcional) — "donde" o "con"
    # ------------------------------------------------
    if i < n and tokens_lematizados[i] in ("donde", "con", "que"):
        i += 1

        # Tomamos el resto como posible condición y lo analizamos de forma robusta
        # Ejemplos que queremos cubrir:
        #   id menor a 5
        #   edad mayor 30
        #   precio igual 10
        #   id menor que 5
        #   id < 5  (si llega en tokens)
        rem = tokens_lematizados[i:]
        if len(rem) >= 2:
            # Buscamos patrón: atributo operador valor (con o sin preposición)
            atributo = rem[0]
            operador_token = rem[1]

            # manejar operadores de palabra
            mapa_op = {"mayor": ">", "menor": "<", "igual": "=", "<": "<", ">": ">"}
            operador = mapa_op.get(operador_token, None)

            # si operador es palabra y hay una preposición antes del número ("a" o "que"), saltarla
            valor = None
            if operador is not None:
                # casos: rem = [atributo, 'menor', 'a', '5']  -> tomar rem[3]
                if len(rem) >= 3:
                    # si rem[2] es preposición y rem[3] existe y es número -> tomar rem[3]
                    if len(rem) >= 4 and rem[2] in ("a", "que") and rem[3].isdigit():
                        valor = rem[3]
                    # si rem[2] es número -> tomar rem[2]
                    elif rem[2].isdigit():
                        valor = rem[2]
                    # si rem[2] es palabra entrecomillada o string -> tomar rem[2]
                    else:
                        valor = rem[2]
                else:
                    print("(P1) Advertencia: condición incompleta (no hay valor).")
            else:
                # intentar detectar operador como token en posición 2 (ej: "id", "<", "5")
                if len(rem) >= 3 and rem[1] in ("<", ">") and rem[2].isdigit():
                    operador = rem[1]
                    valor = rem[2]
                elif len(rem) >= 3 and rem[1] in ("<", ">") and len(rem) >= 4 and rem[2] in ("a", "que") and rem[3].isdigit():
                    operador = rem[1]
                    valor = rem[3]
                else:
                    # fallback: si hay al menos 3 tokens, tomar rem[1] como operador y rem[2] como valor (riesgoso pero usable)
                    if len(rem) >= 3:
                        operador = rem[1]
                        valor = rem[2]

            if atributo and operador is not None and valor is not None:
                estructura_logica["condiciones"].append({
                    "atributo": atributo,
                    "operador": operador,
                    "valor": valor
                })
            else:
                print("(P1) Advertencia: no se pudo parsear la condición de forma segura:", rem)
        else:
            print("(P1) Advertencia: condición incompleta.")

    print(f"(P1) Estructura Lógica (Contrato): {estructura_logica}")
    return estructura_logica

# --- 3.3: FASE 3: Análisis Semántico y Generación (Persona 2 - ¡Tu Tarea!) ---

# (P2) Mapeo de lemas (singular) a tablas (plural)
MAPA_LEMA_A_TABLA = {
    "cliente": "clientes",
    "producto": "productos",
    "venta": "ventas",
    "student": "students",
    "empleado": "empleados",
    "titanic": "titanic"
}

def cargar_esquema_db(relaciones_texto):
    """
    Carga el esquema y DETECTA RELACIONES (Foreign Keys).
    Asume convención de nombres: 'tabla_id' apunta a 'tabla'.
    """
    esquema = {}
    relaciones_fk = {} # Mapa de quién apunta a quién

    for linea in relaciones_texto.strip().split('\n'):
        partes = linea.split('#')
        if len(partes) < 2: continue
        
        nombre_tabla = partes[0]
        columnas = {}
        
        # Leer columnas
        for i in range(1, len(partes), 2):
            if i + 1 < len(partes):
                col_nombre = partes[i]
                col_tipo = partes[i+1]
                columnas[col_nombre] = col_tipo
                
                # --- DETECCIÓN DE JOIN (FK) ---
                # Si la columna termina en '_id' (ej: cliente_id)
                # Asumimos que apunta a la tabla 'clientes'
                if col_nombre.endswith("_id"):
                    tabla_destino = col_nombre[:-3] + "s" # cliente -> clientes
                    # Guardamos la relación: "ventas" -> apunta a -> "clientes"
                    if nombre_tabla not in relaciones_fk: relaciones_fk[nombre_tabla] = []
                    relaciones_fk[nombre_tabla].append({
                        "fk": col_nombre,       # cliente_id
                        "destino": tabla_destino # clientes
                    })

        if nombre_tabla not in esquema:
            esquema[nombre_tabla] = {}
        esquema[nombre_tabla].update(columnas)
        
    print(f"--- (P2) Esquema Cargado. Relaciones detectadas: {len(relaciones_fk)} tablas con FKs ---")
    return esquema, relaciones_fk
def generar_camino_joins(tablas_necesarias, relaciones_fk):
    """
    Genera la cláusula FROM ... JOIN ... ON ...
    Intenta conectar todas las tablas necesarias usando las FK detectadas.
    """
    lista_tablas = list(tablas_necesarias)
    if not lista_tablas: return ""
    
    # Empezamos con la primera tabla (normalmente la que tiene más FKs, como 'ventas')
    # Ordenamos para que las tablas "hechos" (con FKs) vayan primero
    lista_tablas.sort(key=lambda t: 1 if t in relaciones_fk else 0, reverse=True)
    
    tabla_base = lista_tablas[0]
    clausula_from = f"FROM {tabla_base}"
    tablas_unidas = {tabla_base}
    
    # Intentamos unir el resto
    for tabla_objetivo in lista_tablas[1:]:
        if tabla_objetivo in tablas_unidas: continue
        
        unido = False
        # 1. Intento Directo: ¿La tabla base apunta a la objetivo?
        if tabla_base in relaciones_fk:
            for relacion in relaciones_fk[tabla_base]:
                if relacion["destino"] == tabla_objetivo:
                    clausula_from += f" JOIN {tabla_objetivo} ON {tabla_base}.{relacion['fk']} = {tabla_objetivo}.id"
                    tablas_unidas.add(tabla_objetivo)
                    unido = True
                    break
        
        # 2. Intento Inverso: ¿La tabla objetivo apunta a la base?
        if not unido and tabla_objetivo in relaciones_fk:
            for relacion in relaciones_fk[tabla_objetivo]:
                if relacion["destino"] == tabla_base:
                    clausula_from += f" JOIN {tabla_objetivo} ON {tabla_objetivo}.{relacion['fk']} = {tabla_base}.id"
                    tablas_unidas.add(tabla_objetivo)
                    unido = True
                    break
        
        if not unido:
            # Si fallamos, hacemos producto cartesiano (o podríamos buscar tabla puente)
            clausula_from += f", {tabla_objetivo} -- ( No se encontró JOIN directo)"
            
    return clausula_from
def analisis_semantico_y_generacion(estructura_logica, esquema_db, relaciones_fk):
    print("\n--- FASE 3: Generación SQL Robusta (JOINs/GROUP/ORDER) ---")
    
    # 1. Recopilar todas las columnas solicitadas para saber qué tablas necesitamos
    columnas_requeridas = []
    
    # Columnas del SELECT
    for col in estructura_logica.get("atributos_mostrar", []):
        if col != "*" and "COUNT" not in col: columnas_requeridas.append(col)
        
    # Columnas del WHERE
    for cond in estructura_logica.get("condiciones", []):
        columnas_requeridas.append(cond["atributo"])
        
    # Columnas del GROUP BY y ORDER BY
    if estructura_logica.get("agrupar_por"):
        columnas_requeridas.extend(estructura_logica["agrupar_por"])
    if estructura_logica.get("ordenar_por"):
        columnas_requeridas.append(estructura_logica["ordenar_por"]["columna"])

    # 2. Identificar tablas involucradas
    tablas_involucradas = set()
    entidad_principal = estructura_logica.get("entidad")
    # Mapeo rápido
    nombre_real = MAPA_LEMA_A_TABLA.get(entidad_principal, entidad_principal)
    if nombre_real in esquema_db:
        tablas_involucradas.add(nombre_real)

    # Buscar a qué tabla pertenece cada columna requerida
    columna_a_tabla = {} # Mapa: 'nombre' -> 'clientes'
    
    for col in columnas_requeridas:
        encontrado = False
        # Primero buscar en la tabla principal (prioridad)
        if nombre_real and col in esquema_db.get(nombre_real, {}):
             columna_a_tabla[col] = nombre_real
             encontrado = True
        else:
            # Buscar en todo el esquema
            for tabla, cols in esquema_db.items():
                if col in cols:
                    columna_a_tabla[col] = tabla
                    tablas_involucradas.add(tabla)
                    encontrado = True
                    break
        
        if not encontrado:
            return f"-- Error Semántico: Columna '{col}' no encontrada en la DB."

    # 3. Generar cláusula FROM con JOINS automáticos
    if not tablas_involucradas:
        return "-- Error: No se identificaron tablas."
    
    sql_from = generar_camino_joins(tablas_involucradas, relaciones_fk)

    # 4. Generar SELECT
    select_cols = []
    accion = estructura_logica.get("accion", "SELECT")
    
    if accion == "COUNT" and not estructura_logica.get("agrupar_por"):
        select_cols = ["COUNT(*)"]
    else:
        # Si hay GROUP BY, aseguramos que las columnas de grupo estén en el SELECT
        if estructura_logica.get("agrupar_por"):
            for grp in estructura_logica["agrupar_por"]:
                tbl = columna_a_tabla[grp]
                select_cols.append(f"{tbl}.{grp}")
            select_cols.append("COUNT(*)") # Usualmente GROUP BY va con count
        else:
            # Select normal
            attrs = estructura_logica.get("atributos_mostrar", ["*"])
            for attr in attrs:
                if attr == "*" or "COUNT" in attr:
                    select_cols.append(attr)
                else:
                    tbl = columna_a_tabla[attr]
                    select_cols.append(f"{tbl}.{attr}")

    sql = f"SELECT {', '.join(select_cols)} {sql_from}"

    # 5. Generar WHERE
    condiciones = []
    for cond in estructura_logica.get("condiciones", []):
        tbl = columna_a_tabla[cond["atributo"]]
        val = cond["valor"]
        # Validar tipo y comillas
        tipo = esquema_db[tbl].get(cond["atributo"], "str")
        if tipo in {"str", "string", "date"} and not str(val).startswith("'"):
            val = f"'{val}'"
        condiciones.append(f"{tbl}.{cond['atributo']} {cond['operador']} {val}")
    
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)

    # 6. Generar GROUP BY
    if estructura_logica.get("agrupar_por"):
        grupos = [f"{columna_a_tabla[g]}.{g}" for g in estructura_logica["agrupar_por"]]
        sql += " GROUP BY " + ", ".join(grupos)

    # 7. Generar ORDER BY
    if estructura_logica.get("ordenar_por"):
        ord_col = estructura_logica["ordenar_por"]["columna"]
        ord_dir = estructura_logica["ordenar_por"].get("direccion", "ASC")
        tbl = columna_a_tabla[ord_col]
        sql += f" ORDER BY {tbl}.{ord_col} {ord_dir}"

    return sql + ";"
# =====================================================================
# MÓDULO 4: EJECUCIÓN PRINCIPAL (Integración de Tareas 1 y 2)
# =====================================================================
'''
if __name__ == "__main__":
    
    print("Iniciando compilador NL-SQL (Flujo modular)...")
    
    # --- 1. Carga Inicial (Se hace 1 vez) ---
    # Sincroniza 'relaciones_tablas.txt' con 'vocabulario.json'
    sincronizar_diccionario() 
    
    # Carga el Trie de Palabras (para prompt y validación)
    diccionario_valido_trie = generar_trie_desde_diccionario()
    
    # (P2) Tarea 2: Cargas el Esquema de la DB (¡Desde archivo!)esquema_db = cargar_esquema_db()
    with open("relaciones_tablas.txt", "r", encoding="utf-8") as f:
        relaciones_texto = f.read() 
    esquema_db, relaciones_fk = cargar_esquema_db(relaciones_texto)
    
    # (P2) Tarea 1: Creas el prompt para Whisper
    prompt_contexto = crear_prompt_para_whisper()
    
    # (P2) Carga el modelo de Whisper (UNA SOLA VEZ)
    print("\nCargando modelo Whisper (esto puede tardar)...")
    model_whisper = whisper.load_model("base")
    print("Modelo Whisper listo.")
    
    # -------------------------------------------------
    # --- INICIA EL PROCESO DEL COMPILADOR ---
    # -------------------------------------------------
    
    # (P2) Tarea 1: Transcripcicón REAL (desde transcribir_audio.py)
    nombre_archivo_audio = "c2.m4a"
    texto_transcrito = transcribir_audio(nombre_archivo_audio, prompt_contexto)
    if not texto_transcrito:
        print("No se pudo obtener la transcripción. Saliendo.")
    else:
        # (P1) Fase 1: Análisis Léxico
        tokens = analisis_lexico(texto_transcrito)
        
        # (P1) Fase 2: Análisis Sintáctico
        estructura_logica = analisis_sintactico(tokens)
        
        # (P2) Fase 3: Análisis Semántico y Generación de Código
        sql_final = analisis_semantico_y_generacion(estructura_logica, esquema_db, relaciones_fk)

        # --- Resultado Final ---
        print("\n" + "="*40)
        print(f"  Texto Original   : {texto_transcrito}")
        print(f"  Tokens Lematizados: {tokens}")
        print(f"  Estructura Lógica: {estructura_logica}")
        print(f"  SQL GENERADO     : {sql_final}")
        print("="*40)

        # Guardar la consulta SQL final
        nombre_archivo_para_gestor = "consulta_para_gestor.txt"
        with open(nombre_archivo_para_gestor, "w", encoding="utf-8") as f:
            f.write(sql_final)
        print(f"\nConsulta SQL final guardada en: {nombre_archivo_para_gestor}")
'''
if __name__ == "__main__":
    
    print("Iniciando compilador NL-SQL sin Whisper (modo texto)...")
    
    # --- 1. Carga Inicial ---
    sincronizar_diccionario() 
    diccionario_valido_trie = generar_trie_desde_diccionario()
    
    # Cargar esquema
    with open("relaciones_tablas.txt", "r", encoding="utf-8") as f:
        relaciones_texto = f.read() 
    esquema_db, relaciones_fk = cargar_esquema_db(relaciones_texto)

    # -------------------------------
    # LEER ARCHIVO DE CONSULTAS
    # -------------------------------
    archivo_consultas = "consultas.txt"

    if not os.path.exists(archivo_consultas):
        print(f"ERROR: No existe el archivo {archivo_consultas}")
        exit()

    with open(archivo_consultas, "r", encoding="utf-8") as f:
        consultas = [line.strip() for line in f.readlines() if line.strip()]

    print(f"\nSe encontraron {len(consultas)} consultas para procesar.\n")

    # Archivo donde se guardarán todos los resultados SQL
    salida = "sql_generado.txt"
    salida_f = open(salida, "w", encoding="utf-8")

    # -------------------------------
    # PROCESAR CADA CONSULTA
    # -------------------------------
    for consulta in consultas:
        print("\n--------------------------------------------")
        print("Consulta NL:", consulta)

        # FASE 1: Léxico
        tokens = analisis_lexico(consulta)

        # FASE 2: Sintáctico
        estructura_logica = analisis_sintactico(tokens)

        # FASE 3: Semántico
        sql_final = analisis_semantico_y_generacion(estructura_logica, esquema_db, relaciones_fk)

        # Mostrar
        print("SQL generado:", sql_final)

        # Guardar
        salida_f.write(f"-- Consulta NL: {consulta}\n")
        salida_f.write(sql_final + "\n\n")

    salida_f.close()
    print("\nProceso completado. SQL generado en:", salida)
