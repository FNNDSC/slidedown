/*
 * Nexus navigation: runtime dispatcher tests
 *
 * Exercises assets/js/slidedown.js under a minimal DOM stub, using only
 * node's built-in assert. No npm toolchain, no jsdom: the runtime is a
 * dispatcher over a compile-time graph, so the surface worth testing is
 * small and does not need a real document.
 *
 * Run:  node tests/js/nexus.test.js
 */

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SOURCE = path.join(__dirname, '..', '..', 'assets', 'js', 'slidedown.js');

/**
 * Minimal sessionStorage stub.
 *
 * @param {boolean} throws  When true, every operation throws, as in
 *                          private-browsing modes.
 * @returns {object} Storage-like object.
 */
function storage_make(throws) {
    const data = {};
    return {
        data,
        getItem(k) {
            if (throws) { throw new Error('storage disabled'); }
            return Object.prototype.hasOwnProperty.call(data, k)
                ? data[k] : null;
        },
        setItem(k, v) {
            if (throws) { throw new Error('storage disabled'); }
            data[k] = String(v);
        }
    };
}

// Anchor at (100,200), 300x40, so its centre lands on (250,220).
const RECT_ANCHOR_DEFAULT = { left: 100, top: 200, width: 300, height: 40 };

// A slide fills the 2560x1440 baseline with its origin at the origin, so
// slide-local coordinates and screen coordinates differ only by scale.
const RECT_SLIDE = { left: 0, top: 0, width: 2560, height: 1440 };

// The heading a spoke arrives as. Three times the entry's height, and
// offset from it on both axes, so a flight between them is unambiguous.
const RECT_HEADING = { left: 200, top: 100, width: 1200, height: 120 };

/**
 * Build a stub heading element.
 *
 * @returns {object} Element-like stub.
 */
function headingElement_make() {
    return {
        style: { visibility: '', opacity: '', transition: '' },
        removeAttribute() {},
        querySelectorAll: () => [],
        cloneNode: () => headingElement_make(),
        getBoundingClientRect: () => RECT_HEADING
    };
}

/**
 * Build a stub anchor element carrying a jump address.
 *
 * @param {string} address  data-jump value.
 * @returns {object} Anchor stub with a recording classList.
 */
function anchorElement_make(address, revealed, rect) {
    const classes = new Set();
    return {
        classes,
        // Unset style properties read as empty strings in a real DOM, and
        // the runtime restores them by writing that back.
        style: { visibility: '', opacity: '', transition: '' },
        removeAttribute() {},
        querySelectorAll: () => [],
        cloneNode: () => anchorElement_make(address, revealed, rect),
        getAttribute: (n) => (n === 'data-jump' ? address : null),
        classList: {
            add: (c) => classes.add(c),
            remove: (c) => classes.delete(c),
            contains: (c) => classes.has(c)
        },
        // Revealed anchors report no hiding snippet above them.
        closest: (sel) => (sel === '.snippet' && !revealed ? {
            classList: { contains: (cls) => cls === 'sl-hidden' }
        } : null),
        getBoundingClientRect: () => rect || RECT_ANCHOR_DEFAULT
    };
}

/**
 * Find a stub anchor for a slide matching a querySelector expression.
 *
 * @param {object} anchors   Map of slide number -> {address: revealed}.
 * @param {number} slide     Slide being queried.
 * @param {string} selector  The .sd-jump[data-jump="..."] expression.
 * @returns {object|null} Anchor stub, or null when absent.
 */
function anchor_find(slideAnchors, selector) {
    const match = /data-jump="([^"]+)"/.exec(selector || '');
    if (!match) {
        return null;
    }

    for (const anchor of slideAnchors) {
        if (anchor.getAttribute('data-jump') === match[1]) {
            return anchor;
        }
    }
    return null;
}

/**
 * Build a sandbox with just enough DOM for slidedown.js to load.
 *
 * @param {object} options
 * @param {object|null} options.graph  Navigation graph to expose, or null.
 * @param {string} options.search      window.location.search value.
 * @param {number} options.slideCount  Number of slides in the fake deck.
 * @returns {object} The evaluated sandbox context.
 */
function context_make(options) {
    const opts = Object.assign(
        { graph: null, search: '', slideCount: 0 }, options || {}
    );

    const elements = {};
    if (opts.graph !== null) {
        elements.nexusGraph = {
            textContent: typeof opts.graph === 'string'
                ? opts.graph
                : JSON.stringify(opts.graph)
        };
    }
    if (opts.transition) {
        elements.slideTransition = { innerHTML: opts.transition };
    }
    if (opts.chrome) {
        // Footer furniture slide_commit writes to. Only the tests that
        // drive a real transition need these.
        elements.pageTitle    = { innerHTML: '' };
        elements.slideCounter = { innerHTML: '' };
        elements.slideBar     = { style: {} };
    }
    if (opts.slideCount > 0) {
        elements.numberOfSlides = { innerHTML: String(opts.slideCount) };
        elements.slideIDprefix = { innerHTML: 'slide-' };
        for (let i = 1; i <= opts.slideCount; i++) {
            // One stable stub per anchor, so a class added by the runtime
            // is still there when the test looks for it.
            const declared = (opts.anchors && opts.anchors[i]) || {};
            const slideAnchors = Object.keys(declared).map(
                (addr) => anchorElement_make(
                    addr, declared[addr], (opts.rects || {})[addr]
                )
            );

            const heading = headingElement_make();

            elements['slide-' + i] = {
                style: { visibility: '', opacity: '', transition: '' },
                heading,
                getElementsByClassName: () => [],
                offsetLeft: 0,
                offsetTop: 0,
                offsetWidth: 2560,
                offsetHeight: 1440,
                // Anchors declared per slide via options.anchors, so tests
                // can control whether a jump is revealed.
                querySelector: (sel) => (
                    sel === 'h1' ? heading : anchor_find(slideAnchors, sel)
                ),
                // Selector-aware: the runtime also asks a slide for its
                // typewriters, which are not anchors and answer a
                // different interface.
                querySelectorAll: (sel) => (
                    String(sel).indexOf('sd-jump') >= 0 ? slideAnchors : []
                ),
                anchors: slideAnchors,
                getBoundingClientRect: () => RECT_SLIDE
            };
            elements['slide-' + i + '-title'] = { innerHTML: 'Slide ' + i };
        }
    }

    const sandbox = {
        console: { log() {}, warn() {}, error() {} },
        URLSearchParams,
        setTimeout,
        clearTimeout,
        transitions: [],
        document: {
            getElementById: (id) => elements[id] || null,
            // The viewport is the box a slide fills, and carries the
            // scale scalePresentation() fitted it to the window with.
            querySelector: (sel) => (
                sel === '.presentation-viewport'
                    ? {
                        offsetWidth: 2560,
                        offsetHeight: 1440,
                        getBoundingClientRect: () => RECT_SLIDE
                    }
                    : null
            ),
            querySelectorAll: () => [],
            getElementsByClassName: () => [],
            addEventListener() {},
            body: {},
            onkeydown: null,
            onclick: null
        },
        window: {
            location: { search: opts.search, pathname: '/deck/' },
            matchMedia: (query) => ({
                matches: query === '(prefers-reduced-motion: reduce)'
                            && opts.reducedMotion === true
            }),
            addEventListener() {},
            innerWidth: 2560,
            innerHeight: 1440,
            onload: null,
            sessionStorage: opts.storage || storage_make()
        },
        $: () => ({})
    };
    sandbox.globalThis = sandbox;

    sandbox.elements = elements;

    vm.createContext(sandbox);
    vm.runInContext(fs.readFileSync(SOURCE, 'utf8'), sandbox, {
        filename: 'slidedown.js'
    });

    // Record navigation instead of touching the fake DOM.
    sandbox.page.slide_transition = function (from, to) {
        sandbox.transitions.push([from, to]);
    };

    return sandbox;
}

const GRAPH = {
    version: 1,
    slideCount: 3,
    slides: { 'the-menu': 1, depth: 2, registry: 3 },
    jumps: [
        { target: 'depth', targetSlide: 2, from: 1 },
        { target: 'registry', targetSlide: 3, from: 1 }
    ]
};

const tests = [];
function test(name, fn) { tests.push([name, fn]); }


/* --- graph parsing ---------------------------------------------------- */

test('parses a well-formed graph', () => {
    const ctx = context_make({ graph: GRAPH });
    assert.strictEqual(ctx.page.nexus.isLoaded(), true);
});

test('resolves an address to its slide number', () => {
    const ctx = context_make({ graph: GRAPH });
    assert.strictEqual(ctx.page.nexus.slideFor('depth'), 2);
    assert.strictEqual(ctx.page.nexus.slideFor('registry'), 3);
});

test('unknown address resolves to 0', () => {
    const ctx = context_make({ graph: GRAPH });
    assert.strictEqual(ctx.page.nexus.slideFor('nope'), 0);
});

test('empty address resolves to 0', () => {
    const ctx = context_make({ graph: GRAPH });
    assert.strictEqual(ctx.page.nexus.slideFor(''), 0);
    assert.strictEqual(ctx.page.nexus.slideFor(null), 0);
});

test('absent graph element leaves runtime unloaded', () => {
    const ctx = context_make({ graph: null });
    assert.strictEqual(ctx.page.nexus.isLoaded(), false);
    assert.strictEqual(ctx.page.nexus.slideFor('depth'), 0);
});

test('malformed JSON is survived, not thrown', () => {
    const ctx = context_make({ graph: '{ not json' });
    assert.strictEqual(ctx.page.nexus.isLoaded(), false);
});

test('future graph version is refused rather than guessed', () => {
    const future = Object.assign({}, GRAPH, { version: 99 });
    const ctx = context_make({ graph: future });
    assert.strictEqual(ctx.page.nexus.isLoaded(), false);
});


/* --- ?slide= resolution ----------------------------------------------- */

test('no slide parameter starts at slide 1', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    assert.strictEqual(ctx.page.startSlide_fromURL(), 1);
});

test('numeric slide parameter is honoured', () => {
    const ctx = context_make({
        graph: GRAPH, slideCount: 3, search: '?slide=2'
    });
    assert.strictEqual(ctx.page.startSlide_fromURL(), 2);
});

test('named slide parameter resolves through the graph', () => {
    const ctx = context_make({
        graph: GRAPH, slideCount: 3, search: '?slide=registry'
    });
    assert.strictEqual(ctx.page.startSlide_fromURL(), 3);
});

test('out-of-range number falls back to slide 1', () => {
    const ctx = context_make({
        graph: GRAPH, slideCount: 3, search: '?slide=99'
    });
    assert.strictEqual(ctx.page.startSlide_fromURL(), 1);
});

test('unknown name falls back to slide 1', () => {
    const ctx = context_make({
        graph: GRAPH, slideCount: 3, search: '?slide=ghost'
    });
    assert.strictEqual(ctx.page.startSlide_fromURL(), 1);
});

test('empty slide parameter falls back to slide 1', () => {
    const ctx = context_make({
        graph: GRAPH, slideCount: 3, search: '?slide='
    });
    assert.strictEqual(ctx.page.startSlide_fromURL(), 1);
});


/* --- slide_goto ------------------------------------------------------- */

test('goto moves the deck and records a transition', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    assert.strictEqual(ctx.page.slide_goto(3), true);
    assert.strictEqual(ctx.page.currentSlide, 3);
    assert.deepStrictEqual(ctx.transitions, [[1, 3]]);
});

test('goto to the current slide is a no-op', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    assert.strictEqual(ctx.page.slide_goto(1), false);
    assert.deepStrictEqual(ctx.transitions, []);
});

test('goto rejects out-of-range indices', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    assert.strictEqual(ctx.page.slide_goto(0), false);
    assert.strictEqual(ctx.page.slide_goto(4), false);
    assert.strictEqual(ctx.page.slide_goto(-1), false);
    assert.deepStrictEqual(ctx.transitions, []);
});

test('goto rejects non-numeric input', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    assert.strictEqual(ctx.page.slide_goto('2'), false);
    assert.strictEqual(ctx.page.slide_goto(NaN), false);
    assert.strictEqual(ctx.page.slide_goto(undefined), false);
});


/* --- jump clicks ------------------------------------------------------ */

/**
 * Build a fake click event whose target sits inside a jump anchor.
 *
 * @param {string|null} address  data-jump value, or null for a non-jump.
 * @returns {object} Event stub with a prevented flag.
 */
function clickEvent_make(address) {
    const anchor = address === null ? null : {
        getAttribute: (name) => (name === 'data-jump' ? address : null)
    };
    const event = {
        prevented: false,
        preventDefault() { this.prevented = true; },
        target: {
            closest: (sel) => (sel === '.sd-jump' ? anchor : null)
        }
    };
    return event;
}

test('clicking a jump navigates and suppresses the default', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    const event = clickEvent_make('depth');

    assert.strictEqual(ctx.page.jumpClick_process(event), true);
    assert.strictEqual(event.prevented, true);
    assert.strictEqual(ctx.page.currentSlide, 2);
});

test('clicking a non-jump is not handled', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    const event = clickEvent_make(null);

    assert.strictEqual(ctx.page.jumpClick_process(event), false);
    assert.strictEqual(event.prevented, false);
    assert.deepStrictEqual(ctx.transitions, []);
});

test('jump to an unknown address does not move the deck', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    const event = clickEvent_make('ghost');

    // Still handled — the click belonged to a jump, so it must not also
    // advance the slide.
    assert.strictEqual(ctx.page.jumpClick_process(event), true);
    assert.deepStrictEqual(ctx.transitions, []);
});

test('a jump click does not also advance the deck', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    const event = clickEvent_make('registry');
    event.clientX = 2000;   // right half: would advance if mishandled

    ctx.page.checkForMouseClick.call(ctx.page, event);

    // Exactly one transition, to the jump target — not an advance.
    assert.deepStrictEqual(ctx.transitions, [[1, 3]]);
});


/* --- nexus mode ------------------------------------------------------- */

const NEXUS_GRAPH = {
    version: 1,
    slideCount: 4,
    slides: { 'the-menu': 1, depth: 2, registry: 3, 'back': 4 },
    jumps: [],
    isNexusDeck: true,
    nexuses: [
        { id: 'menu', slide: 1, jumps: ['depth', 'registry'] },
        { id: 'menu', slide: 4, jumps: ['depth', 'registry'] }
    ]
};

/** Anchors for slide 1 with both jumps revealed. */
const REVEALED = { 1: { depth: true, registry: true } };

test('a deck with a nexus is a nexus deck', () => {
    const ctx = context_make({ graph: NEXUS_GRAPH, slideCount: 4 });
    assert.strictEqual(ctx.page.nexus.isNexusDeck(), true);
});

test('a deck with jumps but no nexus is not a nexus deck', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });
    assert.strictEqual(ctx.page.nexus.isNexusDeck(), false);
});

test('placementFor finds the nexus on a slide', () => {
    const ctx = context_make({ graph: NEXUS_GRAPH, slideCount: 4 });
    assert.strictEqual(ctx.page.nexus.placementFor(1).id, 'menu');
    assert.strictEqual(ctx.page.nexus.placementFor(4).id, 'menu');
});

test('placementFor returns null off a nexus slide', () => {
    const ctx = context_make({ graph: NEXUS_GRAPH, slideCount: 4 });
    assert.strictEqual(ctx.page.nexus.placementFor(2), null);
});

test('the same nexus placed twice yields distinct placements', () => {
    const ctx = context_make({ graph: NEXUS_GRAPH, slideCount: 4 });
    const first = ctx.page.nexus.placementFor(1);
    const second = ctx.page.nexus.placementFor(4);

    assert.strictEqual(first.id, second.id);
    assert.notStrictEqual(first.slide, second.slide);
});


/* --- digit keys ------------------------------------------------------- */

test('digit jumps to the nth entry of the current nexus', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH, slideCount: 4, anchors: REVEALED
    });

    assert.strictEqual(ctx.page.nexusDigit_process(2), true);
    assert.strictEqual(ctx.page.currentSlide, 3);
});

test('digit beyond the entry count is ignored', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH, slideCount: 4, anchors: REVEALED
    });

    assert.strictEqual(ctx.page.nexusDigit_process(5), false);
    assert.deepStrictEqual(ctx.transitions, []);
});

test('digits do nothing off a nexus slide', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH, slideCount: 4, anchors: REVEALED
    });
    ctx.page.currentSlide = 2;

    assert.strictEqual(ctx.page.nexusDigit_process(1), false);
    assert.deepStrictEqual(ctx.transitions, []);
});

test('an unrevealed jump is inert', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH,
        slideCount: 4,
        anchors: { 1: { depth: false, registry: true } }
    });

    // Sending the room to a topic they have not seen listed is never
    // intended.
    assert.strictEqual(ctx.page.nexusDigit_process(1), false);
    assert.deepStrictEqual(ctx.transitions, []);
});

test('a revealed jump beside an unrevealed one still works', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH,
        slideCount: 4,
        anchors: { 1: { depth: false, registry: true } }
    });

    assert.strictEqual(ctx.page.nexusDigit_process(2), true);
    assert.strictEqual(ctx.page.currentSlide, 3);
});

test('modified digit presses are left alone', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH, slideCount: 4, anchors: REVEALED
    });

    const handled = ctx.page.nexusDigit_keyHandle({ key: '1', ctrlKey: true });
    assert.strictEqual(handled, false);
});

test('zero is not a nexus digit', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH, slideCount: 4, anchors: REVEALED
    });

    // 0 belongs to the typography scale.
    assert.strictEqual(
        ctx.page.nexusDigit_keyHandle({ key: '0' }), false
    );
});

test('non-digit keys are left alone', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH, slideCount: 4, anchors: REVEALED
    });

    assert.strictEqual(
        ctx.page.nexusDigit_keyHandle({ key: 'a' }), false
    );
});


/* --- click-to-advance suppression ------------------------------------- */

test('clicking blank space on a nexus slide does not advance', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH, slideCount: 4, anchors: REVEALED
    });

    ctx.page.checkForMouseClick.call(ctx.page, {
        clientX: 2000,
        preventDefault() {},
        target: { closest: () => null }
    });

    assert.deepStrictEqual(ctx.transitions, []);
});

test('clicking blank space off a nexus slide still advances', () => {
    const ctx = context_make({
        graph: NEXUS_GRAPH, slideCount: 4, anchors: REVEALED
    });
    ctx.page.currentSlide = 2;

    ctx.page.checkForMouseClick.call(ctx.page, {
        clientX: 2000,
        preventDefault() {},
        target: { closest: () => null }
    });

    assert.deepStrictEqual(ctx.transitions, [[2, 3]]);
});


/* --- return semantics ------------------------------------------------- */

// Menu at 1, spokes at 2 and 3, closing menu at 4.
const SANDWICH = {
    version: 1,
    slideCount: 4,
    slides: { 'the-menu': 1, depth: 2, registry: 3, back: 4 },
    jumps: [],
    isNexusDeck: true,
    nexuses: [
        { id: 'menu', slide: 1, jumps: ['depth', 'registry'] },
        { id: 'menu', slide: 4, jumps: ['depth', 'registry'] }
    ],
    spokes: [
        { address: 'depth', start: 2, end: 2 },
        { address: 'registry', start: 3, end: 3 }
    ]
};

/**
 * A sandwich context with both jumps revealed on both menus.
 * @returns {object} sandbox
 */
function sandwich_make() {
    return context_make({
        graph: SANDWICH,
        slideCount: 4,
        anchors: {
            1: { depth: true, registry: true },
            4: { depth: true, registry: true }
        }
    });
}

test('spokeFor locates the spoke containing a slide', () => {
    const ctx = sandwich_make();
    assert.strictEqual(ctx.page.nexus.spokeFor(2).address, 'depth');
    assert.strictEqual(ctx.page.nexus.spokeFor(1), null);
});

test('spokeEndsAt marks the last slide of a spoke', () => {
    const ctx = sandwich_make();
    assert.strictEqual(ctx.page.nexus.spokeEndsAt(2), true);
    assert.strictEqual(ctx.page.nexus.spokeEndsAt(1), false);
});

test('jumping records a return point', () => {
    const ctx = sandwich_make();
    ctx.page.nexusDigit_process(1);

    assert.strictEqual(ctx.page.l_returnStack.length, 1);
    assert.strictEqual(ctx.page.l_returnStack[0].slide, 1);
});

test('advancing off the end of a jumped-into spoke returns', () => {
    const ctx = sandwich_make();
    ctx.page.nexusDigit_process(1);         // menu(1) -> depth(2)
    ctx.transitions.length = 0;

    ctx.page.rightArrow_process();

    // Back to the menu it came from, not onward to slide 3.
    assert.strictEqual(ctx.page.currentSlide, 1);
    assert.deepStrictEqual(ctx.transitions, [[2, 1]]);
});

test('a spoke walked into linearly falls through instead', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 2;              // arrived by walking
    ctx.transitions.length = 0;

    ctx.page.rightArrow_process();

    // The mirror rule: no jump, so no return.
    assert.strictEqual(ctx.page.currentSlide, 3);
});

test('return restores the departure reveal count', () => {
    const ctx = sandwich_make();
    ctx.page.l_snippetPerSlideON[0] = 1;    // one of two entries shown
    ctx.page.nexusDigit_process(1);

    assert.strictEqual(ctx.page.l_returnStack[0].revealed, 1);
});

test('returning empties the stack', () => {
    const ctx = sandwich_make();
    ctx.page.nexusDigit_process(1);
    ctx.page.return_process();

    assert.strictEqual(ctx.page.l_returnStack.length, 0);
});

test('return goes to the placement departed from, not the definition', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 4;              // the closing menu
    ctx.page.nexusDigit_process(1);         // -> depth(2)
    ctx.page.return_process();

    // Back to placement 4, not to placement 1.
    assert.strictEqual(ctx.page.currentSlide, 4);
});

test('escape returns from mid-spoke, not only from its end', () => {
    const wide = JSON.parse(JSON.stringify(SANDWICH));
    wide.spokes[0].end = 3;                 // depth spans slides 2-3

    const ctx = context_make({
        graph: wide,
        slideCount: 4,
        anchors: { 1: { depth: true, registry: true } }
    });

    ctx.page.nexusDigit_process(1);         // -> slide 2
    ctx.page.slide_goto(3);                 // still inside the spoke
    ctx.page.return_process();

    assert.strictEqual(ctx.page.currentSlide, 1);
});

test('return with no history falls back to the preceding nexus', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 3;              // deep-linked straight in
    assert.strictEqual(ctx.page.l_returnStack.length, 0);

    assert.strictEqual(ctx.page.return_process(), true);
    assert.strictEqual(ctx.page.currentSlide, 1);
});

test('return outside any nexus deck does nothing', () => {
    const ctx = context_make({ graph: GRAPH, slideCount: 3 });

    assert.strictEqual(ctx.page.return_process(), false);
});

test('jumping from a non-nexus slide records no return point', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 2;              // a spoke, not a menu

    assert.strictEqual(ctx.page.return_push(), false);
    assert.strictEqual(ctx.page.l_returnStack.length, 0);
});


/* --- visited marking -------------------------------------------------- */

test('jumping marks the target visited', () => {
    const ctx = sandwich_make();
    ctx.page.nexusDigit_process(1);

    assert.strictEqual(ctx.page.d_visited.depth, true);
    assert.strictEqual(ctx.page.d_visited.registry, undefined);
});

test('visited state is keyed on the target, not the placement', () => {
    const ctx = sandwich_make();
    ctx.page.nexusDigit_process(1);         // from the opening menu

    // The closing menu is a different placement of the same nexus and
    // must agree that this topic has been covered.
    ctx.page.visited_apply(4);
    const anchor = ctx.elements['slide-4'].anchors
        .find((a) => a.getAttribute('data-jump') === 'depth');

    assert.strictEqual(anchor.classList.contains('sd-jump--visited'), true);
});

test('unvisited jumps carry no visited class', () => {
    const ctx = sandwich_make();
    ctx.page.nexusDigit_process(1);
    ctx.page.visited_apply(4);

    const anchor = ctx.elements['slide-4'].anchors
        .find((a) => a.getAttribute('data-jump') === 'registry');

    assert.strictEqual(anchor.classList.contains('sd-jump--visited'), false);
});

test('visited state survives a reload', () => {
    const storage = storage_make();

    const first = context_make({
        graph: SANDWICH, slideCount: 4, storage,
        anchors: { 1: { depth: true, registry: true } }
    });
    first.page.nexusDigit_process(1);

    // Same storage, fresh page: the browser died and came back.
    const second = context_make({
        graph: SANDWICH, slideCount: 4, storage,
        anchors: { 1: { depth: true, registry: true } }
    });

    assert.strictEqual(second.page.d_visited.depth, true);
});

test('disabled storage does not break navigation', () => {
    const ctx = context_make({
        graph: SANDWICH,
        slideCount: 4,
        storage: storage_make(true),
        anchors: { 1: { depth: true, registry: true } }
    });

    // Private browsing: marking must degrade, not throw.
    assert.strictEqual(ctx.page.nexusDigit_process(1), true);
    assert.strictEqual(ctx.page.currentSlide, 2);
});

test('marking an empty address is refused', () => {
    const ctx = sandwich_make();
    assert.strictEqual(ctx.page.visited_mark(''), false);
});


/* --- zoom transition -------------------------------------------------- */

/**
 * Read a runtime constant out of a sandbox.
 *
 * Top-level const declarations do not become properties of the sandbox
 * global, so they have to be evaluated in the context rather than read
 * off it. Going through the runtime keeps the tests honest if the
 * constant is ever retuned.
 *
 * @param {object} ctx   Contextified sandbox.
 * @param {string} name  Constant to read.
 * @returns {*} Its value.
 */
function constant_read(ctx, name) {
    return vm.runInContext(name, ctx);
}

/**
 * Assert an entry box.
 *
 * Objects built inside the vm sandbox carry that realm's prototype, so
 * deepStrictEqual rejects them however equal their contents.
 *
 * @param {object|null} rect  Rect under test.
 * @param {object} expected   {left, top, width, height}.
 */
function rect_assert(rect, expected) {
    assert.ok(rect, 'expected a rect, got ' + rect);
    for (const k of ['left', 'top', 'width', 'height']) {
        assert.strictEqual(rect[k], expected[k], 'rect.' + k);
    }
}

/**
 * A sandwich context that has opted into the zoom transition.
 *
 * @param {object} extra  Additional context_make options.
 * @returns {object} sandbox
 */
function zoomable_make(extra) {
    return context_make(Object.assign({
        graph: SANDWICH,
        slideCount: 4,
        transition: 'zoom',
        anchors: {
            1: { depth: true, registry: true },
            4: { depth: true, registry: true }
        }
    }, extra || {}));
}

test('the transition is read from the deck, defaulting to none', () => {
    assert.strictEqual(sandwich_make().page.str_transition, 'none');
    assert.strictEqual(zoomable_make().page.str_transition, 'zoom');
});

test('an entry box is the anchor jumped from', () => {
    const ctx = zoomable_make();
    rect_assert(ctx.page.zoom_anchorRect(1, 'depth'), RECT_ANCHOR_DEFAULT);
});

test('an unrevealed anchor yields no box', () => {
    const ctx = zoomable_make({ anchors: { 1: { depth: false } } });
    assert.strictEqual(ctx.page.zoom_anchorRect(1, 'depth'), null);
});

test('an absent anchor yields no box', () => {
    const ctx = zoomable_make();
    assert.strictEqual(ctx.page.zoom_anchorRect(1, 'nope'), null);
});

test('a zero-sized anchor yields no box', () => {
    const ctx = zoomable_make({
        rects: { depth: { left: 0, top: 0, width: 0, height: 0 } }
    });
    assert.strictEqual(ctx.page.zoom_anchorRect(1, 'depth'), null);
});

test('a jump into a spoke resolves a box', () => {
    const ctx = zoomable_make();
    rect_assert(
        ctx.page.zoom_rectResolve(1, 2, { jumpAddress: 'depth' }),
        RECT_ANCHOR_DEFAULT
    );
});

test('a plain advance resolves no box', () => {
    // Sequential slides do not contain one another, so there is nothing
    // for the movement to assert about them.
    const ctx = zoomable_make();
    assert.strictEqual(ctx.page.zoom_rectResolve(1, 2, {}), null);
});

test('a return flies back to the box recorded on departure', () => {
    const ctx = zoomable_make();
    rect_assert(
        ctx.page.zoom_rectResolve(2, 1, {
            isReturn: true, rect: RECT_ANCHOR_DEFAULT
        }),
        RECT_ANCHOR_DEFAULT
    );
});

test('a return with no recorded box does not animate', () => {
    // The deep-link fallback has no departure to have measured.
    const ctx = zoomable_make();
    assert.strictEqual(
        ctx.page.zoom_rectResolve(2, 1, { isReturn: true, rect: null }), null
    );
});

test('reduced motion refuses every box', () => {
    const ctx = zoomable_make({ reducedMotion: true });
    assert.strictEqual(ctx.page.motion_isReduced(), true);
    assert.strictEqual(
        ctx.page.zoom_rectResolve(1, 2, { jumpAddress: 'depth' }), null
    );
});

test('a deck that did not opt in resolves no box', () => {
    const ctx = sandwich_make();
    assert.strictEqual(
        ctx.page.zoom_rectResolve(1, 2, { jumpAddress: 'depth' }), null
    );
});

test('a non-nexus deck resolves no box', () => {
    const ctx = context_make({
        graph: GRAPH, slideCount: 3, transition: 'zoom',
        anchors: { 1: { depth: true } }
    });
    assert.strictEqual(
        ctx.page.zoom_rectResolve(1, 2, { jumpAddress: 'depth' }), null
    );
});

test('a move to the slide already showing resolves no box', () => {
    const ctx = zoomable_make();
    assert.strictEqual(
        ctx.page.zoom_rectResolve(1, 1, { jumpAddress: 'depth' }), null
    );
});

test('a departure records the box it must return through', () => {
    const ctx = zoomable_make();
    ctx.page.currentSlide = 1;
    assert.strictEqual(ctx.page.return_push('depth'), true);

    const departure = ctx.page.l_returnStack[0];
    rect_assert(departure.rect, RECT_ANCHOR_DEFAULT);
    assert.strictEqual(departure.slide, 1);
});

test('a departure with no address records no box', () => {
    const ctx = zoomable_make();
    ctx.page.currentSlide = 1;
    ctx.page.return_push();
    assert.strictEqual(ctx.page.l_returnStack[0].rect, null);
});


/* --- the shared element ----------------------------------------------- */

/**
 * A stand-in for the flying copy.
 *
 * @returns {object} Element-like stub.
 */
function ghostStub_make() {
    return {
        style: {},
        offsetWidth: 300,
        parentNode: null,
        addEventListener() {},
        removeEventListener() {}
    };
}

// Entry is 40 high at (100,200); heading is 120 high at (200,100). So the
// carry scales by 120/40 and shifts by (200-100) across and by
// (100+60)-(200+20) down.
const TRANSFORM_TOHEADING = 'translate(100px, -60px) scale(3)';
const TRANSFORM_TOENTRY =
    'translate(-100px, 60px) scale(' + (40 / 120) + ')';

test('a spoke is found by the heading it arrives as', () => {
    const ctx = zoomable_make();
    assert.strictEqual(
        ctx.page.heading_find(2), ctx.elements['slide-2'].heading
    );
});

test('the entry is carried onto the heading', () => {
    const ctx = zoomable_make();
    const ghost = ghostStub_make();

    ctx.page.ghost_fly(ghost, RECT_ANCHOR_DEFAULT, RECT_HEADING, () => {});
    assert.strictEqual(ghost.style.transform, TRANSFORM_TOHEADING);
});

test('the heading is carried back onto the entry', () => {
    const ctx = zoomable_make();
    const ghost = ghostStub_make();

    ctx.page.ghost_fly(ghost, RECT_HEADING, RECT_ANCHOR_DEFAULT, () => {});
    assert.strictEqual(ghost.style.transform, TRANSFORM_TOENTRY);
});

test('the carry is scaled by height, not by width', () => {
    // The two phrasings are rarely the same length, but both are a line
    // of type, and it is the type that has to match on arrival.
    const ctx = zoomable_make();
    const ghost = ghostStub_make();

    ctx.page.ghost_fly(ghost, RECT_ANCHOR_DEFAULT, RECT_HEADING, () => {});
    const scale = /scale\(([^)]+)\)/.exec(ghost.style.transform)[1];
    assert.strictEqual(
        Number(scale), RECT_HEADING.height / RECT_ANCHOR_DEFAULT.height
    );
});

test('a ghost that cannot fly finishes rather than hangs', () => {
    const ctx = zoomable_make();
    let done = false;

    ctx.page.ghost_fly(null, RECT_ANCHOR_DEFAULT, RECT_HEADING, () => {
        done = true;
    });

    assert.strictEqual(done, true);
    assert.strictEqual(ctx.page.l_zoomPending.length, 0);
});

test('landing hands over to the real element', () => {
    const ctx = zoomable_make();
    const ghost = ghostStub_make();
    const arriving = headingElement_make();
    arriving.style.visibility = 'hidden';

    ctx.page.ghost_land(ghost, arriving, () => {});

    // The copy goes as the real one comes, so a wording that differs
    // between the two does not pop.
    assert.strictEqual(arriving.style.visibility, '');
    assert.strictEqual(arriving.style.opacity, '1');
    assert.strictEqual(ghost.style.opacity, '0');
});


/* --- lifting a slide out of the flow ---------------------------------- */

test('a departing slide is pinned to the box it already occupies', () => {
    const ctx = zoomable_make();
    ctx.page.slide_detach(1);

    // Two flex children cannot both be shown without stacking, so the
    // outgoing one is taken out of the flow exactly where it stands.
    const slide = ctx.elements['slide-1'];
    assert.strictEqual(slide.style.position, 'absolute');
    assert.strictEqual(slide.style.width, '2560px');
    assert.strictEqual(slide.style.height, '1440px');
    assert.strictEqual(slide.style.left, '0px');
});

test('a pinned slide is put back into the flow', () => {
    const ctx = zoomable_make();
    ctx.page.slide_detach(1);
    ctx.page.slide_reattach(1);

    const slide = ctx.elements['slide-1'];
    assert.strictEqual(slide.style.position, '');
    assert.strictEqual(slide.style.width, '');
    assert.strictEqual(slide.style.opacity, '');
});


/* --- zoom sequencing -------------------------------------------------- */

/**
 * A zoom context whose slide_transition runs for real, with the flying
 * copy replaced by a stub.
 *
 * Building a true ghost needs cloneNode, getComputedStyle and a live
 * document; the choreography it serves needs none of that, and the
 * choreography is what can regress.
 *
 * @returns {object} sandbox, with ctx.ghost holding the stub
 */
function zoomLive_make() {
    const ctx = zoomable_make({ chrome: true });
    delete ctx.page.slide_transition;   // restore the prototype's

    ctx.ghost = ghostStub_make();
    ctx.page.ghost_create = () => ctx.ghost;
    return ctx;
}

/**
 * Run exactly one pending finisher.
 *
 * zoom_cancel() drains to the end, which is the wrong instrument for
 * looking at the state between the selection beat and the flight.
 *
 * @param {object} ctx  sandbox
 */
function beat_advance(ctx) {
    const finish = ctx.page.l_zoomPending.shift();
    assert.ok(finish, 'expected something pending');
    finish();
}

/**
 * The anchor stub for an address on a slide.
 *
 * @param {object} ctx     sandbox
 * @param {number} slide   Slide number.
 * @param {string} address Jump address.
 * @returns {object} Anchor stub.
 */
function anchor_of(ctx, slide, address) {
    return ctx.elements['slide-' + slide].querySelector(
        '.sd-jump[data-jump="' + address + '"]'
    );
}

test('the chosen entry is marked before anything moves', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 1;
    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });

    // The room is told what was picked, and nothing has flown yet.
    assert.strictEqual(
        anchor_of(ctx, 1, 'depth').classList.contains('sd-jump--selected'),
        true
    );
    assert.strictEqual(ctx.ghost.style.transform, undefined);
});

test('the mark is taken off once the flight begins', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 1;
    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });
    beat_advance(ctx);

    assert.strictEqual(
        anchor_of(ctx, 1, 'depth').classList.contains('sd-jump--selected'),
        false
    );
    assert.strictEqual(ctx.ghost.style.transform, TRANSFORM_TOHEADING);
});

test('a return marks nothing, having selected nothing', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 2;
    ctx.page.slide_transition(2, 1, {
        isReturn: true, rect: RECT_ANCHOR_DEFAULT
    });

    assert.strictEqual(
        anchor_of(ctx, 1, 'depth').classList.contains('sd-jump--selected'),
        false
    );
});

test('a return carries the heading back to the entry it came from', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 2;
    ctx.page.slide_transition(2, 1, {
        isReturn: true, rect: RECT_ANCHOR_DEFAULT
    });

    // No address is passed on a return; the spoke names its own entry.
    assert.strictEqual(ctx.ghost.style.transform, TRANSFORM_TOENTRY);
});

test('both ends of the shared element step aside for the copy', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 1;
    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });
    beat_advance(ctx);

    // Otherwise the text would be on screen twice for the whole flight.
    assert.strictEqual(
        anchor_of(ctx, 1, 'depth').style.visibility, 'hidden'
    );
    assert.strictEqual(ctx.elements['slide-2'].heading.style.visibility,
                       'hidden');
});

test('the heading is measured only once the flow is clear', () => {
    const ctx = zoomLive_make();
    const spoke = ctx.elements['slide-2'];

    // Both slides are flex children. Measured while the outgoing one is
    // still in the flow, the incoming one lays out beneath it and its
    // heading reads half a page too low — which sent the carry
    // downwards instead of up.
    const RECT_PUSHEDDOWN = { left: 200, top: 900, width: 1200, height: 120 };
    spoke.heading.getBoundingClientRect = () => (
        ctx.elements['slide-1'].style.position === 'absolute'
            ? RECT_HEADING
            : RECT_PUSHEDDOWN
    );

    ctx.page.currentSlide = 1;
    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });
    beat_advance(ctx);

    // Upwards, onto the real heading position.
    assert.strictEqual(ctx.ghost.style.transform, TRANSFORM_TOHEADING);
});

test('both slides are on screen while the copy is in flight', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 1;
    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });
    beat_advance(ctx);

    // The pages cross over underneath the text rather than cutting.
    assert.strictEqual(ctx.elements['slide-1'].style.display, 'block');
    assert.strictEqual(ctx.elements['slide-1'].style.position, 'absolute');
    assert.strictEqual(ctx.elements['slide-2'].style.display, 'block');
    assert.strictEqual(ctx.elements['slide-2'].style.opacity, '1');
});

test('the deck is left with nothing pinned or concealed', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 1;
    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });
    ctx.page.zoom_cancel();

    const leaving = ctx.elements['slide-1'];
    const arrived = ctx.elements['slide-2'];

    assert.strictEqual(leaving.style.display, 'none');
    assert.strictEqual(leaving.style.position, '');
    assert.strictEqual(leaving.style.opacity, '');
    assert.strictEqual(arrived.style.display, 'block');
    assert.strictEqual(arrived.style.opacity, '');
    assert.strictEqual(anchor_of(ctx, 1, 'depth').style.visibility, '');
    assert.strictEqual(arrived.heading.style.visibility, '');
    assert.strictEqual(ctx.page.l_zoomPending.length, 0);
});

test('outrunning the animation still lands on the destination', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 1;
    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });

    // The presenter presses again before the movement finishes.
    ctx.page.zoom_cancel();

    assert.strictEqual(ctx.elements['slide-1'].style.display, 'none');
    assert.strictEqual(ctx.elements['slide-2'].style.display, 'block');
    assert.strictEqual(ctx.page.l_zoomPending.length, 0);
});

test('a non-animating move commits immediately', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 1;

    // A plain advance: no jump address, so no flight and no deferral.
    ctx.page.slide_transition(1, 2, {});

    assert.strictEqual(ctx.elements['slide-2'].style.display, 'block');
    assert.strictEqual(ctx.page.l_zoomPending.length, 0);
});

test('a ghost that cannot be built falls back to the instant swap', () => {
    const ctx = zoomLive_make();
    ctx.page.ghost_create = () => null;
    ctx.page.currentSlide = 1;

    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });
    beat_advance(ctx);

    assert.strictEqual(ctx.elements['slide-2'].style.display, 'block');
    assert.strictEqual(ctx.page.l_zoomPending.length, 0);
});

test('a spoke with no heading falls back to the instant swap', () => {
    const ctx = zoomLive_make();
    ctx.page.heading_find = () => null;
    ctx.page.currentSlide = 1;

    ctx.page.slide_transition(1, 2, { jumpAddress: 'depth' });
    beat_advance(ctx);

    assert.strictEqual(ctx.elements['slide-2'].style.display, 'block');
    assert.strictEqual(ctx.page.l_zoomPending.length, 0);
});

/* --- cursor selection ------------------------------------------------- */

/**
 * A key event stub.
 *
 * @param {string} key    KeyboardEvent.key value.
 * @param {object} extra  Modifier flags to set.
 * @returns {object} Event-like stub.
 */
function key_make(key, extra) {
    return Object.assign({ key, ctrlKey: false, metaKey: false,
                           altKey: false, shiftKey: false }, extra || {});
}

/**
 * A menu of twelve entries, past the digit keys' ceiling of nine.
 *
 * @returns {object} sandbox
 */
function wideMenu_make() {
    const addresses = {};
    const jumps = [];
    const anchors = { 1: {} };
    for (let i = 1; i <= 12; i++) {
        const addr = 'topic-' + i;
        addresses[addr] = i + 1;
        jumps.push(addr);
        anchors[1][addr] = true;
    }

    return context_make({
        slideCount: 13,
        anchors,
        graph: {
            version: 1, slideCount: 13,
            slides: Object.assign({ menu: 1 }, addresses),
            jumps: [], isNexusDeck: true,
            nexuses: [{ id: 'wide', slide: 1, jumps }],
            spokes: jumps.map((a, i) => ({ address: a, start: i + 2,
                                           end: i + 2 }))
        }
    });
}

test('a step down with no cursor lands on the first entry', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 1;

    assert.strictEqual(ctx.page.nexusCursor_keyHandle(key_make('ArrowDown')),
                       true);
    assert.strictEqual(ctx.page.index_cursor, 1);
    assert.strictEqual(
        anchor_of(ctx, 1, 'depth').classList.contains('sd-jump--cursor'),
        true
    );
});

test('a step up with no cursor lands on the last entry', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 1;

    ctx.page.nexusCursor_keyHandle(key_make('ArrowUp'));
    assert.strictEqual(ctx.page.index_cursor, 2);
    assert.strictEqual(
        anchor_of(ctx, 1, 'registry').classList.contains('sd-jump--cursor'),
        true
    );
});

test('the cursor wraps at both ends', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 1;

    ctx.page.cursor_move(1);            // 1
    ctx.page.cursor_move(1);            // 2
    ctx.page.cursor_move(1);            // wraps to 1
    assert.strictEqual(ctx.page.index_cursor, 1);

    ctx.page.cursor_move(-1);           // wraps to 2
    assert.strictEqual(ctx.page.index_cursor, 2);
});

test('the mark sits on one entry and no other', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 1;

    ctx.page.cursor_move(1);
    ctx.page.cursor_move(1);

    assert.strictEqual(
        anchor_of(ctx, 1, 'depth').classList.contains('sd-jump--cursor'),
        false
    );
    assert.strictEqual(
        anchor_of(ctx, 1, 'registry').classList.contains('sd-jump--cursor'),
        true
    );
});

test('the cursor skips entries not yet revealed', () => {
    const ctx = context_make({
        graph: SANDWICH, slideCount: 4,
        anchors: { 1: { depth: true, registry: false } }
    });
    ctx.page.currentSlide = 1;

    // An unannounced entry is not a choice the room has been offered.
    assert.deepStrictEqual(
        Array.from(ctx.page.cursorEntries_get(1)), ['depth']
    );

    ctx.page.cursor_move(1);
    ctx.page.cursor_move(1);
    assert.strictEqual(ctx.page.index_cursor, 1);
});

test('enter takes the jump the cursor is on', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 1;

    ctx.page.cursor_move(1);
    ctx.page.cursor_move(1);            // registry
    assert.strictEqual(ctx.page.nexusCursor_keyHandle(key_make('Enter')),
                       true);

    assert.strictEqual(ctx.page.currentSlide, 3);
    assert.strictEqual(ctx.page.d_visited['registry'], true);
    assert.strictEqual(ctx.page.l_returnStack.length, 1);
    assert.strictEqual(ctx.page.l_returnStack[0].slide, 1);
});

test('enter with no cursor is not consumed', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 1;
    assert.strictEqual(ctx.page.nexusCursor_keyHandle(key_make('Enter')),
                       false);
});

test('arrows off a menu are left to mean first and last slide', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 2;          // a spoke, not a menu

    assert.strictEqual(ctx.page.nexusCursor_keyHandle(key_make('ArrowDown')),
                       false);
    assert.strictEqual(ctx.page.index_cursor, 0);
});

test('a modified arrow is not a cursor step', () => {
    const ctx = sandwich_make();
    ctx.page.currentSlide = 1;

    for (const mod of ['ctrlKey', 'metaKey', 'altKey', 'shiftKey']) {
        const e = key_make('ArrowDown', { [mod]: true });
        assert.strictEqual(ctx.page.nexusCursor_keyHandle(e), false);
    }
    assert.strictEqual(ctx.page.index_cursor, 0);
});

test('the cursor does not survive leaving the menu', () => {
    const ctx = zoomLive_make();
    ctx.page.currentSlide = 1;
    ctx.page.cursor_move(1);

    ctx.page.slide_transition(1, 2, {});

    // A position within one menu means nothing on the next slide.
    assert.strictEqual(ctx.page.index_cursor, 0);
    assert.strictEqual(
        anchor_of(ctx, 1, 'depth').classList.contains('sd-jump--cursor'),
        false
    );
});

test('a menu may hold more entries than there are digit keys', () => {
    const ctx = wideMenu_make();
    ctx.page.currentSlide = 1;

    // Nine is a limit on the shortcut, not on the menu: the ceiling is
    // in the key handler, because 0 belongs to the typography scale and
    // a tenth entry has no key left to name it.
    assert.strictEqual(ctx.page.cursorEntries_get(1).length, 12);
    assert.strictEqual(ctx.page.nexusDigit_keyHandle(key_make('0')), false);

    for (let i = 0; i < 12; i++) {
        ctx.page.cursor_move(1);
    }
    assert.strictEqual(ctx.page.index_cursor, 12);

    ctx.page.cursor_activate();
    assert.strictEqual(ctx.page.currentSlide, 13);
});


/* --- runner ----------------------------------------------------------- */

let passed = 0;
const failures = [];

for (const [name, fn] of tests) {
    try {
        fn();
        passed++;
    } catch (err) {
        failures.push([name, err]);
    }
}

for (const [name, err] of failures) {
    console.error(`FAIL  ${name}\n      ${err.message}`);
}

console.log(`${passed} passed, ${failures.length} failed`);
process.exit(failures.length === 0 ? 0 : 1);
