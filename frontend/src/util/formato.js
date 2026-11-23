// Textos y formatos compartidos por todas las vistas (principio de uniformidad, L4 §4.2).

export const ESTADOS = {
  Critico: { texto: 'Crítico', icono: '▲', clase: 'crit' },
  Advertencia: { texto: 'Advertencia', icono: '◆', clase: 'adv' },
  Desconectado: { texto: 'Desconectado', icono: '✕', clase: 'desc' },
  Normal: { texto: 'Normal', icono: '●', clase: 'ok' },
}
export const ORDEN_ESTADOS = ['Critico', 'Advertencia', 'Desconectado', 'Normal']

export const METRICAS = {
  CPU: { texto: 'CPU', unidad: '%', campo: 'usoCpu' },
  RAM: { texto: 'RAM', unidad: '%', campo: 'usoRam' },
  Disco: { texto: 'Disco (unidad más llena)', unidad: '%', campo: 'usoDiscoMax' },
  Temperatura: { texto: 'Temperatura CPU', unidad: '°C', campo: 'temperaturaCpu' },
  HorasEncendido: { texto: 'Horas encendido', unidad: 'h', campo: 'horasEncendido' },
}

export const ESTADOS_COMANDO = {
  Pendiente: 'Pendiente', Entregado: 'Entregado', Ejecutado: 'Ejecutado', Fallido: 'Fallido',
  Cancelado: 'Cancelado', Expirado: 'Expirado', Denegado: 'Denegado',
}

export const TIPOS_ACCION = {
  ReiniciarApagar: 'Reinicio / apagado', Formatear: 'Formateo', InstalarApp: 'Instalación de aplicación',
  ActualizarSO: 'Actualización del SO', EscritorioRemoto: 'Escritorio remoto',
}

export function valorMetrica(valor, unidad) {
  if (valor === null || valor === undefined) return 'No disponible'
  return `${Number(valor).toLocaleString('es-CL', { maximumFractionDigits: 1 })} ${unidad}`
}

export function fechaHora(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CL', { dateStyle: 'short', timeStyle: 'short' })
}

export function haceCuanto(iso) {
  if (!iso) return 'Nunca'
  const segundos = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (segundos < 60) return 'hace menos de 1 min'
  const minutos = Math.floor(segundos / 60)
  if (minutos < 60) return `hace ${minutos} min`
  const horas = Math.floor(minutos / 60)
  if (horas < 48) return `hace ${horas} h`
  return `hace ${Math.floor(horas / 24)} días`
}
