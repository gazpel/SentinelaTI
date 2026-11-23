// Alertas abiertas (RF16). Seleccionar una alerta abre el detalle del equipo (CU04, flujo 3a).
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/cliente'
import { EtiquetaEstado, MensajeError, Paginacion } from '../componentes/comunes.jsx'
import { METRICAS, fechaHora, haceCuanto, valorMetrica } from '../util/formato'

const TAMANO = 50

export default function Alertas() {
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const cargar = () => api('/alertas', { parametros: { pagina, tamano: TAMANO } }).then(setDatos).catch(setError)
    cargar()
    const t = setInterval(cargar, 30000)
    return () => clearInterval(t)
  }, [pagina])

  return (
    <>
      <h1>Alertas abiertas</h1>
      <p className="sub">Se abre una alerta cuando una lectura supera el umbral crítico o un equipo deja de reportar. Se cierra sola cuando la métrica vuelve bajo el umbral o el equipo reporta de nuevo.</p>
      <MensajeError error={error} />
      {datos && datos.items.length === 0 && <div className="vacio">No hay alertas abiertas. ✓</div>}
      {datos && datos.items.length > 0 && (
        <>
          <table className="tabla">
            <thead><tr><th>Nivel</th><th>Equipo</th><th>Motivo</th><th>Valor</th><th>Abierta</th><th></th></tr></thead>
            <tbody>
              {datos.items.map((a) => (
                <tr key={a.idAlerta}>
                  <td><EtiquetaEstado estado={a.metrica ? a.nivel : 'Desconectado'} /></td>
                  <td><strong>{a.nombreEquipo}</strong></td>
                  <td>{a.metrica ? `${METRICAS[a.metrica].texto} sobre el umbral crítico` : 'El equipo dejó de reportar'}</td>
                  <td>{a.metrica ? valorMetrica(a.valor, METRICAS[a.metrica].unidad) : '—'}</td>
                  <td title={fechaHora(a.fechaApertura)}>{haceCuanto(a.fechaApertura)}</td>
                  <td><Link to={`/equipos/${a.idEquipo}`}>Ver equipo ›</Link></td>
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
