"""Genera el documento del L5 con el estilo del L4. Uso: python docs/L5/generar_documento_l5.py <raíz del repo>"""
import copy
import re
import sys
from pathlib import Path

import docx
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

REPO = Path(sys.argv[1])
L4 = REPO / "docs/L4/L4 - SentinelaTI - Arquitectura, diseño OO y wireframe.docx"
SALIDA = REPO / "docs/L5/L5 - SentinelaTI - Prototipo y esbozo del plan de pruebas.docx"
IMG = REPO / "docs/L5/img"

d = docx.Document(str(L4))
cuerpo = d.element.body
sect_final = copy.deepcopy(cuerpo[-1])
for el in list(cuerpo):
    cuerpo.remove(el)
cuerpo.append(sect_final)
sec = d.sections[-1]
sec.orientation = WD_ORIENT.PORTRAIT
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)

MARCA = RGBColor(0x1F, 0x6F, 0x78)
n_tabla = 0
n_figura = 0


def runs(p, texto, tam=None):
    """Agrega texto con **negrita** y `código` como runs reales (sin marcas literales)."""
    for trozo in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", texto):
        if not trozo:
            continue
        if trozo.startswith("**"):
            r = p.add_run(trozo[2:-2]); r.bold = True
        elif trozo.startswith("`"):
            r = p.add_run(trozo[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(9)
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        else:
            r = p.add_run(trozo)
        if tam and not trozo.startswith("`"):
            r.font.size = Pt(tam)
    return p


def par(texto="", alineado=None, tam=None, negrita=False, espacio_despues=None):
    p = d.add_paragraph()
    if negrita:
        r = p.add_run(texto); r.bold = True
        if tam: r.font.size = Pt(tam)
    else:
        runs(p, texto, tam)
    if alineado: p.alignment = alineado
    if espacio_despues is not None: p.paragraph_format.space_after = Pt(espacio_despues)
    return p


def h(nivel, texto):
    return d.add_heading(texto, level=nivel)


def vinetas(items):
    for it in items:
        runs(d.add_paragraph(style="List Bullet"), it)


def _nueva_numeracion():
    """Crea una instancia de numeración nueva para que cada lista numerada empiece en 1."""
    numeracion = d.part.numbering_part.element
    estilo = d.styles["List Number"].element
    num_id_estilo = estilo.pPr.numPr.numId.val
    abstracto = numeracion.num_having_numId(num_id_estilo).abstractNumId.val
    nuevo = numeracion.add_num(abstracto)
    override = OxmlElement("w:lvlOverride"); override.set(qn("w:ilvl"), "0")
    inicio = OxmlElement("w:startOverride"); inicio.set(qn("w:val"), "1")
    override.append(inicio); nuevo.append(override)
    return nuevo.numId


def numeros(items):
    num_id = _nueva_numeracion()
    for it in items:
        p = d.add_paragraph(style="List Number")
        numPr = p._p.get_or_add_pPr().get_or_add_numPr()
        numPr.get_or_add_ilvl().val = 0
        numPr.get_or_add_numId().val = num_id
        runs(p, it)


def sombrear(celda, color="EAF4F5"):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def repetir_encabezado(fila):
    trPr = fila._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader"); el.set(qn("w:val"), "true"); trPr.append(el)


def tabla(titulo, encabezados, filas, anchos=None, tam=9):
    global n_tabla
    n_tabla += 1
    cap = d.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(f"Tabla {n_tabla}. {titulo}"); r.bold = True; r.font.size = Pt(9)
    cap.paragraph_format.keep_with_next = True
    t = d.add_table(rows=1, cols=len(encabezados)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, e in enumerate(encabezados):
        c = t.rows[0].cells[i]; c.text = ""; sombrear(c)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        rr = c.paragraphs[0].add_run(e); rr.bold = True; rr.font.size = Pt(tam)
    repetir_encabezado(t.rows[0])
    for fila in filas:
        celdas = t.add_row().cells
        for i, valor in enumerate(fila):
            celdas[i].text = ""
            celdas[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
            runs(celdas[i].paragraphs[0], str(valor), tam)
    if anchos:
        for fila in t.rows:
            for i, a in enumerate(anchos):
                fila.cells[i].width = Cm(a)
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return n_tabla


def figura(archivo, titulo, ancho=15.5):
    global n_figura
    n_figura += 1
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(IMG / archivo), width=Cm(ancho))
    cap = d.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(f"Figura {n_figura}. {titulo}"); r.italic = True; r.font.size = Pt(9)
    return n_figura


def salto():
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def indice():
    p = d.add_paragraph()
    for tipo, texto in (("begin", None), (None, 'TOC \\o "1-3" \\h \\z \\u'), ("separate", None), (None, None), ("end", None)):
        r = p.add_run()
        if tipo:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), tipo); r._r.append(fc)
        elif texto:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = texto; r._r.append(it)
        else:
            r.text = "Actualice el índice (clic derecho › Actualizar campos)."


# ==================================================================== portada
for _ in range(2): par()
for texto, tam in (("Universidad de Santiago de Chile", 13), ("Departamento de Ingeniería Informática", 12),
                   ("Fundamentos de Ingeniería de Software", 12)):
    par(texto, WD_ALIGN_PARAGRAPH.CENTER, tam)
for _ in range(4): par()
par("Laboratorio 5", WD_ALIGN_PARAGRAPH.CENTER, 14)
p = par("Prototipo, integración de la interfaz y esbozo del plan de pruebas", WD_ALIGN_PARAGRAPH.CENTER, 18, negrita=True)
p = par("SentinelaTI", WD_ALIGN_PARAGRAPH.CENTER, 28, negrita=True)
p.runs[0].font.color.rgb = MARCA
par("Plataforma de monitoreo y mantención remota de computadores para equipos de TI", WD_ALIGN_PARAGRAPH.CENTER, 12)
par("Prototipo v0.5  ·  Documento versión 1.0", WD_ALIGN_PARAGRAPH.CENTER, 10)
for _ in range(7): par()
for t in ("Integrantes: Felipe Cifuentes, Paula Rivas", "Profesor: Joaquín Macías Cáceres",
          "Repositorio: https://github.com/gazpel/SentinelaTI (rama feat/l5-prototipo)", "Fecha: 23 de noviembre de 2026"):
    par(t, negrita=True)
salto()

par("Historial de versiones", tam=16, negrita=True)
tabla("Historial de versiones del documento.", ["Versión", "Fecha", "Autor(es)", "Descripción"], [
    ["1.0", "23-11-2026", "F. Cifuentes, P. Rivas",
     "Primera versión: prototipo funcional (agente, API y panel web) que implementa 12 de los 18 RF, interfaz integrada a partir "
     "de los wireframes del L4, trazabilidad diseño → código, esbozo del plan de pruebas con 33 casos basados en requerimientos "
     "y particiones de equivalencia sobre cuatro entradas, y guía para continuar el desarrollo en el L6."]],
    [1.6, 2.2, 3.2, 9.0])
par("Índice", tam=16, negrita=True)
indice()
salto()

# ==================================================================== 1. Introducción
h(1, "1. Introducción")
h(2, "1.1 Propósito")
par("Este documento acompaña la entrega del Laboratorio 5. Describe la porción del sistema SentinelaTI que quedó implementada "
    "en el prototipo, muestra cómo el código respeta la arquitectura y el diseño de clases del L4, presenta la interfaz de usuario "
    "integrada a partir de los wireframes y deja un primer plan de pruebas trazable a los requerimientos implementados. "
    "El código fuente está en el repositorio del proyecto; este documento no lo repite, sino que indica dónde está cada pieza.")
h(2, "1.2 Relación con los laboratorios anteriores")
vinetas([
    "**L1** fijó el stack (agente Python, FastAPI, PostgreSQL y React) y la priorización MoSCoW: el prototipo cubre los *Must* y parte de los *Should*.",
    "**L2 (ERS v1.0)** define los RF01–RF18 y RNF01–RNF12 con sus criterios de aceptación. Los casos de prueba de la sección 6 usan esos criterios como resultado esperado.",
    "**L3 y L4** definen las clases, las secuencias de CU02 y CU07, las decisiones D1–D12 y los wireframes W1–W3. La sección 4 muestra dónde quedó cada elemento en el código.",
])
h(2, "1.3 Convenciones")
vinetas([
    "El diseño usa nombres en *camelCase* (por ejemplo `registrarOrden()`); el código Python usa *snake_case* (`registrar_orden()`) por convención del lenguaje (PEP 8). La correspondencia es directa y se verificó con un script (sección 4.2).",
    "Las rutas de archivos son relativas a la raíz del repositorio. Las pruebas automatizadas se citan como `archivo::función`.",
    "«Modo seguro» es la ejecución del agente que registra un reinicio o apagado sin aplicarlo al equipo (sección 3.4).",
])

# ==================================================================== 2. Alcance
h(1, "2. Alcance del prototipo")
h(2, "2.1 Porción implementada")
par("Se implementó el flujo completo que atraviesa los tres componentes del sistema: un agente se enrola, reporta métricas, el "
    "servidor calcula el estado y las alertas, un técnico ve el parque y ordena un reinicio, el agente lo ejecuta y la orden queda "
    "en la bitácora. Esto corresponde a los hitos H6 (métricas de punta a punta) y H7 (reinicio remoto con auditoría) del L1. "
    "La Tabla 2 muestra el estado de cada requerimiento funcional.")
tabla("Estado de los requerimientos funcionales en el prototipo.", ["RF", "Requerimiento", "Prioridad", "Estado", "Observación"], [
    ["RF01", "Enrolar equipo con código de la organización", "Must", "Implementado", "Token propio por equipo; el reenrolamiento revoca el token anterior."],
    ["RF02", "Reporte de métricas cada N minutos", "Must", "Implementado", "CPU, RAM, discos, temperatura y horas encendido con psutil; intervalo 1–60 min."],
    ["RF03", "Inventario del equipo", "Should", "Parcial", "Se envían modelo, n.º de serie, SO, IP y último usuario al enrolar. Faltan las aplicaciones instaladas."],
    ["RF04", "Actualizaciones pendientes del SO", "Should", "Pendiente L6", "—"],
    ["RF05", "Listado del parque con búsqueda y filtro", "Must", "Implementado", "Ordenado por severidad y paginado en la base de datos (D6)."],
    ["RF06", "Detalle con gráficos 24 h / 7 días / 30 días", "Must", "Implementado", "Gráficos con las líneas de umbral de advertencia y crítico."],
    ["RF07", "Umbrales de advertencia y crítico", "Should", "Implementado", "Solo Administrador; validación en el panel y en el servidor."],
    ["RF08", "Reinicio y apagado remoto", "Must", "Implementado", "Real con `shutdown.exe`; en desarrollo corre en modo seguro."],
    ["RF09", "Instalación desde el catálogo", "Should", "Pendiente L6", "Botón visible y deshabilitado, con la indicación «L6»."],
    ["RF10", "Actualización del SO (simulada)", "Could", "Pendiente L6", "El agente ya tiene el ejecutor simulado; falta la orden en el servidor."],
    ["RF11", "Formateo con doble confirmación (simulado)", "Could", "Implementado", "Exige escribir el nombre exacto; exclusivo del Administrador."],
    ["RF12", "Escritorio remoto (simulado)", "Could", "Pendiente L6", "—"],
    ["RF13", "Gestión de usuarios y roles", "Must", "Implementado", "Crear, editar nombre y rol, y desactivar."],
    ["RF14", "Bitácora de auditoría", "Must", "Implementado", "Una entrada por orden, abierta al ordenar y cerrada con el resultado."],
    ["RF15", "Aviso al usuario final con cuenta regresiva", "Should", "Parcial", "Cuenta regresiva de 5 min en la consola del agente; la ventana con «Posponer» (W3) queda para el L6."],
    ["RF16", "Alertas por umbral crítico y desconexión", "Should", "Implementado", "Máximo una alerta abierta por equipo y métrica."],
    ["RF17", "Inicio de sesión obligatorio", "Must", "Implementado", "JWT de 8 h; bloqueo de 15 min tras 5 intentos fallidos."],
    ["RF18", "Consulta de la bitácora con filtros", "Should", "Implementado", "Por equipo, usuario, tipo de acción y rango de fechas."],
], [1.2, 4.3, 1.5, 2.2, 6.8])
par("En resumen: **12 RF implementados** (los 8 *Must* y 4 *Should*), **2 parciales** (RF03 y RF15) y **4 pendientes** para el L6 (RF04, RF09, RF10 y RF12).")
h(2, "2.2 Criterio de selección")
vinetas([
    "**Representatividad:** la porción toca las cuatro capas del servidor, el agente y el panel, y ejercita las dos secuencias refinadas en el L4 (CU02 y CU07).",
    "**Riesgo primero:** se implementaron antes las piezas con más incertidumbre técnica (lectura de métricas en Windows, cola sin conexión, ejecución remota y su auditoría).",
    "**Valor para la demostración del L7:** el guion «una VM reporta, se dispara una alerta, se reinicia remotamente y se muestra la auditoría» ya funciona de punta a punta.",
    "**Lo simulado se mantuvo simulado:** el formateo se implementó como define el ERS, sin tocar el equipo.",
])
h(2, "2.3 Requerimientos no funcionales abordados")
tabla("Requerimientos no funcionales en el prototipo.", ["RNF", "Estado", "Cómo se aborda en el prototipo"], [
    ["RNF01 Seguridad", "Parcial", "Token propio por agente (el servidor guarda solo su hash SHA-256) y JWT en el panel; contraseñas con PBKDF2-SHA256. HTTPS: el servidor lo admite con `--ssl-keyfile`, pero en desarrollo corre en HTTP local."],
    ["RNF02 Servicio protegido", "Pendiente L6", "El agente corre en primer plano; falta instalarlo como servicio de Windows y proteger el token con DPAPI."],
    ["RNF03 Impacto ≤ 2 % CPU", "Por medir (L6)", "El agente duerme entre ciclos y solo mide 1 s de CPU por lectura; la medición con el Monitor de rendimiento es una prueba del L6."],
    ["RNF04 Buffer sin conexión", "Implementado", "Cola local SQLite con retención de 72 h, reenvío en orden y sin duplicados (CP-30, CP-13)."],
    ["RNF05 Privacidad", "Implementado", "El contrato de la lectura rechaza cualquier campo extra (CP-14d); los recolectores solo leen contadores del sistema."],
    ["RNF06 Críticos visibles", "Implementado", "Tarjetas de resumen y tabla ordenada por severidad en la pantalla principal."],
    ["RNF07 Control de acceso", "Implementado", "Autorización por Permiso en un único servicio; 403 para el Técnico (CP-07, CP-26)."],
    ["RNF08 Listado ≤ 3 s", "Por medir (L6)", "Filtro, orden y paginación en SQL; falta la medición con 200 equipos."],
    ["RNF10 Tecnologías", "Parcial", "Python 3.14, FastAPI y React. Se desarrolla con SQLite; PostgreSQL queda a una variable de entorno (sección 4.4, AJ3)."],
    ["RNF11 Aviso al trabajador", "Parcial", "Mensaje de consola al iniciar el agente; el ícono de bandeja es del L6."],
    ["RNF12 Bitácora inmutable", "Implementado", "La API solo expone GET sobre la bitácora (CP-27b) y una entrada cerrada no se puede modificar."],
], [3.2, 2.4, 10.4])

# ==================================================================== 3. Arquitectura e implementación
h(1, "3. Implementación")
h(2, "3.1 Estructura del repositorio")
tabla("Carpetas del repositorio y componente del L4 al que corresponden.", ["Carpeta", "Contenido", "Componente del L4"], [
    ["`backend/app/presentacion`", "Routers del panel y del agente, esquemas JSON, dependencias por petición y tareas periódicas.", "RoutersPanel, RoutersAgente, TareasPeriodicas"],
    ["`backend/app/aplicacion`", "Servicios de aplicación (uno por archivo).", "Servicios de aplicación"],
    ["`backend/app/dominio`", "Entidades, enumeraciones y contratos de repositorio.", "Modelo de dominio, Repositorios (interfaz)"],
    ["`backend/app/infraestructura`", "Conexión a la base de datos, repositorios SQL y criptografía.", "Repositorios PostgreSQL"],
    ["`backend/tests`", "106 pruebas automatizadas de la API y del dominio (pytest).", "—"],
    ["`backend/scripts`", "`sembrar_demo.py`: 20 equipos ficticios con 30 días de historial.", "—"],
    ["`agent/sentinela_agente`", "Agente: recolectores, cola local, cliente HTTP, ejecutores y notificador.", "Agente SentinelaTI"],
    ["`agent/tests`", "19 pruebas del agente con la API simulada.", "—"],
    ["`frontend/src`", "Panel React: vistas, componentes comunes, cliente de la API y sesión.", "Panel web (React)"],
    ["`docs/L5`", "Este documento y las capturas de la interfaz.", "—"],
], [4.3, 7.2, 4.5])
h(2, "3.2 Tecnologías")
tabla("Tecnologías y versiones usadas.", ["Pieza", "Tecnología", "Motivo"], [
    ["API", "Python 3.14, FastAPI 0.165, SQLAlchemy 2.1, PyJWT 2.15", "Definidas en el L1 (RNF10). FastAPI genera el contrato OpenAPI en `/docs`."],
    ["Base de datos", "SQLite (desarrollo y pruebas); PostgreSQL (producción)", "El mismo código funciona con ambas (AJ3)."],
    ["Agente", "Python 3.14, psutil 7.2, httpx 0.28, sqlite3", "psutil lee CPU, RAM, discos y tiempo encendido sin privilegios; sqlite3 viene con Python."],
    ["Panel", "React 19, React Router 6, Recharts 2, Vite 6", "Definido en el L1; Recharts dibuja los gráficos de RF06."],
    ["Pruebas", "pytest 9, TestClient de FastAPI, httpx.MockTransport", "Pruebas de API sin levantar un servidor y del agente sin red real."],
], [2.6, 6.4, 7.0])
h(2, "3.3 Servidor: capas y flujo de una petición")
par("El servidor sigue las cuatro capas del L4. Una petición del panel atraviesa las capas siempre en el mismo orden:")
numeros([
    "El router (`presentacion/routers_panel.py`) valida el JSON con un esquema Pydantic y obtiene la sesión con `sesion_actual()`, que llama a `ServicioAutenticacion.validar_sesion()` (RF17).",
    "`dependencias.obtener_bd()` abre **una transacción por petición** y el `Contenedor` arma los servicios con los repositorios SQL. Es el único punto donde la aplicación se conecta con la infraestructura.",
    "El servicio de aplicación autoriza con `autorizar(sesion, permiso)` (D7), aplica las reglas usando las entidades del dominio y persiste mediante los contratos `*Repository`.",
    "Si todo sale bien la transacción se confirma; si hay un error se revierte. Dos errores conservan lo escrito a propósito: el intento fallido de inicio de sesión (para contar el bloqueo) y la entrada de bitácora de un intento sin permiso (excepción 1f de CU07).",
    "Los errores de aplicación se traducen a códigos HTTP en `main.py`: 401 sin sesión o token, 403 sin permiso, 404 inexistente, 422 regla de negocio violada y 423 cuenta bloqueada.",
])
par("Las tareas periódicas (`presentacion/tareas_periodicas.py`) se ejecutan cada 60 s dentro del mismo proceso, como supuso el L4 §6.1: marcan como Desconectado a los equipos sin reporte por más de 3 intervalos y expiran las órdenes vencidas.")
h(2, "3.4 Agente")
par("`AgenteSentinela` repite dos ciclos: cada 5 minutos compone una lectura y la envía, y cada 60 s consulta sus órdenes pendientes (D2: el agente siempre inicia la comunicación). Antes de enviar una lectura nueva vacía la cola local, para que el servidor reciba las lecturas en orden cronológico. Cada orden se ejecuta en su propio hilo, así la cuenta regresiva del aviso no detiene el envío de métricas.")
par("**Salvaguarda del prototipo (modo seguro).** El ejecutor de reinicio solo llama a `shutdown.exe` si la variable `SENTINELA_ACCIONES_REALES=1` está definida, lo que se hace únicamente en la VM de pruebas (L1: «todas las acciones remotas se prueban solo en máquinas virtuales»). Sin ella, el agente registra el comando que habría ejecutado e informa el resultado; así el flujo completo se puede probar en el equipo de desarrollo sin apagarlo.")
h(2, "3.5 Panel web")
par("El panel es una aplicación React de una sola página. `sesion.jsx` guarda el JWT en `sessionStorage` (se borra al cerrar la pestaña) y `api/cliente.js` lo adjunta a cada petición. Ante cualquier 401 el panel cierra la sesión local y vuelve al inicio de sesión con un mensaje (RF17). Las vistas se refrescan solas cada 15–30 s, de modo que el técnico ve los cambios de estado sin recargar la página.")
h(2, "3.6 Contrato de la API")
par("La documentación interactiva del contrato está en `http://localhost:8000/docs` (OpenAPI generado por FastAPI). La Tabla 6 resume los endpoints.")
tabla("Endpoints del prototipo.", ["Método y ruta", "Servicio", "RF", "Permiso / autenticación"], [
    ["POST /api/panel/sesion", "ServicioAutenticacion.iniciar_sesion", "RF17", "Público"],
    ["GET /api/panel/equipos", "ParqueComputacional.listar", "RF05", "ConsultarParque"],
    ["GET /api/panel/equipos/{id}", "ParqueComputacional.detalle", "RF06", "ConsultarParque"],
    ["GET /api/panel/equipos/{id}/lecturas?rango=", "ParqueComputacional.historial", "RF06", "ConsultarParque"],
    ["POST /api/panel/equipos/{id}/comandos", "ServicioAcciones.crear_comando", "RF08, RF11", "OrdenarAccion / Formatear"],
    ["GET /api/panel/comandos", "ServicioAcciones.listar", "RF08", "ConsultarParque"],
    ["POST /api/panel/comandos/{id}/cancelar", "ServicioAcciones.cancelar", "RF08", "OrdenarAccion"],
    ["GET /api/panel/alertas", "GestorAlertas.consultar_abiertas", "RF16", "ConsultarParque"],
    ["GET, PUT /api/panel/umbrales[/{métrica}]", "ServicioConfiguracion", "RF07", "Sesión / ConfigurarUmbrales"],
    ["GET, POST, PUT /api/panel/usuarios…", "ServicioUsuarios", "RF13", "GestionarUsuarios"],
    ["GET /api/panel/bitacora", "BitacoraAuditoria.consultar", "RF18", "ConsultarBitacora"],
    ["POST /api/agente/enrolamiento", "ServicioEnrolamiento.enrolar", "RF01", "Código de enrolamiento"],
    ["POST /api/agente/lecturas", "ServicioRecepcionDatos.recibir_lectura", "RF02", "Token del agente"],
    ["GET /api/agente/comandos/pendientes", "ServicioAcciones.comandos_pendientes", "RF08", "Token del agente"],
    ["POST /api/agente/comandos/{id}/resultado", "ServicioAcciones.registrar_resultado", "RF08, RF14", "Token del agente"],
], [5.6, 5.4, 1.8, 3.2], tam=8.5)

# ==================================================================== 4. Trazabilidad
h(1, "4. Trazabilidad diseño → implementación")
h(2, "4.1 Clases del diseño del L4 en el código")
par("La Tabla 7 ubica cada clase de los diagramas refinados del L4. De las 63 clases, enumeraciones e interfaces del diseño, 53 están en el código; las 10 restantes pertenecen a los RF que quedan para el L6.")
I, P_, N = "Implementada", "Parcial", "Pendiente L6"
tabla("Clases del L4 y su ubicación en el código.", ["Clase del L4", "Ubicación en el código", "Estado"], [
    ["Usuario, Tecnico, Administrador, Sesion", "`dominio/usuarios.py`", I],
    ["Permiso, TipoAccion, Rol, EstadoEquipo, EstadoComando, Metrica, NivelAlerta, ModoApagado", "`dominio/enumeraciones.py`", I],
    ["EntradaBitacora, FiltroBitacora", "`dominio/auditoria.py`", I],
    ["Equipo, TokenAgente, Lectura, UsoDisco, Alerta, Umbral, ConfiguracionUmbrales", "`dominio/monitoreo.py`", I],
    ["ParqueComputacional", "`aplicacion/parque_computacional.py`", I + " (AJ4)"],
    ["Comando, ComandoReinicioApagado, ComandoFormateo, OrdenComando", "`dominio/acciones.py`", I],
    ["ComandoInstalacionApp, ComandoActualizacionSO, ComandoEscritorioRemoto, CatalogoAplicaciones, AplicacionAprobada, AvisoUsuario", "—", N],
    ["Inventario, AplicacionInstalada, EstadoActualizacionSO", "—", N + " (RF03, RF04)"],
    ["ServicioAutenticacion, ServicioUsuarios, ServicioConfiguracion, ServicioEnrolamiento", "`aplicacion/servicio_*.py`", I],
    ["ServicioRecepcionDatos, ServicioDisponibilidad, GestorAlertas", "`aplicacion/`", I],
    ["ServicioAcciones, BitacoraAuditoria", "`aplicacion/servicio_acciones.py`, `bitacora_auditoria.py`", I],
    ["Siete interfaces *Repository", "`dominio/repositorios.py`", I],
    ["Siete implementaciones *RepositoryPg", "`infraestructura/repositorios_sql.py` (*RepositorySql)", I + " (AJ2)"],
    ["AgenteSentinela, ClienteAPI, ColaLocalLecturas, AlmacenToken", "`agent/sentinela_agente/`", I],
    ["RecolectorMetricas", "`recolectores.py`", I],
    ["RecolectorInventario", "`recolectores.py`", P_ + " (solo leer_hardware)"],
    ["EjecutorAccion, EjecutorReinicioApagado, EjecutorSimulado", "`ejecutores.py`", I],
    ["EjecutorInstalacion", "—", N + " (RF09)"],
    ["NotificadorUsuario", "`notificador.py`", P_ + " (consola)"],
    ["DesenlaceAviso, DatosEquipo, ResultadoEjecucion", "`modelo.py` (agente), `acciones.py`, `servicio_enrolamiento.py`", I],
], [7.0, 6.4, 2.6])
h(2, "4.2 Mensajes de las secuencias refinadas")
par("Se comprobó con un script que **cada mensaje** de los diagramas `secuencia_cu02_l4_*` y `secuencia_cu07_l4_*` existe como método en la clase que lo recibe (convertido a *snake_case*). El resultado fue que no falta ninguno. La Tabla 8 muestra el recorrido de CU07, que es el flujo central de la demostración.")
tabla("Recorrido de CU07 en el código.", ["Paso de la secuencia (L4)", "Método en el código"], [
    ["crearComando(s, e, ReiniciarApagar, p)", "`ServicioAcciones.crear_comando()`"],
    ["autorizar(s, OrdenarAccion)", "`ServicioAutenticacion.autorizar()` con `TipoAccion.permiso_requerido()`"],
    ["registrarIntentoDenegado(u, t) → HTTP 403", "`BitacoraAuditoria.registrar_intento_denegado()` + `PermisoDenegado(conservar_cambios=True)`"],
    ["registrarOrden(c, u) → agregar(entrada)", "`BitacoraAuditoria.registrar_orden()` → `BitacoraRepositorySql.agregar()`"],
    ["falla la escritura → HTTP 500, no hay acción sin registro", "La transacción de la petición se revierte completa (`obtener_bd()`)"],
    ["comandosPendientes(token) → marcarEntregado(), aOrden()", "`ServicioAcciones.comandos_pendientes()`, `Comando.marcar_entregado()`, `Comando.a_orden()`"],
    ["seleccionarEjecutor(o.tipo)", "`AgenteSentinela.seleccionar_ejecutor()`"],
    ["opt interrumpeUso: mostrarAviso(o)", "`NotificadorUsuario.mostrar_aviso()`"],
    ["ejecutar(o) → r", "`EjecutorReinicioApagado.ejecutar()`"],
    ["registrarResultado(id, r) → cerrarEntrada(c, r.estado)", "`ServicioAcciones.registrar_resultado()` → `BitacoraAuditoria.cerrar_entrada()`"],
], [7.4, 8.6])
h(2, "4.3 Decisiones de diseño D1–D12 en el código")
tabla("Evidencia de las decisiones del L4 en el prototipo.", ["Decisión", "Evidencia en el código", "Estado"], [
    ["D1 Token propio por agente", "`Equipo.emitir_token()`, `ServicioEnrolamiento.autenticar_agente()`; el servidor guarda el hash.", I],
    ["D2 El agente inicia la comunicación", "`AgenteSentinela.ciclo_comandos()` cada 60 s; el servidor no abre conexiones al equipo.", I],
    ["D3 Servicio de Windows y token protegido", "`AlmacenToken` en archivo.", N],
    ["D4 Recolectores acotados", "`RecolectorMetricas` + esquema `LecturaEntrada` con `extra=\"forbid\"`.", I],
    ["D5 Cola local con reenvío ordenado", "`ColaLocalLecturas` (SQLite) y `AgenteSentinela._reenviar_pendientes()`.", I],
    ["D6 Estado precalculado y consultas en el repositorio", "`Equipo.evaluar_estado()` guarda estado y severidad; `listar_con_filtros()` ordena y pagina en SQL.", I],
    ["D7 Autorización en un único servicio", "`ServicioAutenticacion.autorizar()`; el panel oculta opciones, pero decide la API.", I],
    ["D8 Código de Windows solo en el agente", "`shutdown.exe`, WMI y psutil están solo en `agent/`.", I],
    ["D9 Tres piezas desplegables", "`frontend/`, `backend/` y la base de datos por URL.", I],
    ["D10 Aviso en lenguaje simple", "Texto del aviso en `notificador.py`; falta la ventana (W3).", P_],
    ["D11 Bitácora antes que la orden", "`crear_comando()` llama a `registrar_orden()` antes de `guardar(c)` en la misma transacción.", I],
    ["D12 OrdenComando y ejecutores intercambiables", "`OrdenComando` sin comportamiento; `EjecutorAccion.soporta()` (Estrategia).", I],
], [4.6, 9.0, 2.4])
h(2, "4.4 Ajustes al diseño durante la implementación")
par("Implementar obliga a decidir detalles que el diseño dejó abiertos. La Tabla 10 registra cada ajuste, su motivo y su efecto, para que el L6 actualice los diagramas.")
tabla("Ajustes al diseño del L4.", ["ID", "Ajuste", "Motivo", "Efecto en el diseño"], [
    ["AJ1", "Las entidades del dominio se declaran con el mapeo declarativo de SQLAlchemy.", "Evita mantener dos modelos paralelos (dominio y ORM). Las consultas siguen detrás de los repositorios.", "El dominio depende solo de los metadatos de mapeo."],
    ["AJ2", "*RepositoryPg pasa a llamarse *RepositorySql.", "La misma implementación sirve a PostgreSQL y SQLite.", "Renombrar en el diagrama de persistencia."],
    ["AJ3", "Base de datos de desarrollo SQLite.", "El equipo de desarrollo no tiene PostgreSQL; el cambio es solo la variable `SENTINELA_BD_URL`.", "Ninguno; RNF10 se verifica en el L6 con PostgreSQL."],
    ["AJ4", "ParqueComputacional queda como objeto de consulta en la capa de aplicación.", "Hay un solo parque; su estado son los equipos.", "Mover la clase o anotarla como «servicio de consulta»."],
    ["AJ5", "Nuevo valor `Denegado` en EstadoComando.", "registrarIntentoDenegado() necesitaba un resultado; ningún valor del L3 lo representaba.", "Agregar el valor (solo lo usan las entradas de bitácora)."],
    ["AJ6", "Sesion no se persiste: vive en el JWT firmado.", "Validar la firma evita una consulta por petición; la desactivación sigue siendo inmediata porque se revisa el usuario.", "Quitar la composición persistente Usuario ◆ Sesion."],
    ["AJ7", "EntradaBitacora copia los nombres de usuario y equipo y no tiene clave foránea al comando.", "La entrada debe seguir legible aunque cambien los datos (RNF12) y se escribe antes que el comando (D11).", "Agregar los atributos de copia."],
    ["AJ8", "Lectura única por (equipo, marca de tiempo).", "Es lo que garantiza «sin duplicados» de RNF04 cuando el agente reenvía.", "Agregar la restricción {unique}."],
    ["AJ9", "Una lectura «supera» el umbral si es estrictamente mayor.", "Interpretación literal de RF16; se fija con casos de valor límite (CP-21).", "Nota en Umbral.evaluar()."],
    ["AJ10", "Operaciones de repositorio adicionales: `existe()`, `ultima()`, `abiertas_de_equipo()`, `de_comando()`, `vigentes()`, `listar()`.", "Las necesitan los servicios; el L4 solo listó las operaciones de las secuencias.", "Agregarlas a los contratos."],
], [1.1, 4.6, 5.6, 4.7], tam=8.5)

# ==================================================================== 5. Interfaz
h(1, "5. Interfaz de usuario integrada")
h(2, "5.1 Del wireframe a la pantalla")
tabla("Correspondencia entre los wireframes del L4 y las vistas del prototipo.", ["Wireframe", "Vista implementada", "Diferencias con el wireframe"], [
    ["W1 Parque", "`vistas/Parque.jsx` (Figuras 2 y 5)", "Las tarjetas de resumen también filtran al hacer clic; se agregó el estado vacío con instrucciones para instalar el agente (CU04 1a)."],
    ["W2 Detalle y formateo", "`vistas/DetalleEquipo.jsx` (Figuras 3, 4 y 6)", "Los gráficos muestran las líneas de umbral; se agregó la confirmación para reiniciar/apagar; las acciones del L6 aparecen deshabilitadas."],
    ["W3 Aviso al usuario", "`agent/…/notificador.py`", "Por ahora solo en consola (RF15 parcial)."],
    ["(sin wireframe)", "Alertas, Acciones, Bitácora, Umbrales y Usuarios", "Reutilizan la estructura de W1 (título, explicación, filtros y tabla), como estableció el L4 §4.4."],
], [3.0, 5.4, 7.6])
h(2, "5.2 Pantallas del prototipo")
par("Las capturas se tomaron del prototipo en funcionamiento con los datos de demostración (`backend/scripts/sembrar_demo.py`); todos los datos son ficticios.")
figura("01_inicio_sesion.png", "Inicio de sesión (RF17).", 12)
figura("02_parque_tecnico.png", "Parque visto por un Técnico: los críticos aparecen primero y el menú no muestra Umbrales ni Usuarios (W1, RNF06, RNF07).")
figura("03_detalle_tecnico.png", "Detalle de un equipo crítico: alertas abiertas, gráficos con umbrales y acciones disponibles para el rol (W2, RF06).", 14)
figura("04_confirmar_reinicio.png", "Confirmación de reinicio: explica qué ocurrirá y deja «Cancelar» como opción por defecto (RF08).")
figura("05_parque_filtro_critico.png", "Parque filtrado por la tarjeta «Crítico» (RF05).")
figura("06_formateo_nombre_incorrecto.png", "Formateo: el botón sigue deshabilitado mientras el nombre escrito no coincide (W2, RF11).")
figura("07_alertas.png", "Alertas abiertas por umbral crítico y por desconexión (RF16).")
figura("08_acciones.png", "Seguimiento de órdenes: una pendiente se puede cancelar; una fallida muestra el motivo (RF08).")
figura("09_bitacora.png", "Bitácora con filtros, sin botones de edición ni borrado (RF14, RF18, RNF12).")
figura("10_umbrales_validacion.png", "Umbrales: el panel avisa antes de enviar un umbral crítico igual al de advertencia (RF07).")
figura("11_usuarios.png", "Gestión de usuarios (RF13).")
h(2, "5.3 Decisiones de usabilidad")
par("El L4 aplicó tres de los principios de diseño de interfaz vistos en clase (Sommerville). En el prototipo se aplicaron los seis; la Tabla 12 justifica cada decisión.")
tabla("Decisiones de usabilidad y su justificación.", ["Principio", "Decisión en el prototipo", "Justificación"], [
    ["Familiaridad del usuario", "Vocabulario del área de TI (equipo, parque, orden, bitácora) y textos sin siglas internas.", "El técnico no conoce el modelo interno (Comando, OrdenComando)."],
    ["Uniformidad", "Todas las vistas usan la misma estructura (título, explicación, filtros, tabla) y las mismas etiquetas de estado.", "Lo aprendido en una vista sirve en las demás."],
    ["Mínima sorpresa", "Cada confirmación dice qué ocurrirá: la orden queda Pendiente, el usuario recibe un aviso y todo queda en la bitácora.", "El técnico no descubre las consecuencias después."],
    ["Recuperabilidad", "«Cancelar» tiene el foco por defecto; el formateo exige el nombre exacto; una orden Pendiente se puede cancelar; Esc cierra los diálogos.", "Las acciones remotas no se pueden deshacer una vez ejecutadas."],
    ["Guía al usuario", "Errores en lenguaje simple junto al campo (umbrales, contraseña); estados vacíos con instrucciones («No hay equipos que coincidan» con «Limpiar filtros»).", "Cada error dice cómo corregirlo."],
    ["Diversidad de usuarios", "Estado con ícono y texto además del color (▲ ◆ ✕ ●); navegación por teclado y foco visible; el menú depende del rol.", "Accesible para personas con daltonismo y adaptado al Técnico y al Administrador."],
], [3.2, 7.2, 5.6])
h(2, "5.4 Manejo de errores y casos borde en la interfaz")
vinetas([
    "**Sesión expirada o usuario desactivado:** cualquier 401 devuelve al inicio de sesión con el motivo.",
    "**Sin conexión con el servidor:** se muestra «No hay conexión con el servidor de SentinelaTI» en lugar de un error técnico.",
    "**Sensor no disponible:** si un equipo no informa temperatura (habitual en máquinas virtuales), el gráfico dice «Sensor no disponible» y no dibuja ceros (criterio de RF02).",
    "**Equipo desconectado:** la confirmación de reinicio avisa que la orden se entregará cuando el equipo vuelva o expirará en 24 h.",
    "**Validación doble:** las reglas de umbrales y contraseñas se revisan en el panel y también en el servidor; el panel solo adelanta el aviso.",
    "**Búsqueda:** espera 300 ms después de la última tecla antes de consultar, para no enviar una petición por cada carácter.",
])

# ==================================================================== 6. Plan de pruebas
h(1, "6. Esbozo del plan de pruebas")
h(2, "6.1 Enfoque")
vinetas([
    "**Pruebas basadas en requerimientos:** cada caso toma como resultado esperado el criterio de aceptación del ERS. Hay al menos un caso por cada RF implementado (Tablas 13 y 14).",
    "**Particiones de equivalencia y valores límite** sobre cuatro entradas del sistema (sección 6.3).",
    "**Niveles:** pruebas unitarias del dominio, de integración de la API (petición HTTP real contra una base SQLite en memoria) y del agente con la API simulada. Las pruebas de sistema en la VM y las de los RNF medibles se planifican para el L6 (sección 6.5).",
    "**Automatización:** los 33 casos están automatizados con pytest; se ejecutan con `python -m pytest` en `backend/` y en `agent/`.",
    "Este esbozo es la base del plan completo del L6, que agregará la planificación, el entorno de la VM y el registro de resultados.",
])
h(2, "6.2 Casos de prueba basados en requerimientos")
CP = [
    ["CP-01", "RF17", "Inicio de sesión con credenciales válidas.", "Correo y contraseña correctos del Administrador.", "200 con token, rol Administrador y sus permisos.", "test_cp01"],
    ["CP-02", "RF17", "Credenciales incorrectas.", "Contraseña errónea; correo inexistente.", "401 en ambos casos con el mismo mensaje (no revela qué dato falló).", "test_cp02"],
    ["CP-03", "RF17", "Endpoints del panel sin sesión.", "7 rutas sin token y con un token falso.", "401 en todas.", "test_cp03"],
    ["CP-04", "RF17", "Bloqueo tras intentos fallidos (CU03 3b).", "4 fallos y luego clave correcta; luego 5 fallos y clave correcta.", "Con 4 fallos ingresa; con 5 responde 423 aunque la clave sea correcta.", "test_cp04"],
    ["CP-05", "RF13", "Usuario creado ingresa con los permisos de su rol.", "El Administrador crea un Técnico; el Técnico inicia sesión.", "Rol Técnico con ConsultarParque, OrdenarAccion y ConsultarBitacora.", "test_cp05"],
    ["CP-06", "RF13", "Usuario desactivado.", "Desactivar al Técnico con su sesión abierta.", "Su sesión responde 401 y no puede volver a ingresar.", "test_cp06"],
    ["CP-07", "RF13, RNF07", "Funciones de Administrador con sesión de Técnico.", "Listar o crear usuarios y modificar un umbral.", "403 en las tres.", "test_cp07"],
    ["CP-08", "RF13", "Edición de rol y reglas de alta.", "Cambiar rol a Administrador; contraseña de 7 y 8 caracteres; correo repetido con mayúsculas.", "El rol cambia sus permisos; 7 → 422, 8 → 201; correo repetido → 422.", "test_cp08, 08b, 08c"],
    ["CP-09", "RF01", "Enrolamiento con código vigente.", "Código válido y datos del equipo.", "201 y el equipo aparece en el listado.", "test_cp09"],
    ["CP-10", "RF01", "Enrolamiento con código inválido.", "Código erróneo.", "401 y ningún equipo creado.", "test_cp10"],
    ["CP-11", "RF01, RNF01", "Reenrolamiento del mismo número de serie.", "Enrolar dos veces con la misma serie.", "Un solo equipo; el token anterior responde 401.", "test_cp11"],
    ["CP-12", "RF02", "Lectura válida con los cinco campos.", "CPU 12,5; RAM 40; disco 70; temperatura nula; 3 h.", "Se almacena y la temperatura queda «no disponible», no 0.", "test_cp12"],
    ["CP-13", "RF02, RNF04", "Reenvío de una lectura.", "La misma lectura dos veces.", "La segunda se informa como duplicada y no se guarda.", "test_cp13"],
    ["CP-14", "RF02, RNF01, RNF05", "Validación de la lectura.", "Sin token; CPU y temperatura fuera de rango; campo extra; fecha futura.", "401; 422 fuera de rango, con campo extra y con fecha > 5 min en el futuro.", "test_cp14 a 14e"],
    ["CP-15", "RF05", "Búsqueda y filtro con 20 equipos.", "2 críticos, 3 en advertencia, 15 normales; filtros por estado y búsquedas por nombre, IP y usuario.", "Cada filtro devuelve exactamente los equipos esperados, ordenados por severidad.", "test_cp15 a 15d"],
    ["CP-16", "RF06", "Historial por rango.", "Lecturas a 1 h, 23 h 58 min, 24 h 2 min, 6 d 23 h, 7 d 1 h y 29 d.", "24 h → 2, 7 días → 4, 30 días → 6; rango inválido → 422.", "test_cp16"],
    ["CP-17", "RF05, RF16", "Detección de equipo desconectado.", "Sin reporte por 15 min exactos y por 15 min 1 s; luego vuelve a reportar.", "15 min: sigue en línea; 15 min 1 s: Desconectado con alerta; al reportar vuelve a Normal y la alerta se cierra.", "test_cp17"],
    ["CP-18", "RF07", "Validación de umbrales.", "Particiones de la Tabla 15.", "Válidos → 200; inválidos → 422 sin alterar el umbral vigente.", "test_cp18, 18b"],
    ["CP-19", "RF07", "Aplicación de un umbral nuevo.", "Lectura CPU 60; umbral 50/55; nueva lectura CPU 60.", "El estado cambia a Crítico solo desde la lectura siguiente.", "test_cp19"],
    ["CP-20", "RF16", "Ciclo de vida de una alerta.", "CPU 99, luego 98, luego 30.", "Se abre una alerta, no se duplica y se cierra.", "test_cp20"],
    ["CP-21", "RF16", "Valores límite de las alertas.", "CPU 80; 80,1; 95; 95,1 (umbrales 80/95); tres métricas sobre el umbral; lectura atrasada.", "Normal, Advertencia, Advertencia, Crítico con alerta; una alerta por métrica; la lectura atrasada no cambia el estado.", "test_cp21 a 21c"],
    ["CP-22", "RF08", "Ciclo de vida del reinicio.", "Técnico ordena reiniciar; el agente consulta y responde.", "Pendiente → Entregado → Ejecutado; no se entrega dos veces; un fallo guarda el motivo; modo inválido → 422.", "test_cp22 a 22c"],
    ["CP-23", "RF08", "Cancelación de una orden.", "Cancelar una orden Pendiente y otra ya Entregada.", "La primera queda Cancelada y no llega al equipo; la segunda → 422.", "test_cp23"],
    ["CP-24", "RF08, RF14", "Expiración de órdenes.", "Orden pendiente a las 23 h 59 min y a las 24 h 1 min.", "Solo la segunda expira y la bitácora registra Expirado.", "test_cp24"],
    ["CP-25", "RF11", "Segunda confirmación del formateo.", "Nombre vacío, en minúsculas, incompleto, con espacio final y exacto.", "Solo el nombre exacto crea la orden, marcada como simulada.", "test_cp25, 25b"],
    ["CP-26", "RF11, RNF07", "Formateo con sesión de Técnico.", "El Técnico ordena formatear.", "403, la orden no llega al equipo y la bitácora registra el intento como Denegado.", "test_cp26"],
    ["CP-27", "RF14, RNF12", "Una entrada por orden e inmutabilidad.", "3 órdenes ejecutadas; revisión del contrato OpenAPI; resultado informado dos veces; agente de otro equipo.", "Exactamente 3 entradas completas; solo GET sobre la bitácora; el segundo resultado → 422; agente ajeno → 404.", "test_cp27 a 27d"],
    ["CP-28", "RF18", "Filtros de la bitácora.", "4 órdenes conocidas (2 usuarios × 2 equipos); 6 combinaciones de filtros y rangos de fecha.", "Cada combinación devuelve exactamente las entradas esperadas; «desde» > «hasta» → 422.", "test_cp28, 28b"],
    ["CP-29", "RF02", "Intervalo de reporte del agente.", "Particiones de la Tabla 18.", "Solo los enteros de 1 a 60 se aceptan.", "test_cp29"],
    ["CP-30", "RNF04", "Cola local sin conexión.", "2 h sin red (24 lecturas) y reconexión; lectura de 73 h; reinicio del agente.", "Llegan las 25 lecturas en orden y sin duplicados; se descarta lo anterior a 72 h; la cola sobrevive al reinicio.", "test_cp30 a 30c"],
    ["CP-31", "RF01 (CU02 3a)", "Token revocado.", "El servidor deja de aceptar el token del agente.", "El agente se reenrola y la lectura pendiente se envía.", "test_cp31"],
    ["CP-32", "RF08", "Ejecución en el agente.", "Orden en modo seguro; modo real con Reiniciar y Apagar; `shutdown` que falla.", "Informa el resultado; llama a `shutdown /r` o `/s`; un fallo se informa como Fallido con el mensaje.", "test_cp32 a 32c"],
    ["CP-33", "RF08 (D12)", "Selección de ejecutor (Estrategia).", "Órdenes de reinicio, formateo e instalación.", "Ejecutor real, simulado y «sin ejecutor» informado como Fallido.", "test_cp33, 33b"],
]
tabla("Casos de prueba basados en requerimientos (todos automatizados).", ["ID", "Req.", "Objetivo", "Entrada / pasos", "Resultado esperado", "Prueba"],
      CP, [1.2, 1.6, 3.0, 4.0, 4.4, 1.8], tam=8)
tabla("Cobertura de los RF implementados por los casos de prueba.", ["RF", "Casos", "RF", "Casos"], [
    ["RF01", "CP-09, CP-10, CP-11, CP-31", "RF11", "CP-25, CP-26"],
    ["RF02", "CP-12, CP-13, CP-14, CP-29", "RF13", "CP-05 a CP-08"],
    ["RF05", "CP-15, CP-17", "RF14", "CP-22, CP-24, CP-27"],
    ["RF06", "CP-16", "RF16", "CP-17, CP-20, CP-21"],
    ["RF07", "CP-18, CP-19", "RF17", "CP-01 a CP-04"],
    ["RF08", "CP-22, CP-23, CP-24, CP-32, CP-33", "RF18", "CP-28"],
], [1.6, 6.4, 1.6, 6.4])

h(2, "6.3 Particiones de equivalencia y valores límite")
par("Se eligieron cuatro entradas donde un error tiene consecuencias concretas: un umbral mal validado dispara o esconde alertas, una lectura fuera de rango contamina los gráficos, un intervalo inválido satura el servidor o deja de reportar, y una confirmación débil permite formatear el equipo equivocado.")
h(3, "Entrada 1: umbrales de una métrica porcentual (RF07)")
par("Dominio válido: `1 ≤ advertencia < crítico ≤ 100`. Se prueba con la CPU; RAM y disco usan la misma regla.")
tabla("Clases de equivalencia del par (advertencia, crítico).", ["Clase", "Condición", "Tipo", "Representante", "Resultado esperado"], [
    ["P1", "1 ≤ adv < crít ≤ 100", "Válida", "(70, 90)", "200; se aplica desde la lectura siguiente"],
    ["P2", "adv < 1", "Inválida", "(0, 90)", "422; el umbral vigente no cambia"],
    ["P3", "crít > 100", "Inválida", "(70, 100,1)", "422"],
    ["P4", "crít ≤ adv", "Inválida", "(90, 70)", "422 (criterio explícito de RF07)"],
], [1.2, 4.0, 1.8, 3.0, 6.0])
tabla("Valores límite del umbral de CPU (CP-18).", ["Caso", "Advertencia", "Crítico", "Límite probado", "Esperado", "Obtenido"], [
    ["VL1", "1", "2", "Mínimo del dominio", "200", "200"],
    ["VL2", "99", "100", "Máximo del dominio", "200", "200"],
    ["VL3", "89,9", "90", "Crítico apenas mayor", "200", "200"],
    ["VL4", "90", "90", "Crítico igual a advertencia", "422", "422"],
    ["VL5", "0", "90", "Bajo el mínimo", "422", "422"],
    ["VL6", "70", "100,1", "Sobre el máximo", "422", "422"],
], [1.4, 2.2, 2.0, 4.4, 2.0, 2.0])
par("**Valor límite asociado (RF16).** Con los umbrales por defecto 80/95, un valor igual al umbral **no** lo supera: CPU 80 → Normal, 80,1 → Advertencia, 95 → Advertencia, 95,1 → Crítico con alerta (CP-21, ajuste AJ9).")
h(3, "Entrada 2: uso de CPU informado en una lectura (RF02)")
tabla("Particiones y valores límite del uso de CPU (CP-14b).", ["Clase", "Condición", "Tipo", "Valores probados", "Esperado"], [
    ["P1", "uso < 0", "Inválida", "−0,1", "422"],
    ["P2", "0 ≤ uso ≤ 100", "Válida", "0 · 55,5 · 100", "200"],
    ["P3", "uso > 100", "Inválida", "100,1", "422"],
], [1.2, 4.0, 1.8, 4.5, 4.5])
par("La temperatura sigue el mismo esquema con dominio `[0, 150] °C` y una clase válida adicional: **nula** («no disponible»). Se probó con nulo, 0, 150, 150,1 y −1 (CP-14c).")
h(3, "Entrada 3: intervalo de reporte del agente (RF02)")
tabla("Particiones y valores límite del intervalo de reporte (CP-29).", ["Clase", "Condición", "Tipo", "Valores probados", "Esperado"], [
    ["P1", "minutos < 1", "Inválida", "0 · −5", "Se rechaza la configuración"],
    ["P2", "1 ≤ minutos ≤ 60", "Válida", "1 · 5 · 60", "Se acepta"],
    ["P3", "minutos > 60", "Inválida", "61", "Se rechaza"],
    ["P4", "No es un entero", "Inválida", "«5» · 2,5", "Se rechaza"],
], [1.2, 4.0, 1.8, 4.5, 4.5])
h(3, "Entrada 4: nombre escrito para confirmar el formateo (RF11)")
tabla("Particiones de la segunda confirmación (equipo «PC-PRUEBA-01», CP-25).", ["Clase", "Condición", "Tipo", "Representante", "Esperado"], [
    ["P1", "Idéntico al nombre del equipo", "Válida", "PC-PRUEBA-01", "201; orden simulada"],
    ["P2", "Vacío", "Inválida", "(vacío)", "422; no se crea la orden"],
    ["P3", "Difiere en mayúsculas", "Inválida", "pc-prueba-01", "422"],
    ["P4", "Prefijo del nombre (falta 1 carácter)", "Inválida", "PC-PRUEBA-0", "422"],
    ["P5", "Con espacios extra", "Inválida", "«PC-PRUEBA-01 »", "422"],
], [1.2, 5.0, 1.8, 3.4, 4.6])
h(3, "Valores límite de tiempo")
tabla("Valores límite de las reglas temporales.", ["Regla", "Justo en el límite", "Pasado el límite", "Caso"], [
    ["Desconexión: 3 intervalos de 5 min sin reporte", "15 min → en línea", "15 min 1 s → Desconectado", "CP-17"],
    ["Expiración de una orden Pendiente (24 h)", "23 h 59 min → sigue Pendiente", "24 h 1 min → Expirado", "CP-24"],
    ["Expiración de una orden Entregada (60 min)", "60 min → vigente", "60 min 1 s → expira", "test_expiracion_valores_limite"],
    ["Bloqueo de la cuenta (15 min)", "14 min 59 s → bloqueada", "15 min → desbloqueada", "test_bloqueo_por_intentos"],
    ["Historial de 24 h", "23 h 58 min → incluida", "24 h 2 min → excluida", "CP-16"],
    ["Retención de la cola local (72 h)", "71 h → se conserva", "73 h → se descarta", "CP-30b"],
], [5.6, 3.8, 4.0, 2.6])

h(2, "6.4 Resultados de la ejecución")
tabla("Resultado de las pruebas automatizadas (23-11-2026).", ["Suite", "Comando", "Pruebas", "Resultado"], [
    ["API y dominio", "`cd backend && python -m pytest`", "106", "106 aprobadas"],
    ["Agente", "`cd agent && python -m pytest`", "19", "19 aprobadas"],
    ["Panel (recorrido)", "Recorrido automatizado con Edge sin interfaz", "11 pantallas", "Sin errores en la consola; el Técnico no ve «Formatear»; el botón de formateo sigue deshabilitado con un nombre incompleto."],
], [3.0, 5.6, 2.2, 5.2])
par("Para comprobar que las pruebas detectan errores reales, se introdujeron dos fallos a propósito y luego se revirtieron: cambiar `>` por `>=` en `Umbral.evaluar()` hizo fallar CP-21 y la prueba unitaria del umbral, y quitar el registro del intento denegado hizo fallar CP-26.")
par("Además se verificó el flujo completo con el agente real en el equipo de desarrollo (modo seguro): enrolamiento, lectura con psutil, orden de reinicio desde la API, aviso con cuenta regresiva, ejecución y cierre de la entrada de bitácora como «Ejecutado».")
h(2, "6.5 Pruebas pendientes para el L6")
tabla("Pruebas planificadas para el plan completo del L6.", ["Prueba", "Requerimiento", "Tipo", "Entorno"], [
    ["Reinicio real ejecutado en ≤ 2 min, con `SENTINELA_ACCIONES_REALES=1`", "RF08", "Sistema, manual", "VM Windows 10 y 11"],
    ["Inventario coincide con «Aplicaciones instaladas» de Windows", "RF03", "Sistema, manual", "VM"],
    ["CPU ≤ 2 % y RAM ≤ 100 MB del agente durante 1 h", "RNF03", "Rendimiento", "VM + Monitor de rendimiento"],
    ["Corte de red de 2 h y reconexión", "RNF04", "Sistema", "VM"],
    ["Listado de 200 equipos en ≤ 3 s", "RNF08", "Rendimiento", "Base sembrada + herramientas del navegador"],
    ["3 usuarios identifican los críticos de 50 equipos en < 10 s", "RNF06", "Usabilidad", "Panel con datos de demostración"],
    ["Cuenta estándar no puede detener el servicio", "RNF02", "Seguridad", "VM"],
    ["Pruebas con PostgreSQL", "RNF10", "Integración", "PostgreSQL 16"],
    ["Pruebas de las vistas React (componentes)", "RF05–RF18", "Unitaria (frontend)", "Vitest + Testing Library"],
], [6.6, 2.4, 3.0, 4.0])

# ==================================================================== 7. Estado y continuación
h(1, "7. Estado de avance y guía para continuar")
h(2, "7.1 Cómo ejecutar el prototipo")
numeros([
    "Requisitos: Python 3.12 o superior y Node.js 20 o superior.",
    "Desde la raíz del repositorio: `python -m venv .venv` y luego `.venv\\Scripts\\pip install -r backend/requirements.txt -r agent/requirements.txt -r requirements-dev.txt`.",
    "Datos de demostración (opcional): en `backend/`, `..\\.venv\\Scripts\\python -m scripts.sembrar_demo --reiniciar`.",
    "API: en `backend/`, `..\\.venv\\Scripts\\python -m uvicorn app.main:app --port 8000`. El contrato queda en `http://localhost:8000/docs`.",
    "Panel: en `frontend/`, `npm install` y `npm run dev`; se abre en `http://localhost:5173`.",
    "Agente: en `agent/`, `..\\.venv\\Scripts\\python -m sentinela_agente --servidor http://localhost:8000 --codigo SENTINELA-DEMO-2026`. En la VM de pruebas, definir antes `SENTINELA_ACCIONES_REALES=1`.",
])
par("Las credenciales de prueba, las variables de configuración y la correspondencia entre módulos y clases del L4 están en `backend/README.md`, `agent/README.md` y `frontend/README.md`.")
h(2, "7.2 Pendientes priorizados para el L6")
tabla("Trabajo pendiente, en orden de prioridad.", ["#", "Pendiente", "RF / RNF", "Dónde empezar"], [
    ["1", "Ventana de aviso con «Posponer 30 minutos» e ícono de bandeja (W3).", "RF15, RNF11", "`NotificadorUsuario`: reemplazar la implementación de consola manteniendo `mostrar_aviso()`."],
    ["2", "Instalar el agente como servicio de Windows y proteger el token con DPAPI.", "RNF02, D3", "`AlmacenToken` y un instalador del servicio."],
    ["3", "Inventario completo y actualizaciones pendientes.", "RF03, RF04", "`RecolectorInventario` + `ServicioRecepcionDatos.recibir_inventario()`."],
    ["4", "Instalación desde el catálogo con winget.", "RF09", "Nueva subclase `ComandoInstalacionApp` y `EjecutorInstalacion`; el patrón Estrategia ya está listo."],
    ["5", "Actualización del SO y escritorio remoto simulados.", "RF10, RF12", "Subclases de `Comando`; el agente ya tiene `EjecutorSimulado`."],
    ["6", "Cambio obligatorio de la contraseña temporal en el primer ingreso.", "CU03 3a", "`ServicioAutenticacion.iniciar_sesion()`."],
    ["7", "Ejecutar las pruebas con PostgreSQL y servir la API por HTTPS.", "RNF01, RNF10", "Variable `SENTINELA_BD_URL` y opciones TLS de uvicorn."],
    ["8", "Actualizar los diagramas del L4 con los ajustes AJ1–AJ10.", "—", "`docs/uml/*_l4*.puml`."],
], [0.7, 6.0, 2.3, 7.0])
h(2, "7.3 Riesgos actualizados")
vinetas([
    "**R1 (temperatura en Windows):** en el equipo de desarrollo la zona térmica ACPI no estuvo disponible y el agente informó la temperatura como nula. El sistema ya lo maneja como «no disponible», que es la contingencia que definió el L1.",
    "**Acciones reales en equipos productivos:** se mitigó con el modo seguro por defecto en el agente.",
    "**Integración del panel con la API:** riesgo cerrado; el recorrido automatizado de las 11 pantallas no muestra errores.",
])

# ==================================================================== 8. Cumplimiento
h(1, "8. Cumplimiento del enunciado del LAB5")
tabla("Exigencias del enunciado y dónde se cumplen.", ["Exigencia del enunciado", "Dónde se cumple"], [
    ["Prototipo funcional con una porción representativa del alcance", "Sección 2 (12 RF de punta a punta) y repositorio (`backend/`, `agent/`, `frontend/`)."],
    ["Coherente con el diseño arquitectónico y de clases del L4", "Sección 4: clases, mensajes de secuencia y decisiones D1–D12 ubicados en el código; ajustes documentados."],
    ["Interfaz integrada coherente con el wireframe del L4", "Sección 5: correspondencia W1–W3 y 11 capturas del prototipo."],
    ["Código en el repositorio del proyecto", "https://github.com/gazpel/SentinelaTI, rama `feat/l5-prototipo`."],
    ["Al menos un caso de prueba basado en requerimientos por RF implementado", "Tablas 13 y 14: 33 casos que cubren los 12 RF implementados."],
    ["Particiones de equivalencia con casos límite sobre al menos una entrada", "Sección 6.3: cuatro entradas con sus particiones y valores límite, más las reglas temporales."],
    ["Manejo de errores y casos borde (rúbrica, nivel destacado)", "Secciones 3.3 y 5.4, y los casos límite de la sección 6.3."],
    ["Documentación que permita a otro equipo continuar", "Sección 7 y los README de `backend/`, `agent/` y `frontend/`: ejecución, configuración y pendientes priorizados con su punto de partida en el código."],
], [6.4, 9.6])

h(1, "9. Referencias")
vinetas([
    "Macías, J. (2026). Enunciado LAB5: Prototipo/Implementación parcial e integración de interfaz. Departamento de Ingeniería Informática, USACH.",
    "SentinelaTI (2026). Laboratorios 2 (ERS v1.0), 3 (Modelado UML) y 4 (Arquitectura, diseño OO y wireframe).",
    "Sommerville, I. (2011). Ingeniería de Software (9.ª ed.). Pearson. Capítulo 8 (pruebas de software).",
    "Sommerville, I. (2005). Ingeniería del Software (7.ª ed.). Pearson. Capítulo 16 (diseño de interfaces de usuario).",
    "Myers, G., Sandler, C. y Badgett, T. (2011). The Art of Software Testing (3.ª ed.). Wiley (particiones de equivalencia y análisis de valores límite).",
    "OWASP (2023). Password Storage Cheat Sheet (PBKDF2-HMAC-SHA256).",
    "Documentación de FastAPI, SQLAlchemy 2, psutil, React y Recharts (versiones de la Tabla 5).",
])

SALIDA.parent.mkdir(parents=True, exist_ok=True)
d.save(str(SALIDA))
print("Tablas:", n_tabla, "Figuras:", n_figura, "→", SALIDA)
