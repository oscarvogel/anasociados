# 🚛 Sistema de Gestión Core AN

Sistema integral de gestión empresarial desarrollado con Django para administración de vehículos, personal, seguridad e higiene, y control operativo.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python)
![Django](https://img.shields.io/badge/Django-4.1-092E20?style=flat-square&logo=django)
![MySQL](https://img.shields.io/badge/MySQL-Database-4479A1?style=flat-square&logo=mysql)
![Celery](https://img.shields.io/badge/Celery-Tasks-37B24D?style=flat-square&logo=celery)
![REST API](https://img.shields.io/badge/REST-API-009688?style=flat-square)

## 📋 Descripción

**Core AN** es un sistema de gestión empresarial que integra múltiples módulos para el control operativo de flotas vehiculares, gestión de personal, seguridad e higiene ocupacional, y administración de viajes. Desarrollado específicamente para empresas del sector forestal y logístico.

## 🎯 Módulos Principales

### 🚗 **Móviles**
- **Gestión de vehículos**: Control de patentes, marcas, modelos y estado
- **Personal**: Administración de conductores con DNI, CUIT y datos personales  
- **Carga de combustible**: Registro detallado con consumos y kilometrajes
- **Vencimientos**: Control de documentación vehicular y personal
- **Gastos**: Seguimiento de costos operativos por centro de costos
- **Viajes**: Sistema completo de registro de traslados con tonelajes
- **Predios**: Gestión de orígenes y destinos

### 👥 **Usuarios**
- **Perfiles**: Vinculación usuario-cliente
- **Áreas de perfil**: Asignación de áreas por usuario
- **Autenticación**: Sistema de login integrado con Django Auth

### 🛡️ **SYH (Seguridad e Higiene)**
- **Movimientos**: Control de hallazgos y acciones correctivas
- **Naturaleza de hallazgos**: Clasificación de tipos de incidentes
- **Clientes y áreas**: Gestión organizacional
- **Parámetros del sistema**: Configuración global
- **Matafuegos**: Control de vencimientos de seguridad

### 🏠 **Home**
- Dashboard principal
- Vistas generales y reportes

### 🔧 **Utiles**
- Funciones auxiliares y herramientas compartidas

## 🏗️ Arquitectura del Proyecto

```
core_an/
├── core_an/                    # Configuración principal
│   ├── settings.py            # Configuración Django + Celery
│   ├── urls.py                # URLs principales
│   ├── celery.py              # Configuración Celery
│   ├── wsgi.py                # WSGI para producción
│   └── asgi.py                # ASGI para async
├── moviles/                   # Gestión de vehículos y viajes
│   ├── models.py              # 9 modelos: Movil, Personal, Viajes, etc.
│   ├── admin.py               # Configuración admin
│   ├── views.py               # Vistas y API ViewSets
│   ├── serializers.py         # DRF Serializers
│   └── migrations/            # Migraciones BD
├── syh/                       # Seguridad e Higiene
│   ├── models.py              # Cliente, Area, Movimientos, etc.
│   └── ...
├── usuarios/                  # Gestión de usuarios
│   ├── models.py              # Profile, AreasProfile
│   └── ...
├── home/                      # Dashboard principal
├── utiles/                    # Herramientas compartidas
├── templates/                 # Plantillas HTML
├── static/                    # Archivos estáticos
├── media/                     # Archivos multimedia
├── tools/                     # Scripts y utilidades
└── requirements.txt           # Dependencias Python
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- **Python** ≥ 3.8
- **MySQL** (configurado en settings)
- **RabbitMQ** (para Celery)
- **Node.js** (opcional, para frontend avanzado)

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd core_an
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear archivo `.env` en el directorio raíz:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database Configuration
DB_ENGINE=mysql
DB_USERNAME=your_db_user
DB_PASS=your_db_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=core_an

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# Celery Configuration
CELERY_BROKER_URL=pyamqp://user:password@localhost:5672/vhost
```

### 5. Configurar base de datos

```bash
# Ejecutar migraciones
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Cargar datos iniciales (opcional)
python manage.py loaddata initial_data.json
```

### 6. Recolectar archivos estáticos

```bash
python manage.py collectstatic --noinput
```

## 🔧 Uso

### Servidor de Desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000`

### Celery Worker (Tareas en Background)

```bash
# En terminal separada
celery -A core_an worker --loglevel=info
```

### URLs Principales

- **Admin**: `http://127.0.0.1:8000/admin/`
- **Home**: `http://127.0.0.1:8000/`
- **Móviles**: `http://127.0.0.1:8000/moviles/`
- **SYH**: `http://127.0.0.1:8000/syh/`
- **API Viajes**: `http://127.0.0.1:8000/moviles/api/viajes/`

## 📊 API REST

### Endpoints Principales

#### Viajes
```bash
# Listar viajes (paginado)
GET /moviles/api/viajes/

# KPIs de viajes
GET /moviles/api/viajes/kpis/

# Crear viaje
POST /moviles/api/viajes/
```

#### Móviles y Personal
```bash
# Listar móviles
GET /moviles/api/movil/

# Listar personal
GET /moviles/api/personal/

# Listar predios
GET /moviles/api/predios/
```

### Ejemplo de Respuesta - KPIs
```json
{
  "total_viajes": 45,
  "tn_pulpable": 5420.75,
  "tn_aserrable": 1230.50,
  "tn_chip": 890.25,
  "tn_total": 7541.50
}
```

## 📈 Características Avanzadas

### 🔄 Procesamiento Asíncrono
- **Celery** con RabbitMQ para tareas pesadas
- **Django Celery Results** para almacenar resultados
- **Configuración de queues** personalizadas

### 🎨 Interfaz de Usuario
- **Django Admin Datta** como tema de administración
- **Dynamic DataTables** para tablas interactivas
- **API Generator** para generación automática de APIs
- **Vue.js** en vistas específicas (viajes)

### 🔒 Seguridad
- **CSRF Protection** habilitado
- **Session-based Authentication**
- **Token Authentication** para APIs
- **Validación de inputs** en modelos y formularios

### 📊 Reportes y Analytics
- **KPIs automáticos** calculados
- **Gráficos** con matplotlib
- **Exportación** de datos
- **Filtros avanzados** por fecha, cliente, área

## 🛠️ Tecnologías Utilizadas

### Backend
- **Django 4.1.2**: Framework web principal
- **Django REST Framework**: APIs REST
- **Celery**: Procesamiento asíncrono
- **PyMySQL**: Conector MySQL
- **python-dotenv**: Variables de entorno
- **WhiteNoise**: Servir archivos estáticos
- **Gunicorn**: Servidor WSGI para producción

### Frontend
- **Vue.js 3**: Framework reactivo
- **Bootstrap 5**: Framework CSS
- **Django Templates**: Motor de plantillas
- **Dynamic DataTables**: Tablas interactivas
- **SweetAlert2**: Notificaciones

### Base de Datos
- **MySQL**: Base de datos principal
- **Django ORM**: Mapeo objeto-relacional
- **Migraciones**: Control de versiones de BD

### DevOps
- **Docker**: Containerización (opcional)
- **Git**: Control de versiones
- **WhiteNoise**: Archivos estáticos en producción

## 📁 Modelos de Datos Principales

### Móviles
```python
class Movil(models.Model):
    empresa = ForeignKey(Cliente)
    patente = CharField(max_length=10)
    marca = CharField(max_length=30)
    modelo = CharField(max_length=30)
    anio = IntegerField()
    baja = BooleanField(default=False)
```

### Viajes
```python
class Viajes(models.Model):
    movil = ForeignKey(Movil)
    fecha = DateField()
    origen = ForeignKey(Predios)
    destino = CharField(choices=DESTINOS_CHOICES)
    producto = CharField(choices=PRODUCTO_CHOICES)
    tn_pulpable = DecimalField(max_digits=10, decimal_places=2)
    tn_aserrable = DecimalField(max_digits=10, decimal_places=2)
    tn_chip = DecimalField(max_digits=10, decimal_places=2)
    sin_actividad = BooleanField(default=False)
```

### Personal
```python
class Personal(models.Model):
    nombre = CharField(max_length=50)
    apellido = CharField(max_length=50)
    dni = CharField(max_length=8)
    cuit = CharField(max_length=13)
    empresa = ForeignKey(Cliente)
    fecha_nacimiento = DateField()
    baja = BooleanField(default=False)
```

## 🚀 Despliegue en Producción

### Variables de Entorno (Producción)
```env
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SECRET_KEY=your-super-secure-secret-key
DB_HOST=production-db-host
CELERY_BROKER_URL=redis://redis-host:6379/0
```

### Docker (Opcional)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "core_an.wsgi:application"]
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /static/ {
        alias /path/to/staticfiles/;
    }
    
    location /media/ {
        alias /path/to/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🧪 Testing

```bash
# Ejecutar tests
python manage.py test

# Con coverage
pip install coverage
coverage run manage.py test
coverage report
```

## 📝 Contribuir

1. Fork el proyecto
2. Crea tu feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es propiedad de **Almada Neri** y está protegido por derechos de autor.

## 🤝 Soporte

Para soporte técnico o reportar bugs:

- **Email**: sistemas@servinlgsm.com.ar
- **Desarrollador**: Jose Oscar Vogel

## 🔄 Changelog

### v2024.10
- ✅ Sistema de viajes con API REST completa
- ✅ KPIs y reportes automáticos
- ✅ Integración con Celery
- ✅ Interfaz responsive con Vue.js

### v2024.09
- ✅ Módulo SYH implementado
- ✅ Control de vencimientos
- ✅ Gestión de matafuegos

### v2024.08
- ✅ Base del sistema implementada
- ✅ Módulos de móviles y personal
- ✅ Sistema de autenticación

---

**Desarrollado con ❤️ para la gestión integral empresarial**