/**
 * API utilities for Inventario Zombie
 * This file contains functions for communicating with the backend API
 */

// Base URL for API requests
const API_BASE_URL = '/api';

/**
 * Generic function to make API calls
 * @param {string} endpoint - API endpoint
 * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
 * @param {object} data - Request body data (for POST/PUT)
 * @returns {Promise} - Promise resolving to the API response
 */
async function apiCall(endpoint, method = 'GET', data = null) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin'
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        
        // Handle HTTP errors
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'API request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Ingredient API functions
const ingredientesAPI = {
    getAll: () => apiCall('/ingredientes'),
    getById: (id) => apiCall(`/ingredientes/${id}`),
    create: (data) => apiCall('/ingredientes', 'POST', data),
    update: (id, data) => apiCall(`/ingredientes/${id}`, 'PUT', data),
    delete: (id) => apiCall(`/ingredientes/${id}`, 'DELETE')
};

// Product API functions
const articulosAPI = {
    getAll: () => apiCall('/articulos'),
    getById: (id) => apiCall(`/articulos/${id}`),
    create: (data) => apiCall('/articulos', 'POST', data),
    update: (id, data) => apiCall(`/articulos/${id}`, 'PUT', data),
    delete: (id) => apiCall(`/articulos/${id}`, 'DELETE'),
    getComposicion: (id) => apiCall(`/articulos/${id}/composicion`),
    updateComposicion: (id, data) => apiCall(`/articulos/${id}/composicion`, 'POST', data)
};

// Sales API functions
const ventasAPI = {
    importar: (data) => apiCall('/ventas/importar', 'POST', data),
    getAll: () => apiCall('/ventas')
};

// Kitchen reception API functions
const recepcionesAPI = {
    getAll: () => apiCall('/recepciones'),
    create: (data) => apiCall('/recepciones', 'POST', data),
    getById: (id) => apiCall(`/recepciones/${id}`)
};

// Reports API functions
const reportesAPI = {
    ventasPorArticulo: () => apiCall('/reportes/ventas_por_articulo'),
    ventasPorCategoria: () => apiCall('/reportes/ventas_por_categoria'),
    tendenciasVentas: () => apiCall('/reportes/tendencias_ventas')
};

/**
 * Inventario Zombie API Client
 * JavaScript module for handling API communication
 */

const API = {
    /**
     * Send a GET request to the API
     * @param {string} endpoint - API endpoint
     * @returns {Promise} - Promise with the response data
     */
    get: async (endpoint) => {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`API error: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('GET request failed:', error);
            throw error;
        }
    },

    /**
     * Send a POST request to the API
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Data to send
     * @returns {Promise} - Promise with the response data
     */
    post: async (endpoint, data) => {
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                throw new Error(`API error: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('POST request failed:', error);
            throw error;
        }
    },

    /**
     * Send a PUT request to the API
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Data to send
     * @returns {Promise} - Promise with the response data
     */
    put: async (endpoint, data) => {
        try {
            const response = await fetch(endpoint, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                throw new Error(`API error: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('PUT request failed:', error);
            throw error;
        }
    },

    /**
     * Send a DELETE request to the API
     * @param {string} endpoint - API endpoint
     * @returns {Promise} - Promise with the response data
     */
    delete: async (endpoint) => {
        try {
            const response = await fetch(endpoint, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error(`API error: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('DELETE request failed:', error);
            throw error;
        }
    },

    /**
     * API endpoints organized by resource
     */
    endpoints: {
        ingredientes: {
            getAll: '/api/ingredientes',
            getById: (id) => `/api/ingredientes/${id}`,
            create: '/api/ingredientes',
            update: (id) => `/api/ingredientes/${id}`,
            delete: (id) => `/api/ingredientes/${id}`
        },
        articulos: {
            getAll: '/api/articulos',
            getById: (id) => `/api/articulos/${id}`,
            create: '/api/articulos',
            update: (id) => `/api/articulos/${id}`,
            delete: (id) => `/api/articulos/${id}`,
            getComposicion: (id) => `/api/articulos/${id}/composicion`,
            addComposicion: (id) => `/api/articulos/${id}/composicion`,
            deleteComposicion: (id) => `/api/composicion/${id}`
        },
        ventas: {
            importar: '/api/ventas/importar'
        },
        recepciones: {
            getAll: '/api/recepciones',
            create: '/api/recepciones',
            getById: (id) => `/api/recepciones/${id}`
        }
    }
};

// Add toast notification functionality
const Toast = {
    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type of toast (success, error, warning, info)
     * @param {number} duration - Duration in milliseconds
     */
    show: (message, type = 'info', duration = 3000) => {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerText = message;
        
        document.body.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // Remove after duration
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, duration);
    }
};

// Add form validation
const Validator = {
    /**
     * Validate a form
     * @param {HTMLFormElement} form - Form to validate
     * @returns {boolean} - Whether the form is valid
     */
    validateForm: (form) => {
        let isValid = true;
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            if (input.required && !input.value.trim()) {
                isValid = false;
                input.classList.add('error');
                
                // Add error message if not exists
                if (!input.nextElementSibling || !input.nextElementSibling.classList.contains('error-message')) {
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'error-message';
                    errorMsg.innerText = 'Este campo es obligatorio';
                    input.parentNode.insertBefore(errorMsg, input.nextSibling);
                }
            } else {
                input.classList.remove('error');
                // Remove existing error message
                if (input.nextElementSibling && input.nextElementSibling.classList.contains('error-message')) {
                    input.parentNode.removeChild(input.nextElementSibling);
                }
            }
        });
        
        return isValid;
    }
};

// Modal functionality
const Modal = {
    /**
     * Open a modal
     * @param {string} id - Modal ID
     */
    open: (id) => {
        const modal = document.getElementById(id);
        if (modal) {
            modal.style.display = 'block';
        }
    },
    
    /**
     * Close a modal
     * @param {string} id - Modal ID
     */
    close: (id) => {
        const modal = document.getElementById(id);
        if (modal) {
            modal.style.display = 'none';
        }
    }
};

// Initialize modals
document.addEventListener('DOMContentLoaded', () => {
    // Set up click handlers for modal close buttons
    const closeButtons = document.querySelectorAll('.close');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const modal = button.closest('.modal');
            modal.style.display = 'none';
        });
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}); 