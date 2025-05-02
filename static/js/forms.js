/**
 * Inventario Zombie Forms
 * JavaScript module for handling forms
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all forms with form handlers
    initForms();
});

/**
 * Initialize form handlers
 */
function initForms() {
    // Handle ingredient form submissions
    const ingredientForm = document.getElementById('ingredient-form');
    if (ingredientForm) {
        ingredientForm.addEventListener('submit', handleIngredientForm);
    }
    
    // Handle product form submissions
    const productForm = document.getElementById('product-form');
    if (productForm) {
        productForm.addEventListener('submit', handleProductForm);
    }
    
    // Handle product composition form submissions
    const compositionForm = document.getElementById('composition-form');
    if (compositionForm) {
        compositionForm.addEventListener('submit', handleCompositionForm);
    }
    
    // Handle delete confirmations
    initDeleteConfirmations();
}

/**
 * Handle ingredient form submission
 * @param {Event} event - Form submit event
 */
async function handleIngredientForm(event) {
    event.preventDefault();
    
    // Validate form
    if (!Validator.validateForm(this)) {
        return;
    }
    
    const formData = new FormData(this);
    const ingredient = {
        nombre: formData.get('nombre'),
        unidad_medida: formData.get('unidad_medida'),
        precio_compra: parseFloat(formData.get('precio_compra')) || 0,
        cantidad_actual: parseFloat(formData.get('cantidad_actual')) || 0,
        stock_minimo: parseFloat(formData.get('stock_minimo')) || 0,
        categoria: formData.get('categoria')
    };
    
    try {
        const ingredientId = formData.get('id');
        let response;
        
        if (ingredientId) {
            // Update existing ingredient
            response = await API.put(API.endpoints.ingredientes.update(ingredientId), ingredient);
            Toast.show('Ingrediente actualizado correctamente', 'success');
        } else {
            // Create new ingredient
            response = await API.post(API.endpoints.ingredientes.create, ingredient);
            Toast.show('Ingrediente creado correctamente', 'success');
            this.reset();
        }
        
        // Redirect to ingredients list after a short delay
        setTimeout(() => {
            window.location.href = '/ingredientes';
        }, 1500);
    } catch (error) {
        Toast.show(`Error: ${error.message}`, 'error');
    }
}

/**
 * Handle product form submission
 * @param {Event} event - Form submit event
 */
async function handleProductForm(event) {
    event.preventDefault();
    
    // Validate form
    if (!Validator.validateForm(this)) {
        return;
    }
    
    const formData = new FormData(this);
    const product = {
        nombre: formData.get('nombre'),
        categoria: formData.get('categoria'),
        subcategoria: formData.get('subcategoria'),
        precio_venta: parseFloat(formData.get('precio_venta')) || 0
    };
    
    try {
        const productId = formData.get('id');
        let response;
        
        if (productId) {
            // Update existing product
            response = await API.put(API.endpoints.articulos.update(productId), product);
            Toast.show('Artículo actualizado correctamente', 'success');
        } else {
            // Create new product
            response = await API.post(API.endpoints.articulos.create, product);
            Toast.show('Artículo creado correctamente', 'success');
            this.reset();
        }
        
        // Redirect to products list after a short delay
        setTimeout(() => {
            window.location.href = '/articulos';
        }, 1500);
    } catch (error) {
        Toast.show(`Error: ${error.message}`, 'error');
    }
}

/**
 * Handle product composition form submission
 * @param {Event} event - Form submit event
 */
async function handleCompositionForm(event) {
    event.preventDefault();
    
    // Validate form
    if (!Validator.validateForm(this)) {
        return;
    }
    
    const formData = new FormData(this);
    const articleId = formData.get('articulo_id');
    const ingredientId = formData.get('ingrediente_id');
    const cantidad = parseFloat(formData.get('cantidad')) || 0;
    
    try {
        const composition = {
            ingrediente_id: ingredientId,
            cantidad: cantidad
        };
        
        await API.post(API.endpoints.articulos.addComposicion(articleId), composition);
        Toast.show('Ingrediente agregado correctamente', 'success');
        
        // Refresh the composition list
        loadComposition(articleId);
        
        // Reset the form fields
        document.getElementById('ingrediente_id').value = '';
        document.getElementById('cantidad').value = '';
    } catch (error) {
        Toast.show(`Error: ${error.message}`, 'error');
    }
}

/**
 * Load composition for a product
 * @param {number} articleId - Product ID
 */
async function loadComposition(articleId) {
    try {
        const composition = await API.get(API.endpoints.articulos.getComposicion(articleId));
        const compositionList = document.getElementById('composition-list');
        
        if (compositionList) {
            compositionList.innerHTML = '';
            
            if (composition.length === 0) {
                compositionList.innerHTML = '<tr><td colspan="3">No hay ingredientes en este artículo</td></tr>';
                return;
            }
            
            composition.forEach(item => {
                compositionList.innerHTML += `
                    <tr>
                        <td>${item.ingrediente_nombre}</td>
                        <td>${item.cantidad} ${item.unidad_medida}</td>
                        <td>
                            <button class="btn btn-danger btn-sm delete-composition" 
                                    data-id="${item.id}" 
                                    data-ingrediente="${item.ingrediente_nombre}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
            
            // Add event listeners to delete buttons
            initDeleteCompositionButtons();
        }
    } catch (error) {
        Toast.show(`Error al cargar la composición: ${error.message}`, 'error');
    }
}

/**
 * Initialize delete composition buttons
 */
function initDeleteCompositionButtons() {
    const deleteButtons = document.querySelectorAll('.delete-composition');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', async (event) => {
            event.preventDefault();
            
            const id = button.dataset.id;
            const ingredientName = button.dataset.ingrediente;
            
            if (confirm(`¿Estás seguro de eliminar ${ingredientName} de la composición?`)) {
                try {
                    await API.delete(API.endpoints.articulos.deleteComposicion(id));
                    Toast.show('Ingrediente eliminado correctamente', 'success');
                    
                    // Remove the row from the table
                    button.closest('tr').remove();
                    
                    // If no more rows, show the empty message
                    const compositionList = document.getElementById('composition-list');
                    if (compositionList.children.length === 0) {
                        compositionList.innerHTML = '<tr><td colspan="3">No hay ingredientes en este artículo</td></tr>';
                    }
                } catch (error) {
                    Toast.show(`Error: ${error.message}`, 'error');
                }
            }
        });
    });
}

/**
 * Initialize delete confirmations
 */
function initDeleteConfirmations() {
    // Handle ingredient delete confirmations
    const deleteIngredientButtons = document.querySelectorAll('.delete-ingredient');
    deleteIngredientButtons.forEach(button => {
        button.addEventListener('click', async (event) => {
            event.preventDefault();
            
            const id = button.dataset.id;
            const name = button.dataset.name;
            
            if (confirm(`¿Estás seguro de eliminar el ingrediente "${name}"?`)) {
                try {
                    await API.delete(API.endpoints.ingredientes.delete(id));
                    Toast.show('Ingrediente eliminado correctamente', 'success');
                    
                    // Remove the row or card from the list
                    const element = button.closest('.item-card') || button.closest('tr');
                    element.remove();
                } catch (error) {
                    Toast.show(`Error: ${error.message}`, 'error');
                }
            }
        });
    });
    
    // Handle product delete confirmations
    const deleteProductButtons = document.querySelectorAll('.delete-product');
    deleteProductButtons.forEach(button => {
        button.addEventListener('click', async (event) => {
            event.preventDefault();
            
            const id = button.dataset.id;
            const name = button.dataset.name;
            
            if (confirm(`¿Estás seguro de eliminar el artículo "${name}"?`)) {
                try {
                    await API.delete(API.endpoints.articulos.delete(id));
                    Toast.show('Artículo eliminado correctamente', 'success');
                    
                    // Remove the row or card from the list
                    const element = button.closest('.item-card') || button.closest('tr');
                    element.remove();
                } catch (error) {
                    Toast.show(`Error: ${error.message}`, 'error');
                }
            }
        });
    });
} 