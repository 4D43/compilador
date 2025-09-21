
import re
import string
import os
from collections import defaultdict

class NL2SOCompiler:

    def __init__(self, config):
        self.config = config

    def _preprocesar(self, texto):
        texto = texto.lower()
        mapeo_operadores = {
            r"\bmayor o igual que\b": ">=", r"\bmenor o igual que\b": "<=",
            r"\bmayor que\b": ">", r"\bmenor que\b": "<",
            r"\bigual a\b": "=", r"\bigual\b": "=",
            r"\bno es\b": "!=", r"\bdiferente de\b": "!="
        }
        for frase, reemplazo in mapeo_operadores.items():
            texto = re.sub(frase, reemplazo, texto)
        return texto

    def analisis_lexico(self, texto):
        texto = self._preprocesar(texto)
        palabras = texto.split()
        tokens = []
        for palabra in palabras:
            palabra_limpia = palabra.strip(string.punctuation)
            if not palabra_limpia:
                continue
            encontrado = False
            for tipo, palabras_clave in self.config["palabras_clave"].items():
                if palabra_limpia in palabras_clave:
                    tokens.append((tipo.upper(), palabra_limpia))
                    encontrado = True
                    break
            if not encontrado:
                tokens.append(("PALABRA", palabra_limpia))
        return tokens

    def analisis_sintactico(self, tokens):
        estructura = {"accion": None, "proceso": None, "recurso": None, "entidad": None}

        # tokens 
        palabras = [valor for _, valor in tokens]

        # Detectar acción
        for tipo, valor in tokens:
            if tipo == "ACCION" and estructura["accion"] is None:
                estructura["accion"] = valor

        # Detectar entidad
        if "grafo" in palabras:
            estructura["entidad"] = "grafo"
        if "deadlock" in palabras:
            estructura["entidad"] = "deadlock"
            
        texto = " ".join(palabras)

        match_proc = re.search(r"proceso\s+(\d+)", texto)
        if match_proc:
            estructura["proceso"] = match_proc.group(1)

        match_recurso = re.search(r"recurso\s+(\d+)", texto)
        if match_recurso:
            estructura["recurso"] = match_recurso.group(1)

        return estructura

    def generar_comando_so(self, estructura):
        """Traduce la estructura sintáctica a un comando interno."""
        accion = estructura.get("accion")
        pid = estructura.get("proceso")
        rid = estructura.get("recurso")
        entidad = estructura.get("entidad")

        # ---- CREATE ----
        if accion in ["crear", "iniciar"]:
            if pid:
                return f"CREATE PROCESS {pid}"
            if rid:
                return f"CREATE RESOURCE {rid}"

        # ---- REQUEST ----
        if accion in ["solicita", "pide"]:
            if pid and rid:
                return f"REQUEST {pid} {rid}"

        # ---- RELEASE ----
        if accion in ["libera", "suelta"]:
            if pid and rid:
                return f"RELEASE {pid} {rid}"

        # ---- SHOW ----
        if accion in ["muestra", "visualiza"] and entidad == "grafo":
            return "SHOW GRAPH"

        # ---- DETECT ----
        if accion in ["detecta", "busca"] and entidad == "deadlock":
            return "DETECT DEADLOCK"

        return "-- Comando no reconocido."


class DeadlockSimulator:
    """
    Simulador que gestiona procesos, recursos y detecta deadlocks.
    """
    def __init__(self):
        self.procesos = set()
        self.recursos = set()
        # Grafo de asignación (Recurso -> Proceso)
        self.grafo_asignacion = defaultdict(list)
        # Grafo de solicitudes (Proceso -> Recurso)
        self.grafo_solicitudes = defaultdict(list)

    def _detectar_ciclo(self, nodo, visitados, pila):
        visitados.add(nodo)
        pila.add(nodo)
        vecinos = self.grafo_solicitudes[nodo] + self.grafo_asignacion[nodo]

        for vecino in vecinos:
            if vecino not in visitados:
                if self._detectar_ciclo(vecino, visitados, pila):
                    return True
            elif vecino in pila:
                return True

        pila.remove(nodo)
        return False

    def ejecutar_comando(self, comando):
        partes = comando.split()
        if not partes:
            return

        accion = partes[0]

        if accion == "CREATE":
            if partes[1] == "PROCESS":
                pid = partes[2]
                self.procesos.add(f"P{pid}")
                print(f"-> Proceso P{pid} creado.")
            elif partes[1] == "RESOURCE":
                rid = partes[2]
                self.recursos.add(f"R{rid}")
                print(f"-> Recurso R{rid} creado.")

        elif accion == "REQUEST":
            pid, rid = partes[1], partes[2]
            proceso_id = f"P{pid}"
            recurso_id = f"R{rid}"
            
            if recurso_id in self.recursos:
                if proceso_id not in self.grafo_asignacion[recurso_id]:
                    self.grafo_asignacion[recurso_id].append(proceso_id)
                    print(f"-> Solicitud: {proceso_id} obtiene {recurso_id}.")
                else:
                    print(f"-> Advertencia: {proceso_id} ya tiene asignado {recurso_id}.")

            # Si el recurso ya está asignado, creamos una arista de solicitud.
            if len(self.grafo_asignacion[recurso_id]) > 0 and self.grafo_asignacion[recurso_id][0] != proceso_id:
                if recurso_id not in self.grafo_solicitudes[proceso_id]:
                    self.grafo_solicitudes[proceso_id].append(recurso_id)
                    print(f"-> {proceso_id} solicita {recurso_id} que ya está en uso.")

        elif accion == "RELEASE":
            pid, rid = partes[1], partes[2]
            proceso_id = f"P{pid}"
            recurso_id = f"R{rid}"
            
            # Libera el recurso del grafo de asignación.
            if proceso_id in self.grafo_asignacion[recurso_id]:
                self.grafo_asignacion[recurso_id].remove(proceso_id)
                print(f"-> Liberación: {proceso_id} liberó {recurso_id}.")
            else:
                print(f"-> Advertencia: {proceso_id} no tiene asignado {recurso_id}.")

        elif accion == "SHOW":
            print("\n--- Grafo de Asignación (Recurso → Proceso) ---")
            for r, ps in self.grafo_asignacion.items():
                print(f"  {r} -> {ps}")
            print("--- Grafo de Solicitudes (Proceso → Recurso) ---")
            for p, rs in self.grafo_solicitudes.items():
                print(f"  {p} -> {rs}")

        elif accion == "DETECT":
            print("-> Buscando ciclos...")
            visitados, pila = set(), set()
            
            nodos_en_grafo = set(self.procesos) | set(self.recursos)
            
            for nodo in nodos_en_grafo:
                if nodo not in visitados:
                    if self._detectar_ciclo(nodo, visitados, pila):
                        print("!! ¡Deadlock detectado! Hay un ciclo en el grafo.")
                        return
            print("-> No se detectaron deadlocks.")

        else:
            print(f"Comando no válido: {comando}")

    def get_graph_data(self):
        """Exporta el estado del grafo en un formato para visualización."""
        nodes = []
        edges = []

        # Agregar nodos de procesos
        for p in self.procesos:
            nodes.append({"id": p, "group": "process"})
        
        # Agregar nodos de recursos
        for r in self.recursos:
            nodes.append({"id": r, "group": "resource"})
        
        # Agregar aristas de asignación (Recurso -> Proceso)
        for r, assigned_procs in self.grafo_asignacion.items():
            for p in assigned_procs:
                edges.append({"source": r, "target": p, "type": "assignment"})
        
        # Agregar aristas de solicitud (Proceso -> Recurso)
        for p, requested_resources in self.grafo_solicitudes.items():
            for r in requested_resources:
                edges.append({"source": p, "target": r, "type": "request"})
                
        return {"nodes": nodes, "edges": edges}

CONFIGURACION_SO = {
    "palabras_clave": {
        "accion": {
            "muestra", "visualiza", "listar", "pide", "solicita",
            "libera", "suelta", "detecta", "busca", "crear", "iniciar"
        },
        "cuantificadores": {"todos", "todas", "el", "la"},
        "conectores": {"que", "donde", "con", "y", "para"},
        "operadores": {"=", ">", "<", ">=", "<=", "!=", "<>"}
    },
    "entidades": {"recurso", "proceso", "deadlock", "grafo"},
    "atributos_globales": {"id", "pid", "nombre"},
    "formatos_fecha": []
}

if __name__ == "__main__":
    transcripciones = [
        "crear proceso 1",
        "crear recurso 1",
        "crear proceso 2",
        "crear recurso 2",
        "el proceso 1 solicita el recurso 1",
        "el proceso 2 solicita el recurso 2",
        "el proceso 1 pide el recurso 2",
        "el proceso 2 pide el recurso 1",
        "detecta un deadlock",
        "el proceso 1 libera el recurso 1",
        "detecta un deadlock"
    ]

    compilador = NL2SOCompiler(CONFIGURACION_SO)
    simulador = DeadlockSimulator()

    for frase in transcripciones:
        print("\n" + "="*50)
        print(f"Transcripción: {frase}")
        tokens = compilador.analisis_lexico(frase)
        estructura = compilador.analisis_sintactico(tokens)
        comando = compilador.generar_comando_so(estructura)
        print(f"Comando generado: {comando}")
        simulador.ejecutar_comando(comando)
        graph_data = simulador.get_graph_data()
        print("\n--- Estado del Grafo (Formato de Datos para Visualización) ---")
        print(f"Nodos: {graph_data['nodes']}")
        print(f"Aristas: {graph_data['edges']}")
