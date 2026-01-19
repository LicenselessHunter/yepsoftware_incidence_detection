window.addEventListener('click', function(event) { 
    if (event.target.matches('.open-report-error-btn')) {
        let reportId = event.target.id;
        let modal = document.getElementById(`error-message-modal-report-${reportId}`);
        modal.style.display = "block";
    }

    else if (event.target.matches('[id^="error-message-modal-report"]')) {
        event.target.style.display = "none";
    }
});