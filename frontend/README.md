# SentinelaTI — Panel web

Aplicación React (Vite) para técnicos y administradores de TI. Implementa los wireframes W1 y W2 del L4 y las
vistas de alertas, acciones, bitácora, umbrales y usuarios.

| Carpeta | Contenido |
|---|---|
| `src/vistas` | Una vista por pantalla (`Parque.jsx` = W1, `DetalleEquipo.jsx` = W2, …) |
| `src/componentes` | Marco (barra y menú según el rol) y componentes comunes (etiquetas de estado, modal, paginación) |
| `src/api/cliente.js` | Llamadas a `/api/panel` con el JWT; un 401 cierra la sesión (RF17) |
| `src/sesion.jsx` | Sesión y permisos del usuario |
| `src/util/formato.js` | Textos de estados y métricas, formatos de fecha |

## Ejecutar

Con la API corriendo en el puerto 8000 (ver `backend/README.md`):

```powershell
npm install
npm run dev
```

Abrir <http://localhost:5173>. Vite redirige `/api` a la API (otra dirección: variable `SENTINELA_API`).

Otros comandos: `npm run build` (versión de producción en `dist/`) y `npm run lint`.
