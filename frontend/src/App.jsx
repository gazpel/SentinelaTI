import { Navigate, Route, Routes } from 'react-router-dom'
import Marco from './componentes/Marco.jsx'
import { useSesion } from './sesion.jsx'
import Acciones from './vistas/Acciones.jsx'
import Alertas from './vistas/Alertas.jsx'
import Bitacora from './vistas/Bitacora.jsx'
import DetalleEquipo from './vistas/DetalleEquipo.jsx'
import InicioSesion from './vistas/InicioSesion.jsx'
import Parque from './vistas/Parque.jsx'
import Umbrales from './vistas/Umbrales.jsx'
import Usuarios from './vistas/Usuarios.jsx'

// Las vistas exclusivas del Administrador ni siquiera se enrutan para un Técnico (RNF07);
// de todas formas la API responde 403 si alguien llega a ellas.
function SoloCon({ permiso, children }) {
  const { puede } = useSesion()
  return puede(permiso) ? children : <Navigate to="/" replace />
}

export default function App() {
  const { usuario } = useSesion()
  if (!usuario) return <InicioSesion />  // RF17: sin sesión no se accede a ninguna vista

  return (
    <Marco>
      <Routes>
        <Route path="/" element={<Parque />} />
        <Route path="/equipos/:id" element={<DetalleEquipo />} />
        <Route path="/alertas" element={<Alertas />} />
        <Route path="/acciones" element={<Acciones />} />
        <Route path="/bitacora" element={<SoloCon permiso="ConsultarBitacora"><Bitacora /></SoloCon>} />
        <Route path="/umbrales" element={<SoloCon permiso="ConfigurarUmbrales"><Umbrales /></SoloCon>} />
        <Route path="/usuarios" element={<SoloCon permiso="GestionarUsuarios"><Usuarios /></SoloCon>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Marco>
  )
}
