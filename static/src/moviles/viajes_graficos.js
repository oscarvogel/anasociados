const { createApp } = Vue;

createApp({
  data() {
    return {
      filters: {
        start_date: '',
        end_date: '',
        movil: '',
        chofer: '',
        producto: ''
      },
      moviles: [],
      personals: [],
      loading: false,
      stats: null,
      lastData: null,
      evolucionChart: null,
      tortaChart: null,
      tortaSinActividadChart: null
      ,
      showVerification: false,
      verificationRows: []
    };
  },
  
  mounted() {
    this.loadMoviles();
    this.loadPersonals();
    this.setDefaultDates();
    this.loadGraficos();
  },
  
  methods: {
    setDefaultDates() {
      // Establecer fecha de fin como hoy
      const today = new Date();
      this.filters.end_date = today.toISOString().split('T')[0];
      
      // Establecer fecha de inicio como hace 30 días
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 30);
      this.filters.start_date = startDate.toISOString().split('T')[0];
    },
    
    async loadMoviles() {
      try {
        const resp = await fetch('/moviles/api/movil/');
        const data = await resp.json();
        this.moviles = data.results || data;
      } catch (error) {
        console.error('Error cargando móviles:', error);
      }
    },

    formatNumber(val) {
      if (val === null || val === undefined) return '-';
      try {
        return Number(val).toLocaleString('es-AR');
      } catch (e) {
        return val;
      }
    },

    formatKg(val) {
      if (val === null || val === undefined) return '-';
      try {
        return Number(val).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' kg';
      } catch (e) {
        return val;
      }
    },
    
    async loadPersonals() {
      try {
        const resp = await fetch('/moviles/api/personal/');
        const data = await resp.json();
        this.personals = data.results || data;
      } catch (error) {
        console.error('Error cargando personal:', error);
      }
    },
    
    async loadGraficos() {
      this.loading = true;
      
      // Agregar clase loading a los KPI cards
      document.querySelectorAll('.kpi-card').forEach(card => {
        card.classList.add('loading');
      });
      
      try {
        // Construir query params
        const params = new URLSearchParams();
        if (this.filters.start_date) params.append('start_date', this.filters.start_date);
        if (this.filters.end_date) params.append('end_date', this.filters.end_date);
        if (this.filters.movil) params.append('movil', this.filters.movil);
        if (this.filters.chofer) params.append('chofer', this.filters.chofer);
        if (this.filters.producto) params.append('producto', this.filters.producto);
        
        const resp = await fetch(`/moviles/api/viajes/graficos-data/?${params.toString()}`);
        const data = await resp.json();
        
        // Guardar datos para uso posterior
  this.lastData = data;
  // También exponer globalmente para callbacks de tooltip que no capturan el contexto Vue
  try { window.lastDataGlobal = data; } catch (e) {}
  // Poblar tabla de verificación si viene en la respuesta
  this.verificationRows = data.verification_rows || [];
        
        // Actualizar estadísticas
        const totalKg = data.proporcion_productos.reduce((sum, p) => sum + p.kg, 0);
        this.stats = {
          total_dias: data.evolucion_diaria.length,
          total_kg: totalKg.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        };
        
        console.log('Datos recibidos:', data);
        console.log('evolucion_diaria length:', data.evolucion_diaria.length);
        console.log('proporcion_productos length:', data.proporcion_productos.length);
        
        // Animar valores KPI al actualizarse
        setTimeout(() => {
          document.querySelectorAll('.kpi-value').forEach(el => {
            el.classList.add('updating');
            setTimeout(() => el.classList.remove('updating'), 600);
          });
        }, 100);
        
      } catch (error) {
        console.error('Error cargando datos de gráficos:', error);
        alert('Error al cargar los datos. Por favor, intente nuevamente.');
      } finally {
        this.loading = false;
        
        // Quitar clase loading de los KPI cards
        setTimeout(() => {
          document.querySelectorAll('.kpi-card').forEach(card => {
            card.classList.remove('loading');
          });
        }, 100);
        
        // Pequeño delay para asegurar que el DOM está actualizado
        setTimeout(() => {
          // Renderizar gráficos después de que loading=false actualice el DOM
          this.renderEvolucionChart(this.lastData?.evolucion_diaria || []);
          this.renderTortaChart(this.lastData?.proporcion_productos || []);
          this.renderTortaSinActividad(this.lastData?.dias_sin_actividad || []);
        }, 50);
      }
    },
    
    renderEvolucionChart(data) {
      const ctx = document.getElementById('evolucionChart');
      console.log('renderEvolucionChart - ctx:', ctx);
      console.log('renderEvolucionChart - data:', data);
      
      if (!ctx) {
        console.error('Canvas evolucionChart no encontrado!');
        return;
      }
      
      if (!data || data.length === 0) {
        console.warn('No hay datos para evolucionChart');
        return;
      }
      
      // Destruir gráfico anterior si existe
      if (this.evolucionChart) {
        this.evolucionChart.destroy();
      }
      
      // Preparar datos para el gráfico de línea
      const labels = data.map(d => {
        const fecha = new Date(d.fecha + 'T00:00:00');
        return fecha.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' });
      });
      
      const datasets = [];
      
      // Nota: no graficar el dataset 'Total KG' según lo solicitado
      
      // Si hay filtro de producto, mostrar solo ese tipo
      if (this.filters.producto) {
        const colores = {
          'Pulpable': { border: 'rgb(23, 162, 184)', bg: 'rgba(23, 162, 184, 0.1)' },
          'Aserrable': { border: 'rgb(40, 167, 69)', bg: 'rgba(40, 167, 69, 0.1)' },
          'Chip': { border: 'rgb(255, 193, 7)', bg: 'rgba(255, 193, 7, 0.1)' }
        };
        
        const color = colores[this.filters.producto] || { border: 'rgb(108, 117, 125)', bg: 'rgba(108, 117, 125, 0.1)' };
        
        datasets.push({
          label: this.filters.producto,
          data: data.map(d => d.total_kg),
          borderColor: color.border,
          backgroundColor: color.bg,
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointRadius: 4,
          pointHoverRadius: 6
        });
      } else {
        // Si no hay filtro de producto, mostrar desglose de todos
        datasets.push({
          label: 'Pulpable',
          data: data.map(d => d.pulpable),
          borderColor: 'rgb(23, 162, 184)',
          backgroundColor: 'rgba(23, 162, 184, 0.1)',
          borderWidth: 2,
          tension: 0.4,
          fill: false,
          pointRadius: 3,
          pointHoverRadius: 5
        });
        
        datasets.push({
          label: 'Aserrable',
          data: data.map(d => d.aserrable),
          borderColor: 'rgb(40, 167, 69)',
          backgroundColor: 'rgba(40, 167, 69, 0.1)',
          borderWidth: 2,
          tension: 0.4,
          fill: false,
          pointRadius: 3,
          pointHoverRadius: 5
        });
        
        datasets.push({
          label: 'Chip',
          data: data.map(d => d.chip),
          borderColor: 'rgb(255, 193, 7)',
          backgroundColor: 'rgba(255, 193, 7, 0.1)',
          borderWidth: 2,
          tension: 0.4,
          fill: false,
          pointRadius: 3,
          pointHoverRadius: 5
        });
      }
      
      this.evolucionChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            title: {
              display: false
            },
            legend: {
              display: true,
              position: 'top',
              labels: {
                usePointStyle: true,
                padding: 15,
                font: {
                  size: 12,
                  weight: '600'
                }
              }
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              titleColor: '#fff',
              bodyColor: '#fff',
              borderColor: 'rgba(102, 126, 234, 0.5)',
              borderWidth: 1,
              padding: 12,
              displayColors: true,
              callbacks: {
                label: function(context) {
                  let label = context.dataset.label || '';
                  if (label) {
                    label += ': ';
                  }
                  label += context.parsed.y.toLocaleString('es-AR', { 
                    minimumFractionDigits: 2, 
                    maximumFractionDigits: 2 
                  }) + ' kg';
                  return label;
                }
              }
            }
          },
          scales: {
            x: {
              grid: {
                display: false
              },
              ticks: {
                font: {
                  size: 11
                }
              }
            },
            y: {
              beginAtZero: true,
              grid: {
                color: 'rgba(0, 0, 0, 0.05)'
              },
              ticks: {
                font: {
                  size: 11
                },
                callback: function(value) {
                  return value.toLocaleString('es-AR') + ' kg';
                }
              }
            }
          },
          interaction: {
            mode: 'index',
            intersect: false
          }
        }
      });
    },
    
    renderTortaChart(data) {
      const ctx = document.getElementById('tortaChart');
      console.log('renderTortaChart - ctx:', ctx);
      console.log('renderTortaChart - data:', data);
      
      if (!ctx) {
        console.error('Canvas tortaChart no encontrado!');
        return;
      }
      
      // Destruir gráfico anterior si existe
      if (this.tortaChart) {
        this.tortaChart.destroy();
      }
      
      // Si no hay datos, mostrar mensaje
      if (!data || data.length === 0) {
        return;
      }
      
      // Colores personalizados para cada tipo de producto
      const colores = {
        'Pulpable': 'rgb(23, 162, 184)',
        'Aserrable': 'rgb(40, 167, 69)',
        'Chip': 'rgb(255, 193, 7)'
      };
      
      const backgroundColors = data.map(d => colores[d.producto] || 'rgb(108, 117, 125)');
      const borderColors = backgroundColors.map(c => c.replace('rgb', 'rgba').replace(')', ', 1)'));
      
      this.tortaChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: data.map(d => d.producto),
          datasets: [{
            label: 'KG',
            data: data.map(d => d.kg),
            backgroundColor: backgroundColors,
            borderColor: borderColors,
            borderWidth: 2,
            hoverOffset: 10
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'bottom',
              labels: {
                usePointStyle: true,
                padding: 15,
                font: {
                  size: 13,
                  weight: '600'
                }
              }
            },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              titleColor: '#fff',
              bodyColor: '#fff',
              borderColor: 'rgba(102, 126, 234, 0.5)',
              borderWidth: 1,
              padding: 12,
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const value = context.parsed;
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = ((value / total) * 100).toFixed(1);
                  
                  return [
                    label + ': ' + value.toLocaleString('es-AR', { 
                      minimumFractionDigits: 2, 
                      maximumFractionDigits: 2 
                    }) + ' kg',
                    '(' + percentage + '%)'
                  ];
                }
              }
            }
          }
        }
      });
    },

    renderTortaSinActividad(data) {
      const ctx = document.getElementById('tortaSinActividadChart');
      console.log('renderTortaSinActividad - ctx:', ctx);
      console.log('renderTortaSinActividad - data:', data);

      if (!ctx) {
        console.error('Canvas tortaSinActividadChart no encontrado!');
        return;
      }

      // Destruir gráfico anterior si existe
      if (this.tortaSinActividadChart) {
        this.tortaSinActividadChart.destroy();
      }

      // Si no hay datos, limpiar/ocultar
      if (!data || data.length === 0) {
        return;
      }

      // Para días sin actividad agrupamos por 'motivo'
      // Usar una paleta de colores genérica ya que los motivos son libres
      const palette = ['#17a2b8', '#28a745', '#ffc107', '#6f42c1', '#e83e8c', '#fd7e14', '#20c997', '#6610f2', '#6c757d'];

      // Para días sin actividad usamos 'dias' como valor (no kg)
      const labels = data.map(d => d.motivo || 'Sin motivo');
      const values = data.map(d => d.dias);
      const backgroundColors = labels.map((_, i) => palette[i % palette.length]);
      const borderColors = backgroundColors.map(c => c);

      this.tortaSinActividadChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            label: 'Días Sin Actividad',
            data: values,
            backgroundColor: backgroundColors,
            borderColor: borderColors,
            borderWidth: 2,
            hoverOffset: 10
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'bottom',
              labels: {
                usePointStyle: true,
                padding: 12,
                font: {
                  size: 12,
                  weight: '600'
                }
              }
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const idx = context.dataIndex;
                  const value = context.parsed;
                  // Intentar usar el porcentaje provisto por el backend (lastData)
                  let pct = null;
                  try {
                    const backend = window.lastDataGlobal || null;
                    if (backend && backend.dias_sin_actividad && backend.dias_sin_actividad[idx]) {
                      pct = backend.dias_sin_actividad[idx].porcentaje;
                    }
                  } catch (e) {
                    pct = null;
                  }
                  const percentage = pct != null ? String(pct.toFixed ? pct.toFixed(1) : pct) : ( (context.dataset.data.reduce((a, b) => a + b, 0) > 0) ? ((value / context.dataset.data.reduce((a, b) => a + b, 0) * 100).toFixed(1)) : '0.0');
                  return label + ': ' + value + ' días (' + percentage + '%)';
                }
              }
            }
          }
        }
      });
    },
    
    formatDate(dateStr) {
      if (!dateStr) return '';
      const d = new Date(dateStr + 'T00:00:00');
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const year = d.getFullYear();
      return `${day}-${month}-${year}`;
    }
  }
}).mount('#graficos-app');
