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
    const leftTop = document.getElementById('top-frame');
    const rightTop = document.querySelector('.right-frame-top');
    const btn = document.getElementById('topBtn');

    if (!leftTop || !rightTop) return;

    topFrameHidden = !topFrameHidden;
    leftTop.classList.toggle('hidden', topFrameHidden);
    rightTop.classList.toggle('hidden', topFrameHidden);
    if (btn) btn.innerHTML = topFrameHidden
        ? '<span class="hop">show</span> detail'
        : '<span class="hop">hide</span> detail';
}

// Topbar / gutter scaling
const SCALE_STOPS = [1, 0.75, 0.5, 0.25];

let topbarScaleIdx = 0;
let gutterScaleIdx = 0;

function applyTopbarScale() {
    const scale = SCALE_STOPS[topbarScaleIdx];
    document.documentElement.style.setProperty('--topbar-scale', scale);
    document.documentElement.classList.toggle('topbar-xs', scale <= 0.25);
    const btn = document.getElementById('tbBtn');
    if (btn) btn.textContent = `TB: ${Math.round(scale * 100)}%`;
    localStorage.setItem('lcars-topbar-scale-idx', topbarScaleIdx);
}

function applyGutterScale() {
    const scale = SCALE_STOPS[gutterScaleIdx];
    document.documentElement.style.setProperty('--gutter-scale', scale);
    const btn = document.getElementById('gwBtn');
    if (btn) btn.textContent = `GW: ${Math.round(scale * 100)}%`;
    localStorage.setItem('lcars-gutter-scale-idx', gutterScaleIdx);
}

function cycleTopbarScale(dir) {
    topbarScaleIdx = (topbarScaleIdx + dir + SCALE_STOPS.length) % SCALE_STOPS.length;
    applyTopbarScale();
}

function cycleGutterScale(dir) {
    gutterScaleIdx = (gutterScaleIdx + dir + SCALE_STOPS.length) % SCALE_STOPS.length;
    applyGutterScale();
}

// Keyboard: [ ] for topbar, { } for gutter
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    switch (e.key) {
        case '[': cycleTopbarScale(+1); break;  // topbar smaller
        case ']': cycleTopbarScale(-1); break;  // topbar larger
        case '{': cycleGutterScale(+1); break;  // gutter narrower
        case '}': cycleGutterScale(-1); break;  // gutter wider
    }
});

// Initialization
window.addEventListener('load', () => {
    // Restore saved scales
    topbarScaleIdx = parseInt(localStorage.getItem('lcars-topbar-scale-idx') || '0');
    gutterScaleIdx = parseInt(localStorage.getItem('lcars-gutter-scale-idx') || '0');
    applyTopbarScale();
    applyGutterScale();

    updateLCARSClock();
    setInterval(updateLCARSClock, 1000);
});
