class Planta:
    def __init__(self, hilera, posicion, litros_agua, gramos_fertilizante, nombre):
        self.hilera = hilera
        self.posicion = posicion
        self.litros_agua = litros_agua
        self.gramos_fertilizante = gramos_fertilizante
        self.nombre = nombre

    def __str__(self):
        return f"H{self.hilera}-P{self.posicion}"