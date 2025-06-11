document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('bot-form');
    const contactsFileInput = document.getElementById('contacts-file');
    const imageFileInput = document.getElementById('image-file');
    const numberColumnSelect = document.getElementById('number-column');
    const messageTemplateInput = document.getElementById('message-template');
    const startBotBtn = document.getElementById('start-bot-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');

    const columnSelectionArea = document.getElementById('column-selection-area');
    const messageArea = document.getElementById('message-area');
    const columnPlaceholders = document.getElementById('column-placeholders');

    const progressModal = new bootstrap.Modal(document.getElementById('progress-modal'));
    const progressStatus = document.getElementById('progress-status');
    const qrCodeArea = document.getElementById('qr-code-area');
    const qrCodeImg = document.getElementById('qr-code-img');
    const logOutput = document.getElementById('log-output');
    const closeModalBtn = document.getElementById('close-modal-btn');

    let statusInterval;

    // When a CSV file is selected
    contactsFileInput.addEventListener('change', async function() {
        if (!this.files.length) return;
        const formData = new FormData();
        formData.append('file', this.files[0]);

        try {
            const response = await fetch('/api/get_columns', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Populate number column dropdown
            numberColumnSelect.innerHTML = '<option value="" disabled selected>Select a column</option>';
            data.columns.forEach(column => {
                const option = new Option(column, column);
                numberColumnSelect.add(option);
            });

            // Populate placeholder buttons
            columnPlaceholders.innerHTML = '';
            data.columns.forEach(column => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'btn btn-sm btn-outline-secondary me-1 mb-1';
                button.textContent = column;
                button.onclick = () => insertPlaceholder(`{${column}}`);
                columnPlaceholders.appendChild(button);
            });

            columnSelectionArea.style.display = 'block';
            messageArea.style.display = 'block';
            startBotBtn.disabled = false;

        } catch (error) {
            alert(`Error processing CSV: ${error.message}`);
            resetForm();
        }
    });

    function insertPlaceholder(placeholder) {
        const start = messageTemplateInput.selectionStart;
        const end = messageTemplateInput.selectionEnd;
        const text = messageTemplateInput.value;
        messageTemplateInput.value = text.substring(0, start) + placeholder + text.substring(end);
        messageTemplateInput.focus();
    }

    // When the form is submitted
    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        setButtonLoading(true);

        const formData = new FormData();
        formData.append('contacts_file', contactsFileInput.files[0]);
        formData.append('number_column', numberColumnSelect.value);
        formData.append('message_template', messageTemplateInput.value);
        if (imageFileInput.files.length) {
            formData.append('image_file', imageFileInput.files[0]);
        }
        
        try {
            const response = await fetch('/api/run_bot', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Show the modal and start polling for status
            progressModal.show();
            logOutput.textContent = '';
            closeModalBtn.style.display = 'none';
            statusInterval = setInterval(() => checkStatus(data.session_id), 1500);

        } catch (error) {
            alert(`Error starting bot: ${error.message}`);
            setButtonLoading(false);
        }
    });
    
    // Periodically check the status of the bot session
    async function checkStatus(sessionId) {
        try {
            const response = await fetch(`/api/status/${sessionId}`);
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }
            
            progressStatus.textContent = data.status;
            logOutput.textContent = data.log.join('\n');
            logOutput.scrollTop = logOutput.scrollHeight; // Auto-scroll

            if (data.status === 'Scan QR Code' && data.qr_path) {
                qrCodeArea.style.display = 'block';
                // Add a timestamp to prevent browser caching the QR image
                qrCodeImg.src = `${data.qr_path}?t=${new Date().getTime()}`;
            } else {
                 qrCodeArea.style.display = 'none';
            }

            if (data.status === 'Completed' || data.status === 'Error') {
                clearInterval(statusInterval);
                setButtonLoading(false);
                closeModalBtn.style.display = 'block';
            }

        } catch (error) {
            console.error('Status check failed:', error);
            clearInterval(statusInterval);
            setButtonLoading(false);
            progressStatus.textContent = 'Error: Lost connection to server.';
            closeModalBtn.style.display = 'block';
        }
    }

    function setButtonLoading(isLoading) {
        if (isLoading) {
            btnText.textContent = 'Running...';
            btnSpinner.style.display = 'inline-block';
            startBotBtn.disabled = true;
        } else {
            btnText.textContent = 'Start Bot';
            btnSpinner.style.display = 'none';
            startBotBtn.disabled = false;
        }
    }
    
    function resetForm() {
        form.reset();
        columnSelectionArea.style.display = 'none';
        messageArea.style.display = 'none';
        startBotBtn.disabled = true;
    }
}); 