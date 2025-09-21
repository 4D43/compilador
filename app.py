from flask import Flask, jsonify, request
from flask_cors import CORS
from nlpposcompil2 import NL2SOCompiler, DeadlockSimulator, CONFIGURACION_SO

app = Flask(__name__)
# Habilita CORS para permitir solicitudes desde cualquier origen
CORS(app)

# Instancia global del compilador y del simulador
compilador = NL2SOCompiler(CONFIGURACION_SO)
simulador = DeadlockSimulator()
simulador.ejecutar_comando("CREATE PROCESS 1")
simulador.ejecutar_comando("CREATE RESOURCE 1")
simulador.ejecutar_comando("CREATE PROCESS 2")
simulador.ejecutar_comando("CREATE RESOURCE 2")
simulador.ejecutar_comando("REQUEST 1 1")
simulador.ejecutar_comando("REQUEST 2 2")

@app.route('/api/graph_data', methods=['GET'])
def get_graph_data():
    """
    Endpoint que devuelve el estado actual del grafo de asignación
    y solicitud en formato JSON.
    """
    graph_data = simulador.get_graph_data()
    return jsonify(graph_data)

@app.route('/api/execute_command', methods=['POST'])
def execute_command():
    """
    Endpoint que recibe un comando, lo procesa y devuelve
    el nuevo estado del grafo.
    """
    data = request.get_json()
    command_text = data.get('command', '')
    
    if not command_text:
        return jsonify({"message": "Error: Comando vacío.", "graph_data": simulador.get_graph_data()}), 400
        
    # El proceso del compilador se ejecuta aquí
    tokens = compilador.analisis_lexico(command_text)
    estructura = compilador.analisis_sintactico(tokens)
    comando_so = compilador.generar_comando_so(estructura)
    
    # El simulador ejecuta el comando y actualiza su estado
    simulador.ejecutar_comando(comando_so)
    
    # Obtiene el estado actualizado del grafo
    graph_data = simulador.get_graph_data()
    
    # Prepara el mensaje de respuesta.
    message = f"Comando '{command_text}' procesado. Nuevo estado del grafo generado."
    if "no reconocido" in comando_so:
        message = f"Advertencia: El comando '{command_text}' no fue reconocido. Intenta con otra frase."
        
    return jsonify({
        "message": message,
        "command_so": comando_so,
        "graph_data": graph_data
    })


if __name__ == '__main__':
    print("Servidor Flask corriendo en http://127.0.0.1:5000/")
    print("Accede a http://127.0.0.1:5000/api/graph_data para ver los datos del grafo.")
    app.run(debug=True)
