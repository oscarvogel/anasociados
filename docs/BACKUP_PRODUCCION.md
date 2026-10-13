# Backup de la base de produccion

La base `an` se respalda todos los dias a las **4:30**, por cron, con
rotacion de 14 dias.

## Como esta montado

```
/etc/cron.d/backup-an          la entrada de cron (no tiene credenciales)
/var/log/backup_an.log         salida de cada corrida
/var/backups/an/               los backups (directorio 700, archivos 600)
```

La entrada de cron:

```
30 4 * * * root cd /var/www/an && /var/www/venv_an/bin/python manage.py backup_base --conservar 14 >> /var/log/backup_an.log 2>&1
```

## El comando

`usuarios/management/commands/backup_base.py`

Tres decisiones que importan:

- **Las credenciales no estan escritas ni en el cron ni en el comando.** Se
  leen de `settings.DATABASES`, que las saca del `.env`. Si cambias la
  password en el `.env`, el backup la toma nueva sin tocar nada mas. Si
  estuvieran escritas en el cron, quedarian dos lugares que actualizar y uno
  se terminaria olvidando.

- **`mysqldump` corre con `--defaults-extra-file`** a un temporal con permiso
  600. Pasar la password en la linea de comandos la haria visible en `ps` para
  cualquier usuario del servidor. El temporal se borra siempre, incluso si el
  dump falla.

- **Un dump vacio o sin tablas se descarta y el comando falla.** Un backup que
  aparenta existir pero no se restaura es peor que no tener backup: te da
  tranquility falsa justo cuando la necesitas.

Opciones:

| Opcion | Default | Para que |
|---|---|---|
| `--destino` | `/var/backups/an` | donde se dejan los archivos |
| `--conservar` | `14` | dias que se mantienen |
| `--etiqueta` | *(vacio)* | texto para identificar el archivo |
| `--mysql-dump` | `mysqldump` | si el binario no esta en el PATH |

## Correrlo a mano

```bash
cd /var/www/an
/var/www/venv_an/bin/python manage.py backup_base
```

Y con una etiqueta para no confundirlo con los automaticos:

```bash
/var/www/venv_an/bin/python manage.py backup_base --etiqueta antes-upgrade
```

## Verificar que un backup sirve

Esto es lo que hay que hacer de vez en cuando. Un backup sin probar es una
suposicion.

```bash
# 1. Ver que el archivo no esta vacio ni corrupto
ls -lh /var/backups/an/
gunzip -t /var/backups/an/an-AAAAMMDD-HHMMSS.sql.gz && echo "gzip sano"
gunzip -c /var/backups/an/an-AAAAMMDD-HHMMSS.sql.gz | grep -c 'CREATE TABLE'
# debe dar 44

# 2. Restaurarlo en una base descartable y comparar
mysql -h vps-3177145-x.dattaweb.com -u root -p -e "CREATE DATABASE prueba_restore;"
gunzip -c /var/backups/an/an-AAAAMMDD-HHMMSS.sql.gz \
  | mysql -h vps-3177145-x.dattaweb.com -u root -p prueba_restore

mysql -h vps-3177145-x.dattaweb.com -u root -p -e "
  SELECT 'movimientos' t, (SELECT COUNT(*) FROM an.movimientos) real,
                        (SELECT COUNT(*) FROM prueba_restore.movimientos) copia
  UNION SELECT 'clientes',    (SELECT COUNT(*) FROM an.clientes),
                             (SELECT COUNT(*) FROM prueba_restore.clientes)
  UNION SELECT 'auth_user',   (SELECT COUNT(*) FROM an.auth_user),
                             (SELECT COUNT(*) FROM prueba_restore.auth_user);"

# 3. SIEMPRE limpiar despues
mysql -h vps-3177145-x.dattaweb.com -u root -p -e "DROP DATABASE prueba_restore;"
```

La comparacion tiene que dar los mismos numeros en las dos columnas. Si el
backup es viejo, la copia va a tener menos filas: eso es normal, no un error.
Lo que no puede pasar es que falte una tabla o de error al restaurar.

Este procedimiento ya se ejecuto una vez contra el backup del 13/10/2026: 44
tablas restauradas y conteos identicos (1.310 movimientos, 16 clientes, 19
usuarios).

## Restaurar de verdad

Solo si la base se corrompe o se perdio. Antes de nada, **sacale una copia del
estado actual**, por roto que este:

```bash
cd /var/www/an
/var/www/venv_an/bin/python manage.py backup_base --etiqueta antes-de-restaurar
```

Despues:

```bash
F=/var/backups/an/an-AAAAMMDD-HHMMSS.sql.gz   # el backup bueno
mkdir -p /root/recuperacion
gunzip -c "$F" > /root/recuperacion/an.sql

# sobre la base REAL (esto borra lo que haya ahora)
mysql -h vps-3177145-x.dattaweb.com -u root -p an < /root/recuperacion/an.sql
```

El dump no incluye `CREATE DATABASE` ni `DROP DATABASE`, asi que se restaura
sobre la base que ya existe. Para empezar de cero:

```bash
mysql -h vps-3177145-x.dattaweb.com -u root -p -e "DROP DATABASE an; CREATE DATABASE an;"
mysql -h vps-3177145-x.dattaweb.com -u root -p an < /root/recuperacion/an.sql
```

**Ojo:** hay tablas `managed = False` (`movimientos`, `clientes`, `areas`,
`perfiles`) que Django no migra. Si restaurás sobre una base vacia de verdad,
las tiene que volver a crear el proceso externo que las genera: no hay script
en el repo. Para eso estan en el dump.

Despues de restaurar:

```bash
systemctl restart an.service
supervisorctl restart celery_an
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8086/
```

## Cuando falla

Mirar el log:

```bash
tail -20 /var/log/backup_an.log
```

Cosas tipicas:

| Sintoma | Causa |
|---|---|
| `No se encontro 'mysqldump'` | el paquete de MySQL no esta o no esta en el PATH del cron |
| `mysqldump fallo (exit N)` | credenciales, red, o la base no responde |
| `El dump salio vacio o sin tablas` | la base esta vacia o la consulta fallo |
| el log no crece | cron no esta corriendo: `systemctl status cron` |

**No hay alertas automáticas.** Si el backup falla un dia, nadie te avisa hasta
que lo necesites. Conviene mirar el log de vez en cuando, o agregar algo como
un chequeo que mande mail si el archivo del dia no existe.