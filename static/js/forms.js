/**
 * Form handling utilities for Inventario Zombie
 * This file contains functions for form validation and submission
 */

/**
 * Validate form data
 * @param {HTMLFormElement} form - The form element to validate
 * @returns {boolean} - Whether the form is valid
 */
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    // Reset previous validation messages
    form.querySelectorAll('.validation-message').forEach(el => el.remove());
    
    // Check required fields
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            showValidationError(field, 'Este campo es obligatorio');
        }
    });
    
    // Add additional validation rules as needed
    const numericFields = form.querySelectorAll('[data-type="numeric"]');
    numericFields.forEach(field => {
        if (field.value && isNaN(parseFloat(field.value))) {
            isValid = false;
            showValidationError(field, 'Este campo debe ser numérico');
        }
    });
    
    return isValid;
}

/**
 * Show validation error message
 * @param {HTMLElement} field - The field with the error
 * @param {string} message - The error message
 */
function showValidationError(field, message) {
    const errorElement = document.createElement('div');
    errorElement.className = 'validation-message error';
    errorElement.textContent = message;
    field.parentNode.appendChild(errorElement);
    field.classList.add('error');
}

/**
 * Handle form submission
 * @param {HTMLFormElement} form - The form element
 * @param {Function} submitCallback - Callback function for form submission
 * @param {Function} successCallback - Callback function for successful submission
 * @param {Function} errorCallback - Callback function for submission error
 */
function handleFormSubmit(form, submitCallback, successCallback, errorCallback) {
    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        if (!validateForm(form)) {
            return;
        }
        
        // Show loading state
        const submitButton = form.querySelector('[type="submit"]');
        const originalButtonText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Procesando...';
        
        try {
            // Get form data as object
            const formData = new FormData(form);
            const formDataObj = {};
            formData.forEach((value, key) => {
                formDataObj[key] = value;
            });
            
            // Call the submit callback with the form data
            const result = await submitCallback(formDataObj);
            
            // Call success callback
            if (successCallback) {
                successCallback(result);
            }
            
            // Reset form if needed
            form.reset();
            
        } catch (error) {
            console.error('Form submission error:', error);
            
            // Call error callback
            if (errorCallback) {
                errorCallback(error);
            } else {
                // Default error handling
                alert('Error al procesar el formulario: ' + error.message);
            }
        } finally {
            // Reset button state
            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;
        }
    });
}

/**
 * Initialize a form with validation and submission handling
 * @param {string} formSelector - CSS selector for the form
 * @param {Function} submitCallback - Function to handle the form data
 * @param {Function} successCallback - Function to handle successful submission
 * @param {Function} errorCallback - Function to handle submission errors
 */
function initForm(formSelector, submitCallback, successCallback, errorCallback) {
    const form = document.querySelector(formSelector);
    if (!form) {
        console.error(`Form not found: ${formSelector}`);
        return;
    }
    
    handleFormSubmit(form, submitCallback, successCallback, errorCallback);
} 