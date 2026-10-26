// Basic Interaction
console.log('Luxury Furniture Shop Initialized.');

// Form handling for Contact Page
const contactForm = document.querySelector('form');
if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
        e.preventDefault();
        alert('Thank you for your message! We will get back to you soon.');
        contactForm.reset();
    });
}
