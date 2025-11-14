import sys
import types
import os

fake_numba = types.ModuleType("numba")

def fake_jit(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

fake_numba.jit = fake_jit
fake_numba.cuda = types.ModuleType("numba.cuda")
fake_numba.core = types.ModuleType("numba.core")

sys.modules["numba"] = fake_numba
sys.modules["numba.cuda"] = fake_numba.cuda
sys.modules["numba.core"] = fake_numba.core

import whisper

from fuzzy_dict1 import crear_prompt_para_whisper


def transcribir_audio(ruta_audio, prompt_contexto):
    if not os.path.exists(ruta_audio):
        print(f"Error: El archivo de audio no se encontró en '{ruta_audio}'")
        return ""

    try:
        print("Cargando el modelo Whisper (esto puede tardar la primera vez)...")
        model = whisper.load_model("base")
        print("Modelo Whisper cargado. Transcribiendo audio...")

        result = model.transcribe(
            ruta_audio,
            prompt=prompt_contexto,
            language="es",
            fp16=False
        )

        texto = result["text"]
        print("\n--- Transcripción Completa ---")
        print(texto)
        return texto

    except Exception as e:
        print(f"Ocurrió un error durante la transcripción: {e}")
        return ""


if __name__ == "__main__":
    prompt_final = crear_prompt_para_whisper()

    nombre_archivo_audio = r"C:\Users\S0\PROYECTOS\compilad\compilador\g2.m4a"
    texto = transcribir_audio(nombre_archivo_audio, prompt_final)

    if texto:
        with open("transcripcion.txt", "w", encoding="utf-8") as f:
            f.write(texto)

        print("\nTranscripción guardada en 'transcripcion.txt'")
    else:
        print("No se generó ninguna transcripción.")
