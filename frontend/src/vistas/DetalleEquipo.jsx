// W2 — Detalle del equipo y acciones remotas (CU05, CU07; RF06, RF08, RF11).
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/cliente'
import { EtiquetaComando, EtiquetaEstado, MensajeError, MensajeExito, Modal } from '../componentes/comunes.jsx'
import { useSesion } from '../sesion.jsx'
import { METRICAS, fechaHora, haceCuanto, valorMetrica } from '../util/formato'

const RANGOS = [['24h', '24 h'], ['7d', '7 días'], ['30d', '30 días']]

export default function DetalleEquipo() {
  const { id } = useParams()
  const { puede } = useSesion()
  const [equipo, setEquipo] = useState(null)
  const [lecturas, setLecturas] = useState([])
  const [umbrales, setUmbrales] = useState({})
  const [ordenes, setOrdenes] = useState([])
  const [rango, setRango] = useState('24h')
  const [error, setError] = useState(null)
  const [exito, setExito] = useState(null)
  const [dialogo, setDialogo] = useState(null)  // 'Reiniciar' | 'Apagar' | 'Formatear'

  const cargarEquipo = useCallback(() => {
    api(`/equipos/${id}`).then(setEquipo).catch(setError)
    api('/comandos', { parametros: { equipo: id } }).then(setOrdenes).catch(setError)
  }, [id])

  useEffect(() => {
    cargarEquipo()
    api('/umbrales').then((us) => setUmbrales(Object.fromEntries(us.map((u) => [u.metrica, u])))).catch(() => {})
    const t = setInterval(cargarEquipo, 15000)
    return () => clearInterval(t)
  }, [cargarEquipo])

  useEffect(() => {
    api(`/equipos/${id}/lecturas`, { parametros: { rango } }).then(setLecturas).catch(setError)
  }, [id, rango])

  async function ordenar(cuerpo, mensaje) {
    setError(null)
    try {
      await api(`/equipos/${id}/comandos`, { metodo: 'POST', cuerpo })
      setDialogo(null)
      setExito(mensaje)
      cargarEquipo()
    } catch (err) {
      setDialogo(null)
      setError(err)
    }
  }

  async function cancelar(orden) {
    setError(null)
    try {
      await api(`/comandos/${orden.idComando}/cancelar`, { metodo: 'POST' })
      setExito(`Se canceló la orden de ${orden.descripcion.toLowerCase()}.`)
      cargarEquipo()
    } catch (err) { setError(err) }
  }

  if (!equipo) return error ? <MensajeError error={error} /> : <p className="sub">Cargando…</p>
  const ultima = equipo.ultimaLectura

  return (
    <>
      <div className="migas"><Link to="/">Parque</Link> › {equipo.nombre}</div>
      <h1>{equipo.nombre} <EtiquetaEstado estado={equipo.estado} /></h1>
      <p className="sub">
        Último usuario: {equipo.ultimoUsuario ?? '—'} · IP {equipo.direccionIp ?? '—'} · Último reporte: {haceCuanto(equipo.fechaUltimoReporte)}
      </p>
      <MensajeError error={error} />
      <MensajeExito texto={exito} />

      {puede('OrdenarAccion') && (
        <div className="acciones">
          <button className="boton" onClick={() => setDialogo('Reiniciar')}>Reiniciar</button>
          <button className="boton" onClick={() => setDialogo('Apagar')}>Apagar</button>
          <button className="boton" disabled title="Se implementa en el L6 (RF09)">Instalar aplicación</button>
          <button className="boton" disabled title="Se implementa en el L6 (RF10)">Actualizar SO (simulado)</button>
          <button className="boton" disabled title="Se implementa en el L6 (RF12)">Escritorio remoto (simulado)</button>
          {/* RF11 / RNF07: el formateo solo aparece para el Administrador y tiene un estilo distinto. */}
          {puede('Formatear') && <button className="boton peligro" onClick={() => setDialogo('Formatear')}>Formatear… (simulado)</button>}
        </div>
      )}

      {equipo.alertasAbiertas.length > 0 && (
        <div className="mensaje critico">
          <strong>Alertas abiertas:</strong>{' '}
          {equipo.alertasAbiertas.map((a) => a.metrica
            ? `${METRICAS[a.metrica].texto} ${valorMetrica(a.valor, METRICAS[a.metrica].unidad)} desde ${fechaHora(a.fechaApertura)}`
            : `equipo desconectado desde ${fechaHora(a.fechaApertura)}`).join(' · ')}
        </div>
      )}

      <div className="rango" role="group" aria-label="Rango de los gráficos">
        Rango de los gráficos:
        {RANGOS.map(([valor, texto]) => (
          <button key={valor} className={`boton chico ${rango === valor ? 'primario' : ''}`} aria-pressed={rango === valor} onClick={() => setRango(valor)}>{texto}</button>
        ))}
        <span className="pie">{lecturas.length} lecturas en el rango</span>
      </div>

      <div className="grilla">
        {Object.entries(METRICAS).map(([clave, m]) => (
          <Grafico key={clave} metrica={m} umbral={umbrales[clave]} lecturas={lecturas} rango={rango}
            actual={ultima ? valorMetrica(ultima[m.campo], m.unidad) : '—'} />
        ))}
        <div className="caja">
          <h3>Equipo</h3>
          <dl className="ficha">
            <dt>Modelo</dt><dd>{equipo.modelo ?? '—'}</dd>
            <dt>N.º de serie</dt><dd>{equipo.numeroSerie}</dd>
            <dt>Sistema operativo</dt><dd>{equipo.sistemaOperativo ?? '—'}</dd>
            <dt>Enrolado</dt><dd>{fechaHora(equipo.fechaEnrolamiento)}</dd>
            <dt>Discos</dt><dd>{ultima ? ultima.discos.map((d) => `${d.unidad} ${valorMetrica(d.usoPorcentaje, '%')}`).join(' · ') : '—'}</dd>
          </dl>
          <p className="pie">El inventario de aplicaciones (RF03) se incorpora en el L6.</p>
        </div>
      </div>

      <h2>Órdenes recientes</h2>
      {ordenes.length === 0 ? <p className="sub">Este equipo no tiene órdenes.</p> : (
        <table className="tabla">
          <thead><tr><th>Acción</th><th>Estado</th><th>Ordenada por</th><th>Fecha de la orden</th><th>Resultado</th><th></th></tr></thead>
          <tbody>
            {ordenes.slice(0, 10).map((o) => (
              <tr key={o.idComando}>
                <td>{o.descripcion}</td>
                <td><EtiquetaComando estado={o.estado} /></td>
                <td>{o.ordenadoPor}</td>
                <td>{fechaHora(o.fechaOrden)}</td>
                <td>{o.fechaResultado ? fechaHora(o.fechaResultado) : '—'}{o.motivoFallo && <div className="pie">{o.motivoFallo}</div>}</td>
                <td>{o.estado === 'Pendiente' && <button className="boton chico" onClick={() => cancelar(o)}>Cancelar orden</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {(dialogo === 'Reiniciar' || dialogo === 'Apagar') && (
        <ConfirmacionApagado modo={dialogo} equipo={equipo} onCerrar={() => setDialogo(null)}
          onConfirmar={() => ordenar({ tipo: 'ReiniciarApagar', modo: dialogo },
            `Orden de ${dialogo === 'Reiniciar' ? 'reinicio' : 'apagado'} creada. El equipo la recibirá en su próximo sondeo (≤ 60 s).`)} />
      )}
      {dialogo === 'Formatear' && (
        <ConfirmacionFormateo equipo={equipo} onCerrar={() => setDialogo(null)}
          onConfirmar={(nombre) => ordenar({ tipo: 'Formatear', nombreConfirmado: nombre },
            'Orden de formateo (simulado) creada y registrada en la bitácora.')} />
      )}
    </>
  )
}

function Grafico({ metrica, umbral, lecturas, rango, actual }) {
  const formatoEje = (iso) => new Date(iso).toLocaleString('es-CL', rango === '24h'
    ? { hour: '2-digit', minute: '2-digit' } : { day: '2-digit', month: '2-digit' })
  const sinDatos = lecturas.every((l) => l[metrica.campo] === null || l[metrica.campo] === undefined)
  return (
    <div className="caja">
      <h3>{metrica.texto} <span className="valor-actual">{actual}</span></h3>
      {sinDatos ? <div className="sin-datos">{lecturas.length ? 'Sensor no disponible en este equipo' : 'Sin lecturas en el rango'}</div> : (
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={lecturas} margin={{ top: 6, right: 12, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="#e3e7e8" vertical={false} />
            <XAxis dataKey="marcaTiempo" tickFormatter={formatoEje} minTickGap={40} fontSize={11} />
            <YAxis fontSize={11} domain={metrica.unidad === '%' ? [0, 100] : ['auto', 'auto']} />
            <Tooltip labelFormatter={fechaHora} formatter={(v) => [valorMetrica(v, metrica.unidad), metrica.texto]} />
            {umbral && <ReferenceLine y={umbral.advertencia} stroke="#b7791f" strokeDasharray="4 3" />}
            {umbral && <ReferenceLine y={umbral.critico} stroke="#b02a2a" strokeDasharray="4 3" />}
            <Line type="monotone" dataKey={metrica.campo} stroke="#1F6F78" dot={false} strokeWidth={1.6} isAnimationActive={false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

function ConfirmacionApagado({ modo, equipo, onCerrar, onConfirmar }) {
  const [enviando, setEnviando] = useState(false)
  const verbo = modo === 'Reiniciar' ? 'reiniciará' : 'apagará'
  return (
    <Modal titulo={`${modo} ${equipo.nombre}`} onCerrar={onCerrar}>
      {(refCancelar) => (
        <>
          <p>El equipo se {verbo}. Qué ocurrirá:</p>
          <ul>
            <li>La orden queda <b>Pendiente</b> hasta que el equipo la reciba; mientras tanto puede cancelarla.</li>
            <li>El usuario del equipo recibe un aviso con cuenta regresiva de 5 minutos antes de la ejecución.</li>
            <li>La orden queda registrada en la bitácora con su nombre.</li>
          </ul>
          {equipo.estado === 'Desconectado' && <div className="mensaje aviso">El equipo está desconectado: la orden se entregará cuando vuelva a reportar (o expirará en 24 h).</div>}
          <div className="fila-botones">
            <button className="boton primario" ref={refCancelar} onClick={onCerrar}>Cancelar</button>
            <button className="boton" disabled={enviando} onClick={() => { setEnviando(true); onConfirmar() }}>{modo} equipo</button>
          </div>
        </>
      )}
    </Modal>
  )
}

function ConfirmacionFormateo({ equipo, onCerrar, onConfirmar }) {
  const [nombre, setNombre] = useState('')
  const [enviando, setEnviando] = useState(false)
  const coincide = nombre === equipo.nombre
  return (
    <Modal titulo={`Formatear ${equipo.nombre}`} onCerrar={onCerrar}>
      {(refCancelar) => (
        <>
          <div className="advertencia"><b>Esta acción borra todo el contenido del equipo y no se puede deshacer.</b><br />En esta versión del prototipo la ejecución es simulada.</div>
          <p>Qué ocurrirá:</p>
          <ul>
            <li>La orden queda <b>Pendiente</b> hasta que el equipo la reciba; mientras tanto puede cancelarla desde «Acciones».</li>
            <li>El usuario del equipo recibe un aviso con cuenta regresiva de 5 minutos antes de la ejecución.</li>
            <li>La orden queda registrada en la bitácora con su nombre.</li>
          </ul>
          <label>Para confirmar, escriba el nombre del equipo:
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} autoComplete="off" spellCheck={false} />
          </label>
          {nombre && !coincide && <div className="pie error-texto">El nombre no coincide todavía.</div>}
          <div className="fila-botones">
            <button className="boton primario" ref={refCancelar} onClick={onCerrar}>Cancelar</button>
            <button className="boton peligro" disabled={!coincide || enviando} onClick={() => { setEnviando(true); onConfirmar(nombre) }}>Formatear equipo</button>
          </div>
        </>
      )}
    </Modal>
  )
}
