from django.test import TestCase

# Create your tests here.
import datetime
from.models import Movimientos, Cliente, Area

class TestGetPorcentajeCumplidosPorArea(TestCase):
    def setUp(self):
        # Crear un cliente
        self.cliente = Cliente.objects.create(nombre='Cliente 1')

        # Crear áreas
        self.area1 = Area.objects.create(nombre='Área 1')
        self.area2 = Area.objects.create(nombre='Área 2')

        # Crear movimientos
        self.movimiento1 = Movimientos.objects.create(
            cliente=self.cliente,
            area=self.area1,
            fecha=datetime.date(2022, 1, 1),
            estado='Cumplido'
        )
        self.movimiento2 = Movimientos.objects.create(
            cliente=self.cliente,
            area=self.area1,
            fecha=datetime.date(2022, 1, 15),
            estado='No Cumplido'
        )
        self.movimiento3 = Movimientos.objects.create(
            cliente=self.cliente,
            area=self.area2,
            fecha=datetime.date(2022, 2, 1),
            estado='Cumplido'
        )
        self.movimiento4 = Movimientos.objects.create(
            cliente=self.cliente,
            area=self.area2,
            fecha=datetime.date(2022, 2, 15),
            estado='Cumplido'
        )

    def test_get_porcentaje_cumplidos_por_area(self):
        # Probar con un rango de fechas que incluye todos los movimientos
        fecha_desde = datetime.date(2022, 1, 1)
        fecha_hasta = datetime.date(2022, 2, 28)
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(self.cliente, fecha_desde, fecha_hasta)
        self.assertEqual(resultados['Área 1'], 50.0)
        self.assertEqual(resultados['Área 2'], 100.0)

        # Probar con un rango de fechas que solo incluye los movimientos de enero
        fecha_desde = datetime.date(2022, 1, 1)
        fecha_hasta = datetime.date(2022, 1, 31)
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(self.cliente, fecha_desde, fecha_hasta)
        self.assertEqual(resultados['Área 1'], 50.0)
        self.assertNotIn('Área 2', resultados)

        # Probar con un rango de fechas que solo incluye los movimientos de febrero
        fecha_desde = datetime.date(2022, 2, 1)
        fecha_hasta = datetime.date(2022, 2, 28)
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(self.cliente, fecha_desde, fecha_hasta)
        self.assertEqual(resultados['Área 2'], 100.0)
        self.assertNotIn('Área 1', resultados)