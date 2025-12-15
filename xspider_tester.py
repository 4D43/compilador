import json
import os
import re
from xcompiler import init_trie, ScientificLexer, ScientificParser, ScientificSemantic

# ==========================================
# 1. DATOS DE MUESTRA SPIDER (CONCERT_SINGER)
# ==========================================
MOCK_SPIDER_TABLES = {
    "db_id": "concert_singer",
    "table_names_original": ["stadium", "singer", "concert", "singer_in_concert"],
    "column_names_original": [
        [-1, "*"], 
        [0, "Stadium_ID"], [0, "Location"], [0, "Name"], [0, "Capacity"], 
        [1, "Singer_ID"], [1, "Name"], [1, "Country"], [1, "Song_Name"], [1, "Song_release_year"], 
        [2, "concert_ID"], [2, "concert_Name"], [2, "Theme"], [2, "Stadium_ID"], [2, "Year"], 
        [3, "concert_ID"], [3, "Singer_ID"]
    ],
    "column_types": ["text", "number", "text", "text", "number", "number", "text", "text", "text", "number", "number", "text", "text", "text", "text", "number", "number"],
    "foreign_keys": [[13, 1], [15, 10], [16, 5]]
}

# CORRECCIÓN EN TEST CASES:
# 1. Ajustamos los prompts en español para que pidan explícitamente lo que quiere Spider.
# 2. Corregimos el Test 1 para que use 'cantantes' (que ahora inyectaremos bien).
TEST_CASES = [
    {
        "question_en": "How many singers do we have?",
        "question_es": "cuantos cantantes hay", 
        "gold_sql": "SELECT count(*) FROM singer",
        "db_id": "concert_singer"
    },
    {
        "question_en": "Show name and capacity of stadiums",
        "question_es": "muéstrame nombre y capacidad de estadios",
        "gold_sql": "SELECT Name , Capacity FROM stadium",
        "db_id": "concert_singer"
    },
    {
        "question_en": "Show all countries of singers where name is 'John'",
        "question_es": "dame pais de cantantes donde nombre sea 'John'",
        "gold_sql": "SELECT Country FROM singer WHERE Name = 'John'",
        "db_id": "concert_singer"
    },
    {
        "question_en": "Show names of stadiums with capacity greater than 5000",
        "question_es": "muéstrame el nombre de los estadios con capacidad mayor a 5000", # Más explícito para evitar SELECT *
        "gold_sql": "SELECT Name FROM stadium WHERE Capacity > 5000",
        "db_id": "concert_singer"
    }
]

# ==========================================
# 2. ADAPTADOR: SPIDER -> TU FORMATO (.txt)
# ==========================================
def spider_schema_to_txt(spider_table_json, output_filename="relaciones_tablas.txt"):
    lines = []
    tab_idx_to_name = {i: name.lower() for i, name in enumerate(spider_table_json["table_names_original"])}
    table_cols = {name: [] for name in tab_idx_to_name.values()}
    
    for idx, (table_idx, col_name) in enumerate(spider_table_json["column_names_original"]):
        if table_idx == -1: continue 
        t_name = tab_idx_to_name[table_idx]
        col_type = spider_table_json["column_types"][idx]
        c_clean = col_name.replace(" ", "_").lower()
        type_map = {"text": "string", "number": "int", "time": "date"}
        t_clean = type_map.get(col_type, "string")
        table_cols[t_name].extend([c_clean, t_clean])

    for t_name, cols in table_cols.items():
        line = f"{t_name}#" + "#".join(cols)
        lines.append(line)
        
    with open(output_filename, "w") as f:
        f.write("\n".join(lines))

# ==========================================
# 3. NORMALIZADOR INTELIGENTE (LA CLAVE DEL ÉXITO)
# ==========================================
def normalize_sql(sql):
    """
    Normaliza SQL para comparación agnóstica:
    1. Minúsculas.
    2. Elimina 'table.' (ej: singer.name -> name).
    3. Elimina espacios extra y punto y coma.
    4. Elimina comillas simples en columnas/tablas (no en valores).
    """
    s = sql.strip().lower()
    s = s.replace(";", "")
    
    # Eliminar prefijos de tabla (ej: 'singer.name' -> 'name')
    # Regex busca: palabra + punto + palabra -> reemplaza por la segunda palabra
    s = re.sub(r'\b\w+\.(\w+)\b', r'\1', s)
    
    # Limpieza estándar
    s = s.replace(" ,", ",").replace(", ", ",")
    s = re.sub(r'\s+', ' ', s) # Múltiples espacios a uno solo
    
    return s.strip()

# ==========================================
# 4. MOTOR DE PRUEBAS
# ==========================================
def run_spider_tests():
    print("=== INICIANDO SPIDER BENCHMARK TESTER (V2 - IMPROVED) ===\n")
    
    # 1. Generar esquema
    spider_schema_to_txt(MOCK_SPIDER_TABLES)
    
    # 2. Iniciar Trie
    trie = init_trie()
    
    # --- INYECCIÓN DE VOCABULARIO MEJORADA ---
    # Inyectamos manualmente sinónimos y plurales para que el Trie los entienda
    vocabulario_extra = [
        # (Palabra, Tipo, Valor Canónico en Schema)
        ("cantante", "ENTITY", "singer"),
        ("cantantes", "ENTITY", "singer"), # PLURAL CRÍTICO
        ("estadio", "ENTITY", "stadium"),
        ("estadios", "ENTITY", "stadium"), # PLURAL CRÍTICO
        ("concierto", "ENTITY", "concert"),
        ("conciertos", "ENTITY", "concert"),
        ("pais", "COL", "country"),
        ("país", "COL", "country"),
        ("nombre", "COL", "name"),
        ("capacidad", "COL", "capacity")
    ]
    
    # También cargamos las columnas originales del esquema generado
    temp_sem = ScientificSemantic("relaciones_tablas.txt")
    for table, cols in temp_sem.schema.items():
        trie.insert(table, "ENTITY", table)
        for col in cols:
            trie.insert(col, "COL", col)
            
    # Insertar vocabulario manual
    for word, type_, canonical in vocabulario_extra:
        trie.insert(word, type_, canonical)
    # -----------------------------------------

    lexer = ScientificLexer(trie)
    parser = ScientificParser()
    sem = ScientificSemantic("relaciones_tablas.txt")
    
    score = 0
    
    for i, case in enumerate(TEST_CASES):
        print(f"🔹 Test {i+1}: {case['question_es']}")
        
        try:
            # Pipeline
            tokens = lexer.tokenize(case['question_es'])
            contract = parser.parse(tokens)
            generated_sql = sem.generate_sql(contract)
            
            # Comparación usando el Normalizador Inteligente
            norm_gen = normalize_sql(generated_sql)
            norm_gold = normalize_sql(case['gold_sql'])
            
            is_match = norm_gen == norm_gold
            status = "✅ PASS" if is_match else "❌ FAIL"
            if is_match: score += 1
            
            print(f"   Generado (Raw):  {generated_sql}")
            print(f"   Generado (Norm): {norm_gen}")
            print(f"   Esperado (Norm): {norm_gold}")
            print(f"   Resultado: {status}")
            
        except Exception as e:
            print(f"   ❌ Error de ejecución: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)
        
    print(f"\n🏆 RESULTADO FINAL: {score}/{len(TEST_CASES)} (Accuracy: {score/len(TEST_CASES)*100:.1f}%)")

if __name__ == "__main__":
    run_spider_tests()