# Sistema de Gestión de Viajes

## Descripción
Sistema web para gestionar viajes de móviles con visualización de KPIs y operaciones CRUD (Crear, Leer, Actualizar, Eliminar).

## Características

### Backend (Django REST Framework)
- **API REST completa** para viajes, móviles y predios
- **Serializers** con campos calculados y relaciones
- **Filtros** por fecha y móvil
- **Endpoint de KPIs** con agregaciones (suma de toneladas)
- **Paginación** automática de resultados

### Frontend (Vue 3)
- **Interfaz responsive** optimizada para móviles y desktop
- **Vista adaptativa**: Tarjetas en móvil, tabla en desktop
- **KPIs visuales** con gradientes de color
- **Formulario modal** para crear/editar viajes
- **Validaciones** y notificaciones con SweetAlert2
- **Filtros dinámicos** por rango de fechas y móvil

## Estructura de Archivos

```
moviles/
├── models.py               # Modelo Viajes con campos TN (toneladas)
├── serializer.py           # ViajesSerializer con campos relacionados
├── views.py                # ViajesViewSet y vista viajes_kpis
├── urls.py                 # Rutas API y vistas HTML
└── admin.py

templates/pages/moviles/
└── viajes_list.html        # Template Vue con diseño responsive

static/src/moviles/
└── viajes.js               # Lógica Vue 3 (setup composition API)
```

## Endpoints API

### Listar Viajes (con paginación)
```
GET /moviles/api/viajes/
GET /moviles/api/viajes/?start_date=2024-01-01&end_date=2024-12-31
GET /moviles/api/viajes/?movil=5
```

**Respuesta:**
```json
{
  "count": 150,
  "next": "http://...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "fecha": "2024-10-01",
      "movil": 5,
      "movil_patente": "ABC123",
      "origen": 2,
      "origen_nombre": "Predio Norte",
      "destino": "ASPP",
      "destino_display": "ASERRADERO PUERTO PIRAY",
      "producto": "Pulpable",
      "producto_display": "Pulpable",
      "tn_pulpable": "125.50",
      "tn_aserrable": "0.00",
      "tn_chip": "15.20",
      ...
    }
  ]
}
```

### KPIs de Viajes
```
GET /moviles/api/viajes/kpis/
GET /moviles/api/viajes/kpis/?start_date=2024-10-01&end_date=2024-10-31
```

**Respuesta:**
```json
{
  "total_viajes": 45,
  "tn_pulpable": 5420.75,
  "tn_aserrable": 1230.50,
  "tn_chip": 890.25,
  "tn_total": 7541.50
}
```

### Crear Viaje
```
POST /moviles/api/viajes/
Content-Type: application/json
X-CSRFToken: <token>

{
  "fecha": "2024-10-03",
  "movil": 5,
  "origen": 2,
  "destino": "ASPP",
  "producto": "Pulpable",
  "tn_pulpable": 125.50,
  "tn_aserrable": 0,
  "tn_chip": 15.20
}
```

### Actualizar Viaje
```
PUT /moviles/api/viajes/{id}/
Content-Type: application/json
X-CSRFToken: <token>

{...datos actualizados...}
```

### Eliminar Viaje
```
DELETE /moviles/api/viajes/{id}/
X-CSRFToken: <token>
```

### Listar Móviles y Predios
```
GET /moviles/api/movil/
GET /moviles/api/predios/
```

## Instalación y Uso

### 1. Activar entorno virtual
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias (si es necesario)
```powershell
pip install -r requirements.txt
```

### 3. Ejecutar migraciones (si hay cambios en modelos)
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 4. Recolectar archivos estáticos (producción)
```powershell
python manage.py collectstatic --noinput
```

### 5. Ejecutar servidor de desarrollo
```powershell
python manage.py runserver
```

### 6. Acceder a la aplicación
- **Página de Viajes:** http://127.0.0.1:8000/moviles/viajes/
- **API Viajes:** http://127.0.0.1:8000/moviles/api/viajes/
- **KPIs:** http://127.0.0.1:8000/moviles/api/viajes/kpis/

## Depuración

### Ver logs en consola del navegador
1. Abrir DevTools (F12)
2. Ir a la pestaña **Console**
3. Buscar mensajes:
   - "Cargando viajes desde..."
   - "Viajes cargados: X registros"
   - "KPIs recibidos: {...}"

### Ver requests en Network
1. Abrir DevTools (F12)
2. Ir a la pestaña **Network**
3. Filtrar por "viajes"
4. Verificar:
   - Status: 200 OK
   - Response: JSON con datos
   - Request URL correcta

### Problemas comunes

#### Las TN no se muestran
- Verificar en consola que `viajes.value[0].tn_pulpable` tiene valor
- Comprobar que los registros en BD tienen valores en campos TN (no null)
- Ver el Response de `/moviles/api/viajes/` en Network

#### Error 404 en KPIs
- Verificar que la ruta `api/viajes/kpis/` está ANTES de `path('api/', include(router.urls))` en `urls.py`

#### Modal no se muestra
- Verificar que Vue se cargó correctamente (ver consola)
- Comprobar que `static/src/moviles/viajes.js` se sirve sin 404

#### Datos en blanco en tabla
- Verificar que el endpoint devuelve `data.results` (paginación DRF)
- Ver en consola: "Primer viaje (muestra): {...}"

## Modelo de Datos

### Viajes
```python
class Viajes(models.Model):
    movil = ForeignKey(Movil)           # Móvil que realiza el viaje
    cliente = ForeignKey(Cliente)       # Cliente (nullable)
    area = ForeignKey(Area)             # Área (nullable)
    fecha = DateField()                 # Fecha del viaje
    origen = ForeignKey(Predios)        # Predio de origen
    destino = CharField(choices)        # Destino (ASPP, PPE)
    producto = CharField(choices)       # Tipo (Pulpable, Aserrable, Chip)
    tn_pulpable = DecimalField()        # Toneladas pulpable
    tn_aserrable = DecimalField()       # Toneladas aserrable
    tn_chip = DecimalField()            # Toneladas chip
    sin_actividad = BooleanField()      # Viaje sin actividad
    motivo_sin_actividad = CharField()  # Motivo si sin actividad
    observaciones = TextField()         # Observaciones
    personal = ForeignKey(Personal)     # Chofer (nullable)
    record_id = CharField()             # ID de registro externo
    created_at = DateTimeField()        # Fecha de creación
    updated_at = DateTimeField()        # Última actualización
```

## Tecnologías

- **Backend:** Django 5.0.1, Django REST Framework
- **Frontend:** Vue 3 (Composition API), Bootstrap 5
- **Base de Datos:** (la configurada en settings.py)
- **Autenticación:** Session + CSRF tokens

## Mejoras Futuras

- [ ] Paginación en el frontend (botones prev/next)
- [ ] Exportar a Excel/PDF
- [ ] Gráficos con Chart.js
- [ ] Filtros avanzados (por cliente, área, producto)
- [ ] Búsqueda de texto completo
- [ ] Validaciones más estrictas en formulario
- [ ] Tests unitarios y de integración
- [ ] Documentación API con Swagger/OpenAPI

## Soporte

Para reportar bugs o solicitar features, contactar al equipo de desarrollo.

---
**Última actualización:** Octubre 2024
