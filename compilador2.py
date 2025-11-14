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

# Importar Whisper aquí para pasarlo al transcriptor
# (El parche de numba debe estar en transcribir_audio.py)
import whisper 

# =====================================================================
# MÓDULO 3: FASES DEL COMPILADOR (P1 Simulado + P2 Real)
# =====================================================================

# --- 3.1: FASE 1: Análisis Léxico (Persona 1 - Simulado) ---
# (La Persona 1 te entregará el código real de esta función)
def analisis_lexico(texto_transcrito):
    """
    (SIMULACIÓN DE PERSONA 1)
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

# --- 3.2: FASE 2: Análisis Sintáctico (Persona 1 - Simulado) ---

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
    }
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

def cargar_esquema_db():
    """
    (TU TAREA 2 - Utilidad)
    ¡MODIFICADO! Lee 'relaciones_tablas.txt' directamente.
    """
    esquema = {}
    archivo_esquema = "relaciones_tablas.txt"
    
    if not os.path.exists(archivo_esquema):
        print(f"--- (P2) Error: No se encontró '{archivo_esquema}' ---")
        return esquema

    try:
        with open(archivo_esquema, "r", encoding="utf-8") as f:
            for linea in f:
                partes = linea.strip().split('#')
                if len(partes) < 2: continue
                
                nombre_tabla = partes[0]
                columnas = {}
                # Lee las columnas de 2 en 2 (nombre, tipo)
                for i in range(1, len(partes), 2):
                    if i + 1 < len(partes):
                        columnas[partes[i]] = partes[i+1]
                
                if nombre_tabla not in esquema:
                    esquema[nombre_tabla] = {}
                esquema[nombre_tabla].update(columnas)
                
    except Exception as e:
        print(f"--- (P2) Error leyendo el esquema: {e} ---")
        
    print(f"--- (P2) Esquema de DB Cargado desde archivo: {list(esquema.keys())} ---")
    return esquema

def analisis_semantico_y_generacion(estructura_logica, esquema_db):
    """
    (TU TAREA 2 - PRINCIPAL)
    FASE 3: ANÁLISIS SEMÁNTICO Y GENERACIÓN DE CÓDIGO
    Valida el "Contrato" contra el esquema de la DB y genera el SQL.
    """
    print("\n--- FASE 3: Análisis Semántico y Generación de Código ---")
    
    # --- 1. Análisis Semántico (Validación) ---
    entidad_lematizada = estructura_logica.get("entidad")
    if not entidad_lematizada:
        return "-- Error Semántico: No se especificó ninguna entidad (tabla)."

    # Intentos para normalizar la entidad (ej: cliente -> clientes)
    nombre_tabla_real = MAPA_LEMA_A_TABLA.get(entidad_lematizada, entidad_lematizada)

    # Si no está, intentar autocorregir:
    if nombre_tabla_real not in esquema_db:
        # 1) probar con 's' al final (cliente -> clientes)
        cand = entidad_lematizada + "s"
        if cand in esquema_db:
            nombre_tabla_real = cand
        else:
            # 2) probar quitando 's' final (clientes -> cliente)
            cand2 = entidad_lematizada.rstrip("s")
            if cand2 in esquema_db:
                nombre_tabla_real = cand2
            else:
                # 3) buscar coincidencias cercanas entre claves del esquema (ej: cliente -> clientes)
                posibles = get_close_matches(entidad_lematizada, esquema_db.keys(), n=1, cutoff=0.6)
                if posibles:
                    nombre_tabla_real = posibles[0]
                else:
                    # 4) buscar forma plural o substring dentro de los nombres de las tablas
                    for t in esquema_db.keys():
                        if entidad_lematizada == t or entidad_lematizada in t or (entidad_lematizada + "s") in t:
                            nombre_tabla_real = t
                            break

    if nombre_tabla_real not in esquema_db:
        sugerencia = get_close_matches(nombre_tabla_real, esquema_db.keys(), n=1, cutoff=0.7)
        sug_texto = f" Quizás quisiste decir: {sugerencia[0]}?" if sugerencia else ""
        return f"-- Error Semántico: La tabla '{nombre_tabla_real}' no existe.{sug_texto}"
    
    columnas_tabla = esquema_db[nombre_tabla_real]
    atributos_sql = []
    
    accion = estructura_logica.get("accion", "SELECT")
    # Si la lista existe pero está vacía, usamos "*"
    atributos_a_mostrar = estructura_logica.get("atributos_mostrar") or ["*"]

    if accion == "COUNT":
        if len(atributos_a_mostrar) > 1 or atributos_a_mostrar[0].upper() != "COUNT(*)":
             return f"-- Error Semántico: No se puede usar 'COUNT' con atributos específicos (ej: '{atributos_a_mostrar[0]}'). Use 'mostrar' en su lugar."
        campos = "COUNT(*)"
    
    else: # (accion == "SELECT")
        for attr in atributos_a_mostrar:
            if attr == "*" or attr.upper().startswith("COUNT("):
                atributos_sql.append(attr)
                continue
            
            if attr not in columnas_tabla:
                sugerencia = get_close_matches(attr, columnas_tabla.keys(), n=1, cutoff=0.7)
                sug_texto = f" Quizás quisiste decir: {sugerencia[0]}?" if sugerencia else ""
                return f"-- Error Semántico: La columna '{attr}' no existe en '{nombre_tabla_real}'.{sug_texto}"
            
            atributos_sql.append(attr)
        campos = ", ".join(atributos_sql) if atributos_sql else "*"

    sql = f"SELECT {campos} FROM {nombre_tabla_real}"

    # --- 2. Generación de SQL (WHERE) ---
    clausulas_where = []
    for cond in estructura_logica.get("condiciones", []):
        attr = cond["atributo"]
        op = cond["operador"]
        val = str(cond["valor"])

        if attr not in columnas_tabla:
            sugerencia = get_close_matches(attr, columnas_tabla.keys(), n=1, cutoff=0.7)
            sug_texto = f" Quizás quisiste decir: {sugerencia[0]}?" if sugerencia else ""
            return f"-- Error Semántico: La columna de condición '{attr}' no existe en '{nombre_tabla_real}'.{sug_texto}"

        tipo_dato = columnas_tabla.get(attr)
        # validar si val es dígito o número con punto
        if re.fullmatch(r"\d+(\.\d+)?", val):
            formatted_val = val
        else:
            # eliminar comillas sobrantes y envolver entre comillas simples
            stripped = val.strip("\"' ")
            formatted_val = f"'{stripped}'"

        if tipo_dato in {"str", "string", "date"} and not (formatted_val.startswith("'") and formatted_val.endswith("'")):
            formatted_val = f"'{stripped}'"

        clausulas_where.append(f"{attr} {op} {formatted_val}")
        
    if clausulas_where:
        sql += " WHERE " + " AND ".join(clausulas_where)
        
    print("--- (P2) Validación Semántica y Generación OK ---")
    return sql + ";"


# =====================================================================
# MÓDULO 4: EJECUCIÓN PRINCIPAL (Integración de Tareas 1 y 2)
# =====================================================================

if __name__ == "__main__":
    
    print("Iniciando compilador NL-SQL (Flujo modular)...")
    
    # --- 1. Carga Inicial (Se hace 1 vez) ---
    # Sincroniza 'relaciones_tablas.txt' con 'vocabulario.json'
    sincronizar_diccionario() 
    
    # Carga el Trie de Palabras (para prompt y validación)
    diccionario_valido_trie = generar_trie_desde_diccionario()
    
    # (P2) Tarea 2: Cargas el Esquema de la DB (¡Desde archivo!)
    esquema_db = cargar_esquema_db()
    
    # (P2) Tarea 1: Creas el prompt para Whisper
    prompt_contexto = crear_prompt_para_whisper()
    
    # (P2) Carga el modelo de Whisper (UNA SOLA VEZ)
    print("\nCargando modelo Whisper (esto puede tardar)...")
    model_whisper = whisper.load_model("base")
    print("Modelo Whisper listo.")
    
    # -------------------------------------------------
    # --- INICIA EL PROCESO DEL COMPILADOR ---
    # -------------------------------------------------
    
    # (P2) Tarea 1: Transcripción REAL (desde transcribir_audio.py)
    nombre_archivo_audio = "g2.m4a"
    texto_transcrito = transcribir_audio(nombre_archivo_audio, prompt_contexto)
    if not texto_transcrito:
        print("No se pudo obtener la transcripción. Saliendo.")
    else:
        # (P1) Fase 1: Análisis Léxico
        tokens = analisis_lexico(texto_transcrito)
        
        # (P1) Fase 2: Análisis Sintáctico
        estructura_logica = analisis_sintactico(tokens)
        
        # (P2) Fase 3: Análisis Semántico y Generación de Código
        sql_final = analisis_semantico_y_generacion(estructura_logica, esquema_db)

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