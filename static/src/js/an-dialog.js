/* AN & Asociados — diálogos de confirmación y aviso
 *
 * Reemplaza a window.confirm() y window.alert(), que dibujan el chrome del
 * sistema operativo: un recuadro gris del Windows o del Android en medio de
 * una pagina con el diseno de AN rompe el conjunto. Y se usan desde el
 * celular, donde el dialogo nativo tapa el contenido y no se puede estilar.
 *
 *   ANDialog.confirm({titulo, mensaje, confirmar, cancelar, tono}) -> Promise<boolean>
 *   ANDialog.alert({titulo, mensaje, confirmar, tono})              -> Promise<boolean>
 *
 * `tono` es info (default), aviso, peligro o exito. El overlay va en
 * position:fixed sobre <body> porque las cards del proyecto tienen
 * overflow:hidden y lo recortarían.
 */
(function () {
    'use strict';

    var GLIFOS = {
        info: 'i',
        aviso: '!',
        peligro: '!',
        exito: '✓'
    };

    var capa = null;
    var piezas = {};

    function armar() {
        if (capa) return;

        capa = document.createElement('div');
        capa.className = 'an-dialog';
        capa.hidden = true;

        var tarjeta = document.createElement('div');
        tarjeta.className = 'an-dialog__tarjeta';
        tarjeta.setAttribute('role', 'alertdialog');
        tarjeta.setAttribute('aria-modal', 'true');

        piezas.icono = document.createElement('div');
        piezas.icono.className = 'an-dialog__icono';
        piezas.icono.setAttribute('aria-hidden', 'true');

        piezas.titulo = document.createElement('h2');
        piezas.titulo.className = 'an-dialog__titulo';

        piezas.texto = document.createElement('p');
        piezas.texto.className = 'an-dialog__texto';

        var acciones = document.createElement('div');
        acciones.className = 'an-dialog__acciones';

        piezas.no = document.createElement('button');
        piezas.no.type = 'button';
        piezas.no.className = 'an-btn an-btn--fantasma';

        piezas.si = document.createElement('button');
        piezas.si.type = 'button';
        piezas.si.className = 'an-btn an-btn--primario';

        acciones.append(piezas.no, piezas.si);
        tarjeta.append(piezas.icono, piezas.titulo, piezas.texto, acciones);
        capa.appendChild(tarjeta);
        document.body.appendChild(capa);

        if (!piezas.titulo.id) {
            piezas.titulo.id = 'an-dialog-titulo';
            tarjeta.setAttribute('aria-labelledby', piezas.titulo.id);
        }
    }

    function mostrar(opciones, conCancelar) {
        armar();

        var tono = opciones.tono || 'info';
        var focoPrevio = document.activeElement;

        piezas.icono.textContent = GLIFOS[tono] || GLIFOS.info;
        piezas.icono.className = 'an-dialog__icono an-dialog__icono--' + tono;
        piezas.titulo.textContent = opciones.titulo || '';
        piezas.texto.textContent = opciones.mensaje || '';
        piezas.si.textContent = opciones.confirmar || 'Aceptar';
        piezas.no.textContent = opciones.cancelar || 'Cancelar';
        piezas.no.hidden = !conCancelar;

        capa.hidden = false;
        piezas.si.focus();

        return new Promise(function (resolver) {
            function cerrar(valor) {
                capa.hidden = true;
                piezas.si.removeEventListener('click', aceptar);
                piezas.no.removeEventListener('click', cancelar);
                capa.removeEventListener('mousedown', fuera);
                document.removeEventListener('keydown', teclado);
                // Si el boton que abrio el dialogo ya no esta (por ejemplo la
                // tarjeta se borro al decidir), foco() es un no-op inofensivo.
                if (focoPrevio && typeof focoPrevio.focus === 'function') focoPrevio.focus();
                resolver(valor);
            }
            function aceptar() { cerrar(true); }
            function cancelar() { cerrar(false); }
            function fuera(evento) { if (evento.target === capa) cerrar(false); }
            function teclado(evento) {
                if (evento.key === 'Escape') { evento.preventDefault(); cerrar(false); }
            }

            piezas.si.addEventListener('click', aceptar);
            piezas.no.addEventListener('click', cancelar);
            capa.addEventListener('mousedown', fuera);
            document.addEventListener('keydown', teclado);
        });
    }

    window.ANDialog = {
        confirm: function (opciones) { return mostrar(opciones || {}, true); },
        alert: function (opciones) { return mostrar(opciones || {}, false); }
    };
})();
