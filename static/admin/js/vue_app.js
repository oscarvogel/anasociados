document.addEventListener('DOMContentLoaded', function () {
    new Vue({
        el: '#excesosvelocidad_form',
        delimiters: ['[[', ']]'],
        data: {
            cliente: jQuery('#id_cliente').val(),
            area: jQuery('#id_area').val(),
            anio: jQuery('#id_anio').val(),
            mes: jQuery('#id_mes').val(),
            excesos: django.jQuery('#id_excesos').val(),

            years: Array.from({ length: 32 }, (v, k) => k + 2000),  // Genera los años desde 2000 hasta 2031
            months: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
            areas: [],
            selectedCliente: '', // Cliente seleccionado
        },
        methods: {
            fetchAreas() {
                console.log("ingresando a fetchAreas - Cliente seleccionado " + this.selectedCliente);
                if (!this.selectedCliente) {
                    this.areas = [];
                    this.area = null;  // Asignar el area a null
                    return;
                }
                // if (!this.cliente) {
                //     this.areas = [];
                //     this.area = null;
                //     return;
                // }
                const url = '/syh/obtener-areas-vue/?cliente=' + this.selectedCliente;
                console.log('Fetching areas for cliente:', this.selectedCliente);  // Verificar si esta función se llama
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        this.areas = data;
                        console.log(data);
                        if (!this.areas.some(area => area.id === this.area)) {
                            this.area = null;
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching areas:', error);
                    });
            }
        },
        watch: {
            cliente(newVal, oldVal) {
                console.log('Cliente changed from', oldVal, 'to', newVal);  // Verificar si detecta el cambio de cliente
                this.fetchAreas();
            }
        },
    });
});
