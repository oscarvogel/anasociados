from django.utils import timezone
import random
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Max
from moviles.models import CargaCombustible, Personal, Movil, Cliente

def obtener_ultimo_registro(movil):
    """
    Obtiene el último registro de carga de combustible para un móvil específico
    Retorna el último km y la última fecha
    """
    ultimo_registro = CargaCombustible.objects.filter(
        movil=movil
    ).order_by('-fecha', '-km_hora').first()
    
    if ultimo_registro:
        return ultimo_registro.km_hora, ultimo_registro.fecha
    return 0, None

def generar_cargas_combustible(cantidad=10, tipo_combustible='Ultra'):
    """
    Genera registros de prueba para el modelo CargaCombustible asegurando
    que las fechas sean coherentes con el incremento de kilómetros
    
    Parameters:
    cantidad (int): Número de registros a generar
    tipo_combustible (str): Tipo de combustible a usar
    """
    # Validar que el tipo de combustible sea válido
    tipos_validos = dict(CargaCombustible.TIPOS_COMBUSTIBLE)
    if tipo_combustible not in tipos_validos:
        tipos_disponibles = ', '.join(tipos_validos.keys())
        raise ValueError(f"Tipo de combustible inválido. Tipos disponibles: {tipos_disponibles}")
    
    # Obtenemos datos existentes de las tablas relacionadas
    choferes = list(Personal.objects.all())
    moviles = list(Movil.objects.all())
    
    if not choferes or not moviles:
        raise ValueError("Necesitas tener registros en Personal y Movil para generar cargas de combustible")

    # Fecha base para el último registro
    fecha_base = timezone.now().date()
    
    # Diccionario para mantener el seguimiento del último registro por móvil
    seguimiento_moviles = {}
    registros_creados = []
    
    for i in range(cantidad):
        # Seleccionamos datos aleatorios
        chofer = random.choice(choferes)
        movil = random.choice(moviles)
        
        # Si el móvil no está en el seguimiento, obtenemos su último registro de la base de datos
        if movil.id not in seguimiento_moviles:
            ultimo_km, ultima_fecha = obtener_ultimo_registro(movil)
            seguimiento_moviles[movil.id] = {
                'km': ultimo_km,
                'fecha': ultima_fecha or (fecha_base - timedelta(days=365))  # Si no hay fecha, empezamos 30 días atrás
            }
        
        # Obtenemos el último registro para este móvil
        ultimo_registro = seguimiento_moviles[movil.id]
        
        # Generamos un nuevo kilometraje mayor al último
        incremento_km = random.randint(100, 1000)
        km_hora = ultimo_registro['km'] + incremento_km
        
        # Calculamos una nueva fecha posterior a la última
        # Asumimos que cada 100km representa aproximadamente 1 día
        dias_incremento = max(1, incremento_km // 100)
        nueva_fecha = ultimo_registro['fecha'] + timedelta(days=dias_incremento)
        
        # Si la nueva fecha supera la fecha actual, saltamos este registro
        if nueva_fecha > fecha_base:
            continue
        
        # Generamos valores aleatorios realistas
        litros = Decimal(str(random.uniform(20.0, 100.0))).quantize(Decimal('0.01'))
        precio_por_litro = Decimal(str(random.uniform(150.0, 300.0))).quantize(Decimal('0.01'))
        importe = (litros * precio_por_litro).quantize(Decimal('0.01'))
        
        try:
            # Crear el registro
            carga = CargaCombustible(
                chofer=chofer,
                movil=movil,
                fecha=nueva_fecha,
                litros=litros,
                importe=importe,
                km_hora=km_hora,
                tipo_combustible=tipo_combustible
            )
            
            carga.save()
            registros_creados.append(carga)
            
            # Actualizamos el seguimiento para este móvil
            seguimiento_moviles[movil.id] = {
                'km': km_hora,
                'fecha': nueva_fecha
            }
            
        except Exception as e:
            print(f"Error al crear registro para móvil {movil}: {str(e)}")
            continue
        
    return registros_creados

def generar_reporte_cargas(registros):
    """
    Genera un reporte simple de las cargas generadas, ordenado por móvil y fecha
    """
    print("\nReporte de Cargas de Combustible Generadas:")
    print("-" * 100)
    
    # Ordenamos los registros por móvil y fecha
    registros_ordenados = sorted(registros, key=lambda x: (x.movil.id, x.fecha))
    
    movil_actual = None
    for carga in registros_ordenados:
        # Agregar una línea en blanco entre diferentes móviles
        if movil_actual != carga.movil:
            if movil_actual is not None:
                print("-" * 100)
            movil_actual = carga.movil
            
        print(f"Móvil: {carga.movil} | "
              f"Fecha: {carga.fecha} | "
              f"Km: {carga.km_hora:,} | "
              f"Chofer: {carga.chofer} | "
              f"Combustible: {carga.tipo_combustible} | "
              f"Litros: {carga.litros} | "
              f"Importe: ${carga.importe:,.2f}")
    print("-" * 100)

if __name__ == "__main__":
    try:
        registros = generar_cargas_combustible(10, tipo_combustible='Infinia Nafta')
        generar_reporte_cargas(registros)
        print(f"\nSe generaron {len(registros)} registros exitosamente.")
    except Exception as e:
        print(f"Error al generar registros: {str(e)}")