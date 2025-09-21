import sys
import types

# Crear un "numba falso" para que Whisper no falle
fake_numba = types.ModuleType("numba")

# jit falso: simplemente devuelve la función sin modificarla
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

import whisper
import os

ruta_audio = "grabacion.wav"

def transcribir_audio(ruta_audio):
    if not os.path.exists(ruta_audio):
        print(f"Error: El archivo de audio no se encontró en '{ruta_audio}'")
        return ""

    # try: # Comenta esta línea
    print("Cargando el modelo Whisper (esto puede tardar la primera vez)...")
    model = whisper.load_model("base")
    print("Modelo Whisper cargado. Transcribiendo audio...")

    result = model.transcribe(ruta_audio)

    transcripcion = result["text"]
    print("\n--- Transcripción Completa ---")
    print(transcripcion)
    return transcripcion

    # except Exception as e: # Comenta esta línea
    #    print(f"Ocurrió un error durante la transcripción: {e}") # Comenta esta línea
    #    return ""

if __name__ == "__main__":
    nombre_archivo_audio = "grabacion.wav"
    transcripcion_final = transcribir_audio(nombre_archivo_audio)

    if transcripcion_final:
        with open("transcripcion.txt", "w", encoding="utf-8") as f:
            f.write(transcripcion_final)
        print("\nTranscripción guardada en 'transcripcion.txt'")