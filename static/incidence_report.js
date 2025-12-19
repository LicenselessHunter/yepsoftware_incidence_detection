//Función que se ejecutará al hacer click en cualquier lugar de la ventana
window.addEventListener('click', function(event) {

    //Si es que se hace click en el botón para ver los productos no scrapeables
    if (event.target.matches('#not_scrapeable_products_btn')) {
        modal = document.getElementById("not-scrapeable-products-modal");
        modal.style.display = "block";
    }

    //Si es que se hace click en el botón para ver los productos que no existen en la base de datos local
    else if (event.target.matches('#not_existing_products_in_local_btn')) {
        modal = document.getElementById("not-existing-products-in-local-modal");
        modal.style.display = "block";
    }

    //Si es que se hace click fuera del contenido del modal de productos no scrapeables
    else if (event.target.matches('#not-scrapeable-products-modal')) {
        event.target.style.display = "none";
    }
    
    //Si es que se hace click fuera del contenido del modal de productos que no existen en la base de datos local
    else if (event.target.matches('#not-existing-products-in-local-modal')) {
        event.target.style.display = "none";
    }
});
