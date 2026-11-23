// Usuarios del panel (RF13, CU10). Exclusivo del Administrador (RNF07).
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/cliente'
import { MensajeError, MensajeExito, Modal } from '../componentes/comunes.jsx'
import { useSesion } from '../sesion.jsx'

const NUEVO = { nombre: '', correo: '', rol: 'Tecnico', clave: '' }

export default function Usuarios() {
  const { usuario: yo } = useSesion()
  const [usuarios, setUsuarios] = useState([])
  const [nuevo, setNuevo] = useState(NUEVO)
  const [editando, setEditando] = useState(null)
  const [porDesactivar, setPorDesactivar] = useState(null)
  const [error, setError] = useState(null)
  const [exito, setExito] = useState(null)

  const cargar = useCallback(() => api('/usuarios').then(setUsuarios).catch(setError), [])
  useEffect(() => { cargar() }, [cargar])

  const ejecutar = async (accion, mensaje) => {
    setError(null); setExito(null)
    try { await accion(); setExito(mensaje); cargar(); return true } catch (err) { setError(err); return false }
  }

  async function crear(e) {
    e.preventDefault()
    const ok = await ejecutar(() => api('/usuarios', { metodo: 'POST', cuerpo: nuevo }),
      `Usuario ${nuevo.correo} creado. Entréguele su contraseña temporal por un canal seguro.`)
    if (ok) setNuevo(NUEVO)
  }

  return (
    <>
      <h1>Usuarios del panel</h1>
      <p className="sub">Cree cuentas para técnicos y administradores de TI. Un usuario desactivado no puede iniciar sesión y pierde su sesión abierta.</p>
      <MensajeError error={error} />
      <MensajeExito texto={exito} />

      <form className="caja formulario" onSubmit={crear}>
        <h3>Nuevo usuario</h3>
        <label>Nombre<input value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} required minLength={2} maxLength={120} /></label>
        <label>Correo<input type="email" value={nuevo.correo} onChange={(e) => setNuevo({ ...nuevo, correo: e.target.value })} required /></label>
        <label>Rol
          <select value={nuevo.rol} onChange={(e) => setNuevo({ ...nuevo, rol: e.target.value })}>
            <option value="Tecnico">Técnico</option><option value="Administrador">Administrador</option>
          </select>
        </label>
        <label>Contraseña temporal<input type="password" autoComplete="new-password" value={nuevo.clave} onChange={(e) => setNuevo({ ...nuevo, clave: e.target.value })} required minLength={8} /></label>
        <button className="boton primario">Crear usuario</button>
      </form>

      <table className="tabla">
        <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          {usuarios.map((u) => (
            <tr key={u.idUsuario} className={u.activo ? '' : 'inactivo'}>
              <td>{editando?.idUsuario === u.idUsuario
                ? <input value={editando.nombre} onChange={(e) => setEditando({ ...editando, nombre: e.target.value })} aria-label="Nombre" />
                : u.nombre}</td>
              <td>{u.correo}</td>
              <td>{editando?.idUsuario === u.idUsuario && u.idUsuario !== yo.idUsuario
                ? <select value={editando.rol} onChange={(e) => setEditando({ ...editando, rol: e.target.value })} aria-label="Rol">
                    <option value="Tecnico">Técnico</option><option value="Administrador">Administrador</option>
                  </select>
                : (u.rol === 'Administrador' ? 'Administrador' : 'Técnico')}</td>
              <td>{u.activo ? 'Activo' : 'Desactivado'}</td>
              <td className="celda-botones">
                {editando?.idUsuario === u.idUsuario ? (
                  <>
                    <button className="boton chico primario" onClick={async () => {
                      if (await ejecutar(() => api(`/usuarios/${u.idUsuario}`, { metodo: 'PUT', cuerpo: { nombre: editando.nombre, rol: editando.rol } }), 'Cambios guardados.')) setEditando(null)
                    }}>Guardar</button>
                    <button className="boton chico" onClick={() => setEditando(null)}>Cancelar</button>
                  </>
                ) : (
                  <>
                    {u.activo && <button className="boton chico" onClick={() => setEditando({ idUsuario: u.idUsuario, nombre: u.nombre, rol: u.rol })}>Editar</button>}
                    {u.activo && u.idUsuario !== yo.idUsuario && <button className="boton chico peligro" onClick={() => setPorDesactivar(u)}>Desactivar</button>}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {porDesactivar && (
        <Modal titulo={`Desactivar a ${porDesactivar.nombre}`} onCerrar={() => setPorDesactivar(null)}>
          {(refCancelar) => (
            <>
              <p>{porDesactivar.correo} no podrá volver a iniciar sesión y su sesión abierta se cerrará. Sus registros en la bitácora se conservan.</p>
              <div className="fila-botones">
                <button className="boton primario" ref={refCancelar} onClick={() => setPorDesactivar(null)}>Cancelar</button>
                <button className="boton peligro" onClick={async () => {
                  await ejecutar(() => api(`/usuarios/${porDesactivar.idUsuario}/desactivar`, { metodo: 'POST' }), `${porDesactivar.nombre} fue desactivado.`)
                  setPorDesactivar(null)
                }}>Desactivar usuario</button>
              </div>
            </>
          )}
        </Modal>
      )}
    </>
  )
}
