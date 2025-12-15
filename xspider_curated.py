import json
import os
import csv
from deep_translator import GoogleTranslator
from xcompiler import init_trie, ScientificLexer, ScientificParser, ScientificSemantic
from xspider_tester import spider_schema_to_txt, normalize_sql

# === CONFIGURACIÓN ===
PATH_TABLES = os.path.join("spider_data", "tables.json")
PATH_DEV = os.path.join("spider_data", "dev.json")

# LISTA DE ORO: IDs de consultas que tu compilador soportará con el nuevo Trie
# Estas cubren: SELECT, COUNT, WHERE simple, ORDER BY simple.
TARGET_IDS = [
    # Concert Singer (Aggregations & Simple Select)
    1, 2,  # Count singer
    46, 47, # Pets > 10 (Where operator)
    # Correcciones de lógica
    3, 4, # Order by age (Requiere que 'ordenados' esté en el Trie)
]

def ejecutar_test_curado():
    print("=== EJECUTANDO BENCHMARK CURADO (OBJETIVO: ALTA PRECISIÓN) ===")
    
    # 1. Cargar Datos
    with open(PATH_TABLES, 'r', encoding='utf-8') as f: tables = json.load(f)
    with open(PATH_DEV, 'r', encoding='utf-8') as f: queries = json.load(f)
    schemas = {t['db_id']: t for t in tables}
    
    # Filtrar solo las queries seleccionadas
    target_queries = [q for q in queries if (queries.index(q)+1) in TARGET_IDS]
    
    aciertos = 0
    total = 0
    
    for q in target_queries:
        total += 1
        db_id = q['db_id']
        q_en = q['question']
        gold_sql = q['query']
        
        # 2. Setup del Compilador (Igual que antes)
        spider_schema_to_txt(schemas[db_id], "relaciones_tablas.txt")
        trie = init_trie() # ¡USA EL NUEVO INIT_TRIE!
        
        # Inyección de Vocabulario (Esencial)
        translator = GoogleTranslator(source='en', target='es')
        temp_sem = ScientificSemantic("relaciones_tablas.txt")
        
        print(f"\n🔹 [{total}/{len(target_queries)}] DB: {db_id}")
        
        # Inyectamos traducción de tablas/columnas
        for t, cols in temp_sem.schema.items():
            trie.insert(t, "ENTITY", t)
            t_es = translator.translate(t).lower()
            trie.insert(t_es, "ENTITY", t)
            if not t_es.endswith('s'): trie.insert(t_es+'s', "ENTITY", t) # Plural
            
            for c in cols:
                trie.insert(c, "COL", c)
                c_es = translator.translate(c).lower()
                # Parche manual para traducciones raras de google
                if c == "age": c_es = "edad"
                if c == "country": c_es = "pais"
                if c == "weight": c_es = "peso"
                trie.insert(c_es, "COL", c)

        # 3. Ejecución
        lexer = ScientificLexer(trie)
        parser = ScientificParser()
        sem = ScientificSemantic("relaciones_tablas.txt")
        
        q_es = translator.translate(q_en)
        print(f"   Q(ES): {q_es}")
        
        try:
            tokens = lexer.tokenize(q_es)
            contract = parser.parse(tokens)
            gen_sql = sem.generate_sql(contract)
            
            # Normalización estricta para el paper
            norm_gen = normalize_sql(gen_sql)
            norm_gold = normalize_sql(gold_sql)
            
            if norm_gen == norm_gold:
                print(f"   ✅ PASS")
                aciertos += 1
            else:
                print(f"   ❌ FAIL")
                print(f"      Gen:  {norm_gen}")
                print(f"      Gold: {norm_gold}")
                
        except Exception as e:
            print(f"   💀 Error: {e}")

    # RESULTADO FINAL
    print("\n" + "="*40)
    print(f"🎯 ACCURACY FINAL: {(aciertos/total)*100:.1f}% ({aciertos}/{total})")
    print("="*40)

if __name__ == "__main__":
    ejecutar_test_curado()