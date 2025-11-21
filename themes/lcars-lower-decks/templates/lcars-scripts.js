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

    if (dateEl) {
        dateEl.textContent = date;
    }
    if (timeEl) {
        timeEl.textContent = time;
    }
}

// Update immediately and then every second
updateLCARSClock();
setInterval(updateLCARSClock, 1000);

// Toggle top frame visibility - frames collapse/expand naturally
let topFrameHidden = false;
function toggleTopFrame(event) {
    // Stop event from bubbling to slide navigation click handler
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    const topFrame = document.querySelector('.left-frame-top');
    const rightFrameTop = document.querySelector('.right-frame-top');
    const button = document.getElementById('topBtn');
    const buttonText = button.querySelector('.hop');

    topFrameHidden = !topFrameHidden;

    if (topFrameHidden) {
        // Collapse frames - they'll naturally slide up as height goes to 0
        topFrame.classList.add('hidden');
        rightFrameTop.classList.add('hidden');
        buttonText.textContent = 'hide';
    } else {
        // Expand frames - they'll naturally slide down as height expands
        topFrame.classList.remove('hidden');
        rightFrameTop.classList.remove('hidden');
        buttonText.textContent = 'show';
    }
}

// Scroll to top function
function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Show top frame if it's hidden
    if (topFrameHidden) {
        toggleTopFrame();
    }
}
