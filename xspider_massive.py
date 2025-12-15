import json
import os
import csv
import re
import time
from deep_translator import GoogleTranslator
from xcompiler import init_trie, ScientificLexer, ScientificParser, ScientificSemantic

# --- CONFIGURACIÓN DE RUTAS ---
# Apuntamos a la carpeta que me mostraste
PATH_TABLES = os.path.join("spider_data", "tables.json")
PATH_DEV = os.path.join("spider_data", "dev.json")

# ==========================================
# 1. HERRAMIENTAS DE ADAPTACIÓN (Helpers)
# ==========================================
def spider_schema_to_txt(spider_table_json, output_filename="relaciones_tablas.txt"):
    """Convierte el esquema JSON de Spider al formato .txt de tu compilador"""
    lines = []
    # Mapeo de índices a nombres reales
    tab_idx_to_name = {i: name.lower() for i, name in enumerate(spider_table_json["table_names_original"])}
    
    # Estructura temporal
    table_cols = {name: [] for name in tab_idx_to_name.values()}
    
    for idx, (table_idx, col_name) in enumerate(spider_table_json["column_names_original"]):
        if table_idx == -1: continue # Ignorar *
        
        t_name = tab_idx_to_name[table_idx]
        col_type = spider_table_json["column_types"][idx]
        
        # Limpieza: minúsculas y espacios por guiones bajos
        c_clean = col_name.strip().replace(" ", "_").lower()
        
        # Mapeo de tipos
        type_map = {"text": "string", "number": "int", "time": "date", "boolean": "bool"}
        t_clean = type_map.get(col_type, "string")
        
        table_cols[t_name].extend([c_clean, t_clean])

    # Generar líneas
    for t_name, cols in table_cols.items():
        if not cols: continue # Saltar tablas vacías si las hubiera
        line = f"{t_name}#" + "#".join(cols)
        lines.append(line)
        
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def normalize_sql(sql):
    """Normaliza para comparar (quita prefijos de tabla y espacios extra)"""
    if not sql: return ""
    s = sql.strip().lower()
    s = s.replace(";", "").replace("'", "").replace('"', "")
    # Quitar alias de tablas (ej: t1.col -> col)
    s = re.sub(r'\b\w+\.(\w+)\b', r'\1', s)
    # Estandarizar espacios
    s = re.sub(r'\s+', ' ', s)
    # Estandarizar comas
    s = s.replace(" ,", ",").replace(", ", ",")
    return s.strip()

def traducir_lote(textos):
    """Traduce una lista de textos (futura optimización). Por ahora uno por uno."""
    # Nota: GoogleTranslator tiene límites. Para 1000 queries, irá lento pero gratis.
    translator = GoogleTranslator(source='en', target='es')
    return [translator.translate(t) for t in textos]

# ==========================================
# 2. MOTOR DE PRUEBA MASIVA
# ==========================================
def ejecutar_massive_test(limite=50):
    print(f"📂 Cargando Spider dataset desde: {PATH_DEV}")
    
    if not os.path.exists(PATH_TABLES) or not os.path.exists(PATH_DEV):
        print("❌ Error: No encuentro los archivos JSON en la carpeta 'spider_data'.")
        return

    # Cargar JSONs
    with open(PATH_TABLES, 'r', encoding='utf-8') as f:
        tables_data = json.load(f)
    with open(PATH_DEV, 'r', encoding='utf-8') as f:
        dev_data = json.load(f)

    # Indexar esquemas por db_id
    schemas = {item['db_id']: item for item in tables_data}
    
    print(f"🚀 Iniciando Test Masivo con {limite} consultas...")
    print("   (Esto tomará tiempo debido a la traducción automática...)\n")
    
    archivo_csv = "resultados_spider_masivo.csv"
    
    # Contadores
    stats = {
        "total": 0,
        "aciertos": 0,
        "errores_sintaxis": 0,
        "errores_logica": 0,
        "errores_traduccion": 0
    }

    # Agrupar queries por DB para eficiencia
    queries_por_db = {}
    for q in dev_data[:limite]:
        db_id = q['db_id']
        if db_id not in queries_por_db: queries_por_db[db_id] = []
        queries_por_db[db_id].append(q)

    with open(archivo_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "DB", "Dificultad", "Pregunta (EN)", "Pregunta (ES)", "Gold SQL", "Generated SQL", "Estado", "Error"])

        total_global = 0
        
        for db_id, queries in queries_por_db.items():
            schema = schemas.get(db_id)
            if not schema: continue
            
            # 1. Configurar Entorno para esta DB
            spider_schema_to_txt(schema, "relaciones_tablas.txt")
            
            
            # Trie Dinámico: Inyectamos vocabulario de esta DB
            trie = init_trie()
            temp_sem = ScientificSemantic("relaciones_tablas.txt")
            translator = GoogleTranslator(source='en', target='es')
            print(f"   ⚙️ Inyectando vocabulario bilingüe para {db_id}...")
            for t, cols in temp_sem.schema.items():
                # 1. Inyectar nombre original (singer)
                trie.insert(t, "ENTITY", t)
                
                # 2. Inyectar traducción (cantante)
                t_es = translator.translate(t).lower()
                trie.insert(t_es, "ENTITY", t)
                # Truco: Inyectar plural simple (cantantes)
                if not t_es.endswith('s'): 
                    trie.insert(t_es + 's', "ENTITY", t)

                for c in cols:
                    # 1. Original (name, country)
                    trie.insert(c, "COL", c)
                    
                    # 2. Traducción (nombre, país)
                    c_es = translator.translate(c).lower()
                    trie.insert(c_es, "COL", c)
            
            # Vocabulario extra genérico (Parche rápido para mejorar traducción)
            extras = [("pais", "COL", "country"), ("edad", "COL", "age"), ("nombre", "COL", "name")]
            for w, type_, can in extras: trie.insert(w, type_, can)

            lexer = ScientificLexer(trie)
            parser = ScientificParser()
            sem = ScientificSemantic("relaciones_tablas.txt")

            # 2. Procesar Queries
            for q in queries:
                total_global += 1
                q_en = q['question']
                sql_gold = q['query']
                difficulty = q.get('difficulty', 'Unknown') # Spider a veces tiene metadata
                
                # Barra de progreso simple
                print(f"[{total_global}/{limite}] DB: {db_id} | Traduciendo...", end="\r")
                
                try:
                    # Traducción
                    q_es = GoogleTranslator(source='en', target='es').translate(q_en)
                    if not q_es: q_es = q_en # Fallback
                    
                    # Compilación
                    tokens = lexer.tokenize(q_es)
                    contract = parser.parse(tokens)
                    sql_gen = sem.generate_sql(contract)
                    
                    # Verificación
                    norm_gen = normalize_sql(sql_gen)
                    norm_gold = normalize_sql(sql_gold)
                    
                    # Determinación de Estado
                    if "-- Error" in sql_gen:
                        status = "ERROR_SYNTAX"
                        stats["errores_sintaxis"] += 1
                        error_msg = sql_gen
                    elif norm_gen == norm_gold:
                        status = "PASS"
                        stats["aciertos"] += 1
                        error_msg = ""
                    else:
                        status = "FAIL_LOGIC"
                        stats["errores_logica"] += 1
                        error_msg = "Mismatch"

                except Exception as e:
                    status = "EXCEPTION"
                    error_msg = str(e)
                    q_es = "(Error Traduccion)"
                    stats["errores_traduccion"] += 1
                
                # Escribir fila
                writer.writerow([total_global, db_id, difficulty, q_en, q_es, sql_gold, sql_gen, status, error_msg])
                stats["total"] += 1

    # --- REPORTE FINAL ---
    print("\n\n" + "="*60)
    print(f"📊 RESULTADOS DEL BENCHMARK SPIDER ({limite} muestras)")
    print("="*60)
    print(f"✅ Aciertos (Exact Match): {stats['aciertos']}")
    print(f"⚠️  Fallos Lógicos:        {stats['errores_logica']}")
    print(f"❌ Errores Sintaxis/Ambig: {stats['errores_sintaxis']}")
    print(f"💀 Excepciones:            {stats['errores_traduccion']}")
    print("-" * 60)
    acc = (stats['aciertos'] / stats['total']) * 100 if stats['total'] > 0 else 0
    print(f"🏆 ACCURACY: {acc:.2f}%")
    print(f"💾 Resultados detallados guardados en: {archivo_csv}")
    print("="*60)

if __name__ == "__main__":
    # ¡CÁMBIALO! Pon 1000 si tienes tiempo (tardará ~20 mins por la traducción)
    # Para probar rápido, déjalo en 20 o 50.
    ejecutar_massive_test(limite=50)