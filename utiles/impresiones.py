import os
import tempfile
from io import BytesIO

from django.http import HttpResponse
from reportlab.pdfgen import canvas

from core import settings
from syh.models import Movimientos
from utiles.funciones_usuario import FormatoFecha, dividir_texto, obtener_parametro, getTempFileName
import matplotlib.pyplot as plt
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter

class Impresiones:

    pdf = None
    response = None
    titulo = None
    buffer = None
    ubicacion = {}
    fila = 725
    # archivo = next(tempfile._get_candidate_names())
    archivo = getTempFileName(base=True)
    pagina = 0
    diferencia_hoja = 0
    titulos = {
        'encabezado': 90
    }
    tamanio_fuente_detalle = 10
    nombre_fuente = "Helvetica"
    nombre_fuente_bold = "Helvetica-Bold"

    def cabecera(self):
        self.fila = 725
        self.pagina += 1
        if self.pagina > 1:
            self.pdf.showPage()
            self.pdf.setFont(self.nombre_fuente, 10)

        pdf = self.pdf
        # Utilizamos el archivo logo_django.png que está guardado en la carpeta media/imagenes
        archivo_imagen = f'{os.path.join(settings.MEDIA_ROOT, obtener_parametro("logo_encabezado", "encabezado_informe.png"))}'
        # Definimos el tamaño de la imagen a cargar y las coordenadas correspondientes
        pdf.drawImage(archivo_imagen, 0, 750 - self.diferencia_hoja, 600, 90, preserveAspectRatio=True)
        # pdf.setFont(self.nombre_fuente, 14)
        # pdf.drawString(x=self.titulos['encabezado'], y=830 - self.diferencia_hoja, text=f"{obtener_parametro('nombre_institucion', 'Fundacion Lapacho')}")
        # pdf.drawString(x=self.titulos['encabezado'], y=818 - self.diferencia_hoja, text=f"{obtener_parametro('iniciales_institucion', 'IAES')}")
        # pdf.setFont(self.nombre_fuente, 10)
        # pdf.drawString(x=self.titulos['encabezado'], y=780 - self.diferencia_hoja, text=f"{obtener_parametro('direccion_institucion', 'Jose Manuel Estrada 1264')}")
        # pdf.drawString(x=self.titulos['encabezado'], y=770 - self.diferencia_hoja, text=f"{obtener_parametro('localidad_institucion', '3334 Puerto Rico - Misiones')}")
        # pdf.setFont(self.nombre_fuente, 8)
        # pdf.drawString(x=self.titulos['encabezado'], y=760 - self.diferencia_hoja, text=f"{obtener_parametro('telefono_institucion', '3743 443336')}")
        # pdf.drawString(x=self.titulos['encabezado'], y=750 - self.diferencia_hoja, text=f"{obtener_parametro('iva_responsable', 'IVA RESPONSABLE EXENTO')}")
        # pdf.setFont(self.nombre_fuente, 10)
        # pdf.setFont(self.nombre_fuente_bold, 8)
        # pdf.drawString(x=350, y=760 - self.diferencia_hoja, text=f"{obtener_parametro('codigo_cuit', 'CUIT: 33-71101311-9')}")
        # pdf.drawString(x=450, y=760 - self.diferencia_hoja, text=f"{obtener_parametro('codigo_ing_brutos', 'Ing. Brutos: 33-71101311-9')}")
        # pdf.drawString(x=350, y=750 - self.diferencia_hoja, text=f"{obtener_parametro('email_institucion', 'nivelprimario@iaes.edu.ar')}")
        pdf.setFont(self.nombre_fuente, 10)
        if self.titulo:
            pdf.drawString(x=self.titulos['encabezado'], y=720 - self.diferencia_hoja, text=f"{self.titulo}")
        self.fila -= 30
        self.encabezadodetalle()
        self.fila -= 15

    def inicia(self):
        # Indicamos el tipo de contenido a devolver, en este caso un pdf
        self.response = HttpResponse(content_type='application/pdf')
        self.response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.archivo)
        # La clase io.BytesIO permite tratar un array de bytes como un fichero binario, se utiliza como almacenamiento temporal
        self.buffer = BytesIO()
        # Canvas nos permite hacer el reporte con coordenadas X y Y
        self.pdf = canvas.Canvas(self.buffer)
        self.pdf.setFont(self.nombre_fuente, self.tamanio_fuente_detalle)

    def finaliza(self):
        self.pdf.showPage()
        self.pdf.save()
        self.pdf = self.buffer.getvalue()
        self.buffer.close()
        self.response.write(self.pdf)

    def encabezadodetalle(self):
        if self.ubicacion:
            self.pdf.roundRect(x=8, y=self.fila, width=550, height=20, radius=4)
            self.fila += 5
            self.pdf.setFont(self.nombre_fuente, self.tamanio_fuente_detalle)
            for k, v in self.ubicacion.items():
                self.pdf.drawString(x=v, y=self.fila, text=k)

    def check_break_page(self, alto=20):
        if self.fila - alto < 0:
            self.cabecera()
    
    def pie(self):
        self.pdf.setFont(self.nombre_fuente, self.tamanio_fuente_detalle)
        self.pdf.line(x1=0, y1=460 - self.diferencia_hoja, x2=600, y2=460 - self.diferencia_hoja)
        self.diferencia_hoja = 440
    
    def centrar_texto_con_linea(self, texto, tamanio=12):
        # Obtener el ancho de la página
        ancho_pagina = self.pdf._pagesize[0]  # El tamaño de la página (ancho)
        
        # Calcular el ancho del texto para centrarlo
        ancho_texto = self.pdf.stringWidth(texto, "Helvetica", 12)  # Usamos fuente Helvetica, tamaño 12
        
        # Coordenada X para centrar el texto
        x_centrada = (ancho_pagina - ancho_texto) / 2
        
        # Dibujar el texto centrado
        self.pdf.setFont(self.nombre_fuente, tamanio)  # Establece la fuente y tamaño
        self.pdf.drawString(x=x_centrada, y=self.fila, text=texto)
        
        # Dibujar la línea justo debajo del texto
        margen_lateral = 20  # Define el margen de la línea desde los bordes de la página
        y_linea = self.fila - 10  # Ajustar la posición de la línea justo debajo del texto
        self.pdf.line(margen_lateral, y_linea, ancho_pagina - margen_lateral, y_linea)

        # Ajustar la posición vertical para el siguiente contenido
        self.fila -= 30  # Disminuye la fila para dar espacio para el siguiente texto

class ResumenCobro(Impresiones):

    boletas = None
    ubicacion = {
        'Recibo':10,
        'Fecha':80,
        'Hora':150,
        'Asociado':200,
        'Conexion':400,
        'Monto':500,
    }
    request = None
    agrupado_por_pdc = False

    def detalle(self):
        b = None
        self.fila -= 15
        totalcobrado = 0
        total_por_pdc = 0
        pdc = 0
        porcentaje = 0
        razon = ''
        cantidad = 0

        for b in self.boletas:
            cantidad += 1
            if self.agrupado_por_pdc:
                if pdc != b.pdc.id:
                    if pdc != 0:
                        self.pdf.drawString(x=50, y=self.fila, text='Total cobrado por {}: ${}'.format(
                            razon, total_por_pdc
                        ))
                        self.pdf.drawString(x=350, y=self.fila, text='Comision: ${}'.format(
                            round(totalcobrado * porcentaje / 100, 2)
                        ))
                        self.fila -= 20

                    self.pdf.drawString(x=15, y=self.fila, text="Punto de cobro: {}".format(
                        b.pdc.razon_social
                    ))
                    self.fila -= 12
                    pdc = b.pdc.id
                    total_por_pdc = 0
                    porcentaje = b.pdc.porcentaje
                    razon = b.pdc.razon_social

            totalcobrado += b.monto_cobrado
            total_por_pdc += b.monto_cobrado
            self.pdf.drawString(x=self.ubicacion['Recibo'], y=self.fila, text=str(b.recibo))
            self.pdf.drawString(x=self.ubicacion['Fecha'], y=self.fila, text=b.fecha_cobro.strftime('%d/%m%Y'))
            self.pdf.drawString(x=self.ubicacion['Hora'], y=self.fila, text=b.hora_cobro.strftime('%H:%M:%S'))
            self.pdf.drawString(x=self.ubicacion['Asociado'], y=self.fila, text='{}, {}'.format(
                b.conexion.asociado.apellido, b.conexion.asociado.nombre
            ))
            self.pdf.drawString(x=self.ubicacion['Conexion'], y=self.fila, text=str(b.conexion.nro_conexion))
            self.pdf.drawString(x=self.ubicacion['Monto'], y=self.fila, text=str(b.monto_cobrado))

            self.fila -= 12
            self.check_break_page()

        self.fila -= 5
        self.pdf.line(x1=0, y1=self.fila, x2=600, y2=self.fila)
        self.fila -= 10
        self.pdf.drawString(x=50, y=self.fila, text='Total cobrado por {}: ${}      Cantidad cobradas {}'.format(
            razon, total_por_pdc, cantidad
        ))
        if b:
            self.pdf.drawString(x=350, y=self.fila, text='Comision: ${}'.format(
                round(total_por_pdc * b.pdc.porcentaje / 100, 2)
            ))

class ImprimeHallazgos(Impresiones):

    def __init__(self) -> None:
        super().__init__()

    def imprime_hallazgo(self, queryset):
        if queryset.exists():
            cliente = queryset.first().cliente
            area = queryset.first().area
            titulo = f"Reporte de Movimientos para {cliente} - Área: {area}"
        else:
            titulo = "Reporte de Movimientos"

        self.titulo = titulo
        width, height = letter
        self.inicia()
        self.ubicacion = {
            'Fecha': 10,
            'Periodo': 65,
            'Hallazgo': 120,
            'Estado': 500
        }
        # Crear el PDF
        self.cabecera()
        data = [['Fecha', 'Periodo', 'Estado', 'Hallazgo']]
        for movimiento in queryset:
            self.fila -=10
            self.check_break_page()
            self.pdf.drawString(x=self.ubicacion['Fecha'], y=self.fila, text=FormatoFecha(movimiento.fecha, formato='dma'))
            self.pdf.drawString(x=self.ubicacion['Periodo'], y=self.fila, text=str(movimiento.periodo))
            self.pdf.drawString(x=self.ubicacion['Estado'], y=self.fila, text=str(movimiento.estado))
            lineas = dividir_texto(movimiento.hallazgo, 80)
            for linea in lineas:
                self.pdf.drawString(x=self.ubicacion['Hallazgo'], y=self.fila, text=linea)
                self.fila -= 10
            # Paragraph(movimiento.hallazgo, getSampleStyleSheet()['BodyText'])
            data.append([
                str(movimiento.fecha),
                movimiento.periodo,
                movimiento.hallazgo,
                movimiento.estado
            ])
        
        self.fila -= 30
        self.check_break_page()
        
        datos_grafico, sizes = self.crea_grafico_torta(cliente, area)

        # Posicion inicial donde empezar la impresion del grafico
        y_position = self.fila

        # Cargar la imagen del gráfico de torta
        img_reader = ImageReader('grafico_torta.png')
        img_width, img_height = img_reader.getSize()

        # Escalar la imagen para mantener la relación de aspecto
        aspect = img_height / img_width
        new_width = 400  # Ancho deseado
        new_height = new_width * aspect

        # Dibujar la imagen manteniendo la relación de aspecto y comenzando desde la última posición de impresión
        # self.pdf.drawImage(img_reader, 100, y_position - new_height, width=new_width, height=new_height)
        
        colores = ['#ff9999','#66b3ff','#99ff99']  # Colores para cada segmento

        # Crear una tabla con los colores y los datos
        data = [['Color', 'Estado', 'Porcentaje']]
        for i, dato in enumerate(datos_grafico):
            color = colors.toColor(colores[i])
            estado = dato['label']
            porcentaje = f"{(dato['value'] / sum(sizes)) * 100:.1f}%"
            data.append([Paragraph(f'<font color="{color}">&#9608;</font>', getSampleStyleSheet()['BodyText']), estado, porcentaje])

        # Definir el estilo de la tabla
        table = Table(data, colWidths=[50, 150, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        self.fila -= 400
        self.check_break_page(alto=400)
        # Ajustar la tabla y agregarla al PDF
        table.wrapOn(self.pdf, width, height)
        table.drawOn(self.pdf, 30, self.fila - 100)
        self.finaliza()
        return self.response

    def crea_grafico_torta(self, cliente, area):

        # Obtiene los datos de las tareas agrupadas por estado
        tareas_por_estado = Movimientos.contar_tareas_por_estado(cliente.id, area.id)
        # Formatea los datos para Morris.js
        datos_grafico = [
            {"label": tarea["estado"], "value": tarea["cantidad"]}
            for tarea in tareas_por_estado
        ]
        # Crear el gráfico de torta
        labels = [dato["label"] for dato in datos_grafico]
        sizes = [dato["value"] for dato in datos_grafico]
        colors = ['#ff9999','#66b3ff','#99ff99']  # Colores para cada segmento

        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Igualar los ejes para que el gráfico sea un círculo perfecto

        # Guardar el gráfico como PNG
        plt.savefig('grafico_torta.png')
        return datos_grafico, sizes
