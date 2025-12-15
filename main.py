import os
from xcompiler import init_trie, ScientificLexer, ScientificParser, ScientificSemantic
from xaudio_service import transcribir
from xfuzzy_logic import FuzzyCorrector

def main():
    # --- CONFIGURACIÓN ---
    # Asegúrate de poner la ruta correcta a tu archivo de audio
    archivo_audio = r"C:\Users\S0\PROYECTOS\compilad\compilador\xpdesc.m4a"
    archivo_schema = "relaciones_tablas.txt"

    print("=== INICIANDO SISTEMA DE VOZ A SQL ===")

    # 1. Inicializar Fuzzy Logic y obtener Prompt
    corrector = FuzzyCorrector(archivo_schema)
    prompt_whisper = corrector.generar_prompt_contextual()

    # 2. Transcripción (Audio -> Texto Sucio)
    try:
        texto_whisper = transcribir(archivo_audio, prompt_whisper)
        print(f"\n📝 Transcripción Original: '{texto_whisper}'")
    except Exception as e:
        print(f"❌ Error en audio: {e}")
        return

    # 3. Corrección Difusa (Texto Sucio -> Texto Limpio)
    texto_limpio = corrector.corregir_frase(texto_whisper)
    print(f"✨ Transcripción Corregida: '{texto_limpio}'")

    # 4. Compilación (Texto Limpio -> SQL)
    print("\n⚙️ Compilando...")
    try:
        trie = init_trie()
        lexer = ScientificLexer(trie)
        parser = ScientificParser()
        sem = ScientificSemantic(archivo_schema)

        tokens = lexer.tokenize(texto_limpio)
        contract = parser.parse(tokens)
        sql = sem.generate_sql(contract)

        print(f"\n✅ SQL GENERADO:\n\033[92m{sql}\033[0m")
        
        # Opcional: Guardar log para el paper
        with open("resultado.log", "w") as f:
            f.write(f"Input: {texto_limpio}\nOutput: {sql}")

    except Exception as e:
        print(f"❌ Error de compilación: {e}")

if __name__ == "__main__":
    main()