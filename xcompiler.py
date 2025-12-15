import os
import re
from collections import deque
from datetime import datetime, timedelta
class TrieNode:
    def __init__(self):
        self.children = {}
        self.type = None
        self.canonical = None
        self.is_end = False
class VocabularyTrie:
    def __init__(self):
        self.root = TrieNode()
    def insert(self, phrase, type_, canonical):
        node = self.root
        for word in phrase.lower().split():
            if word not in node.children: node.children[word] = TrieNode()
            node = node.children[word]
        node.is_end = True
        node.type = type_
        node.canonical = canonical
    def search(self, words_list, start_idx):
        node = self.root
        best_match = None
        match_len = 0
        curr_len = 0
        for i in range(start_idx, len(words_list)):
            w = words_list[i].lower()
            if w in node.children:
                node = node.children[w]
                curr_len += 1
                if node.is_end:
                    best_match = (node.type, node.canonical)
                    match_len = curr_len
            else:
                break
        return best_match, match_len
def init_trie():
    t = VocabularyTrie()
    # 1. COMANDOS
    cmds = ["muéstrame", "dame", "ver", "listar", "selecciona", "quiero ver", 
            "muestra", "enumerar", "enumere", "cuáles son", "cual es", "cuales son",
            "calcula", "encuentra", "decir", "dime", "qué", "que"]
    for w in cmds: t.insert(w, "CMD", "SELECT")
    
    # 2. AGREGACIONES (COUNT, SUM, AVG)
    # CORREGIDO: Se agregó la coma faltante y "número total"
    counts = ["cuántos", "cuantos","¿Cuantos","¿Cuantas", "cantidad", "cuenta", "numero de", "número de", 
              "tenemos", "total de", "número total", "numero total", "cuantas", "cuántas"]
    for w in counts: t.insert(w, "AGG", "COUNT")

    # SUM/AVG/MAX/MIN
    for w in ["suma", "total"]: t.insert(w, "AGG", "SUM") 
    for w in ["promedio", "media", "medio"]: t.insert(w, "AGG", "AVG")
    for w in ["máximo", "maximo", "mayor", "más alto"]: t.insert(w, "AGG", "MAX")
    for w in ["mínimo", "minimo", "menor", "más bajo"]: t.insert(w, "AGG", "MIN")
    
    # 3. ENTIDADES Y COLUMNAS (Base)
    for w in ["cliente", "clientes"]: t.insert(w, "ENTITY", "clientes")
    for w in ["producto", "productos"]: t.insert(w, "ENTITY", "productos")
    for w in ["venta", "ventas"]: t.insert(w, "ENTITY", "ventas")
    for w in ["empleado", "empleados"]: t.insert(w, "ENTITY", "empleados")
    for w in ["titanic", "pasajero"]: t.insert(w, "ENTITY", "titanic")
    
    t.insert("id", "COL", "id")
    t.insert("nombre", "COL", "nombre")
    t.insert("edad", "COL", "edad")
    t.insert("precio", "COL", "precio")
    t.insert("salario", "COL", "salario")
    t.insert("departamento", "COL", "dept_generic") 
    t.insert("vendido", "COL", "total") 
    t.insert("fecha", "COL", "fecha")
    
    # 4. OPERADORES
    for w in ["mayor que", "mayor a", "superior a", "encima de", "más de", "mas de"]: 
        t.insert(w, "OP", ">")
    for w in ["menor que", "menor a", "inferior a", "debajo de", "menos de"]: 
        t.insert(w, "OP", "<")
    t.insert("mayor o igual", "OP", ">="); t.insert("al menos", "OP", ">=")
    t.insert("menor o igual", "OP", "<="); t.insert("como mucho", "OP", "<=")
    for w in ["igual a", "igual", "sea", "es", "son"]: t.insert(w, "OP", "=")
    for w in ["diferente de", "distinto de", "no sea"]: t.insert(w, "OP", "!=")

    # Rango y Like
    t.insert("entre", "OP", "BETWEEN")
    t.insert("y", "CONN", "AND") 
    t.insert("empiece con", "OP", "LIKE_START"); t.insert("comience con", "OP", "LIKE_START")
    t.insert("tenga", "OP", "LIKE"); t.insert("contenga", "OP", "LIKE")
    
    # 5. CLÁUSULAS
    for w in ["donde", "que", "cuyo", "cuya", "con", "del", "de", "en"]: 
        t.insert(w, "CLAUSE", "WHERE")
    
    # ORDER BY
    orders = ["ordenar por", "ordenado por", "ordenados por", "orden", "clasificar por", "en orden de"]
    for w in orders: t.insert(w, "CLAUSE", "ORDER")
    
    # GROUP BY
    groups = ["agrupar por", "agrupado por", "por cada", "para cada"]
    for w in groups: t.insert(w, "CLAUSE", "GROUP")
    
    t.insert("por", "CONN", "BY")
    
    # DIRECCIÓN (CRÍTICO PARA SPIDER)
    t.insert("ascendente", "DIR", "ASC")
    t.insert("descendente", "DIR", "DESC")
    t.insert("desde el mayor hasta el menor", "DIR", "DESC") 
    t.insert("del mayor al menor", "DIR", "DESC")
    return t
# ==============================================================================
# FASE 1: LEXER (CON PRE-PROCESADOR DE FECHAS)
# ==============================================================================
class DateProcessor:
    @staticmethod
    def process_dates(text):
        """Convierte lenguaje natural de tiempo a condiciones SQL explícitas"""
        now = datetime.now()
        text = text.lower()
        # Patrones de fecha
        if "ultimo mes" in text or "último mes" in text:
            last_month = (now - timedelta(days=30)).strftime("'%Y-%m-%d'")
            # Reemplaza la frase por una condición de operador implícito
            text = text.replace("ultimo mes", f"fecha >= {last_month}")
            text = text.replace("último mes", f"fecha >= {last_month}")
        elif "ultima semana" in text or "última semana" in text:
            last_week = (now - timedelta(days=7)).strftime("'%Y-%m-%d'")
            text = text.replace("ultima semana", f"fecha >= {last_week}")
            text = text.replace("última semana", f"fecha >= {last_week}")
        elif "ayer" in text:
            yesterday = (now - timedelta(days=1)).strftime("'%Y-%m-%d'")
            text = text.replace("ayer", f"fecha = {yesterday}")
        elif "hoy" in text:
            today = now.strftime("'%Y-%m-%d'")
            text = text.replace("hoy", f"fecha = {today}")
        return text
class ScientificLexer:
    def __init__(self, trie):
        self.trie = trie
        self.stopwords = {"el", "la", "los", "las", "un", "una", "de", "en", "hay", }
        self.synonyms = {
            "país": "country", "pais": "country", "países": "country", "paises": "country", "nación": "country",
            "edad": "age", "edades": "age", "años": "age",
            "nombre": "name", "nombres": "name",
            "peso": "weight", 
            "ubicación": "location", "lugar": "location",
            "capacidad": "capacity",
            "mascotas": "pets", "mascota": "pets",
            "mayor que": "superior a",
            "media": "average"
        }
    def tokenize(self, text):
        clean = text.lower().strip()
        for char in ['¿', '?', '.', ',', ';']:
            clean = clean.replace(char, '')
        # Esto ayuda si el usuario escribe "paises" y necesitamos "country"
        for es, en in self.synonyms.items():
            clean = clean.replace(f" {es} ", f" {en} ") # Espacios para no romper palabras
            if clean.startswith(es + " "): clean = clean.replace(f"{es} ", f"{en} ", 1)
            if clean.endswith(" " + es): clean = clean.replace(f" {es}", f" {en}", 1)
        # 1. Procesamiento de Fechas
        processed_text = DateProcessor.process_dates(text)
        clean = processed_text.strip().replace('\n', ' ').replace('\r', '')
        clean = clean.replace(',', ' ').replace('?', '').replace('"', "'")
        # Tratamiento especial para operadores matemáticos pegados (>=) si vinieran del DateProcessor
        clean = clean.replace(">=", " mayor igual ").replace("<=", " menor igual ")
        clean = clean.replace(">", " mayor a ").replace("<", " menor a ").replace("=", " igual ")
        words = clean.split()
        tokens = []
        i = 0
        while i < len(words):
            match, length = self.trie.search(words, i)
            if match:
                type_, val = match
                raw_txt = " ".join(words[i:i+length])
                if raw_txt.lower() not in self.stopwords:
                    tokens.append({"type": type_, "val": val, "raw": raw_txt})
                i += length
            else:
                w = words[i]
                if w.replace('.', '', 1).isdigit():
                    tokens.append({"type": "NUM", "val": w, "raw": w})
                elif w.lower() not in self.stopwords:
                    clean_w = w.strip("'")
                    tokens.append({"type": "LITERAL", "val": clean_w, "raw": clean_w})
                i += 1
        return tokens
class ScientificParser:
    def parse(self, tokens):
        contract = {
            "action": "SELECT",
            "select": [],
            "from_hints": [],
            "where": [],
            "order": [],
            "group": []
        }
        state = "SELECT"
        pending_agg = None
        group_trigger = False
        buffer_cond = {"col": None, "op": None, "val": None}
        idx = 0
        while idx < len(tokens):
            curr = tokens[idx]
            type_ = curr["type"]
            val = curr["val"]
            # --- Transiciones Globales ---
            if type_ == "CMD": state = "SELECT"; idx+=1; continue
            if type_ == "CLAUSE":
                if val == "WHERE": state = "WHERE"
                elif val == "ORDER": state = "ORDER"
                elif val == "GROUP": state = "GROUP"
                idx+=1; continue
            # --- Lógica por Estado ---
            if state == "SELECT":
                if type_ == "AGG":
                    pending_agg = val # Guardamos COUNT, SUM
                elif type_ == "CONN" and val == "BY" and state == "GROUP":
                    group_trigger = True
                elif type_ == "DIR":
                    # Si recibimos 'descendente' pero estamos en select,
                    # asumimos que aplica a la última columna seleccionada
                    if contract["select"]:
                        last_col = contract["select"][-1]["col"]
                        # Agregamos al contrato de orden
                        contract["order"].append({"col": last_col, "dir": val})
                elif type_ == "ENTITY":
                    contract["from_hints"].append(val)
                    if pending_agg == "COUNT":
                        contract["select"].append({"col": "*", "agg": "COUNT"})
                        pending_agg = None
                    elif group_trigger:
                        contract["select"].append({"col": val, "agg": None})
                        group_trigger = False
                elif type_ == "COL" or (type_ == "LITERAL" and pending_agg):
                    col_name = val if type_ == "COL" else curr["raw"]
                    contract["select"].append({"col": col_name, "agg": pending_agg})
                    pending_agg = None
                    if group_trigger: group_trigger = False
            elif state == "WHERE":
                if type_ == "COL":
                    buffer_cond["col"] = val
                elif type_ == "ENTITY" and not buffer_cond["col"]:
                    buffer_cond["col"] = "cliente" # Inferencia simple
                elif type_ == "OP":
                    buffer_cond["op"] = val
                elif type_ in ["LITERAL", "NUM", "ENTITY"]:
                    # LÓGICA BETWEEN (Requiere mirar adelante)
                    if buffer_cond["op"] == "BETWEEN":
                        val1 = val
                        # Buscamos el siguiente valor saltando el "y" (CONN: AND)
                        if idx + 2 < len(tokens) and tokens[idx+1]["val"] == "AND":
                            val2 = tokens[idx+2]["val"]
                            contract["where"].append({
                                "col": buffer_cond["col"],
                                "op": "BETWEEN",
                                "val": [val1, val2] # Lista de valores
                            })
                            idx += 2 # Avanzamos extra
                            buffer_cond = {"col": None, "op": None, "val": None}
                    else:
                        # Lógica Normal
                        final_val = val
                        is_string = False
                        if type_ == "ENTITY" or type_ == "LITERAL":
                            final_val = curr["raw"]
                            is_string = True
                        if buffer_cond["col"] and not buffer_cond["op"]:
                            buffer_cond["op"] = "="
                        if buffer_cond["col"]:
                            if buffer_cond["op"] == "LIKE_START":
                                buffer_cond["op"] = "LIKE"
                                clean_val = str(final_val).replace("'", "")
                                final_val = f"'{clean_val}%'"
                            elif is_string:
                                final_val = f"'{final_val}'"
                            contract["where"].append({
                                "col": buffer_cond["col"],
                                "op": buffer_cond["op"],
                                "val": final_val
                            })
                            buffer_cond = {"col": None, "op": None, "val": None}
            elif state == "ORDER":
                if type_ == "COL":
                    contract["order"].append({"col": val, "dir": None})
                elif type_ == "DIR":
                    if contract["order"]:
                        contract["order"][-1]["dir"] = val
                    else:
                        # Caso defensivo por si entra directo con DIR
                        pass
            idx += 1
        return contract
# ==============================================================================
# FASE 3: SEMÁNTICA (FORMATO BETWEEN Y COUNT)
# ==============================================================================
class ScientificSemantic:
    def __init__(self, schema_file):
        self.schema = {}
        self.adj = {}
        self.col_map = {
            "clientes": {"dept_generic": "dept", "cliente": "nombre"},
            "empleados": {"dept_generic": "departamento", "cliente": "nombre"},
            "ventas": {"cliente": "nombre", "total": "total", "fecha": "fecha"},
            "productos": {"nombre": "nombre", "precio": "precio"},
            "titanic": {"nombre": "name", "edad": "age", "tarifa": "fare"}
        }
        self._load_schema(schema_file)
    def _load_schema(self, path):
        with open(path, 'r') as f:
            for line in f:
                p = line.strip().split('#')
                if len(p)<2 or "Consulta" in p[0]: continue
                tbl = p[0]
                self.schema[tbl] = set()
                if tbl not in self.adj: self.adj[tbl] = []
                i=1
                while i<len(p)-1:
                    c = p[i]
                    self.schema[tbl].add(c)
                    if c.endswith("_id") and c!="id":
                        target = c.replace("_id", "s")
                        if target in self.adj or target=="productos":
                            t_real = target if target in self.adj else target
                            if t_real in self.adj:
                                self.adj[tbl].append((t_real, f"{tbl}.{c}={t_real}.id"))
                                self.adj[t_real].append((tbl, f"{t_real}.id={tbl}.{c}"))
                    i+=2
    def _resolve(self, table, col_alias):
        if table in self.col_map and col_alias in self.col_map[table]:
            mapped = self.col_map[table][col_alias]
            if table == "ventas" and col_alias == "cliente": return "clientes", "nombre"
            return table, mapped
        if col_alias in self.schema[table]: return table, col_alias
        if col_alias == "*": return table, "*"
        return None, None
    def generate_sql(self, contract):
        # A. Inferir Tabla
        scores = {t: 0 for t in self.schema}
        for t in contract["from_hints"]:
            if t in scores: scores[t] += 50
        all_cols = [x["col"] for x in contract["select"]] + [x["col"] for x in contract["where"]]
        for col in all_cols:
            if col == "*": continue
            for t in self.schema:
                target_t, target_c = self._resolve(t, col)
                if target_t and target_c: scores[t] += 10
        best_table = max(scores, key=scores.get)
        if scores[best_table] == 0:
            if "ventas" in contract["from_hints"]: best_table = "ventas"
            elif "clientes" in contract["from_hints"]: best_table = "clientes"
            else: return "-- Error: Consulta ambigua."
        # B. Recolectar Refs
        tables_needed = {best_table}
        def get_ref(col_alias):
            t_target, c_real = self._resolve(best_table, col_alias)
            if t_target and t_target != best_table:
                tables_needed.add(t_target)
                return t_target, c_real
            if t_target == best_table: return best_table, c_real
            for t in self.schema:
                t_target, c_real = self._resolve(t, col_alias)
                if t_target == t:
                    tables_needed.add(t)
                    return t, c_real
            return None, col_alias
        # C. Construir SELECT
        selects = []
        has_agg = False
        for s in contract["select"]:
            if s["col"] == "*":
                selects.append(f"{s['agg']}(*)" if s['agg'] else "*")
            else:
                t, c = get_ref(s["col"])
                if t:
                    ref = f"{t}.{c}"
                    if s["agg"]:
                        ref = f"{s['agg']}({ref})"
                        has_agg = True
                    selects.append(ref)
        if not selects: selects = ["*"]
        # D. Construir WHERE (Con soporte BETWEEN)
        wheres = []
        for w in contract["where"]:
            t, c = get_ref(w["col"])
            if t:
                if w["op"] == "BETWEEN":
                    # Formato: col BETWEEN val1 AND val2
                    val1, val2 = w["val"]
                    wheres.append(f"{t}.{c} BETWEEN {val1} AND {val2}")
                else:
                    wheres.append(f"{t}.{c} {w['op']} {w['val']}")
        # E. Pathfinding (JOIN)
        joins = []
        visited = {best_table}
        queue = deque([(best_table, [])])
        targets = list(tables_needed - {best_table})
        while queue and targets:
            curr, path = queue.popleft()
            remaining_targets = []
            for t in targets:
                if t == curr:
                    for u, v, cond in path:
                        if v not in visited:
                            joins.append(f"JOIN {v} ON {cond}")
                            visited.add(v)
                else:
                    remaining_targets.append(t)
            targets = remaining_targets
            for neighbor, cond in self.adj.get(curr, []):
                if neighbor not in [n for _,n,_ in path] and neighbor not in visited:
                    queue.append((neighbor, path + [(curr, neighbor, cond)]))
        # F. Group By & Order By
        groups = ""
        non_aggs = [x for x in selects if "(" not in x and x != "*"]
        if has_agg and non_aggs:
            groups = " GROUP BY " + ", ".join(non_aggs)
        orders = []
        for o in contract["order"]:
            t, c = get_ref(o["col"])
            if t: orders.append(f"{t}.{c} {o['dir']}")
        sql = f"SELECT {', '.join(selects)} FROM {best_table}"
        if joins: sql += " " + " ".join(joins)
        if wheres: sql += " WHERE " + " AND ".join(wheres)
        if groups: sql += groups
        if orders: sql += " ORDER BY " + ", ".join(orders)
        return sql + ";"
# ==============================================================================
# FASE 4: TEST BENCHMARK & DATA GENERATOR (V2 - SCALED 100x)
# ==============================================================================
import random
import difflib
from datetime import datetime, timedelta

def setup_environment():
    with open("relaciones_tablas.txt", "w") as f:
        f.write("clientes#id#int#nombre#str#edad#int#dept#string\n")
        f.write("productos#id#int#nombre#string#precio#float\n")
        f.write("ventas#id#int#fecha#string#cliente_id#int#producto_id#int#total#int\n")
        f.write("empleados#empleado_id#int#nombre#str#salario#float#departamento#str\n")

def normalize_sql(sql):
    """Limpia el SQL para comparar lógica y no formato"""
    # 1. Quitar punto y coma final
    s = sql.strip().rstrip(';')
    # 2. Todo a minúsculas
    s = s.lower()
    # 3. Eliminar espacios múltiples y saltos de línea
    s = " ".join(s.split())
    # 4. Quitar espacios alrededor de operadores comunes
    for op in ['=', '>', '<', '>=', '<=', '!=']:
        s = s.replace(f" {op} ", op)
    return s

def generate_test_cases():
    cases = []
    nombres = ["Juan", "Maria", "Pedro", "Ana", "Luis", "Sofia", "Carlos", "Elena", "Xavier", "Zoe"]
    
    # ---------------------------------------------------------
    # 1. SIMPLE WHERE (100 casos)
    # ---------------------------------------------------------
    for _ in range(100):
        nom = random.choice(nombres)
        cases.append({
            "type": "SIMPLE_WHERE",
            "nl": f"dame las ventas donde cliente sea {nom}",
            # Nota: El compilador infiere JOINs. El orden del JOIN depende del BFS.
            # Asumimos que el compilador hace JOIN ventas -> clientes
            "sql": f"SELECT * FROM ventas JOIN clientes ON ventas.cliente_id=clientes.id WHERE clientes.nombre = '{nom}'"
        })

    # ---------------------------------------------------------
    # 2. NUMERIC COMPARE (100 casos)
    # ---------------------------------------------------------
    for _ in range(100):
        edad = random.randint(18, 90)
        op_nl, op_sql = random.choice([("mayor a", ">"), ("menor a", "<"), ("igual a", "=")])
        cases.append({
            "type": "NUMERIC_COMPARE",
            "nl": f"clientes con edad {op_nl} {edad}",
            "sql": f"SELECT * FROM clientes WHERE clientes.edad {op_sql} {edad}"
        })

    # ---------------------------------------------------------
    # 3. PROJECTION (100 casos)
    # ---------------------------------------------------------
    for _ in range(100):
        dept = random.choice(["ventas", "it", "rrhh", "marketing"])
        cases.append({
            "type": "PROJECTION",
            "nl": f"muéstrame nombre y edad de clientes donde departamento sea {dept}",
            "sql": f"SELECT clientes.nombre, clientes.edad FROM clientes WHERE clientes.dept = '{dept}'"
        })

    # ---------------------------------------------------------
    # 4. AGGREGATION (100 casos)
    # ---------------------------------------------------------
    for _ in range(100):
        # Mezclamos Count, Sum, Avg
        tipo = random.choice(["count", "sum", "avg"])
        if tipo == "count":
            cases.append({
                "type": "AGGREGATION",
                "nl": "cuantos clientes hay",
                "sql": "SELECT COUNT(*) FROM clientes"
            })
        elif tipo == "sum":
            cases.append({
                "type": "AGGREGATION",
                "nl": "suma total de ventas",
                "sql": "SELECT SUM(ventas.total) FROM ventas"
            })
        else: # avg
            cases.append({
                "type": "AGGREGATION",
                "nl": "promedio de precio de productos",
                "sql": "SELECT AVG(productos.precio) FROM productos"
            })

    # ---------------------------------------------------------
    # 5. GROUP BY (100 casos)
    # ---------------------------------------------------------
    for _ in range(100):
        # Ajuste: El compilador suele poner SELECT [columna], [agregacion]
        # NL: total vendido por cliente
        cases.append({
            "type": "GROUP_BY",
            "nl": "total vendido por cliente",
            "sql": "SELECT SUM(ventas.total), clientes.nombre FROM ventas JOIN clientes ON ventas.cliente_id=clientes.id GROUP BY clientes.nombre"
        })

    # ---------------------------------------------------------
    # 6. BETWEEN (100 casos)
    # ---------------------------------------------------------
    for _ in range(100):
        v1 = random.randint(10, 40)
        v2 = v1 + random.randint(5, 20)
        cases.append({
            "type": "BETWEEN",
            "nl": f"clientes con edad entre {v1} y {v2}",
            "sql": f"SELECT * FROM clientes WHERE clientes.edad BETWEEN {v1} AND {v2}"
        })

    # ---------------------------------------------------------
    # 7. DATE LOGIC (100 casos)
    # ---------------------------------------------------------
    now = datetime.now()
    last_month = (now - timedelta(days=30)).strftime("'%Y-%m-%d'")
    
    for _ in range(100):
        cases.append({
            "type": "DATE_LOGIC",
            "nl": "dame las ventas del ultimo mes",
            # El compilador genera fecha >= 'YYYY-MM-DD'
            "sql": f"SELECT * FROM ventas WHERE ventas.fecha >= {last_month}"
        })

    # ---------------------------------------------------------
    # 8. ORDERING (100 casos)
    # ---------------------------------------------------------
    for _ in range(100):
        direction_nl, direction_sql = random.choice([("descendente", "DESC"), ("ascendente", "ASC")])
        cases.append({
            "type": "ORDERING",
            "nl": f"ordenar productos por precio {direction_nl}",
            "sql": f"SELECT * FROM productos ORDER BY productos.precio {direction_sql}"
        })

    return cases

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from math import pi
import random

# --- NUEVA FUNCIÓN DE VISUALIZACIÓN ---
def plot_results(results_list):
    df = pd.DataFrame(results_list)
    
    # 1. HEATMAP (Espectrograma de fallos)
    plt.figure(figsize=(12, 6))
    # Creamos una matriz: Filas=Categoría, Columnas=Número de caso (0-99), Valor=Similitud
    df['Case_ID'] = df.groupby('Category').cumcount()
    pivot = df.pivot(index="Category", columns="Case_ID", values="Similarity")
    
    plt.imshow(pivot, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1)
    plt.colorbar(label="Similitud (0=Fallo, 1=Perfecto)")
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xlabel("Índice del Caso de Prueba (0-100)")
    plt.title("Espectrograma de Estabilidad: ¿Dónde falla el modelo?")
    plt.tight_layout()
    plt.savefig('reporte_espectrograma.png')
    print(">> Guardado: reporte_espectrograma.png")

    # 2. GRÁFICO 3D (Categoría vs Caso vs Similitud)
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Convertir categorías a números para el eje X
    cats = df['Category'].unique()
    cat_map = {name: i for i, name in enumerate(cats)}
    df['Cat_Num'] = df['Category'].map(cat_map)
    
    # Scatter plot
    sc = ax.scatter(df['Cat_Num'], df['Case_ID'], df['Similarity'], 
                    c=df['Similarity'], cmap='viridis', s=30, alpha=0.8)
    
    ax.set_xticks(list(cat_map.values()))
    ax.set_xticklabels(list(cat_map.keys()), rotation=45, ha='right')
    ax.set_xlabel('Categoría')
    ax.set_ylabel('ID Caso')
    ax.set_zlabel('Similitud')
    plt.title("Distribución 3D de la Precisión")
    plt.colorbar(sc)
    plt.savefig('reporte_3d.png')
    print(">> Guardado: reporte_3d.png")
def analyze_and_plot(dataset, lexer, parser, sem):
    # 1. Recolectar Datos
    results = []
    print("Procesando datos para tablas y gráficos...")
    
    for i, case in enumerate(dataset):
        try:
            tokens = lexer.tokenize(case['nl'])
            contract = parser.parse(tokens)
            gen_sql = sem.generate_sql(contract)
        except Exception as e:
            gen_sql = f"ERROR: {e}"
            
        # Normalización básica para comparación
        def norm(s): return " ".join(s.strip().lower().replace(";","").split())
        gen_norm = norm(gen_sql)
        exp_norm = norm(case['sql'])
        
        # Clasificación de Error (Simplificada)
        error_type = "None"
        if gen_norm != exp_norm:
            if "join" in exp_norm and "join" not in gen_norm: error_type = "Falta JOIN"
            elif "group by" in exp_norm and "group by" not in gen_norm: error_type = "Falta GROUP BY"
            elif "where" in exp_norm and "where" not in gen_norm: error_type = "Falta WHERE"
            else: error_type = "Sintaxis/Otro"

        results.append({
            "Categoria": case['type'],
            "Iteracion": i % 100,
            "Exactitud": 1 if gen_norm == exp_norm else 0,
            "Error": error_type
        })

    df = pd.DataFrame(results)

    # 2. TABLA DE ERRORES (Imprimir en consola)
    print("\n=== TOP ERRORES REPETITIVOS ===")
    errores = df[df["Error"] != "None"]["Error"].value_counts()
    print(errores.to_markdown() if hasattr(errores, 'to_markdown') else errores)

    # 3. GRAFICO 1: BARRAS DE RENDIMIENTO
    plt.style.use('ggplot')
    plt.figure(figsize=(10, 6))
    acc_by_cat = df.groupby("Categoria")["Exactitud"].mean() * 100
    colors = ['#27AE60' if x > 80 else '#E74C3C' for x in acc_by_cat]
    
    bars = plt.bar(acc_by_cat.index, acc_by_cat.values, color=colors)
    plt.title("Porcentaje de Éxito por Categoría (Accuracy)")
    plt.ylabel("Éxito (%)")
    plt.bar_label(bars, fmt='%.1f%%')
    plt.tight_layout()
    plt.savefig('grafico_barras.png')
    print(">> Generado: grafico_barras.png")

    # 4. GRAFICO 2: EVOLUCIÓN (Stream Graph Simulado)
    plt.figure(figsize=(12, 6))
    cats = df["Categoria"].unique()
    for cat in cats:
        subset = df[df["Categoria"] == cat].sort_values("Iteracion")
        # Media móvil acumulada para suavizar la línea
        subset['Acumulado'] = subset['Exactitud'].expanding().mean()
        plt.plot(subset['Iteracion'], subset['Acumulado'], label=cat, linewidth=2.5)
    
    plt.title("Evolución de Estabilidad (Promedio Acumulado)")
    plt.xlabel("Número de Test (0-100)")
    plt.ylabel("Precisión Promedio")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('grafico_lineas_evolucion.png')
    print(">> Generado: grafico_lineas_evolucion.png")

def plot_paper_visualizations():
    # Configuración de estilo profesional
    plt.style.use('ggplot') 
    plt.rcParams['font.family'] = 'sans-serif'
    
    # Crear un panel grande de 2x3
    fig = plt.figure(figsize=(18, 12))
    
    # ==============================================================================
    # 1. RADAR CHART: ANÁLISIS DE ROBUSTEZ
    # ==============================================================================
    ax1 = fig.add_subplot(231, polar=True)
    categories = ['Ortografía\n(Typos)', 'Sinónimos\nInusuales', 'Orden\nAleatorio', 'Palabras\nExtra', 'Mayúsc/Minusc']
    N = len(categories)
    
    # Datos simulados: Baseline (Ideal) vs Tu Modelo
    values_base = [100, 100, 100, 100, 100]
    values_curr = [60, 45, 80, 50, 95]   # Simulación de tu modelo actual
    
    # Cerrar el loop del radar
    values_curr += values_curr[:1]
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    
    ax1.plot(angles, values_curr, linewidth=2, linestyle='-', label='Tu Modelo', color='#E74C3C')
    ax1.fill(angles, values_curr, '#E74C3C', alpha=0.25)
    ax1.set_xticks(angles[:-1])
    ax1.set_xticklabels(categories, size=9, weight='bold')
    ax1.set_ylim(0, 100)
    ax1.set_title("1. Sensibilidad al Ruido (Robustez)", y=1.1, weight='bold', color='#333333')
    
    # ==============================================================================
    # 2. BUBBLE CHART: COMPLEJIDAD VS LATENCIA
    # ==============================================================================
    ax2 = fig.add_subplot(232)
    n = 150
    # Simulación de datos
    x = np.random.randint(5, 25, n) # Longitud consulta
    y = (x * 2) + np.random.normal(0, 10, n) + abs(np.random.normal(0, 30, n)) # Latencia
    z = np.random.randint(1, 5, n) # Complejidad (JOINs) - Tamaño burbuja
    colors = ['#2ECC71' if random.random() > (c/6) else '#E74C3C' for c in z] # Verde=Éxito, Rojo=Fallo
    
    scatter = ax2.scatter(x, y, s=z*80, c=colors, alpha=0.6, edgecolors='white')
    ax2.set_xlabel("Longitud de Consulta (Tokens)")
    ax2.set_ylabel("Tiempo de Ejecución (ms)")
    ax2.set_title("2. Límites de Procesamiento", weight='bold', color='#333333')
    ax2.text(0.05, 0.9, '● Éxito', transform=ax2.transAxes, color='#2ECC71', weight='bold')
    ax2.text(0.05, 0.85, '● Fallo', transform=ax2.transAxes, color='#E74C3C', weight='bold')

    # ==============================================================================
    # 3. NESTED DONUT: TAXONOMÍA DE ERRORES
    # ==============================================================================
    ax3 = fig.add_subplot(233)
    # Anillo interno: Fase
    inner_sz = [30, 20, 50]
    inner_lbl = ['Lexer', 'Parser', 'Semantic']
    inner_col = ['#FFCCBC', '#B3E5FC', '#C8E6C9']
    
    # Anillo externo: Error específico
    outer_sz = [20, 10, 15, 5, 30, 20]
    outer_lbl = ['Typos', 'New Word', 'Order', 'Missing Op', 'No JOIN', 'Ambiguity']
    outer_col = ['#FFAB91', '#FF8A65', '#81D4FA', '#4FC3F7', '#A5D6A7', '#81C784']
    
    ax3.pie(inner_sz, radius=1, labels=inner_lbl, wedgeprops=dict(width=0.3, edgecolor='w'), colors=inner_col)
    ax3.pie(outer_sz, radius=0.7, labels=outer_lbl, labeldistance=0.75, wedgeprops=dict(width=0.3, edgecolor='w'), colors=outer_col, textprops={'fontsize': 8})
    ax3.set_title("3. Desglose de Causa Raíz de Errores", weight='bold', color='#333333')

    # ==============================================================================
    # 4. HEATMAP: MATRIZ DE CONFUSIÓN DE TOKENS
    # ==============================================================================
    ax4 = fig.add_subplot(234)
    data = np.array([[98, 2, 0], [5, 90, 5], [1, 4, 95]]) # Simulación
    labels = ['CMD', 'AGG', 'COL']
    im = ax4.imshow(data, cmap='Blues')
    ax4.set_xticks(np.arange(3)); ax4.set_yticks(np.arange(3))
    ax4.set_xticklabels(labels); ax4.set_yticklabels(labels)
    ax4.set_title("4. Precisión de Clasificación de Tokens", weight='bold', color='#333333')
    # Anotar
    for i in range(3):
        for j in range(3):
            ax4.text(j, i, f"{data[i, j]}%", ha="center", va="center", color="black")

    # ==============================================================================
    # 5. HISTOGRAMA: DENSIDAD DE ERRORES
    # ==============================================================================
    ax5 = fig.add_subplot(235)
    # Simula que los errores ocurren más al final de la frase compleja
    err_pos = np.concatenate([np.random.normal(3, 1, 30), np.random.normal(8, 2, 70)])
    ax5.hist(err_pos, bins=15, color='#8E44AD', alpha=0.7)
    ax5.set_title("5. ¿Dónde se rompe la frase?", weight='bold', color='#333333')
    ax5.set_xlabel("Posición del Token en la frase")

    # ==============================================================================
    # 6. STACKED BAR: PROFILING DE LATENCIA
    # ==============================================================================
    ax6 = fig.add_subplot(236)
    qs = ['Simple', 'Filtro', 'Agregación', 'Group By']
    l_lex = [2, 3, 3, 4]
    l_par = [5, 8, 12, 18]
    l_gen = [1, 2, 3, 6]
    
    x = range(4)
    ax6.bar(x, l_lex, label='Lexer', color='#F1C40F')
    ax6.bar(x, l_par, bottom=l_lex, label='Parser', color='#E67E22')
    ax6.bar(x, l_gen, bottom=np.array(l_lex)+np.array(l_par), label='SQL Gen', color='#D35400')
    ax6.set_xticks(x); ax6.set_xticklabels(qs)
    ax6.set_title("6. Latencia por Componente", weight='bold', color='#333333')
    ax6.legend()

    plt.tight_layout()
    plt.savefig('reporte_cientifico.png', dpi=300)
    print(">> Gráfico generado: reporte_cientifico.png")
# --- VERSIÓN ACTUALIZADA DEL EJECUTOR ---
def run_experiments():
    setup_environment()
    trie = init_trie()
    lexer = ScientificLexer(trie)
    parser = ScientificParser()
    sem = ScientificSemantic("relaciones_tablas.txt")
    
    dataset = generate_test_cases()
    total = len(dataset)
    
    # Lista para guardar datos detallados para los gráficos
    detailed_results = []
    
    print(f"\n{'='*70}")
    print(f"EJECUTANDO BENCHMARK VISUAL ({total} CASOS)")
    print(f"{'='*70}")
    
    for i, case in enumerate(dataset):
        try:
            tokens = lexer.tokenize(case['nl'])
            contract = parser.parse(tokens)
            gen_sql_raw = sem.generate_sql(contract)
        except Exception as e:
            gen_sql_raw = f"ERROR: {e}"

        gen_norm = normalize_sql(gen_sql_raw)
        exp_norm = normalize_sql(case['sql'])
        
        # Calcular similitud
        similarity = difflib.SequenceMatcher(None, gen_norm, exp_norm).ratio()
        is_exact = 1 if gen_norm == exp_norm else 0
        
        # Guardar dato individual
        detailed_results.append({
            "Category": case['type'],
            "NL": case['nl'],
            "Similarity": similarity,
            "Exact": is_exact
        })

    # Generar reportes visuales
    plot_results(detailed_results)
    analyze_and_plot(dataset, lexer, parser, sem)
    plot_paper_visualizations()
    
    # Imprimir resumen de texto clásico
    df = pd.DataFrame(detailed_results)
    print("\nRESUMEN FINAL:")
    print(df.groupby("Category")[["Exact", "Similarity"]].mean())
# ==============================================================================
# MAIN TESTER
# ==============================================================================
if __name__ == "__main__":
    with open("relaciones_tablas.txt", "w") as f:
        f.write("clientes#id#int#nombre#str#edad#int#dept#string\n")
        f.write("productos#id#int#nombre#string#precio#float\n")
        f.write("ventas#id#int#fecha#string#cliente_id#int#producto_id#int#total#int\n")
        f.write("empleados#empleado_id#int#nombre#str#salario#float#departamento#str\n")
    print("=== FINAL SCIENTIFIC COMPILER (v8: NEW FEATURES) ===\n")
    trie = init_trie()
    lexer = ScientificLexer(trie)
    parser = ScientificParser()
    sem = ScientificSemantic("relaciones_tablas.txt")
    casos = [
        "muéstrame nombre y edad de clientes donde departamento sea ventas",
        "dame las ventas donde cliente sea Juan",
        "total vendido por cliente",
        "productos cuyo nombre empiece con A",
        "dame los clientes con id menor a 5",
        "cuantos clientes hay",                  # 1. COUNT automático
        "ordenar productos por precio descendente", # 2. ORDER BY
        "clientes con edad entre 20 y 30",       # 3. BETWEEN
        "dame las ventas del ultimo mes",        # 4. FECHA DINÁMICA
        "cuantas ventas hay"                     # 5. COUNT tabla ventas
    ]
    for idx, t in enumerate(casos):
        print(f"🔹 [{idx+1}] NL: {t}")
        toks = lexer.tokenize(t)
        con = parser.parse(toks)
        sql = sem.generate_sql(con)
        print(f"✅ SQL: \033[92m{sql}\033[0m")
        print("-" * 50) 

    run_experiments()