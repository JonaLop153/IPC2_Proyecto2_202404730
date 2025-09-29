from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import os
import xml.etree.ElementTree as ET
from models.invernadero import Invernadero
from models.dron import Dron
from models.planta import Planta
from models.plan import PlanRiego
from models.simulador import Simulador
from models.tda import ListaEnlazada

app = Flask(__name__)
app.secret_key = 'ipc2_guateriegos'

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
REPORTS_FOLDER = 'reports'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

invernaderos = ListaEnlazada()

@app.route('/')
def index():
    return render_template('index.html', invernaderos=invernaderos)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    global invernaderos
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.xml'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            try:
                invernaderos = cargar_configuracion(filepath)
                flash(' Configuración cargada exitosamente.')
            except Exception as e:
                flash(f' Error: {str(e)}')
            return redirect(url_for('index'))
        else:
            flash(' Sube un archivo .xml')
    return render_template('upload.html')

def cargar_configuracion(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    lista_invernaderos = ListaEnlazada()

    # Drones globales
    drones_globales = {}
    for dron_elem in root.find('listaDrones'):
        dron_id = int(dron_elem.get('id'))
        nombre = dron_elem.get('nombre')
        drones_globales[dron_id] = Dron(dron_id, nombre)

    # Invernaderos
    for inv_elem in root.find('listaInvernaderos'):
        nombre = inv_elem.get('nombre')
        if not nombre:
            raise ValueError("Invernadero sin atributo 'nombre'")
        num_hileras = int(inv_elem.find('numeroHileras').text)
        plantas_x = int(inv_elem.find('plantasXhilera').text)
        invernadero = Invernadero(nombre, num_hileras, plantas_x)

        # Plantas
        for p in inv_elem.find('listaPlantas'):
            hilera = int(p.get('hilera'))
            posicion = int(p.get('posicion'))
            agua = float(p.get('litrosAgua'))
            fert = float(p.get('gramosFertilizante'))
            nombre_planta = p.text.strip() if p.text else f"Planta H{hilera}P{posicion}"
            invernadero.plantas.agregar(Planta(hilera, posicion, agua, fert, nombre_planta))

        # Asignación drones
        for asig in inv_elem.find('asignacionDrones'):
            dron_id = int(asig.get('id'))
            hilera = int(asig.get('hilera'))
            invernadero.asignar_dron_a_hilera(dron_id, hilera)
            if dron_id in drones_globales:
                invernadero.drones.agregar(drones_globales[dron_id])
            else:
                raise ValueError(f"Dron ID {dron_id} no definido")

        # Planes - CORRECCIÓN IMPORTANTE
        for plan_elem in inv_elem.find('planesRiego'):
            nombre_plan = plan_elem.get('nombre')
            plan_text = plan_elem.text.strip() if plan_elem.text else ""
            secuencia = ListaEnlazada()
            
            # Parsear correctamente las referencias
            for ref in plan_text.split(','):
                ref = ref.strip()
                if not ref:
                    continue
                try:
                    # Manejar formato "H1-P2"
                    h_part, p_part = ref.split('-')
                    hilera = int(h_part[1:])  # Remover 'H'
                    posicion = int(p_part[1:])  # Remover 'P'
                    
                    # Buscar la planta correspondiente
                    planta_encontrada = None
                    for planta in invernadero.plantas:
                        if planta.hilera == hilera and planta.posicion == posicion:
                            planta_encontrada = planta
                            break
                    
                    if planta_encontrada:
                        secuencia.agregar(planta_encontrada)
                    else:
                        print(f"Advertencia: Planta {ref} no encontrada en invernadero {nombre}")
                        
                except (ValueError, IndexError) as e:
                    print(f"Error parseando referencia '{ref}': {e}")
                    continue
                    
            invernadero.planes.agregar(PlanRiego(nombre_plan, secuencia))

        lista_invernaderos.agregar(invernadero)
    return lista_invernaderos

@app.route('/simulate/<int:inv_idx>/<int:plan_idx>')
def simulate(inv_idx, plan_idx):
    invernadero = invernaderos.obtener(inv_idx)
    if not invernadero:
        flash("Invernadero no encontrado")
        return redirect(url_for('index'))

    plan = invernadero.planes.obtener(plan_idx)
    if not plan:
        flash("Plan no encontrado")
        return redirect(url_for('index'))

    simulador = Simulador(invernadero, plan)
    simulador.simular()

    report_html = simulador.generar_reporte_html()
    report_name = f"report_{invernadero.nombre}_{plan.nombre}.html".replace(" ", "_").replace("/", "_")
    with open(os.path.join(REPORTS_FOLDER, report_name), 'w', encoding='utf-8') as f:
        f.write(report_html)

    return render_template('simulate.html',
                           inv_idx=inv_idx,
                           plan_idx=plan_idx,
                           invernadero=invernadero,
                           plan=plan,
                           simulador=simulador,
                           report_url=url_for('serve_report', filename=report_name))

@app.route('/graph/<int:inv_idx>/<int:plan_idx>', methods=['GET', 'POST'])
def graph(inv_idx, plan_idx):
    invernadero = invernaderos.obtener(inv_idx)
    plan = invernadero.planes.obtener(plan_idx)
    simulador = Simulador(invernadero, plan)
    simulador.simular()

    t = request.form.get('t', 1, type=int)
    svg_grafico = simulador.generar_grafico_tda(t)

    return render_template('graph.html',
                           inv_idx=inv_idx,
                           plan_idx=plan_idx,
                           invernadero=invernadero,
                           plan=plan,
                           t=t,
                           svg_grafico=svg_grafico)

@app.route('/reports/<filename>')
def serve_report(filename):
    return send_from_directory(REPORTS_FOLDER, filename)

@app.route('/generar_salida')
def generar_salida():
    if len(invernaderos) == 0:
        flash("No hay configuración cargada")
        return redirect(url_for('index'))

    root = ET.Element("datosSalida")
    lista_inv = ET.SubElement(root, "listaInvernaderos")

    for inv in invernaderos:
        for plan in inv.planes:
            simulador = Simulador(inv, plan)
            simulador.simular()
            simulador.generar_xml_salida(lista_inv)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    salida_path = os.path.join(OUTPUT_FOLDER, "salida.xml")
    tree.write(salida_path, encoding='utf-8', xml_declaration=True)
    flash(" Archivo salida.xml generado")
    return redirect(url_for('index'))

@app.route('/outputs/<path:filename>')
def download_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

@app.route('/help')
def help_page():
    return render_template('help.html')

if __name__ == '__main__':
    app.run(debug=True)