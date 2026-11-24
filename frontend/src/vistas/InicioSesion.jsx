// CU03 — Iniciar sesión (RF17).
import { useState } from 'react'
import { MensajeError } from '../componentes/comunes.jsx'
import { useSesion } from '../sesion.jsx'

export default function InicioSesion() {
  const { iniciar, motivoCierre } = useSesion()
  const [correo, setCorreo] = useState('')
  const [clave, setClave] = useState('')
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await iniciar(correo, clave)
    } catch (err) {
      setError(err)
      setClave('')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="pantalla-ingreso">
      <form className="tarjeta-ingreso" onSubmit={enviar}>
        <div className="logo-ingreso"><img src="/escudo.svg" alt="" /> SentinelaTI</div>
        <p className="sub">Panel de monitoreo y mantención remota del parque computacional.</p>
        {motivoCierre && !error && <div className="mensaje aviso">{motivoCierre}</div>}
        <MensajeError error={error} />
        <label>Correo
          <input type="email" autoComplete="username" value={correo} onChange={(e) => setCorreo(e.target.value)} required autoFocus />
        </label>
        <label>Contraseña
          <input type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} required />
        </label>
        <button className="boton primario ancho" disabled={enviando}>{enviando ? 'Ingresando…' : 'Ingresar'}</button>
        <p className="pie">Tras 5 intentos fallidos la cuenta se bloquea por 15 minutos.</p>
      </form>
    </div>
  )
}
