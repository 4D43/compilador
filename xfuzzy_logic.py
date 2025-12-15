import difflib
import json
import os
from xcompiler import init_trie  # Importamos el Trie de tu compilador

class FuzzyCorrector:
    def __init__(self, schema_file="relaciones_tablas.txt"):
        self.vocabulario = self._cargar_vocabulario(schema_file)

    def _cargar_vocabulario(self, schema_file):
        """
        Extrae palabras clave del Trie del compilador Y del esquema de la BD.
        """
        words = set()
        
        # 1. Palabras fijas del compilador (SELECT, WHERE, etc.)
        # Extraemos recorriendo el Trie (o hardcodeando las claves críticas)
        # Para el paper, es mejor extraerlas dinámicamente si es posible, 
        # pero por simplicidad usaremos la lista crítica definida en init_trie:
        keywords = [
            "muéstrame", "dame", "ver", "listar", "selecciona", "quiero",
            "cuántos", "cuantos", "cantidad", "cuenta", "suma", "total", "promedio",
            "mayor", "menor", "igual", "entre", "donde", "ordenar", "agrupar", 
            "ascendente", "descendente", "empiece", "comience"
        ]
        words.update(keywords)

        # 2. Palabras dinámicas del esquema (Tablas y Columnas)
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                for line in f:
                    parts = line.strip().split('#')
                    if len(parts) > 0:
                        words.add(parts[0]) # Tabla
                        # Columnas (saltando tipos de datos)
                        for i in range(1, len(parts), 2):
                            words.add(parts[i])
        
        return list(words)

    def corregir_frase(self, texto_sucio):
        """
        Toma el texto de Whisper y corrige palabras fonéticamente similares.
        Ej: "clien tes" -> "clientes"
        """
        tokens = texto_sucio.lower().split()
        tokens_corregidos = []

        for token in tokens:
            # Si es número o está en el vocabulario exacto, se queda igual
            if token.isdigit() or token in self.vocabulario:
                tokens_corregidos.append(token)
                continue

            # Buscamos la palabra más parecida (Similarity > 0.8)
            matches = difflib.get_close_matches(token, self.vocabulario, n=1, cutoff=0.8)
            
            if matches:
                # Si hay match, reemplazamos
                print(f"   🔧 Corrección Fuzzy: '{token}' -> '{matches[0]}'")
                tokens_corregidos.append(matches[0])
            else:
                # Si no, asumimos que es un literal (ej. 'Juan')
                tokens_corregidos.append(token)
        
        return " ".join(tokens_corregidos)

    def generar_prompt_contextual(self):
        """Genera el string para ayudar a Whisper"""
        return f"Consulta SQL técnica. Vocabulario: {', '.join(self.vocabulario)}."