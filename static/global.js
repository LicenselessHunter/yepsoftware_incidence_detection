let dropbtn; /*Esta variable servira de manera global para referenciar al botón de activación del dropdown.

/*Esta función se activa al hacer click en cualquier lugar de la ventana*/
window.onclick = function(event) { 
  /*Si es que se clickea algún botón para activar el dropdown del sidebar*/
  if (event.target.matches('.dropbtn')) { 

    /*'event.target' va a ser el elemento exacto al que se hizo click.*/
    
    /*Si es que ya había un dropdown activado, este se cerrara, para evitar que se active más de un dropdown a la vez*/
    if (dropbtn){ 
      dropbtn.nextElementSibling.style.display = "none";
    } 
    
    dropbtn = event.target
    
    dropbtn.nextElementSibling.style.display = "block"; /*Se activa el dropdown*/
  }

  /*Si es que se hace click en cualquier lugar de la ventana, excepto un botón de activavión del dropdown*/
  else if (!event.target.matches('.dropbtn') && dropbtn) {
    dropbtn.nextElementSibling.style.display = "none"; /*Se desactiva el dropdown*/
  }
}