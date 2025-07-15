
#include "gestor.h"

int main() {
    leerEntrada();
    if (validarTamano() != 1) {
        procesarConsulta();
        analizarComandos();
        analizarCondiciones();
                imprimirArbolSemantico(); // <--- Llamada a la nueva función aquí

        validarArchivo();
        seleccionar();
        ingresar();
    }
    return 0;
}
