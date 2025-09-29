class Dron:
    def __init__(self, id_dron, nombre):
        self.id_dron = id_dron
        self.nombre = nombre
        self.posicion_actual = 0
        self.agua_usada = 0
        self.fertilizante_usado = 0
        self.plantas_regadas = []
        self.estado = "Esperando"
        self.hilera_asignada = None

    def reset(self):
        self.posicion_actual = 0
        self.agua_usada = 0
        self.fertilizante_usado = 0
        self.plantas_regadas = []
        self.estado = "Esperando"
        self.hilera_asignada = None

    def regar_planta(self, planta):
        self.agua_usada += planta.litros_agua
        self.fertilizante_usado += planta.gramos_fertilizante
        self.plantas_regadas.append(planta)
        self.estado = "Regando"
        
    def __str__(self):
        return f"{self.nombre} (Pos: {self.posicion_actual})"