(function () {
    const batchMs = 520;
    const batchMax = 4;
    const batchMin = 1;
    const pulseMs = 130;
    const randomBase = 10;

    function cascadeStyles_inject() {
        const style = document.createElement("style");
        style.textContent = `
            .data-wrapper .slidedown-cascade-pulse {
                color: var(--gold) !important;
                text-shadow: 0 0 0.45rem currentColor;
            }
        `;
        document.head.appendChild(style);
    }

    function reducedMotion_prefers() {
        return window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;
    }

    function digit_generate(length) {
        let value = "";
        for (let index = 0; index < length; index += 1) {
            value += Math.floor(Math.random() * randomBase).toString();
        }
        return value;
    }

    function cellValue_generate(cell) {
        const original = cell.dataset.originalValue || cell.textContent || "";
        const trimmed = original.trim();
        if (!/^\d+$/.test(trimmed)) {
            return original;
        }

        if (trimmed.length === 1 && trimmed === "0") {
            return trimmed;
        }

        return digit_generate(trimmed.length);
    }

    function cascadeCell_update(cell) {
        cell.classList.remove("slidedown-cascade-pulse");
        cell.dataset.originalValue = cell.dataset.originalValue
            || cell.textContent
            || "";
        cell.textContent = cellValue_generate(cell);
        cell.classList.add("slidedown-cascade-pulse");

        window.setTimeout(function () {
            cell.classList.remove("slidedown-cascade-pulse");
        }, pulseMs);
    }

    function randomIndex_get(limit) {
        return Math.floor(Math.random() * limit);
    }

    function batchSize_get() {
        return batchMin + randomIndex_get(batchMax - batchMin + 1);
    }

    function cascadeBatch_update(cells) {
        const usedIndexes = new Set();
        const batchSize = batchSize_get();

        while (usedIndexes.size < batchSize) {
            usedIndexes.add(randomIndex_get(cells.length));
        }

        usedIndexes.forEach(function (index) {
            cascadeCell_update(cells[index]);
        });
    }

    function dataCascade_animate() {
        const cells = Array.from(document.querySelectorAll(
            ".data-wrapper .data-column > div"
        ));

        if (cells.length === 0 || reducedMotion_prefers()) {
            return;
        }

        cascadeStyles_inject();
        window.setInterval(function () {
            cascadeBatch_update(cells);
        }, batchMs);
    }

    window.addEventListener("load", dataCascade_animate);
}());
