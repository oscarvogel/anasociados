"""Tests de los porcentajes de cumplimiento por área.

Este archivo estaba roto y nadie lo había visto: `Area` pasó de `nombre` a
`detalle` y pasó a exigir `cliente`, y los estados que usaba ('No Cumplido')
no están en los que filtra `get_porcentaje_cumplidos_por_area`. Se reescribió
con el modelo actual manteniendo las mismas expectativas: 50% para un área con
un cumplido y uno incumplido, 100% para una con los dos cumplidos.

Los `id` de Movimientos van explícitos porque el campo está declarado como
`default=generate_unique_id(20)`, que se evalúa una sola vez al importar el
módulo: todos los movimientos creados sin id reciben la misma PK y el segundo
choca con Duplicate entry.
"""
import datetime

from django.test import TestCase

from syh.models import Area, Cliente, Movimientos


class TestGetPorcentajeCumplidosPorArea(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            id="CLIPOR", nombre="Cliente de prueba", email="prueba@example.com"
        )

        self.area1 = Area.objects.create(
            id="ARP01", cliente=self.cliente, detalle="Área 1", responsable="Ana"
        )
        self.area2 = Area.objects.create(
            id="ARP02", cliente=self.cliente, detalle="Área 2", responsable="Beto"
        )

        self.movimiento1 = self.crear("ARP01", datetime.date(2022, 1, 1), "Cumplido", 1)
        self.movimiento2 = self.crear("ARP01", datetime.date(2022, 1, 15), "Incumplido", 2)
        self.movimiento3 = self.crear("ARP02", datetime.date(2022, 2, 1), "Cumplido", 3)
        self.movimiento4 = self.crear("ARP02", datetime.date(2022, 2, 15), "Cumplido", 4)

    def crear(self, area_id, fecha, estado, secuencia):
        return Movimientos.objects.create(
            id=f"movpor{secuencia:07d}",
            cliente=self.cliente,
            area_id=area_id,
            fecha=fecha,
            periodo="Enero" if fecha.month == 1 else "Febrero",
            hallazgo="Prueba de porcentaje",
            responsable="Ana",
            plazo=30,
            estado=estado,
            fecha_cumplimiento=fecha,
        )

    def test_get_porcentaje_cumplidos_por_area(self):
        # Rango completo: un área con 1 de 2 cumplidos y otra con 2 de 2.
        fecha_desde = datetime.date(2022, 1, 1)
        fecha_hasta = datetime.date(2022, 2, 28)
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(
            self.cliente, fecha_desde, fecha_hasta
        )
        self.assertEqual(resultados["Área 1"], 50.0)
        self.assertEqual(resultados["Área 2"], 100.0)

        # Solo enero: aparece el área 1, no el área 2.
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(
            self.cliente, datetime.date(2022, 1, 1), datetime.date(2022, 1, 31)
        )
        self.assertEqual(resultados["Área 1"], 50.0)
        self.assertNotIn("Área 2", resultados)

        # Solo febrero: aparece el área 2, no el área 1.
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(
            self.cliente, datetime.date(2022, 2, 1), datetime.date(2022, 2, 28)
        )
        self.assertEqual(resultados["Área 2"], 100.0)
        self.assertNotIn("Área 1", resultados)