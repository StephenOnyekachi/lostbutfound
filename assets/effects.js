
// TYPING ANIMATION
function createTypingEffect(selector, words, speed = 100, deleteSpeed = 50, delay = 1500) {
  const element = document.querySelector(selector);

  let wordIndex = 0;
  let charIndex = 0;
  let isDeleting = false;

  function type() {
    const current = words[wordIndex];
    const text = current.text;
    const color = current.color;

    if (element) {
        if (!isDeleting) {
        element.innerHTML = `<span style="color:${color}">${text.substring(0, charIndex + 1)}</span>`;
        charIndex++;

        if (charIndex === text.length) {
            isDeleting = true;
            setTimeout(type, delay);
            return;
        }
        } else {
        element.innerHTML = `<span style="color:${color}">${text.substring(0, charIndex - 1)}</span>`;
        charIndex--;

        if (charIndex === 0) {
            isDeleting = false;
            wordIndex = (wordIndex + 1) % words.length;
        }
        }
    }
    setTimeout(type, isDeleting ? deleteSpeed : speed);
  }

  type();
}
createTypingEffect(".typing", [
  { text: "Delicious Meals 🍔", color: "#ff5733" },
  { text: "Fresh & Hot Food 🍕", color: "#28a745" },
  { text: "Order Anytime 🍽️", color: "#ffc107" }
]);


// PRELOADER
window.addEventListener("load", () => {
  const loader = document.getElementById("preloader");

  loader.style.opacity = "0";

  setTimeout(() => {
    loader.style.display = "none";
  }, 500);
});


// SMOOTH SCROLL
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener("click", function(e) {
    e.preventDefault();
    document.querySelector(this.getAttribute("href"))
      .scrollIntoView({ behavior: "smooth" });
  });
});


/* TOP MENU SCROW EFFECT */
window.addEventListener('scroll', function() {
    const nav = document.querySelector('.top-menu');
    if (window.scrollY > 50) {
        nav.classList.add('active');
    } else {
        nav.classList.remove('active');
    }
});

// SLIDE TOP EFFECT
window.addEventListener('scroll', slidetop);
function slidetop(){
    var reavels = document.querySelectorAll('.slidetop');
    
    for(var i = 0; i < reavels.length; i++){

        var windowheight = window.innerHeight;
        var reaveltop = reavels[i].getBoundingClientRect().top;
        var reavelpoint = 60;

        if(reaveltop < windowheight - reavelpoint){
            reavels[i].classList.add('active');
        }
        else{
            reavels[i].classList.remove('active');
        }
    }
}

// SLIDE left EFFECT
window.addEventListener('scroll', leftslide);
function leftslide(){
    var reavels = document.querySelectorAll('.slideleft');
    
    for(var i = 0; i < reavels.length; i++){

        var windowheight = window.innerHeight;
        var reaveltop = reavels[i].getBoundingClientRect().top;
        var reavelpoint = 10;

        if(reaveltop < windowheight - reavelpoint){
            reavels[i].classList.add('active');
        }
        else{
            reavels[i].classList.remove('active');
        }
    }
}

// ZOOM IN EFFECT
window.addEventListener('scroll', zoomIn);
function zoomIn(){
    var reavels = document.querySelectorAll('.zoom-in');
    
    for(var i = 0; i < reavels.length; i++){
        var windowheight = window.innerHeight;
        var reaveltop = reavels[i].getBoundingClientRect().top;
        var reavelpoint = 0;

        if(reaveltop < windowheight - reavelpoint){
            reavels[i].classList.add('active');
        }
        else{
            reavels[i].classList.remove('active');
        }
    }
}