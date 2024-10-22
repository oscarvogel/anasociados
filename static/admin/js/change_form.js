'use strict';
{
    // Capturamos el formulario por su ID
    const form = document.querySelector('form');
    if (form) {
        // Obtenemos el nombre del formulario
        const formName = form.getAttribute('id');

        // Recorremos los elementos del formulario
        for (const element of form.elements) {
            if (element.type == 'date') {
                // Detectar el campo de fecha
                const value = element.value;
                console.log(element.value);
                const datePattern = /^(\d{2})-(\d{2})-(\d{4})$/;
                if (datePattern.test(value)) {
                    // Convertir el valor de dd-MM-yyyy a yyyy-MM-dd
                    const parts = value.match(datePattern);
                    const formattedDate = `${parts[3]}-${parts[2]}-${parts[1]}`;
                    element.value = formattedDate;
                }
            }
        }
    }
}
