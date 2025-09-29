from .tda import ListaEnlazada

class Invernadero:
    def __init__(self, nombre, numero_hileras, plantas_x_hilera):
        self.nombre = nombre
        self.numero_hileras = numero_hileras
        self.plantas_x_hilera = plantas_x_hilera
        self.plantas = ListaEnlazada()
        self.drones = ListaEnlazada()
        self.asignaciones = {}  # hilera -> dron_id
        self.planes = ListaEnlazada()  #  Ahora está correctamente indentado

    def asignar_dron_a_hilera(self, dron_id, hilera):
        self.asignaciones[hilera] = dron_id