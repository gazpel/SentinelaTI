"""ServicioConfiguracion (L4, cambio C3) — RF07, CU06."""
from app.aplicacion.errores import DatosInvalidos
from app.aplicacion.servicio_autenticacion import ServicioAutenticacion
from app.dominio.base import ErrorDominio
from app.dominio.enumeraciones import Metrica, Permiso
from app.dominio.monitoreo import ConfiguracionUmbrales, Umbral
from app.dominio.repositorios import ConfiguracionRepository
from app.dominio.usuarios import Sesion


class ServicioConfiguracion:
    def __init__(self, configuracion: ConfiguracionRepository, autenticacion: ServicioAutenticacion):
        self.configuracion = configuracion
        self.autenticacion = autenticacion

    def definir_umbral(self, s: Sesion, m: Metrica, advertencia: float, critico: float) -> Umbral:
        """Valida antes de modificar: un umbral rechazado no altera la configuración vigente."""
        self.autenticacion.autorizar(s, Permiso.CONFIGURAR_UMBRALES)
        candidato = Umbral(metrica=m, valor_advertencia=advertencia, valor_critico=critico)
        try:
            candidato.validar()
        except ErrorDominio as error:
            raise DatosInvalidos(str(error)) from error
        umbral = self.configuracion.obtener().umbral_de(m)
        umbral.valor_advertencia, umbral.valor_critico = advertencia, critico
        self.configuracion.guardar(umbral)
        return umbral

    def obtener_configuracion(self) -> ConfiguracionUmbrales:
        return self.configuracion.obtener()
