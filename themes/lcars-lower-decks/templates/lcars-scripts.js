// LCARS real-time clock
function updateLCARSClock() {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour12: false });
    const date = now.toLocaleDateString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });

    const dateEl = document.getElementById('lcars-date');
    const timeEl = document.getElementById('lcars-time');
    if (dateEl) dateEl.textContent = date;
    if (timeEl) timeEl.textContent = time;
}

// Frame toggle
let topFrameHidden = false;
function toggleTopFrame(event) {
    if (event) event.preventDefault();
    const topFrame = document.getElementById('top-frame');
    const gap = document.getElementById('gap');
    const btn = document.getElementById('topBtn');

    if (!topFrame || !gap) return;

    if (topFrameHidden) {
        topFrame.style.maxHeight = '100vh';
        topFrame.style.opacity = '1';
        topFrame.style.margin = '0';
        gap.style.marginTop = '0';
        if (btn) btn.innerHTML = '<span class="hop">hide</span> detail';
    } else {
        topFrame.style.maxHeight = '0';
        topFrame.style.opacity = '0';
        topFrame.style.margin = '-20px 0 0 0';
        gap.style.marginTop = '20px';
        if (btn) btn.innerHTML = '<span class="hop">show</span> detail';
    }
    topFrameHidden = !topFrameHidden;
}

// Initialization
window.addEventListener('load', () => {
    updateLCARSClock();
    setInterval(updateLCARSClock, 1000);
});
