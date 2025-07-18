document.addEventListener('DOMContentLoaded', function () {
    const typeSelect = document.querySelector('#id_notification_type');
    const freqSelect = document.querySelector('#id_message_frequency');

    if (!typeSelect || !freqSelect) return;

    function updateIntervals(typeId) {
        fetch(`/admin/osf/notificationsubscription/get-intervals/${typeId}/`)
            .then(response => response.json())
            .then(data => {
                // Clear current options
                freqSelect.innerHTML = '';

                // Add new ones
                data.intervals.forEach(choice => {
                    const option = document.createElement('option');
                    option.value = choice;
                    option.textContent = choice;
                    freqSelect.appendChild(option);
                });
            });
    }

    typeSelect.addEventListener('change', function () {
        if (this.value) {
            updateIntervals(this.value);
        }
    });

    // Auto-load if there's an initial value
    if (typeSelect.value) {
        updateIntervals(typeSelect.value);
    }
});