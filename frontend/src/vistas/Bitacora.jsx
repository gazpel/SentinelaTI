// Bitácora de auditoría (RF14, RF18). Solo consulta y filtros: no hay edición ni borrado (RNF12).
import { useEffect, useState } from 'react'
import { api } from '../api/cliente'
import { EtiquetaComando, MensajeError } from '../componentes/comunes.jsx'
import { TIPOS_ACCION, fechaHora } from '../util/formato'

const FILTROS_VACIOS = { equipo: '', usuario: '', tipo: '', desde: '', hasta: '' }

// Las fechas del formulario son locales; la API recibe instantes en ISO 8601.
const inicioDelDia = (d) => (d ? new Date(`${d}T00:00:00`).toISOString() : '')
const finDelDia = (d) => (d ? new Date(`${d}T23:59:59.999`).toISOString() : '')

export default function Bitacora() {
  const [filtros, setFiltros] = useState(FILTROS_VACIOS)
  const [entradas, setEntradas] = useState(null)
  const [equipos, setEquipos] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api('/equipos', { parametros: { tamano: 100 } }).then((r) => setEquipos(r.items)).catch(() => {})
    api('/bitacora/usuarios').then(setUsuarios).catch(() => {})
  }, [])

  useEffect(() => {
    if (filtros.desde && filtros.hasta && filtros.desde > filtros.hasta) {
      setError(new Error('La fecha «desde» no puede ser posterior a «hasta».'))
      return
    }
    api('/bitacora', { parametros: { ...filtros, desde: inicioDelDia(filtros.desde), hasta: finDelDia(filtros.hasta) } })
      .then((r) => { setEntradas(r); setError(null) })
      .catch(setError)
  }, [filtros])

  const cambiar = (campo) => (e) => setFiltros({ ...filtros, [campo]: e.target.value })

  return (
    <>
      <h1>Bitácora de auditoría</h1>
      <p className="sub">Una entrada por cada acción remota, con quién la ordenó y su resultado. Las entradas no se pueden editar ni eliminar.</p>
      <div className="filtros envolver">
        <select value={filtros.equipo} onChange={cambiar('equipo')} aria-label="Equipo">
          <option value="">Equipo: Todos</option>
          {equipos.map((e) => <option key={e.idEquipo} value={e.idEquipo}>{e.nombre}</option>)}
        </select>
        <select value={filtros.usuario} onChange={cambiar('usuario')} aria-label="Usuario">
          <option value="">Usuario: Todos</option>
          {usuarios.map((u) => <option key={u.idUsuario} value={u.idUsuario}>{u.nombre}</option>)}
        </select>
        <select value={filtros.tipo} onChange={cambiar('tipo')} aria-label="Tipo de acción">
          <option value="">Acción: Todas</option>
          {Object.entries(TIPOS_ACCION).map(([v, t]) => <option key={v} value={v}>{t}</option>)}
        </select>
        <label className="en-linea">Desde <input type="date" value={filtros.desde} onChange={cambiar('desde')} /></label>
        <label className="en-linea">Hasta <input type="date" value={filtros.hasta} onChange={cambiar('hasta')} /></label>
        <button className="boton" onClick={() => setFiltros(FILTROS_VACIOS)}>Limpiar filtros</button>
      </div>
      <MensajeError error={error} />
      {entradas && entradas.length === 0 && <div className="vacio">No hay entradas que coincidan con los filtros.</div>}
      {entradas && entradas.length > 0 && (
        <table className="tabla">
          <thead><tr><th>Fecha de la orden</th><th>Equipo</th><th>Acción</th><th>Usuario</th><th>Resultado</th><th>Fecha del resultado</th></tr></thead>
          <tbody>
            {entradas.map((en) => (
              <tr key={en.idEntrada}>
                <td>{fechaHora(en.fechaOrden)}</td>
                <td>{en.nombreEquipo}</td>
                <td>{en.descripcion}</td>
                <td>{en.nombreUsuario}</td>
                <td>{en.cerrada ? <EtiquetaComando estado={en.estadoResultante} /> : <span className="estado chico adv">En curso</span>}</td>
                <td>{fechaHora(en.fechaResultado)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}
