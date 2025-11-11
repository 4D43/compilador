import json
import os
import re
from difflib import get_close_matches
import collections
from rapidfuzz import process
from Trie import Trie, TrieNode

DICCIONARIO_JSON = "diccionario.json"
RELACIONES_TXT = "relaciones_tablas.txt"
APRENDIZAJE_JSON = "aprendizaje.json"  # nuevo: correcciones aprendidas por fuzzy logic

# ===============================
#  EXTRAER PALABRAS DE RELACIONES
# ===============================
def extraer_palabras_relaciones():
    palabras = set()
    if not os.path.exists(RELACIONES_TXT):
        return palabras
    with open(RELACIONES_TXT, "r", encoding="utf-8") as f:
        for linea in f:
            partes = linea.strip().split("#")
            for p in partes:
                if p.isalpha():
                    palabras.add(p.lower())
    return palabras


def cargar_diccionario():
    if os.path.exists(DICCIONARIO_JSON):
        with open(DICCIONARIO_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Soporta tu estructura actual
            palabras = set()
            if "palabras" in data:
                palabras = set(data["palabras"])
            else:
                # Extrae de tus claves y subclaves
                for grupo in data.values():
                    if isinstance(grupo, dict):
                        for lista in grupo.values():
                            palabras.update(map(str.lower, lista))
                    elif isinstance(grupo, list):
                        palabras.update(map(str.lower, grupo))
            return palabras
    return set()

def guardar_diccionario(palabras):
    """Guarda las palabras simples en un campo adicional sin romper tu estructura."""
    if os.path.exists(DICCIONARIO_JSON):
        with open(DICCIONARIO_JSON, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}

    data["palabras"] = sorted(list(palabras))

    with open(DICCIONARIO_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ===============================
#  SINCRONIZACIÓN Y TRIE
# ===============================
def sincronizar_diccionario():
    palabras_existentes = cargar_diccionario()
    palabras_nuevas = extraer_palabras_relaciones()
    actualizado = palabras_existentes.union(palabras_nuevas)
    guardar_diccionario(actualizado)
    return actualizado

def generar_trie_desde_diccionario():
    palabras = cargar_diccionario()
    trie = Trie()
    for palabra in palabras:
        trie.insert(palabra)
    return trie

# ===============================
#  FUZZY LOGIC
# ===============================
def sugerir_palabra_difusa(palabra, diccionario):
    if not diccionario:
        return palabra, 0
    resultado = process.extractOne(palabra, diccionario, score_cutoff=60)
    if resultado:
        mejor, score, _ = resultado
        return mejor, score
    return palabra, 0



def revisar_palabras(texto, palabras_validas):
    """
    Aplica fuzzy logic solo a palabras relevantes (entidades o atributos),
    detectando contexto semántico según el texto natural.
    """
    palabras = re.findall(r"\w+", texto.lower())
    texto_modificado = texto

    # Palabras que no deben analizarse
    stopwords = {
        "dame", "muestrame", "muestra", "listame", "listar", "obtén", "obten",
        "todos", "todas", "los", "las", "un", "una", "el", "la",
        "por", "de", "del", "en", "y", "para", "a", "que", "cuyo", "cuya"
    }

    # Operadores comparativos o de filtro — se ignoran en fuzzy
    operadores = {"menor", "mayor", "igual", "mayorigual", "menorigual", "entre"}

    # Contexto semántico para guiar el análisis
    contexto_entidad = {"dame", "muestrame", "muestra", "listar", "listame", "obtén", "obten", "todos", "todas"}
    contexto_atributo = {"con", "donde", "cuyo", "cuya", "tiene", "tengan", "que"}

    # Cargar entidades y atributos desde el diccionario
    entidades, atributos = set(), set()
    if os.path.exists(DICCIONARIO_JSON):
        with open(DICCIONARIO_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "entidades" in data:
                for entidad, cols in data["entidades"].items():
                    entidades.add(entidad.lower())
                    atributos.update([c.lower() for c in cols])

    ultima_palabra = None

    for palabra in palabras:
        # Saltar palabras irrelevantes o operadores
        if palabra in stopwords or palabra in operadores:
            ultima_palabra = palabra
            continue

        # Determinar contexto semántico según la palabra anterior
        if ultima_palabra in contexto_entidad:
            contexto = "entidad"
            vocab_referencia = entidades
        elif ultima_palabra in contexto_atributo:
            contexto = "atributo"
            vocab_referencia = atributos
        else:
            # No intentar corregir si no hay contexto claro
            ultima_palabra = palabra
            continue

        # Solo aplicar fuzzy si no está ya en las válidas o en el vocabulario
        if palabra not in vocab_referencia and vocab_referencia:
            mejor, score = sugerir_palabra_difusa(palabra, vocab_referencia)
            if mejor != palabra and score >= 70:
                print(f"🤖 [{contexto}] '{palabra}' ≈ '{mejor}' ({score:.1f}%) → reemplazado")
                texto_modificado = re.sub(rf"\b{palabra}\b", mejor, texto_modificado)
                actualizar_aprendizaje(palabra, mejor)

        ultima_palabra = palabra

    return texto_modificado

def actualizar_aprendizaje(palabra_erronea, palabra_correcta):
    """Guarda relaciones aprendidas (fuzzy learning)"""
    data = {}
    if os.path.exists(APRENDIZAJE_JSON):
        try:
            with open(APRENDIZAJE_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    data[palabra_erronea.lower()] = palabra_correcta.lower()

    with open(APRENDIZAJE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"🧠 Aprendido: '{palabra_erronea}' → '{palabra_correcta}' guardado en {APRENDIZAJE_JSON}")
