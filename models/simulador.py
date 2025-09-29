from .tda import ListaEnlazada
from graphviz import Digraph
import xml.etree.ElementTree as ET

class Simulador:
    def __init__(self, invernadero, plan):
        self.invernadero = invernadero
        self.plan = plan
        self.tiempo_total = 0
        self.instrucciones_por_tiempo = ListaEnlazada()
        self.estadisticas = None
        self.historial_tda = []

    def simular(self):
        # Reiniciar drones - Asegurar que empiezan en posición 0
        for dron in self.invernadero.drones:
            dron.reset()
            dron.posicion_actual = 0  # Forzar posición inicial

        # Mapeo hilera -> dron
        hilera_a_dron = {}
        for hilera, dron_id in self.invernadero.asignaciones.items():
            for dron in self.invernadero.drones:
                if dron.id_dron == dron_id:
                    hilera_a_dron[hilera] = dron
                    dron.hilera_asignada = hilera
                    break

        plantas_plan = [p for p in self.plan.secuencia_plantas]
        indice_plan = 0
        tiempo = 1
        drones_finalizados = set()
        max_iteraciones = 100

        print(f"=== SIMULANDO {self.plan.nombre} ===")
        print(f"Plantas en plan: {len(plantas_plan)}")
        for i, planta in enumerate(plantas_plan):
            print(f"  {i+1}. H{planta.hilera}-P{planta.posicion}")

        while (indice_plan < len(plantas_plan) or len(drones_finalizados) < len(self.invernadero.drones)) and tiempo <= max_iteraciones:
            acciones = {d.nombre: "Esperar" for d in self.invernadero.drones}
            riego_realizado = False

            # MOVIMIENTO: Todos los drones se mueven simultáneamente hacia sus objetivos
            for dron in self.invernadero.drones:
                if dron.nombre in drones_finalizados:
                    continue
                    
                # Encontrar la próxima planta para este dron
                planta_objetivo = None
                for i in range(indice_plan, len(plantas_plan)):
                    planta = plantas_plan[i]
                    if planta.hilera == dron.hilera_asignada:
                        planta_objetivo = planta
                        break
                
                if planta_objetivo:
                    # Mover hacia la planta objetivo
                    if dron.posicion_actual < planta_objetivo.posicion:
                        dron.posicion_actual += 1
                        acciones[dron.nombre] = f"Adelante(H{planta_objetivo.hilera}P{dron.posicion_actual})"
                    elif dron.posicion_actual > planta_objetivo.posicion:
                        dron.posicion_actual -= 1
                        acciones[dron.nombre] = f"Atrás(H{planta_objetivo.hilera}P{dron.posicion_actual})"

            # RIEGO: Solo una planta por ciclo, en el orden del plan
            if indice_plan < len(plantas_plan) and not riego_realizado:
                planta_actual = plantas_plan[indice_plan]
                dron_actual = hilera_a_dron.get(planta_actual.hilera)
                
                if dron_actual and dron_actual.posicion_actual == planta_actual.posicion:
                    # Riego exclusivo - sobrescribir todas las acciones
                    acciones = {d.nombre: "Esperar" for d in self.invernadero.drones}
                    acciones[dron_actual.nombre] = "Regar"
                    dron_actual.regar_planta(planta_actual)
                    riego_realizado = True
                    indice_plan += 1
                    print(f"Tiempo {tiempo}: {dron_actual.nombre} riega H{planta_actual.hilera}-P{planta_actual.posicion}")

            # REGRESO AL INICIO: Drones sin más plantas
            for dron in self.invernadero.drones:
                if dron.nombre in drones_finalizados:
                    continue
                    
                # Verificar si tiene más plantas en el plan
                tiene_mas_plantas = False
                for i in range(indice_plan, len(plantas_plan)):
                    planta = plantas_plan[i]
                    if planta.hilera == dron.hilera_asignada:
                        tiene_mas_plantas = True
                        break
                
                if not tiene_mas_plantas and dron.posicion_actual > 0:
                    # Solo regresar si no está haciendo otra acción
                    if acciones[dron.nombre] == "Esperar":
                        dron.posicion_actual -= 1
                        if dron.posicion_actual > 0:
                            acciones[dron.nombre] = f"Atrás(H{dron.hilera_asignada}P{dron.posicion_actual})"
                        else:
                            acciones[dron.nombre] = "FIN"
                            drones_finalizados.add(dron.nombre)
                            print(f"Tiempo {tiempo}: {dron.nombre} finaliza")

            # Debug: mostrar estado actual
            if tiempo <= 10:  # Solo mostrar primeros 10 tiempos para no saturar
                print(f"T{tiempo}: {acciones}")

            self._guardar_estado(tiempo, acciones)
            tiempo += 1

        # Si se alcanzó el límite, forzar finalización
        if tiempo > max_iteraciones:
            print(f"ADVERTENCIA: Se alcanzó el límite de {max_iteraciones} iteraciones")
            # Forzar finalización de todos los drones
            for dron in self.invernadero.drones:
                if dron.nombre not in drones_finalizados:
                    acciones[dron.nombre] = "FIN"
            self._guardar_estado(tiempo, acciones)

        self.tiempo_total = tiempo - 1
        self.estadisticas = {
            'agua_total': sum(d.agua_usada for d in self.invernadero.drones),
            'fertilizante_total': sum(d.fertilizante_usado for d in self.invernadero.drones),
            'drones': [(d.nombre, d.agua_usada, d.fertilizante_usado) for d in self.invernadero.drones]
        }
        
        print(f"=== FIN SIMULACIÓN {self.plan.nombre} ===")
        print(f"Tiempo total: {self.tiempo_total} segundos")
        print(f"Agua total: {self.estadisticas['agua_total']}L")
        print(f"Fertilizante total: {self.estadisticas['fertilizante_total']}g")
        for nombre, agua, fert in self.estadisticas['drones']:
            print(f"  {nombre}: {agua}L, {fert}g")

    def _guardar_estado(self, tiempo, acciones):
        self.instrucciones_por_tiempo.agregar({
            'tiempo': tiempo,
            'acciones': acciones.copy()
        })
        self.historial_tda.append({
            'tiempo': tiempo,
            'acciones': acciones.copy(),
            'drones': [(d.nombre, d.posicion_actual, d.estado) for d in self.invernadero.drones]
        })

    def generar_grafico_tda(self, t):
        dot = Digraph(comment=f'Estado de TDAs en tiempo t={t}')
        dot.attr(rankdir='LR', fontname='Arial', fontsize='12')
        dot.node('plan', 'Plan de Riego', shape='ellipse', style='filled', color='lightblue')

        estado = None
        for e in self.historial_tda:
            if e['tiempo'] == t:
                estado = e
                break

        if not estado:
            dot.node('error', f'No hay estado para t={t}', shape='box', style='filled', color='lightcoral')
            return dot.pipe(format='svg').decode('utf-8')

        for nombre, pos, estado_dron in estado['drones']:
            dron_id = f'dron_{nombre}'
            dot.node(dron_id, f'{nombre}\\nPos: {pos}\\nEstado: {estado_dron}', 
                    shape='box', style='filled', color='lightskyblue')
            dot.edge('plan', dron_id)
            
            accion = estado['acciones'].get(nombre, 'Esperar')
            accion_id = f'accion_{nombre}_{t}'
            dot.node(accion_id, accion, shape='box', style='filled', color='lightpink')
            dot.edge(dron_id, accion_id)

        return dot.pipe(format='svg').decode('utf-8')

    def generar_reporte_html(self):
        from jinja2 import Template
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reporte - {{ invernadero }}</title>
            <style>
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
            </style>
        </head>
        <body>
        <h1>Reporte: {{ invernadero }}</h1>
        <h2>Plan: {{ plan }}</h2>
        <p><strong>Tiempo óptimo:</strong> {{ tiempo }} segundos</p>
        <p><strong>Agua total:</strong> {{ agua_total }} litros</p>
        <p><strong>Fertilizante total:</strong> {{ fertilizante_total }} gramos</p>
        
        <h3>Estadísticas por dron:</h3>
        <table>
            <tr><th>Dron</th><th>Agua (L)</th><th>Fertilizante (g)</th></tr>
            {% for nombre, agua, fert in drones %}
            <tr>
                <td>{{ nombre }}</td>
                <td>{{ agua }}</td>
                <td>{{ fert }}</td>
            </tr>
            {% endfor %}
        </table>

        <h3>Instrucciones por tiempo:</h3>
        <table>
            <tr>
                <th>Tiempo (s)</th>
                {% for dron in drones %}
                    <th>{{ dron[0] }}</th>
                {% endfor %}
            </tr>
            {% for inst in instrucciones %}
            <tr>
                <td>{{ inst.tiempo }}</td>
                {% for dron in drones %}
                    <td>{{ inst.acciones.get(dron[0], 'Esperar') }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </table>
        </body>
        </html>
        """
        template = Template(template_str)
        return template.render(
            invernadero=self.invernadero.nombre,
            plan=self.plan.nombre,
            tiempo=self.tiempo_total,
            agua_total=self.estadisticas['agua_total'],
            fertilizante_total=self.estadisticas['fertilizante_total'],
            drones=self.estadisticas['drones'],
            instrucciones=list(self.instrucciones_por_tiempo)
        )

    def generar_xml_salida(self, root_lista_invernaderos):
        invernadero_elem = ET.SubElement(root_lista_invernaderos, "invernadero")
        invernadero_elem.set("nombre", self.invernadero.nombre)

        lista_planes = ET.SubElement(invernadero_elem, "listaPlanes")
        plan_elem = ET.SubElement(lista_planes, "plan")
        plan_elem.set("nombre", self.plan.nombre)

        ET.SubElement(plan_elem, "tiempoOptimoSegundos").text = str(self.tiempo_total)
        ET.SubElement(plan_elem, "aguaRequeridaLitros").text = str(int(self.estadisticas['agua_total']))
        ET.SubElement(plan_elem, "fertilizanteRequeridoGramos").text = str(int(self.estadisticas['fertilizante_total']))

        eficiencia = ET.SubElement(plan_elem, "eficienciaDronesRegadores")
        for nombre, agua, fert in self.estadisticas['drones']:
            dron_elem = ET.SubElement(eficiencia, "dron")
            dron_elem.set("nombre", nombre)
            dron_elem.set("litrosAgua", str(int(agua)))
            dron_elem.set("gramosFertilizante", str(int(fert)))

        instrucciones_elem = ET.SubElement(plan_elem, "instrucciones")
        for inst in self.instrucciones_por_tiempo:
            tiempo_elem = ET.SubElement(instrucciones_elem, "tiempo")
            tiempo_elem.set("segundos", str(inst['tiempo']))
            for dron_nombre, accion in inst['acciones'].items():
                dron_inst = ET.SubElement(tiempo_elem, "dron")
                dron_inst.set("nombre", dron_nombre)
                dron_inst.set("accion", accion)