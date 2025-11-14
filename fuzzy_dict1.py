import json
import os
import re
import string
from Trie import Trie # Asumiendo que Trie.py existe en la misma carpeta

VOCABULARIO_JSON = "vocabulario.json"
RELACIONES_TABLAS = "relaciones_tablas.txt"

def sincronizar_diccionario():
    """
    Lee 'relaciones_tablas.txt', extrae todas las palabras únicas 
    (tablas, columnas) y las guarda en 'vocabulario.json'.
    """
    if not os.path.exists(RELACIONES_TABLAS):
        print(f"Error: No se encontró '{RELACIONES_TABLAS}'. No se puede sincronizar.")
        return

    print(f"Sincronizando vocabulario desde '{RELACIONES_TABLAS}'...")
    
    palabras_validas = set()
    
    # Palabras clave de SQL que queremos ignorar
    ignorar_palabras = {"int", "str", "string", "float", "date"}

    try:
        with open(RELACIONES_TABLAS, "r", encoding="utf-8") as f:
            for linea in f:
                # Usamos re.split para separar por # y por . (para casos como 'clientes.id')
                partes = re.split(r'[#.]', linea.lower())
                for palabra in partes:
                    palabra_limpia = palabra.strip(string.punctuation).strip()
                    if palabra_limpia and palabra_limpia not in ignorar_palabras:
                        palabras_validas.add(palabra_limpia)

        # Guardar en el archivo JSON
        with open(VOCABULARIO_JSON, "w", encoding="utf-8") as f:
            json.dump(list(palabras_validas), f, indent=4)
            
        print(f"Sincronización completa. {len(palabras_validas)} palabras guardadas en '{VOCABULARIO_JSON}'.")

    except Exception as e:
        print(f"Error durante la sincronización: {e}")

def generar_trie_desde_diccionario():
    """
    Carga 'vocabulario.json' y construye un objeto Trie 
    con todas las palabras válidas.
    """
    trie = Trie()
    if not os.path.exists(VOCABULARIO_JSON):
        print(f"Advertencia: '{VOCABULARIO_JSON}' no encontrado. Ejecutando sincronización...")
        sincronizar_diccionario() # Intentamos crearlo
        if not os.path.exists(VOCABULARIO_JSON):
            print("Error: No se pudo crear el vocabulario. Trie estará vacío.")
            return trie

    try:
        with open(VOCABULARIO_JSON, "r", encoding="utf-8") as f:
            palabras = json.load(f)
            for palabra in palabras:
                trie.insert(palabra)
        print(f"Trie generado con {len(palabras)} palabras.")
        return trie
    except Exception as e:
        print(f"Error al cargar el Trie desde JSON: {e}")
        return trie

def crear_prompt_para_whisper():
    print("Creando prompt de contexto para Whisper...")
    
    # 1. Obtenemos el Trie con todas las palabras
    trie = generar_trie_desde_diccionario()
    palabras_validas = trie.get_all_words()
    
    if not palabras_validas:
        print("Advertencia: No se cargaron palabras para el prompt.")
        return ""

    palabras_filtradas = [p for p in palabras_validas if len(p) > 2]
    
    # 3. Creamos la cadena de texto (el prompt)
    prompt_contexto = ", ".join(palabras_filtradas)
    
    print(f"Prompt generado ({len(prompt_contexto)} caracteres).")
    return prompt_contexto
