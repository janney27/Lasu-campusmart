const productImage = document.getElementById("productImage");
const imagePreview = document.getElementById("imagePreview");

productImage.addEventListener("change", function () {

    const file = this.files[0];

    if (file) {

        imagePreview.src = URL.createObjectURL(file);

        imagePreview.style.display = "block";

    }

});
   
    
