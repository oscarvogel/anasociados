import datetime
import io
import os
import re
from io import BytesIO
from venv import logger
from syh.models import Cliente, EmisionCarbono, ExcesosVelocidad, IndiceAccidentabilidad, ParametroSistema
from django.http import HttpResponse
from reportlab.pdfgen import canvas

from core_an import settings
from syh.models import Movimientos
from utiles.funciones_usuario import FormatoFecha, dividir_texto, getTempFileName
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from utiles.generador_graficos import GraficoTorta

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
        archivo_imagen = f'{os.path.join(settings.MEDIA_ROOT, ParametroSistema.obtener_parametro("logo_encabezado", "encabezado_informe.png"))}'
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
        # pdf.drawString(x=350, y=750 - self.diferencia_hoja, text=f"{obtener_parametro('email_institucion', 'nivelprimario@iaes.edu.ar')}").
        pdf.drawString(x=10, y=810 - self.diferencia_hoja, text=f"Impreso {FormatoFecha(datetime.datetime.now(), formato='dma_hms')}")
        pdf.setFont(self.nombre_fuente, 12)
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

    def finaliza(self, grabar=False):
        self.pie()
        self.pdf.showPage()
        self.pdf.save()
        self.pdf = self.buffer.getvalue()
        self.pdf_content = self.buffer.getvalue()
        self.buffer.close()
        self.response.write(self.pdf)
        # Definir la ruta donde se guardará el PDF
        self.pdf_path = self.archivo 
        if grabar:
            print(self.pdf_path)
            carpeta = os.path.dirname(self.pdf_path)
            if carpeta:
                os.makedirs(carpeta, exist_ok=True)
            # Guardar el PDF en el disco 
            with open(self.pdf_path, 'wb') as f: 
                f.write(self.pdf_content) 
        
        return self.pdf_path

    def encabezadodetalle(self):
        if self.ubicacion:
            self.pdf.roundRect(x=8, y=self.fila, width=550, height=20, radius=4)
            self.fila += 5
            self.pdf.setFont(self.nombre_fuente, self.tamanio_fuente_detalle)
            for k, v in self.ubicacion.items():
                self.pdf.drawString(x=v, y=self.fila, text=k)

    def check_break_page(self, alto=70):
        self.pie()
        if self.fila - alto < 0:
            self.cabecera()
    
    def pie(self):
        # self.pdf.setFont(self.nombre_fuente, self.tamanio_fuente_detalle)
        self.pdf.line(x1=0, y1=47 - self.diferencia_hoja, x2=600, y2=47 - self.diferencia_hoja)
        # self.diferencia_hoja = 440
        archivo_imagen = f'{os.path.join(settings.MEDIA_ROOT, ParametroSistema.obtener_parametro("imagen_pie", "pie_pagina.png"))}'
        # Definimos el tamaño de la imagen a cargar y las coordenadas correspondientes
        self.pdf.drawImage(archivo_imagen, 0, 15 - self.diferencia_hoja, 600, 30, preserveAspectRatio=True)

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
    """
    Reporte PDF de los hallazgos.

    Este reporte existio para el boton "Imprimir" del Tablero, que desaparecio
    con el rediseño de la pantalla de hallazgos. Vuelve, con tres cosas
    arregladas:

    - No revienta cuando no hay empresa ni area filtradas: el resumen por
      estado sale de los propios hallazgos del reporte y no de una consulta que
      necesita cliente y area.
    - No escribe archivos en el servidor: antes guardaba "grafico_torta.png" en
      el directorio de trabajo en cada pedido.
    - El archivo se llama con la empresa y la fecha, para reconocerlo en el
      celular cuando se lo manda por WhatsApp al encargado.
    - El resumen por estado cuenta todos los estados del recorte (empresa,
      area, busqueda), no solo los que quedaron en la lista por los chips de
      estado. Si no, al filtrar por "Incumplido" y "Gestion en Curso" los
      porcentajes sumaban 100% y los cumplidos desaparecian.

    La cabecera lo pone la clase base y ya trae el sello "Impreso dd/mm/aaaa
    hh:mm:ss": es lo que zanja eldiskusion de "pero si te lo mande hace 15
    dias, sigue apareciendo como incumplido".
    """

    # Columnas del reporte. Los anchos estan en puntos de una hoja carta (612
    # de ancho): el hallazgo se parte en 45 caracteres para no pisar la columna
    # del responsable.
    COLUMNAS = {
        "Fecha": 10,
        "Vence": 55,
        "Estado": 115,
        "Hallazgo": 195,
        "Responsable": 430,
    }
    # El color de cada estado, del mismo sistema visual del portal.
    COLOR_ESTADO = {
        "Cumplido": "#287044",
        "Gestión en Curso": "#805b12",
        "Incumplido": "#a33e36",
    }
    COLOR_OTRO = "#667363"

    def __init__(self, archivo=None):
        super().__init__()
        if archivo:
            self.archivo = archivo

    def nombre_archivo(self, cliente=None, empresas=1):
        """Un nombre que se entienda en el celular: empresa y fecha."""
        partes = ["hallazgos"]
        if empresas > 1:
            # El reporte es de varias empresas: poner el nombre de la primera
            # seria mentir en la etiqueta del archivo.
            partes.append(f"{empresas}-empresas")
        elif cliente:
            limpio = re.sub(r"[^A-Za-z0-9]+", "-", str(cliente)).strip("-").lower()
            if limpio:
                partes.append(limpio[:40])
        partes.append(datetime.datetime.now().strftime("%Y%m%d"))
        return "-".join(partes) + ".pdf"

    def imprime_hallazgo(self, queryset, filtro_cliente=None, filtro_area=None, resumen=None):
        hallazgos = list(queryset)
        # Lo que va a la tabla resumen. Puede traer estados que la lista no
        # muestra (los chips de estado solo recortan la lista). Si no llega,
        # se usa la misma lista para no cambiar el comportamiento del admin.
        hallazgos_resumen = list(resumen) if resumen is not None else hallazgos

        # La empresa y el area salen de los hallazgos del reporte. Antes se
        # tomaban de los parametros del filtro, y si no habia filtro no habia
        # ni titulo: el reporte reventaba al hacer el resumen.
        cliente = filtro_cliente
        area = filtro_area
        if hallazgos:
            cliente = cliente or hallazgos[0].cliente
            area = area or hallazgos[0].area

        if cliente and area:
            titulo = f"Hallazgos de {cliente} - {area}"
        elif cliente:
            titulo = f"Hallazgos de {cliente}"
        elif area:
            titulo = f"Hallazgos de {area}"
        else:
            titulo = "Hallazgos"

        self.titulo = titulo
        empresas = len({movimiento.cliente_id for movimiento in hallazgos})
        self.archivo = self.nombre_archivo(cliente, empresas)
        width, height = letter
        self.inicia()
        self.ubicacion = dict(self.COLUMNAS)
        self.cabecera()

        for movimiento in hallazgos:
            lineas = dividir_texto(movimiento.hallazgo or "", 45)
            self.fila -= 10
            # El alto que se pide es el de la fila completa: un hallazgo largo
            # no puede quedar partido entre dos paginas.
            self.check_break_page(alto=10 * len(lineas) + 20)
            self.pdf.setFont(self.nombre_fuente, 8)
            fila = self.fila
            self.pdf.drawString(
                x=self.ubicacion["Fecha"],
                y=fila,
                text=FormatoFecha(movimiento.fecha, formato="dma"),
            )
            self.pdf.drawString(
                x=self.ubicacion["Vence"],
                y=fila,
                text=(
                    FormatoFecha(movimiento.fecha_cumplimiento, formato="dma")
                    if movimiento.fecha_cumplimiento
                    else "-"
                ),
            )
            self.pdf.drawString(
                x=self.ubicacion["Estado"], y=fila, text=str(movimiento.estado or "")
            )
            for numero, linea in enumerate(lineas):
                self.pdf.drawString(
                    x=self.ubicacion["Hallazgo"], y=fila - 10 * numero, text=linea
                )
            if movimiento.responsable:
                self.pdf.drawString(
                    x=self.ubicacion["Responsable"], y=fila, text=movimiento.responsable
                )
            self.fila = fila - 10 * len(lineas)

        # Que hay y en que estado. La lista respeta los chips de estado, pero
        # el resumen cuenta todo el recorte: si no, los porcentajes sumarian
        # 100% entre los estados elegidos y ocultarian los cumplidos.
        self.fila -= 30
        self.check_break_page(alto=220)
        self.pdf.setFont(self.nombre_fuente, 10)
        self.pdf.drawString(
            x=10, y=self.fila, text=f"Total de hallazgos: {len(hallazgos_resumen)}"
        )
        if len(hallazgos_resumen) != len(hallazgos):
            self.fila -= 12
            self.pdf.setFont(self.nombre_fuente, 8)
            self.pdf.drawString(
                x=10,
                y=self.fila,
                text=f"La lista muestra {len(hallazgos)} por el filtro de estado.",
            )
            self.pdf.setFont(self.nombre_fuente, 10)
        self.fila -= 20
        self.resumen_por_estado(hallazgos_resumen)

        self.finaliza()
        return self.response

    def resumen_por_estado(self, hallazgos):
        """Tabla con cuantos hallazgos hay de cada estado."""
        conteo = {}
        for movimiento in hallazgos:
            estado = str(movimiento.estado or "Sin estado")
            conteo[estado] = conteo.get(estado, 0) + 1
        total = sum(conteo.values()) or 1

        data = [["Estado", "Hallazgos", "Porcentaje"]]
        estilos = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c4a1d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e2d4")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for numero, (estado, cantidad) in enumerate(
            sorted(conteo.items(), key=lambda par: -par[1])
        ):
            color = self.COLOR_ESTADO.get(estado, self.COLOR_OTRO)
            data.append(
                [
                    Paragraph(
                        f'<font color="{color}">&#9608;</font> {estado}',
                        getSampleStyleSheet()["BodyText"],
                    ),
                    str(cantidad),
                    f"{(cantidad / total) * 100:.1f}%",
                ]
            )
            estilos.append(
                ("BACKGROUND", (0, numero + 1), (-1, numero + 1), colors.HexColor("#f7f9f5"))
            )

        tabla = Table(data, colWidths=[240, 80, 80])
        tabla.setStyle(TableStyle(estilos))
        _, alto = tabla.wrapOn(self.pdf, 612, 792)
        tabla.drawOn(self.pdf, 30, self.fila - 10 - alto)
        self.fila -= 10 + alto


class ResumenMensual(Impresiones):
    
    def __init__(self, cliente_id):
        self.cliente_id = cliente_id
        self.archivo = "resumen_mensual.pdf"
        # self.generar_pdf()

    def generar_pdf(self, task=None):
        cliente = Cliente.objects.get(id=self.cliente_id)
        titulo = f'Resumen Mensual de {cliente.nombre}'

        print(f'Generando resumen mensual para {cliente.nombre}')
        self.titulo = titulo
        self.inicia()
        # Crear el PDF
        self.cabecera()
        self.generar_grafico()
        
        self.fila -= 350
        self.check_break_page()
        plazo_promedio_clientes, promedio_general = Movimientos.plazo_promedio(cliente)
        self.pdf.drawString(15, self.fila, 'Plazo promedio por cliente en dias')
        data_plazo = [['General', 'Plazo']]
        data_plazo.append(['Promedio general', round(promedio_general, 2)])

        tabla_plazo = Table(data_plazo, colWidths=[300, 100])
        tabla_plazo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        width, height = letter
        tabla_plazo.wrapOn(self.pdf, width, height)
        tabla_plazo.drawOn(self.pdf, 30, self.fila - 80)

        self.fila -= 100
        self.check_break_page()
        #datos de accidentabilidad
        datos = IndiceAccidentabilidad.calcular_indices(cliente=self.cliente_id)
        self.pdf.drawString(15, self.fila, 'Indice de sinestrialidad')
        data = [['Indice', 'Valor']]
        # Recorrer e imprimir los datos y el índice 
        for indice, valor in datos.items():
            data.append([indice.replace('_', ' ').upper(), round(valor, 2)])

        tabla = Table(data, colWidths=[300, 100])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        self.fila -= 10
        width, height = letter
        tabla.wrapOn(self.pdf, width, height)
        tabla.drawOn(self.pdf, 30, self.fila - 100)
        self.check_break_page(alto=400)
        #fin datos de accidentabilidad

        queryset = Movimientos.objects.all()
        queryset = queryset.filter(cliente=self.cliente_id, estado__in=['Gestion en curso', 'Incumplido'])
        queryset = queryset.order_by('-fecha', 'area__detalle')
        
        self.check_break_page()
        self.ubicacion = {
            'Fecha': 10,
            'Area': 65,
            'Hallazgo': 130,
            'Estado': 500
        }
        # Crear el PDF
        self.cabecera()
        data = [['Fecha', 'Periodo', 'Estado', 'Hallazgo']]
        avance = 0
        for movimiento in queryset:
            avance += 1
            if task is not None:
                task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': avance,
                        'total': len(queryset),
                        'message': 'Procesando movimientos...'
                    }
                )
            self.fila -=10
            self.check_break_page()
            self.pdf.drawString(x=self.ubicacion['Fecha'], y=self.fila, text=FormatoFecha(movimiento.fecha, formato='dma'))
            self.pdf.drawString(x=self.ubicacion['Estado'], y=self.fila, text=str(movimiento.estado))
            fila_ant = self.fila

            lineas = dividir_texto(movimiento.area.detalle, 12)
            for linea in lineas:
                self.pdf.drawString(x=self.ubicacion['Area'], y=self.fila, text=linea)
                self.fila -= 10

            self.fila = fila_ant
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

        self.finaliza(grabar=True)
        return self.archivo

    def generar_grafico(self):
        # Obtener los datos de la tabla
        url_grafico = Movimientos.obtener_url_grafico(self.cliente_id)

        self.pdf.drawImage(url_grafico, 0, self.fila - 300, width=250, height=250)

        url_grafico = EmisionCarbono.generar_grafico_emisiones(self.cliente_id)
        self.pdf.drawImage(url_grafico, 300, self.fila - 300, width=250, height=250)

        self.fila -= 300
        
        url_grafico = ExcesosVelocidad.genera_grafico_excesos(self.cliente_id)
        self.pdf.drawImage(url_grafico, 0, self.fila - 300, width=250, height=250)

        url_grafico = Movimientos.obtener_grafico_cumplidos_por_area(self.cliente_id)
        self.pdf.drawImage(url_grafico, 300, self.fila - 300, width=250, height=250)


class GeneradorInformePDF:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.elements = []
    
    def generar_informe(self, cliente, area=None):
        try:
            # Crear buffer para el PDF
            buffer = io.BytesIO()
            
            # Configurar el documento
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Añadir título
            titulo = f"Informe de Tareas - {cliente}"
            if area:
                titulo += f" - {area}"
            self.elements.append(Paragraph(titulo, self.styles['Title']))
            self.elements.append(Spacer(1, 30))
            
            # Generar y añadir el gráfico
            generator = GraficoTorta()
            datos = Movimientos.obtener_datos_tareas(cliente, area)
            imagen_grafico = generator.generar_grafico_torta(datos, cliente, area, formato='reportlab')
            
            # Añadir el gráfico al PDF
            img = Image(imagen_grafico)
            img.drawHeight = 5*inch
            img.drawWidth = 6*inch
            self.elements.append(img)
            self.elements.append(Spacer(1, 20))
            
            # Añadir tabla de resumen
            tabla_datos = self._generar_tabla_resumen(datos)
            self.elements.append(tabla_datos)
            
            # Construir el documento
            doc.build(self.elements)
            
            # Preparar el PDF para retorno
            pdf = buffer.getvalue()
            buffer.close()
            
            return pdf
        except Exception as e:
            logger.error(f"Error generando informe: {str(e)}")
            raise
            
    def _generar_tabla_resumen(self, datos):
        """Genera una tabla de resumen con los datos"""
        # Encabezados de la tabla
        tabla_data = [['Estado', 'Cantidad', 'Porcentaje']]
        
        # Calcular total
        total = sum(item['cantidad'] for item in datos)
        
        # Añadir filas
        for item in datos:
            porcentaje = (item['cantidad'] / total * 100) if total > 0 else 0
            tabla_data.append([
                item['estado'],
                str(item['cantidad']),
                f'{porcentaje:.1f}%'
            ])
            
        # Crear y estilizar la tabla
        tabla = Table(tabla_data, colWidths=[200, 100, 100])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return tabla
