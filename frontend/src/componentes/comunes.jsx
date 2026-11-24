// Componentes pequeños reutilizados en todas las vistas.
import { useEffect, useRef } from 'react'
import { ESTADOS, ESTADOS_COMANDO } from '../util/formato'

// Estado con texto y forma, no solo color (anotación 2 de W1; diversidad de usuarios).
export function EtiquetaEstado({ estado }) {
  const e = ESTADOS[estado] ?? { texto: estado, icono: '?', clase: 'desc' }
  return <span className={`estado ${e.clase}`}><span aria-hidden="true">{e.icono}</span> {e.texto}</span>
}

export function EtiquetaComando({ estado }) {
  const clase = { Ejecutado: 'ok', Fallido: 'crit', Denegado: 'crit', Expirado: 'desc', Cancelado: 'desc' }[estado] ?? 'adv'
  return <span className={`estado chico ${clase}`}>{ESTADOS_COMANDO[estado] ?? estado}</span>
}

export function MensajeError({ error }) {
  if (!error) return null
  return <div className="mensaje error" role="alert">{error.message ?? String(error)}</div>
}

export function MensajeExito({ texto }) {
  if (!texto) return null
  return <div className="mensaje exito" role="status">{texto}</div>
}

// Diálogo modal. «Cancelar» recibe el foco por defecto (recuperabilidad, anotación 1 de W2).
export function Modal({ titulo, children, onCerrar }) {
  const refCancelar = useRef(null)
  useEffect(() => {
    refCancelar.current?.focus()
    const alPresionar = (e) => e.key === 'Escape' && onCerrar()
    window.addEventListener('keydown', alPresionar)
    return () => window.removeEventListener('keydown', alPresionar)
  }, [onCerrar])
  return (
    <div className="fondo-modal" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="titulo-modal">
        <h2 id="titulo-modal">{titulo}</h2>
        {children(refCancelar)}
      </div>
    </div>
  )
}

export function Paginacion({ pagina, tamano, total, onCambiar }) {
  const paginas = Math.max(1, Math.ceil(total / tamano))
  const desde = total === 0 ? 0 : (pagina - 1) * tamano + 1
  const hasta = Math.min(total, pagina * tamano)
  return (
    <div className="paginacion">
      <span>Mostrando {desde}–{hasta} de {total}</span>
      <button className="boton" disabled={pagina <= 1} onClick={() => onCambiar(pagina - 1)}>‹ Anterior</button>
      <span>Página {pagina} de {paginas}</span>
      <button className="boton" disabled={pagina >= paginas} onClick={() => onCambiar(pagina + 1)}>Siguiente ›</button>
    </div>
  )
}
