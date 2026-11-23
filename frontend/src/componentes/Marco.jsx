// Encabezado y menú comunes a todas las vistas (W1/W2). El menú depende del rol (anotación 3 de W1).
import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { api } from '../api/cliente'
import { useSesion } from '../sesion.jsx'

export default function Marco({ children }) {
  const { usuario, puede, cerrar } = useSesion()
  const [alertasAbiertas, setAlertasAbiertas] = useState(null)

  useEffect(() => {
    let vigente = true
    const cargar = () => api('/alertas', { parametros: { tamano: 1 } })
      .then((r) => vigente && setAlertasAbiertas(r.total)).catch(() => {})
    cargar()
    const temporizador = setInterval(cargar, 30000)
    return () => { vigente = false; clearInterval(temporizador) }
  }, [])

  const enlace = ({ isActive }) => (isActive ? 'activo' : undefined)

  return (
    <div className="marco">
      <header className="barra">
        <span className="logo"><img src="/escudo.svg" alt="" /> SentinelaTI</span>
        <span className="usuario">
          {usuario.nombre} <span className="rol">{usuario.rol === 'Administrador' ? 'Administrador' : 'Técnico'}</span>
          <button className="enlace-claro" onClick={() => cerrar()}>Cerrar sesión</button>
        </span>
      </header>
      <div className="cuerpo">
        <nav className="menu" aria-label="Secciones">
          <NavLink to="/" end className={enlace}>▣ Parque</NavLink>
          <NavLink to="/alertas" className={enlace}>
            ⚠ Alertas {alertasAbiertas > 0 && <span className="insignia" aria-label={`${alertasAbiertas} abiertas`}>{alertasAbiertas}</span>}
          </NavLink>
          <NavLink to="/acciones" className={enlace}>⟳ Acciones</NavLink>
          {puede('ConsultarBitacora') && <NavLink to="/bitacora" className={enlace}>☰ Bitácora</NavLink>}
          {(puede('ConfigurarUmbrales') || puede('GestionarUsuarios')) && <hr />}
          {puede('ConfigurarUmbrales') && <NavLink to="/umbrales" className={enlace}>⚙ Umbrales</NavLink>}
          {puede('GestionarUsuarios') && <NavLink to="/usuarios" className={enlace}>👤 Usuarios</NavLink>}
        </nav>
        <main className="principal">{children}</main>
      </div>
    </div>
  )
}
