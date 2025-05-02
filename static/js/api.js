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