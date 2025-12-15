import sys
import types
import os
import whisper

# --- TU PARCHE DE NUMBA (Mantenido intacto) ---
fake_numba = types.ModuleType("numba")
def fake_jit(*args, **kwargs):
    def decorator(func): return func
    return decorator
fake_numba.jit = fake_jit
fake_numba.cuda = types.ModuleType("numba.cuda")
fake_numba.core = types.ModuleType("numba.core")
sys.modules["numba"] = fake_numba
sys.modules["numba.cuda"] = fake_numba.cuda
sys.modules["numba.core"] = fake_numba.core
# ----------------------------------------------

def transcribir(ruta_audio, prompt_contexto):
    if not os.path.exists(ruta_audio):
        raise FileNotFoundError(f"Audio no encontrado: {ruta_audio}")

    print("🎧 Cargando modelo Whisper...")
    # Usamos "base" como en tu código original, para velocidad
    model = whisper.load_model("base") 
    
    print(f"🎙️ Transcribiendo con prompt contextual ({len(prompt_contexto)} chars)...")
    result = model.transcribe(
        ruta_audio,
        prompt=prompt_contexto,
        language="es",
        fp16=False
    )
    return result["text"]