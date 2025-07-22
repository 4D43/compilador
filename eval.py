import json
from compilador import compilador_nl2sql_texto
from difflib import SequenceMatcher

def cargar_testset(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def normalizar_sql(sql):
    return ' '.join(sql.strip().lower().split())

def evaluar_sql_generado(nl_query, expected_sql):
    generated_sql = compilador_nl2sql_texto(nl_query)
    expected = normalizar_sql(expected_sql)
    generated = normalizar_sql(generated_sql)
    exact_match = expected == generated
    similarity = SequenceMatcher(None, expected, generated).ratio()
    return exact_match, similarity, generated

def evaluar_sobre_dataset(path_testset):
    testcases = cargar_testset(path_testset)
    total = len(testcases)
    exact_matches = 0
    similitudes = []

    for idx, caso in enumerate(testcases):
        print(f"\n🧪 Test {idx+1}: {caso['nl_query']}")
        exact, sim, generado = evaluar_sql_generado(caso["nl_query"], caso["expected_sql"])
        similitudes.append(sim)
        if exact:
            print("++++++++Match exacto")
            exact_matches += 1
        else:
            print("--------Diferencia")
            print("Esperado :", caso["expected_sql"])
            print("Generado :", generado)
            print(f"🔍 Similaridad: {sim:.2f}")

    exactitud = exact_matches / total * 100
    promedio_sim = sum(similitudes) / total * 100
    print(f"\n +++++++++Exact match accuracy: {exactitud:.2f}%")
    print(f"++++++++++++++Similarity (avg): {promedio_sim:.2f}%")

if __name__ == "__main__":
    evaluar_sobre_dataset("testset.json")
