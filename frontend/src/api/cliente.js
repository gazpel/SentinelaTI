// Cliente de IPanelAPI (/api/panel). Adjunta el JWT y convierte los errores HTTP en ErrorApi.
const CLAVE_SESION = 'sentinela.sesion'

export class ErrorApi extends Error {
  constructor(estado, mensaje) {
    super(mensaje)
    this.estado = estado
  }
}

export function sesionGuardada() {
  try {
    const sesion = JSON.parse(sessionStorage.getItem(CLAVE_SESION))
    if (sesion && new Date(sesion.expira) > new Date()) return sesion
  } catch { /* almacenamiento no disponible */ }
  return null
}

export function guardarSesion(sesion) {
  try {
    if (sesion) sessionStorage.setItem(CLAVE_SESION, JSON.stringify(sesion))
    else sessionStorage.removeItem(CLAVE_SESION)
  } catch { /* almacenamiento no disponible */ }
}

// RF17: cualquier 401 cierra la sesión local y la app vuelve al inicio de sesión.
let alExpirar = () => {}
export function alExpirarSesion(fn) { alExpirar = fn }

function mensajeDeError(cuerpo, estado) {
  if (!cuerpo) return `Error ${estado}`
  if (typeof cuerpo.detail === 'string') return cuerpo.detail
  if (Array.isArray(cuerpo.detail)) {
    // Errores de validación de FastAPI: se muestra el primero en lenguaje simple.
    const e = cuerpo.detail[0]
    return `Dato inválido en «${e.loc?.at(-1)}»: ${e.msg}`
  }
  return `Error ${estado}`
}

export async function api(ruta, { metodo = 'GET', cuerpo, parametros } = {}) {
  const url = new URL(`/api/panel${ruta}`, window.location.origin)
  Object.entries(parametros ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
  })
  const cabeceras = { 'Content-Type': 'application/json' }
  const sesion = sesionGuardada()
  if (sesion) cabeceras.Authorization = `Bearer ${sesion.token}`

  let respuesta
  try {
    respuesta = await fetch(url, { method: metodo, headers: cabeceras, body: cuerpo ? JSON.stringify(cuerpo) : undefined })
  } catch {
    throw new ErrorApi(0, 'No hay conexión con el servidor de SentinelaTI.')
  }
  if (respuesta.status === 204) return null
  const datos = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    if (respuesta.status === 401 && ruta !== '/sesion') alExpirar()
    throw new ErrorApi(respuesta.status, mensajeDeError(datos, respuesta.status))
  }
  return datos
}
