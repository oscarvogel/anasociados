console.log('=== INICIANDO VIAJES.JS ===');

// Verificar que Vue está disponible
if (typeof Vue === 'undefined') {
  console.error('ERROR: Vue no está cargado!');
  alert('Error: Vue.js no se cargó correctamente');
} else {
  console.log('Vue detectado:', Vue);
}

const { createApp, ref, reactive, onMounted } = Vue;

console.log('Creando app Vue...');

const app = createApp({
  setup() {
    const viajes = ref([]);
    const moviles = ref([]);
    const predios = ref([]);
    const kpis = reactive({ total_viajes: 0, tn_pulpable: 0, tn_aserrable: 0, tn_chip: 0, tn_total: 0 });
  const filters = reactive({ start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0], end_date: new Date().toISOString().split('T')[0], movil: '', chofer: '', producto: '', destino: '' });
    const personals = ref([]);
    const efectividadCamiones = ref([]);
    const syncing = ref(false);
    const formVisible = ref(false);
    const form = reactive({ id: null, movil: null, cliente: null, area: null, fecha: '', origen: null, destino: '', producto: '', tn_pulpable: 0, tn_aserrable: 0, tn_chip: 0, sin_actividad: false, motivo_sin_actividad: '', observaciones: '', personal: null });
    const pagination = reactive({
      count: 0,
      next: null,
      previous: null,
      current: 1,
      total_pages: 0,
      start: 0,
      end: 0
    });

    const apiBase = '/moviles/api/viajes/';

    async function loadMoviles() {
      try {
        console.log('→ Cargando moviles...');
        const res = await fetch('/moviles/api/movil/');
        console.log('Respuesta moviles:', res.status, res.ok);
        if (!res.ok) throw new Error('movil API status ' + res.status);
        const data = await res.json();
        console.log('Data moviles recibida:', data);
        moviles.value = data.results || data;
        console.log('✓ Moviles cargados:', moviles.value.length);
      } catch (e) {
        console.error('✗ Error cargando moviles', e);
      }
    }
    
    async function loadPredios() {
      try {
        console.log('→ Cargando predios...');
        const res = await fetch('/moviles/api/predios/');
        console.log('Respuesta predios:', res.status, res.ok);
        if (!res.ok) throw new Error('predios API status ' + res.status);
        const data = await res.json();
        console.log('Data predios recibida:', data);
        predios.value = data.results || data;
        console.log('✓ Predios cargados:', predios.value.length);
      } catch (e) {
        console.error('✗ Error cargando predios', e);
      }
    }
    async function loadPersonals() {
      try {
        console.log('→ Cargando personals...');
        const res = await fetch('/moviles/api/personal/');
        if (!res.ok) throw new Error('personal API status ' + res.status);
        const data = await res.json();
        personals.value = data.results || data;
        console.log('✓ Personals cargados:', personals.value.length);
      } catch (e) {
        console.error('✗ Error cargando personals', e);
      }
    }
    async function loadViajes() {
      try {
        let url = apiBase + '?';
        if (filters.start_date) url += `start_date=${filters.start_date}&`;
        if (filters.end_date) url += `end_date=${filters.end_date}&`;
        if (filters.movil) url += `movil=${filters.movil}&`;
        if (filters.chofer) url += `chofer=${filters.chofer}&`;
        if (filters.producto) url += `producto=${filters.producto}&`;
        if (filters.destino) url += `destino=${filters.destino}&`;
        console.log('→ Cargando viajes desde:', url);
        const res = await fetch(url);
        console.log('Respuesta viajes:', res.status, res.ok);
        if (!res.ok) throw new Error('viajes API status ' + res.status);
        const data = await res.json();
        console.log('Data viajes completa:', data);
        // DRF pagina los resultados: {count, next, previous, results}
        viajes.value = data.results || data;
        
        // Actualizar info de paginación
        pagination.count = data.count || viajes.value.length;
        pagination.next = data.next;
        pagination.previous = data.previous;
        
        console.log('📄 Paginación RAW:', {
          count: pagination.count,
          next: pagination.next,
          previous: pagination.previous
        });
        
        // Calcular página actual y total de páginas
        const pageSize = viajes.value.length;
        pagination.total_pages = Math.ceil(pagination.count / pageSize);
        
        // Extraer número de página de la URL
        if (data.next) {
          const nextUrl = new URL(data.next);
          const nextPage = parseInt(nextUrl.searchParams.get('page') || '2');
          pagination.current = nextPage - 1;
        } else if (data.previous) {
          const prevUrl = new URL(data.previous);
          const prevPage = parseInt(prevUrl.searchParams.get('page') || '1');
          pagination.current = prevPage + 1;
        } else {
          pagination.current = 1;
        }
        
        // Calcular rango de registros mostrados
        pagination.start = pageSize > 0 ? ((pagination.current - 1) * pageSize) + 1 : 0;
        pagination.end = Math.min(pagination.start + pageSize - 1, pagination.count);
        
        console.log('✓ Viajes cargados:', viajes.value.length, 'registros');
        console.log('📊 Paginación FINAL:', {
          count: pagination.count,
          current: pagination.current,
          total_pages: pagination.total_pages,
          next: pagination.next ? '✅ SÍ' : '❌ NO',
          previous: pagination.previous ? '✅ SÍ' : '❌ NO',
          start: pagination.start,
          end: pagination.end
        });
        if (viajes.value.length > 0) {
          console.log('Primer viaje completo:', viajes.value[0].origen_nombre);
          console.log('TN del primer viaje:', {
            pulpable: viajes.value[0].tn_pulpable,
            aserrable: viajes.value[0].tn_aserrable,
            chip: viajes.value[0].tn_chip
          });
        }
        calcularEfectividadCamiones();
        await loadKpis();
      } catch (e) {
        console.error('✗ Error cargando viajes:', e);
      }
    }
    async function loadKpis() {
      try {
        let url = '/moviles/api/viajes/kpis/';
        const params = [];
        if (filters.start_date) params.push(`start_date=${filters.start_date}`);
        if (filters.end_date) params.push(`end_date=${filters.end_date}`);
        if (filters.movil) params.push(`movil=${filters.movil}`);
        if (filters.chofer) params.push(`chofer=${filters.chofer}`);
        if (filters.producto) params.push(`producto=${filters.producto}`);
        if (filters.destino) params.push(`destino=${filters.destino}`);
        if (params.length) url += '?' + params.join('&');
        console.log('→ Cargando KPIs desde:', url);
        const res = await fetch(url);
        console.log('Respuesta KPIs:', res.status, res.ok);
        if (!res.ok) throw new Error('kpis API status ' + res.status);
        const data = await res.json();
        console.log('✓ KPIs recibidos:', data);
        kpis.total_viajes = data.total_viajes || 0;
        kpis.tn_pulpable = parseFloat(data.tn_pulpable || 0).toFixed(2);
        kpis.tn_aserrable = parseFloat(data.tn_aserrable || 0).toFixed(2);
        kpis.tn_chip = parseFloat(data.tn_chip || 0).toFixed(2);
        kpis.tn_total = parseFloat(data.tn_total || 0).toFixed(2);
        console.log('KPIs actualizados en reactive:', kpis);
      } catch (e) {
        console.error('✗ Error cargando KPIs:', e);
      }
    }

    async function loadPage(url) {
      if (!url) return;
      try {
        console.log('→ Cargando página:', url);
        const res = await fetch(url);
        if (!res.ok) throw new Error('page API status ' + res.status);
        const data = await res.json();
        viajes.value = data.results || data;
        
        // Actualizar paginación
        pagination.count = data.count || viajes.value.length;
        pagination.next = data.next;
        pagination.previous = data.previous;
        
        const pageSize = viajes.value.length;
        pagination.total_pages = Math.ceil(pagination.count / pageSize);
        
        if (data.next) {
          const nextUrl = new URL(data.next);
          pagination.current = parseInt(nextUrl.searchParams.get('page') || '2') - 1;
        } else if (data.previous) {
          const prevUrl = new URL(data.previous);
          pagination.current = parseInt(prevUrl.searchParams.get('page') || '1') + 1;
        } else {
          pagination.current = 1;
        }
        
        pagination.start = pageSize > 0 ? ((pagination.current - 1) * pageSize) + 1 : 0;
        pagination.end = Math.min(pagination.start + pageSize - 1, pagination.count);
        
        console.log('✓ Página cargada:', pagination);
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } catch (e) {
        console.error('✗ Error cargando página:', e);
      }
    }

    function openForm(v) {
      if (v) {
        // editar: cargar todos los valores del viaje
        console.log('Abriendo formulario para editar:', v);
        form.id = v.id;
        form.movil = v.movil;
        form.cliente = v.cliente;
        form.area = v.area;
        form.fecha = v.fecha;
        form.origen = v.origen; // Este es el ID del predio
        form.destino = v.destino;
        form.producto = v.producto;
        form.tn_pulpable = v.tn_pulpable;
        form.tn_aserrable = v.tn_aserrable;
        form.tn_chip = v.tn_chip;
        form.sin_actividad = v.sin_actividad || false;
        form.motivo_sin_actividad = v.motivo_sin_actividad || '';
        form.observaciones = v.observaciones || '';
        form.personal = v.personal;
        console.log('Formulario cargado con:', form);
      } else {
        // nuevo: asignar valores por defecto
        console.log('Abriendo formulario para nuevo viaje');
        form.id = null;
        form.movil = null;
        form.cliente = null;
        form.area = null;
        form.fecha = new Date().toISOString().slice(0,10);
        form.origen = null;
        form.destino = '';
        form.producto = '';
        form.tn_pulpable = 0;
        form.tn_aserrable = 0;
        form.tn_chip = 0;
        form.sin_actividad = false;
        form.motivo_sin_actividad = '';
        form.observaciones = '';
        form.personal = null;
      }
      formVisible.value = true;
    }

    function getCookie(name) {
      const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
      return v ? decodeURIComponent(v[2]) : null;
    }

    async function saveViaje() {
      const payload = { ...form };
      const method = form.id ? 'PUT' : 'POST';
      const url = form.id ? apiBase + form.id + '/' : apiBase;
      try {
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken'), 'Accept': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.text();
          throw new Error(err || ('status ' + res.status));
        }
        formVisible.value = false;
        await loadViajes();
        if (window.Swal) Swal.fire('Guardado', 'Viaje guardado correctamente', 'success');
      } catch (e) {
        console.error('Error guardando viaje', e);
        if (window.Swal) Swal.fire('Error', e.message || 'Error guardando', 'error'); else alert('Error: ' + e.message);
      }
    }

    async function deleteViaje(v) {
      if (!confirm('Confirmar borrado')) return;
      try {
        const res = await fetch(apiBase + v.id + '/', { method: 'DELETE', headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Accept': 'application/json' } });
        if (!res.ok) throw new Error('status ' + res.status);
        await loadViajes();
        if (window.Swal) Swal.fire('Borrado', 'Viaje borrado', 'success');
      } catch (e) {
        console.error('Error borrando viaje', e);
        if (window.Swal) Swal.fire('Error', e.message || 'Error borrando', 'error'); else alert('Error borrando');
      }
    }

    // Función para contar días hábiles (lunes a viernes) entre dos fechas
    function contarDiasHabiles(startDate, endDate) {
      let count = 0;
      const start = new Date(startDate);
      const end = new Date(endDate);
      const current = new Date(start);
      
      while (current <= end) {
        const dayOfWeek = current.getDay();
        // 0 = domingo, 6 = sábado
        if (dayOfWeek !== 0 && dayOfWeek !== 6) {
          count++;
        }
        current.setDate(current.getDate() + 1);
      }
      return count;
    }

    // Función para formatear fechas a dd-mm-yyyy
    function formatDate(dateString) {
      if (!dateString) return '';
      const [year, month, day] = dateString.split('-');
      return `${day}-${month}-${year}`;
    }

    async function exportExcel() {
      try {
        const params = new URLSearchParams();
        if (filters.start_date) params.append('start_date', filters.start_date);
        if (filters.end_date) params.append('end_date', filters.end_date);
        if (filters.movil) params.append('movil', filters.movil);
        if (filters.chofer) params.append('chofer', filters.chofer);
        if (filters.producto) params.append('producto', filters.producto);
        if (filters.destino) params.append('destino', filters.destino);
        const url = '/moviles/api/viajes/export/?' + params.toString();
        console.log('→ Exportando viajes a Excel:', url);
        // Abrir en nueva pestaña para que el navegador gestione la descarga
        window.open(url, '_blank');
      } catch (e) {
        console.error('Error exportando a Excel', e);
        alert('Error exportando a Excel: ' + e.message);
      }
    }

    // Función para contar días hábiles (lunes a viernes) entre dos fechas
    function contarDiasHabiles(startDate, endDate) {
      let count = 0;
      const start = new Date(startDate);
      const end = new Date(endDate);
      const current = new Date(start);
      
      while (current <= end) {
        const dayOfWeek = current.getDay();
        // 0 = domingo, 6 = sábado
        if (dayOfWeek !== 0 && dayOfWeek !== 6) {
          count++;
        }
        current.setDate(current.getDate() + 1);
      }
      return count;
    }

    // Función para calcular efectividad por camión
    function calcularEfectividadCamiones() {
      const startDate = filters.start_date;
      const endDate = filters.end_date;
      const diasHabiles = contarDiasHabiles(startDate, endDate);
      
      // Obtener días totales en el mes actual
      const currentDate = new Date();
      const diasTotalesMes = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0).getDate();
      
      // Agrupar viajes por móvil
      const viajesPorMovil = {};
      viajes.value.forEach(viaje => {
        if (!viajesPorMovil[viaje.movil]) {
          viajesPorMovil[viaje.movil] = 0;
        }
        viajesPorMovil[viaje.movil]++;
      });
      
      // Filtrar móviles según si hay filtro de producto
      let movilesToShow = moviles.value;
      if (filters.producto) {
        // Si hay filtro de producto, mostrar solo camiones que transportaron ese producto
        const movilesConProducto = new Set(
          viajes.value
            .filter(v => v.producto === filters.producto)
            .map(v => v.movil)
        );
        movilesToShow = moviles.value.filter(m => movilesConProducto.has(m.id));
      }
      
      // Calcular efectividad para cada móvil filtrado
      const efectividad = movilesToShow.map(movil => {
        const viajesReales = viajesPorMovil[movil.id] || 0;
        const viajesEsperados = (movil.viajes_mes / diasTotalesMes) * diasHabiles;
        const efectividadPct = viajesEsperados > 0 ? (viajesReales / viajesEsperados) * 100 : 0;
        
        return {
          id: movil.id,
          patente: movil.patente,
          viajes_mes: movil.viajes_mes,
          dias_habiles: diasHabiles,
          viajes_esperados: viajesEsperados,
          viajes_reales: viajesReales,
          efectividad: efectividadPct
        };
      });
      
      efectividadCamiones.value = efectividad;
      console.log('Efectividad calculada:', efectividad);
    }

    // Función para obtener clase CSS según efectividad
    function getEfectividadClass(efectividad) {
      if (efectividad >= 90) return 'efectividad-verde';
      if (efectividad >= 70) return 'efectividad-amarillo';
      return 'efectividad-rojo';
    }

    // Función para formatear fechas a dd-mm-yyyy
    function formatDate(dateString) {
      if (!dateString) return '';
      const [year, month, day] = dateString.split('-');
      return `${day}-${month}-${year}`;
    }

    async function syncAirtable() {
      const result = await Swal.fire({
        title: '¿Sincronizar Airtable?',
        html: '<p>Esta acción realizará lo siguiente:</p>' +
              '<ul style="text-align: left; margin: 10px 20px;">' +
              '<li>Insertará/actualizará registros en MySQL</li>' +
              '<li>Eliminará los registros sincronizados de Airtable</li>' +
              '</ul>' +
              '<p><strong>¿Deseas continuar?</strong></p>',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sí, sincronizar',
        cancelButtonText: 'Cancelar'
      });

      if (!result.isConfirmed) {
        return;
      }

      syncing.value = true;
      try {
        const res = await fetch('/moviles/api/viajes/sync-airtable/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
          }
        });

        const data = await res.json();

        if (!res.ok || !data.success) {
          // Mostrar error detallado
          let errorMsg = data.error || 'Error en la sincronización';
          
          // Si hay traceback, mostrarlo en consola
          if (data.traceback) {
            console.error('Traceback completo:', data.traceback);
          }
          
          // Si el error tiene detalles adicionales
          if (data.error_type) {
            errorMsg = `${data.error_type}: ${errorMsg}`;
          }
          
          throw new Error(errorMsg);
        }

        // Mostrar output si existe
        if (data.output) {
          console.log('Output de sincronización:', data.output);
        }

        await Swal.fire({
          title: '¡Éxito!',
          html: `<p>Sincronización completada exitosamente</p>${data.warnings ? `<pre style="text-align: left; font-size: 0.8em; max-height: 200px; overflow-y: auto;">${data.warnings}</pre>` : ''}`,
          icon: 'success',
          confirmButtonText: 'OK'
        });

        // Recargar viajes después de sincronizar
        await loadViajes();
      } catch (e) {
        console.error('Error sincronizando Airtable:', e);
        await Swal.fire({
          title: 'Error de Sincronización',
          html: `<div style="text-align: left;">
                   <p><strong>Error:</strong> ${e.message}</p>
                   <p style="font-size: 0.9em; color: #666;">
                     Verifica que:
                     <ul>
                       <li>Las variables de entorno están configuradas (.env)</li>
                       <li>Las credenciales de Airtable son correctas</li>
                       <li>La conexión a MySQL está disponible</li>
                     </ul>
                   </p>
                   <p style="font-size: 0.85em; color: #999;">
                     Revisa la consola del navegador para más detalles.
                   </p>
                 </div>`,
          icon: 'error',
          confirmButtonText: 'OK',
          width: 600
        });
      } finally {
        syncing.value = false;
      }
    }

    onMounted(async () => {
      console.log('🚀 Vue montado! Iniciando carga de datos...');
      try {
        await loadMoviles();
        await loadPredios();
        await loadPersonals();
        await loadViajes();
        console.log('✅ Todas las cargas completadas');
      } catch (e) {
        console.error('❌ Error en onMounted:', e);
      }
    });

    return { viajes, moviles, predios, personals, kpis, filters, pagination, loadViajes, loadPage, formVisible, form, openForm, saveViaje, deleteViaje, formatDate, exportExcel, efectividadCamiones, getEfectividadClass, syncAirtable, syncing };
  }
});

console.log('Montando app en #viajes-app...');
try {
  app.mount('#viajes-app');
  console.log('✓ App Vue montada exitosamente');
} catch (e) {
  console.error('ERROR al montar Vue:', e);
  alert('Error al inicializar la aplicación: ' + e.message);
}