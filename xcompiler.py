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