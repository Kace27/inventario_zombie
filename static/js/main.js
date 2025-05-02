document.addEventListener('DOMContentLoaded', function() {
    console.log('Inventario Zombie application initialized');
    
    // Mobile navigation toggle (for future responsive design)
    const mobileNavToggle = document.querySelector('.mobile-nav-toggle');
    if (mobileNavToggle) {
        mobileNavToggle.addEventListener('click', function() {
            const navLinks = document.querySelector('.nav-links');
            navLinks.classList.toggle('active');
        });
    }
    
    // Add any other global event listeners or initializations here
}); 