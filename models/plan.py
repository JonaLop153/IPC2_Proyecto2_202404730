from .tda import ListaEnlazada

class PlanRiego:
    def __init__(self, nombre, secuencia_plantas):
        self.nombre = nombre
        self.secuencia_plantas = secuencia_plantas  # ListaEnlazada de Planta