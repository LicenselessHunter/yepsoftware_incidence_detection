// Get the modal
const modal = document.getElementById("not-scrapeable-products-modal");

// Get the button that opens the modal
const btn = document.getElementById("not_scrapeable_products_btn");

// When the user clicks the button, open the modal 
btn.onclick = function() {
    modal.style.display = "block";
}


// When the user clicks anywhere outside of the modal, close it
modal.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}