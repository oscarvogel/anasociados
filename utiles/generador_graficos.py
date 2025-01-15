import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import threading
import logging
import io
import base64
from reportlab.lib.utils import ImageReader
from PIL import Image

logger = logging.getLogger(__name__)

class MatplotlibGraphGenerator:
    _instance_lock = threading.Lock()

    
    def __init__(self):
        self.fig = None
        self.ax = None

class GraficoTorta(MatplotlibGraphGenerator):
    
    ESTADOS_A_MOSTRAR = {
        'cumplido': 'Cumplido',
        'incumplido': 'Incumplido',
        'gestion en curso': 'Gestión en Curso'
    }
    
    COLORES = {
        'cumplido': '#99FF99',
        'incumplido': '#FF9999',
        'gestion en curso': '#66B2FF'
    }

    def __init__(self):
        super().__init__()

    def generar_grafico_torta(self, datos, cliente, area=None, formato='base64'):
        """
        Genera un gráfico de torta y lo devuelve en el formato especificado
        
        Args:
            datos: Lista de diccionarios con {'estado': str, 'cantidad': int}
            cliente: Nombre del cliente
            area: Área opcional
            formato: 'base64' o 'reportlab' o 'ambos'
            
        Returns:
            Dependiendo del formato:
            - 'base64': str con la imagen codificada en base64
            - 'reportlab': ImageReader object
            - 'ambos': tupla (base64_str, ImageReader)
        """
        with self._instance_lock:
            try:
                # Limpiar cualquier figura existente
                plt.clf()
                
                # Preparar los datos
                estados = []
                cantidades = []
                colores_grafico = []
                
                for item in datos:
                    estado_original = item['estado'].lower()
                    estado_mostrar = self.ESTADOS_A_MOSTRAR.get(estado_original, item['estado'])
                    estados.append(estado_mostrar)
                    cantidades.append(item['cantidad'])
                    colores_grafico.append(self.COLORES.get(estado_original, '#CCCCCC'))
                
                # Crear nueva figura
                self.fig = plt.figure(figsize=(10, 8))
                
                if not cantidades:
                    plt.text(0.5, 0.5, 'No hay datos disponibles',
                            horizontalalignment='center',
                            verticalalignment='center',
                            transform=plt.gca().transAxes)
                else:
                    patches, texts, autotexts = plt.pie(
                        cantidades,
                        labels=estados,
                        colors=colores_grafico,
                        autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100.*sum(cantidades)):d})',
                        startangle=90
                    )
                    
                    plt.setp(autotexts, size=9, weight="bold")
                    plt.setp(texts, size=9)
                
                titulo = f'Distribución de Tareas - {cliente}'
                if area:
                    titulo += f' - {area}'
                plt.title(titulo, pad=20, size=12, weight="bold")
                
                plt.axis('equal')
                
                # Guardar a buffer
                buffer = io.BytesIO()
                self.fig.savefig(buffer, 
                               format='png',
                               bbox_inches='tight',
                               dpi=300,
                               facecolor='white')
                buffer.seek(0)
                
                if formato == 'base64':
                    # Para web
                    image_png = buffer.getvalue()
                    graphic = base64.b64encode(image_png).decode('utf-8')
                    return graphic
                    
                elif formato == 'reportlab':
                    # Para ReportLab
                    img = Image.open(buffer)
                    return ImageReader(img)
                    
                elif formato == 'ambos':
                    # Devolver ambos formatos
                    image_png = buffer.getvalue()
                    graphic = base64.b64encode(image_png).decode('utf-8')
                    buffer.seek(0)
                    img = Image.open(buffer)
                    return graphic, ImageReader(img)
                    
            except Exception as e:
                logger.error(f"Error generando gráfico de torta: {str(e)}")
                plt.close('all')
                raise
                
            finally:
                if self.fig is not None:
                    plt.close(self.fig)
                if 'buffer' in locals():
                    buffer.close()

