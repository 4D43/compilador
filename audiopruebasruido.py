import whisper
import os
import numpy as np
from pydub import AudioSegment
from jiwer import wer, cer

# --- Transcripción con Whisper ---
def transcribir_audio(ruta_audio):
    if not os.path.exists(ruta_audio):
        print(f"Error: El archivo de audio no se encontró en '{ruta_audio}'")
        return ""

    print("Cargando el modelo Whisper (esto puede tardar la primera vez)...")
    model = whisper.load_model("base")
    print("Modelo Whisper cargado. Transcribiendo audio...")

    result = model.transcribe(ruta_audio)
    transcripcion = result["text"]
    print("\n--- Transcripción ---")
    print(transcripcion)
    return transcripcion

# --- Añadir ruido con SNR deseado ---
def agregar_ruido(ruta_audio, snr_db, nombre_salida):
    audio = AudioSegment.from_wav(ruta_audio)
    muestras = np.array(audio.get_array_of_samples()).astype(np.float32)

    # Calcular RMS del audio original
    rms_senal = np.sqrt(np.mean(muestras**2))
    rms_ruido = rms_senal / (10**(snr_db / 20))

    # Generar ruido blanco
    ruido = np.random.normal(0, rms_ruido, muestras.shape)
    audio_con_ruido = muestras + ruido
    audio_con_ruido = np.clip(audio_con_ruido, -32768, 32767).astype(np.int16)

    # Guardar audio con ruido
    audio_final = audio._spawn(audio_con_ruido.tobytes())
    audio_final.export(nombre_salida, format="wav")
    return nombre_salida

# --- Evaluar precisión con referencia ---
def evaluar_transcripcion(ruta_audio, referencia):
    prediccion = transcribir_audio(ruta_audio)
    print(f"\nReferencia: {referencia}")
    print(f"Predicción: {prediccion}")
    print(f"WER: {wer(referencia, prediccion):.3f}")
    print(f"CER: {cer(referencia, prediccion):.3f}")

# --- MAIN ---
if __name__ == "__main__":
    ruta_original = "grabacion.wav"
    referencia_textual = "Dame todos los nombres de clientes con ID menor a 5."

    print("\n📌 Evaluación del audio original (sin ruido):")
    evaluar_transcripcion(ruta_original, referencia_textual)

    for snr in [10, 5, 4, 3, 2, 1]:
        ruta_ruido = f"grabacion_ruido_{snr}dB.wav"
        agregar_ruido(ruta_original, snr, ruta_ruido)
        print(f"\n📌 Evaluación con ruido SNR={snr} dB:")
        evaluar_transcripcion(ruta_ruido, referencia_textual)
