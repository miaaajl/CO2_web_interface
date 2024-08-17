document.addEventListener('DOMContentLoaded', (event) => {
    const form = document.querySelector('form');
    form.addEventListener('submit', (event) => {
        const Q0 = document.getElementById('Q0').value;
        const Qmax = document.getElementById('Qmax').value;
        const r = document.getElementById('r').value;
        const tp = document.getElementById('tp').value;
        
        if (Q0 <= 0 || Qmax <= 0 || r <= 0 || tp < 1972 || tp > 2100) {
            event.preventDefault();
            alert('Please enter valid values for all fields.');
        }
    });
});
