// frontend/script.js

document.addEventListener('DOMContentLoaded', () => {
    const ocrForm = document.getElementById('ocr-form');
    const imageUpload = document.getElementById('image-upload');
    const questionInput = document.getElementById('question-input');
    const submitBtn = document.getElementById('submit-btn');
    const imagePreview = document.getElementById('image-preview');
    const loadingDiv = document.getElementById('loading');
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');

    // VERY IMPORTANT: Verify this URL is correct
    const API_URL = 'http://127.0.0.1:8000/api/process';

    imageUpload.addEventListener('change', () => {
        const file = imageUpload.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview.src = e.target.result;
                imagePreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    });

    ocrForm.addEventListener('submit', async (e) => {
        // *** THIS IS THE MOST IMPORTANT LINE TO PREVENT PAGE RELOAD ***
        e.preventDefault(); 

        const imageFile = imageUpload.files[0];
        const question = questionInput.value;

        if (!imageFile || !question) {
            alert('Please upload an image and ask a question.');
            return;
        }

        loadingDiv.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';

        const formData = new FormData();
        formData.append('file', imageFile);
        formData.append('question', question);

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Something went wrong on the server.');
            }

            const data = await response.json();
            resultText.textContent = data.answer;
            resultContainer.classList.remove('hidden');

        } catch (error) {
            console.error('Error:', error);
            resultText.textContent = `Error: ${error.message}`;
            resultContainer.classList.remove('hidden');
        } finally {
            loadingDiv.classList.add('hidden');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Get Answer';
        }
    });
});