// W1 — Parque computacional (CU04; RF05, RNF06, RNF08).
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/cliente'
import { EtiquetaEstado, MensajeError, Paginacion } from '../componentes/comunes.jsx'
import { ESTADOS, ORDEN_ESTADOS, haceCuanto } from '../util/formato'

const TAMANO = 25

export default function Parque() {
  const navegar = useNavigate()
  const [texto, setTexto] = useState('')
  const [busqueda, setBusqueda] = useState('')   // texto ya «asentado» (evita una petición por tecla)
  const [estado, setEstado] = useState('')
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const t = setTimeout(() => { setBusqueda(texto); setPagina(1) }, 300)
    return () => clearTimeout(t)
  }, [texto])

  const cargar = useCallback(() => {
    api('/equipos', { parametros: { estado, texto: busqueda, pagina, tamano: TAMANO } })
      .then((r) => { setDatos(r); setError(null) })
      .catch(setError)
  }, [estado, busqueda, pagina])

  useEffect(() => {
    cargar()
    const temporizador = setInterval(cargar, 30000)  // el estado se refresca solo cada 30 s
    return () => clearInterval(temporizador)
  }, [cargar])

  const elegirEstado = (nuevo) => { setEstado(nuevo === estado ? '' : nuevo); setPagina(1) }
  const limpiar = () => { setTexto(''); setBusqueda(''); setEstado(''); setPagina(1) }
  const total = datos ? Object.values(datos.resumen).reduce((a, b) => a + b, 0) : 0
  const hayFiltros = estado || busqueda

  return (
    <>
      <h1>Parque computacional</h1>
      <p className="sub">Equipos enrolados, ordenados por severidad. Haga clic en un equipo para ver su detalle y sus acciones.</p>
      <MensajeError error={error} />

      {/* Tarjetas de resumen: los críticos se ven sin cambiar de vista (RNF06). También filtran. */}
      <div className="tarjetas" role="group" aria-label="Filtrar por estado">
        {ORDEN_ESTADOS.map((e) => (
          <button key={e} className={`tarjeta ${estado === e ? 'sel' : ''}`} aria-pressed={estado === e} onClick={() => elegirEstado(e)}>
            <EtiquetaEstado estado={e} />
            <span className="numero">{datos?.resumen[e] ?? '–'}</span>
          </button>
        ))}
        <button className={`tarjeta ${!estado ? 'sel' : ''}`} aria-pressed={!estado} onClick={() => elegirEstado('')}>
          <strong>Total</strong><span className="numero">{datos ? total : '–'}</span>
        </button>
      </div>

      <div className="filtros">
        <input className="busqueda" type="search" placeholder="🔍 Buscar por nombre, IP o último usuario"
          value={texto} onChange={(e) => setTexto(e.target.value)} aria-label="Buscar equipos" maxLength={100} />
        <select value={estado} onChange={(e) => elegirEstado(e.target.value)} aria-label="Estado">
          <option value="">Estado: Todos</option>
          {ORDEN_ESTADOS.map((e) => <option key={e} value={e}>{ESTADOS[e].texto}</option>)}
        </select>
        <button className="boton" onClick={limpiar} disabled={!hayFiltros && !texto}>Limpiar filtros</button>
      </div>

      {datos && total === 0 && (
        <div className="vacio">
          <strong>Todavía no hay equipos enrolados.</strong>
          <p>Instale el agente en un equipo y ejecútelo con el código de enrolamiento de la organización:</p>
          <code>python -m sentinela_agente --servidor http://&lt;servidor&gt;:8000 --codigo &lt;código&gt;</code>
        </div>
      )}
      {datos && total > 0 && datos.items.length === 0 && (
        <div className="vacio">No hay equipos que coincidan. <button className="enlace" onClick={limpiar}>Limpiar filtros</button></div>
      )}
      {datos && datos.items.length > 0 && (
        <>
          <table className="tabla">
            <thead>
              <tr><th style={{ width: 160 }}>Estado</th><th>Equipo</th><th>Último usuario</th><th>IP</th><th>Último reporte</th><th style={{ width: 120 }}></th></tr>
            </thead>
            <tbody>
              {datos.items.map((eq) => (
                <tr key={eq.idEquipo} className="fila-enlace" onClick={() => navegar(`/equipos/${eq.idEquipo}`)}>
                  <td><EtiquetaEstado estado={eq.estado} /></td>
                  <td><strong>{eq.nombre}</strong></td>
                  <td>{eq.ultimoUsuario ?? '—'}</td>
                  <td>{eq.direccionIp ?? '—'}</td>
                  <td title={eq.fechaUltimoReporte ?? ''}>{haceCuanto(eq.fechaUltimoReporte)}</td>
                  <td><Link to={`/equipos/${eq.idEquipo}`} onClick={(e) => e.stopPropagation()}>Ver detalle ›</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
          <Paginacion pagina={pagina} tamano={TAMANO} total={datos.total} onCambiar={setPagina} />
        </>
      )}
    </>
  )
}
