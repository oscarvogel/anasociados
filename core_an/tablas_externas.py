"""DDL de las tablas que Django no migra.

`Cliente`, `Area`, `Movimientos` y `Perfil` son `managed = False`: en
produccion las crea un proceso externo, no Django. Por eso una base de tests
armada desde cero se rompe: la migracion `syh.0004_evidencia` agrega una FK a
`movimientos` y no la encuentra (ver docs/ENTORNO_DE_DESARROLLO.md).

Este modulo tiene el DDL para crearlas antes de migrar. Copiado de produccion
con `SHOW CREATE TABLE`, no inventado, para que los tests corran contra la
misma forma de tabla que usa el sistema real.

Solo lo usa el comando `migrate` y unicamente cuando corre bajo `test`: en
produccion estas tablas ya existen y Django tiene que seguir sin tocarlas.
"""

# Antes de migrar. Sin la FK a syh_naturalezahallazgo a proposito: esa tabla la
# crea la migracion y todavia no existe.
DDL_ANTES_DE_MIGRAR = [
    """
    CREATE TABLE IF NOT EXISTS `clientes` (
      `id` varchar(10) NOT NULL,
      `nombre` varchar(80) NOT NULL,
      `celular` varchar(80) DEFAULT NULL,
      `email` varchar(200) NOT NULL,
      `meta_porcentaje` int NOT NULL DEFAULT 0,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1
    """,
    """
    CREATE TABLE IF NOT EXISTS `areas` (
      `id` varchar(10) NOT NULL,
      `cliente` varchar(10) NOT NULL,
      `detalle` varchar(80) NOT NULL,
      `responsable` varchar(80) NOT NULL DEFAULT '',
      `activo` tinyint NOT NULL DEFAULT 1,
      `email` varchar(200) DEFAULT NULL,
      PRIMARY KEY (`id`),
      KEY `FK_areas_clientes` (`cliente`),
      CONSTRAINT `FK_areas_clientes` FOREIGN KEY (`cliente`)
        REFERENCES `clientes` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1
    """,
    """
    CREATE TABLE IF NOT EXISTS `movimientos` (
      `id` varchar(20) NOT NULL,
      `cliente` varchar(10) NOT NULL,
      `fecha` date NOT NULL,
      `periodo` varchar(20) NOT NULL DEFAULT '',
      `hallazgo` text NOT NULL,
      `responsable` varchar(80) NOT NULL DEFAULT '',
      `area` varchar(100) NOT NULL DEFAULT '',
      `plazo` int NOT NULL DEFAULT 0,
      `estado` varchar(20) NOT NULL DEFAULT '0',
      `fecha_cumplimiento` date NOT NULL,
      `ubicacion` varchar(200) DEFAULT '0',
      `fecha_realizado` date DEFAULT NULL,
      `naturaleza_hallazgo_id` int NOT NULL DEFAULT 1,
      `observaciones` text,
      PRIMARY KEY (`id`),
      CONSTRAINT `fk_movimiento_cliente` FOREIGN KEY (`cliente`)
        REFERENCES `clientes` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
      CONSTRAINT `fk_movimiento_area` FOREIGN KEY (`area`)
        REFERENCES `areas` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1
    """,
]

# Despues de migrar: su FK apunta a `auth_user`, que todavia no existe mientras
# corren las migraciones.
DDL_DESPUES_DE_MIGRAR = [
    """
    CREATE TABLE IF NOT EXISTS `perfiles` (
      `id` int NOT NULL AUTO_INCREMENT,
      `user` int NOT NULL DEFAULT 0,
      `cliente` varchar(10) NOT NULL DEFAULT '0',
      PRIMARY KEY (`id`),
      KEY `FK_profile_user` (`user`),
      KEY `FK_profile_cliente` (`cliente`),
      CONSTRAINT `FK_profile_cliente` FOREIGN KEY (`cliente`)
        REFERENCES `clientes` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
      CONSTRAINT `FK_profile_user` FOREIGN KEY (`user`)
        REFERENCES `auth_user` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1
    """,
]


def ejecutar(sentencias):
    from django.db import connection

    with connection.cursor() as cursor:
        for sentencia in sentencias:
            cursor.execute(sentencia)