// ============================================================
// HIGH-FIDELITY BRIDGE SYSTEMS (PORTED FROM ARGUS)
// ============================================================

const BRIDGE_STATE = {
    logs: [],
    cycle: 0,
    interval: null
};

function updateBridgeTelemetry() {
    BRIDGE_STATE.cycle++;
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                    now.getMinutes().toString().padStart(2, '0') + ':' + 
                    now.getSeconds().toString().padStart(2, '0');
    
    // 1. SYS STATUS
    const sysEl = document.getElementById('tele-sys');
    if (sysEl) {
        sysEl.innerHTML = '<span class="dim">[' + timeStr + ']</span><br>' +
                          'MODE: <span class="highlight">ACTIVE</span><br>' +
                          'CYC: ' + BRIDGE_STATE.cycle.toString().padStart(4, '0') + '<br>' +
                          'AUTH: <span class="highlight">TRUSTED</span>';
    }

    // 2. NET TRAFFIC
    const netEl = document.getElementById('tele-net');
    if (netEl) {
        const rx = (42 + Math.random() * 5).toFixed(2);
        const tx = (12 + Math.random() * 2).toFixed(2);
        netEl.innerHTML = 'RX: <span class="highlight">' + rx + ' GB</span><br>' +
                          'TX: <span class="highlight">' + tx + ' GB</span><br>' +
                          'LAT: ' + Math.floor(Math.random() * 20 + 5) + 'ms';
    }

    // 3. PROC LOG
    const logEl = document.getElementById('tele-log');
    if (logEl) {
        const events = ['HASHING', 'INDEXING', 'SIGNING', 'VERIFYING', 'PUSHING', 'MAPPING', 'PARSING'];
        if (Math.random() > 0.7) {
            const newLog = '<span class="dim">' + timeStr.slice(3) + '</span> ' + events[Math.floor(Math.random() * events.length)];
            BRIDGE_STATE.logs.push(newLog);
            if (BRIDGE_STATE.logs.length > 5) BRIDGE_STATE.logs.shift();
        }
        logEl.innerHTML = BRIDGE_STATE.logs.join('<br>');
    }

    // 4. Global Flicker
    document.querySelectorAll('.lcars-flicker').forEach(el => {
        if (Math.random() > 0.9) {
            const digits = Math.floor(Math.random() * 2) + 4; 
            const max = Math.pow(10, digits);
            el.textContent = '-' + Math.floor(Math.random() * max).toString().padStart(digits, '0');
        }
    });
}

function updateBridgeGraphic(slideIndex) {
    const graphicZone = document.getElementById('lcars-nerd-graphic');
    if (!graphicZone) return;

    graphicZone.innerHTML = '';
    const effectMeta = document.getElementById('slide-' + slideIndex + '-effect');
    const effectName = effectMeta ? effectMeta.textContent.trim() : 'starmap';

    if (effectName === 'starmap') {
        graphicZone.innerHTML = '<div class="effect-starmap"></div>';
    } else if (effectName === 'histogram') {
        graphicZone.innerHTML = '<div class="effect-histogram"><div></div><div></div><div></div><div></div><div></div></div>';
    } else if (effectName === 'waveform') {
        graphicZone.innerHTML = '<div class="effect-waveform"></div>';
    } else if (effectName === 'orbital') {
        graphicZone.innerHTML = '<div class="effect-orbital"></div>';
    }
}

function initializeBridgeSystems() {
    console.log("Initializing Bridge Systems...");
    if (BRIDGE_STATE.interval) clearInterval(BRIDGE_STATE.interval);
    BRIDGE_STATE.interval = setInterval(updateBridgeTelemetry, 800);
    updateBridgeGraphic(1);
}

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
    initializeBridgeSystems();
});

// Hook into slidedown's navigation
// We listen for DOM changes or poll for slide changes to update graphics
let lastSlide = 1;
setInterval(() => {
    if (window.page && window.page.currentSlide !== lastSlide) {
        lastSlide = window.page.currentSlide;
        updateBridgeGraphic(lastSlide);
    }
}, 200);
