// Acciones: seguimiento de las órdenes remotas y cancelación de las pendientes (anotación 3 de W2).
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/cliente'
import { EtiquetaComando, MensajeError, MensajeExito } from '../componentes/comunes.jsx'
import { useSesion } from '../sesion.jsx'
import { ESTADOS_COMANDO, fechaHora } from '../util/formato'

export default function Acciones() {
  const { puede } = useSesion()
  const [estado, setEstado] = useState('')
  const [ordenes, setOrdenes] = useState(null)
  const [error, setError] = useState(null)
  const [exito, setExito] = useState(null)

  const cargar = useCallback(() => api('/comandos', { parametros: { estado } }).then(setOrdenes).catch(setError), [estado])
  useEffect(() => {
    cargar()
    const t = setInterval(cargar, 15000)
    return () => clearInterval(t)
  }, [cargar])

  async function cancelar(o) {
    setError(null)
    try {
      await api(`/comandos/${o.idComando}/cancelar`, { metodo: 'POST' })
      setExito(`Se canceló la orden de ${o.descripcion.toLowerCase()} para ${o.nombreEquipo}.`)
      cargar()
    } catch (err) { setError(err) }
  }

  return (
    <>
      <h1>Acciones remotas</h1>
      <p className="sub">Órdenes enviadas a los equipos. Una orden se puede cancelar mientras siga Pendiente. Para ordenar una acción, abra el detalle del equipo desde el Parque.</p>
      <MensajeError error={error} />
      <MensajeExito texto={exito} />
      <div className="filtros">
        <select value={estado} onChange={(e) => setEstado(e.target.value)} aria-label="Estado de la orden">
          <option value="">Estado: Todos</option>
          {Object.keys(ESTADOS_COMANDO).filter((e) => e !== 'Denegado').map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
      </div>
      {ordenes && ordenes.length === 0 && <div className="vacio">No hay órdenes {estado && `en estado ${estado}`}.</div>}
      {ordenes && ordenes.length > 0 && (
        <table className="tabla">
          <thead><tr><th>Equipo</th><th>Acción</th><th>Estado</th><th>Ordenada por</th><th>Orden</th><th>Entrega</th><th>Resultado</th><th></th></tr></thead>
          <tbody>
            {ordenes.map((o) => (
              <tr key={o.idComando}>
                <td><Link to={`/equipos/${o.idEquipo}`}>{o.nombreEquipo}</Link></td>
                <td>{o.descripcion}</td>
                <td><EtiquetaComando estado={o.estado} /></td>
                <td>{o.ordenadoPor}</td>
                <td>{fechaHora(o.fechaOrden)}</td>
                <td>{fechaHora(o.fechaEntrega)}</td>
                <td>{fechaHora(o.fechaResultado)}{o.motivoFallo && <div className="pie">{o.motivoFallo}</div>}</td>
                <td>{o.estado === 'Pendiente' && (o.tipo !== 'Formatear' || puede('Formatear')) &&
                  <button className="boton chico" onClick={() => cancelar(o)}>Cancelar orden</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}
