/* AN & Asociados — autocomplete para <select>
 *
 * Deja el <select> nativo en el DOM (oculto) y dibuja encima un input con
 * filtro. Al elegir se dispara un 'change' nativo sobre el select, así que el
 * código que ya existe —que lee .value o escucha 'change'— sigue funcionando
 * sin tocar una línea.
 *
 * Los combos que se llenan por AJAX (innerHTML) se re-sincronizan solos con un
 * MutationObserver, y los que tienen pocas opciones nunca se convierten: para
 * elegir entre tres meses el select nativo es más rápido que un buscador.
 */
(function () {
    'use strict';

    var MIN_OPCIONES = 6;
    var ALTO_MAXIMO = 260;
    var contador = 0;

    function normalizar(valor) {
        return (valor || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();
    }

    function textoOpcion(opcion) {
        return (opcion.textContent || '').replace(/\s+/g, ' ').trim();
    }

    function opcionesUtilizables(select) {
        return Array.prototype.slice.call(select.options).filter(function (opcion) {
            return !opcion.disabled;
        });
    }

    function umbral(select) {
        var crudo = select.getAttribute('data-an-min-opciones');
        var numero = parseInt(crudo, 10);
        return isNaN(numero) || numero < 0 ? MIN_OPCIONES : numero;
    }

    function mereceAutocomplete(select) {
        if (select.multiple) return false;
        if (select.hasAttribute('data-an-no-autocomplete')) return false;
        if (select.getAttribute('data-an-autocomplete') === 'no') return false;
        if (select.getAttribute('data-an-autocomplete') === 'si') return true;
        return opcionesUtilizables(select).length >= umbral(select);
    }

    /* normalize() borra los acentos y eso mueve los índices, así que no se
       puede buscar con indexOf sobre el texto normalizado. Se recorre carácter
       a carácter guardando la correspondencia y se devuelve el rango real. */
    function rangoReal(texto, consulta) {
        var mapa = [];
        var plano = '';
        for (var i = 0; i < texto.length; i += 1) {
            var base = texto[i].normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
            for (var j = 0; j < base.length; j += 1) {
                mapa.push(i);
                plano += base[j];
            }
        }
        var desde = plano.indexOf(consulta);
        if (desde === -1) return null;
        return { inicio: mapa[desde], fin: mapa[desde + consulta.length - 1] + 1 };
    }

    function resaltar(texto, consulta) {
        var rango = consulta ? rangoReal(texto, consulta) : null;
        if (!rango) return document.createTextNode(texto);
        var fragmento = document.createDocumentFragment();
        fragmento.appendChild(document.createTextNode(texto.slice(0, rango.inicio)));
        var marca = document.createElement('mark');
        marca.textContent = texto.slice(rango.inicio, rango.fin);
        fragmento.appendChild(marca);
        fragmento.appendChild(document.createTextNode(texto.slice(rango.fin)));
        return fragmento;
    }

    /* Los <label for="..."> apuntan al select, que queda oculto: hay que
       reapuntarlos al input o el click en la etiqueta deja de enfocar nada.
       Las etiquetas que envuelven al select no necesitan nada, porque el input
       queda dentro de ellas. */
    function reapuntarEtiqueta(select, idInput) {
        if (!select.id) return;
        var etiquetas = document.querySelectorAll('label[for]');
        for (var i = 0; i < etiquetas.length; i += 1) {
            if (etiquetas[i].getAttribute('for') === select.id) {
                etiquetas[i].setAttribute('for', idInput);
            }
        }
    }

    function crear(select) {
        if (select.multiple || select.dataset.anCombo) return null;

        contador += 1;
        var idBase = select.id || 'an-combo-' + contador;
        var idInput = idBase + '-autocomplete';
        var idLista = idBase + '-autocomplete-lista';

        var wrapper = document.createElement('div');
        wrapper.className = 'an-combo';

        var input = document.createElement('input');
        input.type = 'text';
        input.id = idInput;
        input.className = 'an-combo__input form-control an-field';
        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-expanded', 'false');
        input.setAttribute('aria-controls', idLista);
        input.setAttribute('autocomplete', 'off');
        input.setAttribute('aria-haspopup', 'listbox');

        var boton = document.createElement('button');
        boton.type = 'button';
        boton.tabIndex = -1;
        boton.className = 'an-combo__toggle';
        boton.setAttribute('aria-hidden', 'true');
        boton.innerHTML = '<span class="an-combo__chevron"></span>';

        var lista = document.createElement('ul');
        lista.id = idLista;
        lista.className = 'an-combo__list';
        lista.setAttribute('role', 'listbox');
        lista.hidden = true;

        var vacio = document.createElement('p');
        vacio.className = 'an-combo__vacio';
        vacio.hidden = true;

        wrapper.appendChild(input);
        wrapper.appendChild(boton);
        wrapper.appendChild(vacio);

        /* La lista vive en <body> y en position:fixed. Adentro del combo la
           recortaba cualquier ancestro con overflow:hidden —y .an-card lo tiene
           —, con lo cual una lista de 9 opciones se cortaba a la mitad. */
        document.body.appendChild(lista);

        select.parentNode.insertBefore(wrapper, select);
        select.classList.add('an-combo__nativo');
        select.setAttribute('tabindex', '-1');
        select.setAttribute('aria-hidden', 'true');
        reapuntarEtiqueta(select, idInput);

        var filtro = '';
        var editando = false;
        var indiceActivo = -1;
        var visibles = [];

        function placeholder() {
            var vacia = select.querySelector('option[value=""]');
            var configurado = select.getAttribute('data-an-placeholder');
            if (configurado) return configurado;
            return vacia ? textoOpcion(vacia) : 'Seleccioná una opción';
        }

        function seleccionada() {
            var indice = select.selectedIndex;
            if (indice < 0) return null;
            var opcion = select.options[indice];
            return opcion && opcion.value !== '' ? opcion : null;
        }

        function pintarValor() {
            var opcion = seleccionada();
            editando = false;
            if (opcion) {
                input.value = textoOpcion(opcion);
                input.setAttribute('aria-invalid', 'false');
            } else {
                input.value = '';
                select.value = '';
            }
            input.placeholder = placeholder();
        }

        function pintarEstado() {
            var activo = !select.disabled && opcionesUtilizables(select).length >= umbral(select);
            input.disabled = !activo;
            boton.disabled = !activo;
            wrapper.classList.toggle('an-combo--inactivo', !activo);
            if (!activo) cerrar();
        }

        function cerrar() {
            lista.hidden = true;
            wrapper.classList.remove('an-combo--abierto');
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
            indiceActivo = -1;
            visibles = [];
        }

        /* Se abre hacia abajo salvo que no entre: entonces sube. El alto se
           limita al espacio libre para que nunca tape el borde de la ventana. */
        function posicionar() {
            var caja = input.getBoundingClientRect();
            var espacioAbajo = window.innerHeight - caja.bottom - 16;
            var espacioArriba = caja.top - 16;
            var deseado = Math.min(ALTO_MAXIMO, lista.scrollHeight || ALTO_MAXIMO);
            var haciaArriba = espacioAbajo < Math.min(deseado, 150) && espacioArriba > espacioAbajo;

            lista.style.left = Math.round(caja.left) + 'px';
            lista.style.minWidth = Math.round(caja.width) + 'px';
            lista.style.maxHeight = Math.max(120, Math.min(ALTO_MAXIMO, haciaArriba ? espacioArriba : espacioAbajo)) + 'px';
            if (haciaArriba) {
                lista.style.top = 'auto';
                lista.style.bottom = Math.round(window.innerHeight - caja.top + 4) + 'px';
                lista.classList.add('an-combo__list--arriba');
            } else {
                lista.style.bottom = 'auto';
                lista.style.top = Math.round(caja.bottom + 4) + 'px';
                lista.classList.remove('an-combo__list--arriba');
            }
        }

        function marcarActivo() {
            var items = lista.children;
            for (var i = 0; i < items.length; i += 1) {
                var activo = i === indiceActivo;
                items[i].classList.toggle('an-combo__item--activo', activo);
                items[i].setAttribute('aria-selected', activo ? 'true' : 'false');
            }
            if (indiceActivo >= 0 && items[indiceActivo]) {
                input.setAttribute('aria-activedescendant', items[indiceActivo].id);
                items[indiceActivo].scrollIntoView({ block: 'nearest' });
            } else {
                input.removeAttribute('aria-activedescendant');
            }
        }

        function pintarLista() {
            var consulta = normalizar(filtro);
            var todas = opcionesUtilizables(select).map(function (opcion) {
                return { opcion: opcion, texto: textoOpcion(opcion), indice: opcion.index };
            });
            visibles = consulta
                ? todas.filter(function (item) { return normalizar(item.texto).indexOf(consulta) !== -1; })
                : todas;

            lista.innerHTML = '';
            var elegida = seleccionada();
            visibles.forEach(function (item, posicion) {
                var li = document.createElement('li');
                li.id = idLista + '-' + posicion;
                li.className = 'an-combo__item';
                li.setAttribute('role', 'option');
                li.setAttribute('data-indice', String(item.indice));
                if (elegida && elegida.index === item.indice) li.classList.add('an-combo__item--elegido');
                // Se copia la clase del <option> para no perder los estados que
                // las páginas pintan desde el template (ej. .opt-ya-enviada).
                if (item.opcion.className) li.className += ' ' + item.opcion.className;
                li.appendChild(resaltar(item.texto, consulta));
                lista.appendChild(li);
            });

            vacio.textContent = 'Sin resultados para "' + filtro.trim() + '"';
            vacio.hidden = visibles.length !== 0;

            // Con algo escrito se presume la mejor coincidencia: sin esto
            // Enter no elegiría nada hasta que el usuario apriete la flecha.
            indiceActivo = -1;
            if (visibles.length && consulta) {
                indiceActivo = 0;
            } else if (elegida) {
                indiceActivo = visibles.findIndex(function (item) { return item.indice === elegida.index; });
            }
            marcarActivo();
        }

        function abrir() {
            if (input.disabled) return;
            if (!editando) filtro = '';
            pintarLista();
            lista.hidden = false;
            posicionar();
            wrapper.classList.add('an-combo--abierto');
            input.setAttribute('aria-expanded', 'true');
        }

        function elegir(indice) {
            select.selectedIndex = indice;
            filtro = '';
            pintarValor();
            cerrar();
            select.dispatchEvent(new Event('change', { bubbles: true }));
        }

        function mover(paso) {
            if (lista.hidden) {
                abrir();
                indiceActivo = 0;
                marcarActivo();
                return;
            }
            if (!visibles.length) return;
            indiceActivo = (indiceActivo + paso + visibles.length) % visibles.length;
            marcarActivo();
        }

        function sincronizar() {
            pintarEstado();
            pintarValor();
            if (!lista.hidden) abrir();
        }

        input.addEventListener('focus', function () {
            if (!editando) filtro = '';
            abrir();
        });

        input.addEventListener('input', function () {
            editando = true;
            filtro = input.value;
            if (lista.hidden) abrir(); else pintarLista();
        });

        input.addEventListener('keydown', function (evento) {
            if (evento.key === 'ArrowDown') {
                evento.preventDefault();
                mover(1);
            } else if (evento.key === 'ArrowUp') {
                evento.preventDefault();
                mover(-1);
            } else if (evento.key === 'Enter') {
                if (!lista.hidden && visibles[indiceActivo]) {
                    evento.preventDefault();
                    elegir(visibles[indiceActivo].indice);
                }
            } else if (evento.key === 'Escape') {
                evento.preventDefault();
                cerrar();
                pintarValor();
            } else if (evento.key === 'Tab') {
                cerrar();
                pintarValor();
            }
        });

        // mousedown y no click: el blur del input cortaría el click.
        lista.addEventListener('mousedown', function (evento) {
            evento.preventDefault();
            var item = evento.target.closest('.an-combo__item');
            if (item) elegir(parseInt(item.getAttribute('data-indice'), 10));
        });

        boton.addEventListener('click', function () {
            if (lista.hidden) {
                abrir();
                input.focus();
            } else {
                cerrar();
                pintarValor();
            }
        });

        document.addEventListener('click', function (evento) {
            if (!wrapper.contains(evento.target) && !lista.contains(evento.target)) cerrar();
        });

        // La lista está en position:fixed: si la página se mueve, la lista se
        // va con el scroll. Se recoloca mientras esté abierta.
        window.addEventListener('scroll', function () {
            if (!lista.hidden) posicionar();
        }, true);
        window.addEventListener('resize', function () {
            if (!lista.hidden) posicionar();
        });

        var formulario = select.form;
        if (formulario) {
            formulario.addEventListener('reset', function () {
                window.setTimeout(sincronizar, 0);
            });
        }

        select.anCombo = {
            sincronizar: sincronizar,
            abrir: abrir,
            cerrar: cerrar
        };
        select.dataset.anCombo = '1';
        sincronizar();

        return select.anCombo;
    }

    function observar(select) {
        if (select.dataset.anObservado) return;
        select.dataset.anObservado = '1';

        var pendiente = null;
        new MutationObserver(function () {
            // Varias mutaciones llegan juntas: se agrupan en un solo repintado.
            window.clearTimeout(pendiente);
            pendiente = window.setTimeout(function () {
                if (select.anCombo) select.anCombo.sincronizar();
                else if (mereceAutocomplete(select)) crear(select);
            }, 0);
        }).observe(select, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['disabled', 'selected']
        });
    }

    function iniciar() {
        var selects = document.querySelectorAll('select');
        for (var i = 0; i < selects.length; i += 1) {
            observar(selects[i]);
            if (mereceAutocomplete(selects[i])) crear(selects[i]);
        }
    }

    window.ANAutocomplete = {
        refrescar: function (select) {
            if (select && select.anCombo) select.anCombo.sincronizar();
        },
        crear: crear,
        opcionesMinimas: MIN_OPCIONES
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();

