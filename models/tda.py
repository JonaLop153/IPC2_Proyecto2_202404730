class Nodo:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente = None

class ListaEnlazada:
    def __init__(self):
        self.cabeza = None
        self._tamano = 0

    def agregar(self, dato):
        nuevo = Nodo(dato)
        if not self.cabeza:
            self.cabeza = nuevo
        else:
            actual = self.cabeza
            while actual.siguiente:
                actual = actual.siguiente
            actual.siguiente = nuevo
        self._tamano += 1

    def obtener(self, i):
        if i < 0 or i >= self._tamano:
            return None
        actual = self.cabeza
        for _ in range(i):
            actual = actual.siguiente
        return actual.dato

    def __iter__(self):
        actual = self.cabeza
        while actual:
            yield actual.dato
            actual = actual.siguiente

    def __len__(self):
        return self._tamano

    @property
    def tamano(self):
        return self._tamano