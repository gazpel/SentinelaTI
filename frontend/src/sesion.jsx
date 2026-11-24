// Sesión del panel (RF17, CU03): guarda el JWT y expone el usuario y sus permisos.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { alExpirarSesion, api, guardarSesion, sesionGuardada } from './api/cliente'

const ContextoSesion = createContext(null)

export function ProveedorSesion({ children }) {
  const [sesion, setSesion] = useState(sesionGuardada)
  const [motivoCierre, setMotivoCierre] = useState(null)

  const cerrar = useCallback((motivo = null) => {
    guardarSesion(null)
    setSesion(null)
    setMotivoCierre(motivo)
  }, [])

  useEffect(() => {
    alExpirarSesion(() => cerrar('Su sesión expiró o fue cerrada. Inicie sesión de nuevo.'))
  }, [cerrar])

  const iniciar = useCallback(async (correo, clave) => {
    const nueva = await api('/sesion', { metodo: 'POST', cuerpo: { correo, clave } })
    guardarSesion(nueva)
    setSesion(nueva)
    setMotivoCierre(null)
  }, [])

  const valor = useMemo(() => ({
    usuario: sesion?.usuario ?? null,
    puede: (permiso) => Boolean(sesion?.usuario?.permisos.includes(permiso)),
    iniciar,
    cerrar,
    motivoCierre,
  }), [sesion, iniciar, cerrar, motivoCierre])

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useSesion = () => useContext(ContextoSesion)
