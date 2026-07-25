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

/**
 * Build a stub anchor element carrying a jump address.
 *
 * @param {string} address  data-jump value.
 * @returns {object} Anchor stub with a recording classList.
 */
function anchorElement_make(address) {
    const classes = new Set();
    return {
        classes,
        getAttribute: (n) => (n === 'data-jump' ? address : null),
        classList: {
            add: (c) => classes.add(c),
            remove: (c) => classes.delete(c),
            contains: (c) => classes.has(c)
        }
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
function anchor_find(anchors, slide, selector) {
    if (!anchors || !anchors[slide]) {
        return null;
    }

    const match = /data-jump="([^"]+)"/.exec(selector || '');
    if (!match) {
        return null;
    }

    const revealed = anchors[slide][match[1]];
    if (revealed === undefined) {
        return null;
    }

    return {
        closest: (sel) => (sel === '.snippet' ? {
            classList: {
                contains: (cls) => cls === 'sl-hidden' && !revealed
            }
        } : null)
    };
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
    if (opts.slideCount > 0) {
        elements.numberOfSlides = { innerHTML: String(opts.slideCount) };
        elements.slideIDprefix = { innerHTML: 'slide-' };
        for (let i = 1; i <= opts.slideCount; i++) {
            const slideAnchors = Object.keys(
                (opts.anchors && opts.anchors[i]) || {}
            ).map(anchorElement_make);

            elements['slide-' + i] = {
                style: {},
                getElementsByClassName: () => [],
                // Anchors declared per slide via options.anchors, so tests
                // can control whether a jump is revealed.
                querySelector: (sel) => anchor_find(opts.anchors, i, sel),
                querySelectorAll: () => slideAnchors,
                anchors: slideAnchors
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
            querySelector: () => null,
            querySelectorAll: () => [],
            getElementsByClassName: () => [],
            addEventListener() {},
            body: {},
            onkeydown: null,
            onclick: null
        },
        window: {
            location: { search: opts.search, pathname: '/deck/' },
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
