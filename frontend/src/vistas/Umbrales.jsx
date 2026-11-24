// Umbrales de alerta (RF07, CU06). Exclusivo del Administrador (RNF07).
import { useEffect, useState } from 'react'
import { api } from '../api/cliente'
import { MensajeError, MensajeExito } from '../componentes/comunes.jsx'
import { METRICAS } from '../util/formato'

// Misma regla que el servidor (Umbral.validar): se valida aquí para avisar antes de enviar.
function validar(u, adv, crit) {
  const a = Number(adv), c = Number(crit)
  if (adv === '' || crit === '' || Number.isNaN(a) || Number.isNaN(c)) return 'Ingrese ambos valores.'
  if (a < u.minimo || a > u.maximo || c < u.minimo || c > u.maximo) return `Los valores deben estar entre ${u.minimo} y ${u.maximo} ${u.unidad}.`
  if (c <= a) return 'El umbral crítico debe ser mayor que el de advertencia.'
  return null
}

export default function Umbrales() {
  const [umbrales, setUmbrales] = useState([])
  const [edicion, setEdicion] = useState({})
  const [error, setError] = useState(null)
  const [exito, setExito] = useState(null)

  useEffect(() => {
    api('/umbrales').then((us) => {
      setUmbrales(us)
      setEdicion(Object.fromEntries(us.map((u) => [u.metrica, { adv: String(u.advertencia), crit: String(u.critico) }])))
    }).catch(setError)
  }, [])

  async function guardar(u) {
    const { adv, crit } = edicion[u.metrica]
    setError(null); setExito(null)
    try {
      const nuevo = await api(`/umbrales/${u.metrica}`, { metodo: 'PUT', cuerpo: { advertencia: Number(adv), critico: Number(crit) } })
      setUmbrales(umbrales.map((x) => (x.metrica === u.metrica ? nuevo : x)))
      setExito(`Umbral de ${METRICAS[u.metrica].texto} actualizado. Se aplica desde la próxima lectura de cada equipo.`)
    } catch (err) { setError(err) }
  }

  return (
    <>
      <h1>Umbrales de alerta</h1>
      <p className="sub">Se aplican a todos los equipos. Una métrica que <b>supera</b> el umbral de advertencia deja el equipo en Advertencia; si supera el crítico, en Crítico y se abre una alerta.</p>
      <MensajeError error={error} />
      <MensajeExito texto={exito} />
      <table className="tabla">
        <thead><tr><th>Métrica</th><th>Advertencia</th><th>Crítico</th><th>Rango permitido</th><th></th></tr></thead>
        <tbody>
          {umbrales.map((u) => {
            const e = edicion[u.metrica] ?? { adv: '', crit: '' }
            const problema = validar(u, e.adv, e.crit)
            const cambiado = Number(e.adv) !== u.advertencia || Number(e.crit) !== u.critico
            const fijar = (campo) => (ev) => setEdicion({ ...edicion, [u.metrica]: { ...e, [campo]: ev.target.value } })
            return (
              <tr key={u.metrica}>
                <td><strong>{METRICAS[u.metrica].texto}</strong></td>
                <td><input className="numero-chico" type="number" step="any" value={e.adv} onChange={fijar('adv')} aria-label={`Advertencia ${u.metrica}`} /> {u.unidad}</td>
                <td><input className="numero-chico" type="number" step="any" value={e.crit} onChange={fijar('crit')} aria-label={`Crítico ${u.metrica}`} /> {u.unidad}</td>
                <td>{u.minimo} – {u.maximo} {u.unidad}{problema && <div className="pie error-texto">{problema}</div>}</td>
                <td><button className="boton chico primario" disabled={!cambiado || Boolean(problema)} onClick={() => guardar(u)}>Guardar</button></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </>
  )
}
