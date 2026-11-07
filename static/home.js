function filterItems(category) {

    const products = document.querySelectorAll(".product");

    products.forEach(product => {

        if (
            category === "all" ||
            product.dataset.category === category
        ) {
            product.style.display = "block";
        } else {
            product.style.display = "none";
        }

    });

}

/* =========================================
   LASU CAMPUSMART CAROUSEL (Swiper.js)
   ========================================= */
document.addEventListener('DOMContentLoaded', function () {

    const carouselEl = document.querySelector('.lasu-carousel');

    if (!carouselEl || typeof Swiper === 'undefined') return;

    new Swiper('.lasu-carousel', {
        loop: true,
        autoplay: {
            delay: 5000,
            disableOnInteraction: false,
            pauseOnMouseEnter: true,
        },
        effect: 'slide',
        speed: 800,
        pagination: {
            el: '.swiper-pagination',
            clickable: true,
        },
        navigation: {
            nextEl: '.swiper-button-next',
            prevEl: '.swiper-button-prev',
        },
        grabCursor: true,
    });

});


/* =========================================
   DESKTOP HAMBURGER DROPDOWN
   ========================================= */
document.addEventListener('DOMContentLoaded', function () {

    const hamburgerBtn = document.getElementById('hamburgerBtn');
    const desktopDropdown = document.getElementById('desktopDropdown');

   
    if (!hamburgerBtn || !desktopDropdown) return;

   
    hamburgerBtn.addEventListener('click', function (e) {
        e.stopPropagation(); 
        desktopDropdown.classList.toggle('open');

        
        const icon = hamburgerBtn.querySelector('i');
        if (desktopDropdown.classList.contains('open')) {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-xmark');
        } else {
            icon.classList.remove('fa-xmark');
            icon.classList.add('fa-bars');
        }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function (e) {
        if (!desktopDropdown.contains(e.target) && e.target !== hamburgerBtn) {
            desktopDropdown.classList.remove('open');
            const icon = hamburgerBtn.querySelector('i');
            icon.classList.remove('fa-xmark');
            icon.classList.add('fa-bars');
        }
    });

});

 document.addEventListener("DOMContentLoaded", function() {
        const guestBtn = document.getElementById('guestAccountBtn');
        const guestDropdown = document.getElementById('guestDropdown');
        
        if (guestBtn && guestDropdown) {
            // Open/Close when clicking the icon
            guestBtn.addEventListener('click', function(e) {
                e.preventDefault(); // Stops the page from jumping to the top
                if (guestDropdown.style.display === 'none' || guestDropdown.style.display === '') {
                    guestDropdown.style.display = 'flex';
                } else {
                    guestDropdown.style.display = 'none';
                }
            });

            // Close the menu if they click anywhere else on the page
            document.addEventListener('click', function(e) {
                if (!guestBtn.contains(e.target) && !guestDropdown.contains(e.target)) {
                    guestDropdown.style.display = 'none';
                }
            });
        }
    });
