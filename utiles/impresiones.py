import os
import tempfile
from io import BytesIO

from django.http import HttpResponse
from reportlab.pdfgen import canvas

from core import settings
from utiles.funciones_usuario import obtener_parametro, getTempFileName

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
        archivo_imagen = f'{os.path.join(settings.MEDIA_ROOT, obtener_parametro("logo_mini", "logo_mini.png"))}'
        # Definimos el tamaño de la imagen a cargar y las coordenadas correspondientes
        pdf.drawImage(archivo_imagen, 0, 750 - self.diferencia_hoja, 80, 90, preserveAspectRatio=True)
        pdf.setFont(self.nombre_fuente, 14)
        pdf.drawString(x=self.titulos['encabezado'], y=830 - self.diferencia_hoja, text=f"{obtener_parametro('nombre_institucion', 'Fundacion Lapacho')}")
        pdf.drawString(x=self.titulos['encabezado'], y=818 - self.diferencia_hoja, text=f"{obtener_parametro('iniciales_institucion', 'IAES')}")
        pdf.setFont(self.nombre_fuente, 10)
        pdf.drawString(x=self.titulos['encabezado'], y=780 - self.diferencia_hoja, text=f"{obtener_parametro('direccion_institucion', 'Jose Manuel Estrada 1264')}")
        pdf.drawString(x=self.titulos['encabezado'], y=770 - self.diferencia_hoja, text=f"{obtener_parametro('localidad_institucion', '3334 Puerto Rico - Misiones')}")
        pdf.setFont(self.nombre_fuente, 8)
        pdf.drawString(x=self.titulos['encabezado'], y=760 - self.diferencia_hoja, text=f"{obtener_parametro('telefono_institucion', '3743 443336')}")
        pdf.drawString(x=self.titulos['encabezado'], y=750 - self.diferencia_hoja, text=f"{obtener_parametro('iva_responsable', 'IVA RESPONSABLE EXENTO')}")
        pdf.setFont(self.nombre_fuente, 10)
        pdf.setFont(self.nombre_fuente_bold, 8)
        pdf.drawString(x=350, y=760 - self.diferencia_hoja, text=f"{obtener_parametro('codigo_cuit', 'CUIT: 33-71101311-9')}")
        pdf.drawString(x=450, y=760 - self.diferencia_hoja, text=f"{obtener_parametro('codigo_ing_brutos', 'Ing. Brutos: 33-71101311-9')}")
        pdf.drawString(x=350, y=750 - self.diferencia_hoja, text=f"{obtener_parametro('email_institucion', 'nivelprimario@iaes.edu.ar')}")
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

    def check_break_page(self):
        if self.fila - 20 < 0:
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
