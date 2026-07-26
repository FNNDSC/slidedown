/////////
///////////////////////////
///////// Object prototypes
///////////////////////////
/////////

/////////
///////// Debug object
/////////
/*
    This object provides a straightforward interface for simple debugging --
    mostly entering and exiting functions, printing some state, etc.
*/

function Debug(d) {
    /*
    Print some debugging info to console.

    d.functionName      string      name of function
    d.message           string      message
    d.var               variable    variable to print

    */

    this.functionName   = '<void>';
    this.message        = '<void>';
    this.var            = null;
    this.tab            = 0;

    if (d.constructor == Object) {
        prototype.argcheck(d)
    }

    if(typeof(d) === 'string' || d instanceof String) {
        this.functionName   = d
    }

}

Debug.prototype = {

    constructor:    Debug,

    argcheck:       function (d) {
        if (typeof (d.functionName) != 'undefined')
            this.functionName = d.functionName;
        if (typeof (d.message) != 'undefined')
            this.message = d.message;
        if (typeof (d.var) != 'undefined')
            this.var = d.var;
    },

    cl:             function () {
        console.log(' ');
    },

    indent:         function () {
        str_indent = '';
        for (i = 0; i < this.tab; i++)
            str_indent = str_indent + '\t';
        return str_indent;
    },

    entering:       function () {
        functionCallDepth += 1;
        this.tab = functionCallDepth;
        console.log(
            this.indent()           +
            '--------> Entering '   +
            this.functionName       +
            '...');
    },

    leaving:        function () {
        console.log(
            this.indent()       +
            'Leaving '          +
            this.functionName   +
            ' --------> ');
        functionCallDepth -= 1;
    },

    vlog:           function (d) {
        this.argcheck(d);
        if (typeof (this.var) === 'object') {
            console.log(
                this.indent()               +
                'In ' + this.functionName   +
                ': ' + d.message + ' = '
            );
            console.log(d.var);
        } else
            console.log(
                this.indent()               +
                'In ' + this.functionName   +
                ': ' + d.message    + ' = ' + d.var);
    },

    log:            function (d) {
        this.argcheck(d);
        console.log(
                this.indent()               +
                'In ' + this.functionName + ': ' + d.message);
    }

}

/////////
///////// DOM object
/////////

function DOM(al_keylist) {
    this.str_help = `

        This object provides a convenient abstraction
        for accessing and interacting with named components
        of the DOM, removing the very tight coupling that
        might occur by referening DOM literals directly in JS.

    `;
    this.l_DOM = al_keylist;
}

DOM.prototype = {
    constructor:    DOM,

    elements:           function() {
        return this.l_DOM;
    },

    get:                function(str_key) {
        if(this.l_DOM.includes(str_key)) {
            return $('#'+str_key).val()
        } else {
            return null;
        }
    },

    html:               function(str_key, str_val) {
        if(this.l_DOM.includes(str_key)) {
            $('#'+str_key).html(str_val)
        }
    },

    innerHTML_listadd:  function(str_key, l_val) {
        if(this.l_DOM.includes(str_key)) {
            for(const str_line of l_val) {
                document.getElementById(str_key).innerHTML += str_line;
            }
        }
    },

    innerHTML_listset:  function(str_key, l_val) {
        if(this.l_DOM.includes(str_key)) {
            document.getElementById(str_key).innerHTML = '';
            for(const str_line of l_val) {
                document.getElementById(str_key).innerHTML += str_line;
            }
        }
    },

    style_set:          function(str_key, d_style) {
        if(this.l_DOM.includes(str_key)) {
            for(const [key, value] of Object.entries(d_style)) {
                document.getElementById(str_key).style[key] = value;
            }
        }
    },

    type_set:           function(str_key, typeSet) {
        if(this.l_DOM.includes(str_key)) {
            document.getElementById(str_key).type = typeSet;
        }
    },

    set:                function(str_key, str_val) {
        if(this.l_DOM.includes(str_key)) {
            $('#'+str_key).val(str_val)
            return $('#'+str_key).val();
        } else {
            return null;
        }
    }
}

/////////
///////// URL object
/////////

function URL(dom) {
    this.str_help   = `

        This object parses the URL for parameters to set in the
        dashboard.

    `;
    this.dom        = dom;
    this.str_query  = window.location.search;
    this.urlParams  =  new URLSearchParams(this.str_query);
}

URL.prototype = {
    constructor:    URL,

    parse:          function() {
        this.dom.elements().forEach(el => {
            if(this.urlParams.has(el)) {
                this.dom.set(el, this.urlParams.get(el));
            }
        })
    }
}

/////////
///////// An initial markdown-ish object that understands some
///////// markdown in a string of text and converts to HTML
/////////
function SMarkDown() {
    this.str_help = `

        The Page object defines/interacts with the html page.

        The page element strings are "defined" here, and letious
        DOM objects that can interact with these elements are also
        instantiated.

        The directive for markdown is a markdown marker string,
        followed by a "function" string followed by optional
        "args" for that function. The arguments are separated
        by commas. The remainder of the string line is taken to be
        the string to which apply the markdown.

        So, markdown patterns are:

            <mdMarker><mdFunction>_<mdArg1>,<mdArg2>,...<mdArgN> string

        for example:

        _#_o_1 bullet 1 : create a snippet of "ordering" 1, with text 'bullet 1'
        _#_o_2 bullet 2 : create a snippet of "ordering" 2, with text 'bullet 2'

        _#_font_<figletFont> text : Render <text> with <figletFont>.
        See http://www.jave.de/figlet/fonts/overview.html for figlet fonts.
    `;

    this.str_textWithMarkDown       = "";
    this.str_textWithHTML           = "";

    this.mdMarker                   = "_#_";

}

SMarkDown.prototype = {
    constructor:                    SMarkDown,

    snippetMake:                function(al_argList, astr_text) {
        let str_help = `

            Replace the <astr_text> with the relevant snippet equivalent.

        `;

        str_order   = al_argList[0];
        astr_text   = `
        </pre>
        </div>
        <div class = "snippet" id="order-` + str_order + `"
        <pre>
        ` + astr_text + `
        </pre>
        </div>
        `;
        return astr_text;

    },

    fontify:                    function(al_argList, astr_text) {
        let str_help = `

            Replace the <astr_text> with a figlet font of the same.
            If invalid font, then return the astr_text unchanged.

        `;
        str_font    = al_argList[0];

    },

    markdown_process:           function(astr_commandArg, astr_text) {
        let str_help = `

            Perform the actual markdown execution.

        `;
        d_ret = {
            'status':   false,
            'result':   ''
        }

        l_markdownComArg    = astr_commandArg.split('_')
        str_command         = l_markdownComArg[0];
        l_argList           = l_markdownComArg[1].split(',')
        switch(str_command) {
            case 'o':
                d_ret['status'] = true;
                d_ret['result'] = this.snippetMake(l_argList, astr_text);
                break;
            case 'font':
                d_ret['status'] = true;
                d_ret['result'] = this.fontify(l_argList, astr_text);
                break;
        }
        return d_ret;
    },


    markdown_do:               function(astr_line) {
        let str_help = `

            Process the markdown directive in the <astr_line> and
            branch to appropriate handler.

        `;

        // split astr_line into a list and find the element
        // containing the this.mdMarker
        let l_words     = astr_line.split(/(\s+)/);
        for(let str_word of l_words) {
            if(str_word.includes(this.mdMarker)) {
                let str_commandArg  = str_word.split(this.mdMarker)[1];
                let str_text        = astr_line.split(str_word)[1];
                d_markdown          = this.markdown_process(str_commandArg, str_text);
            }
        }

    },

    parse:                          function(astr_text) {
        let str_help = `

            Parse the <astr_text> for certain markdown
            and replace with suitable HTML, which is
            returned.

        `;

        // Split the input string into an array
        let l_slide     = astr_text.split("\n")
        let d_parsed    = {};

        // find lines that contain the this.mdMarker
        for(let str_line of l_slide) {
            if(str_line.includes(this.mdMarker))
                d_parsed    = this.markdown_do(str_line);
        }

    },

}

/////////
///////// A typewriter effect object
///////// from https://codepen.io/stevn/pen/jEZvXa
/////////

function setupTypewriter(t) {
    // Read from data-text attribute to bypass HTML entity parsing issues
    var HTML = t.getAttribute('data-text') || t.textContent;

    t.innerHTML = "";

    var cursorPosition  = 0,
        tag             = "",
        writingTag      = false,
        tagOpen         = false,
        typeSpeed       = 100,
    tempTypeSpeed = 0;

    var type = function() {

        if (writingTag === true) {
            tag += HTML[cursorPosition];
        }

        if (HTML[cursorPosition] === "<") {
            tempTypeSpeed = 0;
            if (tagOpen) {
                tagOpen = false;
                writingTag = true;
            } else {
                tag = "";
                tagOpen = true;
                writingTag = true;
                tag += HTML[cursorPosition];
            }
        }
        if (!writingTag && tagOpen) {
            tag.innerHTML += HTML[cursorPosition];
        }
        if (!writingTag && !tagOpen) {
            if (HTML[cursorPosition] === " ") {
                tempTypeSpeed = 0;
            }
            else {
                tempTypeSpeed = (Math.random() * typeSpeed) + 50;
            }
            t.innerHTML += HTML[cursorPosition];
        }
        if (writingTag === true && HTML[cursorPosition] === ">") {
            tempTypeSpeed = (Math.random() * typeSpeed) + 50;
            writingTag = false;
            if (tagOpen) {
                var newSpan = document.createElement("span");
                t.appendChild(newSpan);
                newSpan.innerHTML = tag;
                tag = newSpan.firstChild;
            }
        }

        cursorPosition += 1;
        if (cursorPosition < HTML.length - 1) {
            setTimeout(type, tempTypeSpeed);
        }

    };

    return {
        type: type
    };
}

/////////
///////// Runtime typography scale controls
/////////

const typographyScale_STEP = 0.1;
const typographyScale_MIN = 0.6;
const typographyScale_MAX = 2.4;
let typographyScale_base = null;
let typographyScale_current = null;
let typographyScale_noticeTimer = null;

// A beat between choosing and moving. With a clicker the room cannot see
// which key was pressed, so the entry is marked and held long enough to
// be noticed before anything starts travelling.
const zoomTransition_HITMS = 160;

// One flight, carrying one line of text. The pages behind it merely
// cross over, so this is the only duration the eye is actually reading.
const zoomTransition_FLIGHTMS = 300;
// The handover to the real heading at the end. An entry and the heading
// it becomes are rarely word for word the same, so the last moment is a
// short cross-fade rather than a swap.
const zoomTransition_CROSSMS = 120;

// Standard ease: out of rest and back into it, which is what a thing
// being carried somewhere does.
const zoomTransition_EASE = 'cubic-bezier(0.4, 0.0, 0.2, 1.0)';

// transitionend is not guaranteed — an element hidden mid-flight never
// fires one — so every leg also carries a timer.
const zoomTransition_SLACKMS = 60;

function activeElement_isTextEntry() {
    const activeElement = document.activeElement;
    if (!activeElement) {
        return false;
    }

    const tagName = activeElement.tagName;
    if (
        tagName === "INPUT" ||
        tagName === "TEXTAREA" ||
        tagName === "SELECT"
    ) {
        return true;
    }

    return activeElement.isContentEditable === true;
}

function typographyScale_read() {
    const rootStyle = getComputedStyle(document.documentElement);
    const rawScale = rootStyle.getPropertyValue(
        "--deck-typography-scale"
    ).trim();
    const parsedScale = parseFloat(rawScale);

    if (Number.isFinite(parsedScale) && parsedScale > 0) {
        return parsedScale;
    }
    return 1;
}

function typographyScale_write(scale) {
    const clampedScale = Math.min(
        typographyScale_MAX,
        Math.max(typographyScale_MIN, scale)
    );
    const roundedScale = Math.round(clampedScale * 100) / 100;

    document.documentElement.style.setProperty(
        "--deck-typography-scale",
        String(roundedScale)
    );
    typographyScale_current = roundedScale;
    typographyScale_noticeShow(roundedScale);
}

function typographyScale_reset() {
    typographyScale_write(typographyScale_base);
}

function typographyScale_adjust(delta) {
    if (typographyScale_current === null) {
        typographyScale_current = typographyScale_read();
    }
    typographyScale_write(typographyScale_current + delta);
}

function typographyScale_noticeShow(scale) {
    let notice = document.getElementById("typography-scale-notice");
    if (!notice) {
        notice = document.createElement("div");
        notice.id = "typography-scale-notice";
        notice.style.position = "fixed";
        notice.style.right = "24px";
        notice.style.bottom = "24px";
        notice.style.zIndex = "9999";
        notice.style.padding = "10px 14px";
        notice.style.background = "rgba(0, 0, 0, 0.82)";
        notice.style.color = "#fc9";
        notice.style.border = "2px solid #f91";
        notice.style.fontFamily = "sans-serif";
        notice.style.fontSize = "16px";
        notice.style.letterSpacing = "1px";
        notice.style.pointerEvents = "none";
        notice.style.opacity = "0";
        notice.style.transition = "opacity 160ms ease";
        document.body.appendChild(notice);
    }

    notice.textContent = `TEXT SCALE ${scale.toFixed(2)}x`;
    notice.style.opacity = "1";

    if (typographyScale_noticeTimer) {
        clearTimeout(typographyScale_noticeTimer);
    }
    typographyScale_noticeTimer = setTimeout(() => {
        notice.style.opacity = "0";
    }, 900);
}

function typographyScale_keyHandle(event) {
    if (event.ctrlKey || event.metaKey || event.altKey) {
        return false;
    }
    if (activeElement_isTextEntry()) {
        return false;
    }

    if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        typographyScale_adjust(typographyScale_STEP);
        return true;
    }
    if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        typographyScale_adjust(-typographyScale_STEP);
        return true;
    }
    if (event.key === "0") {
        event.preventDefault();
        typographyScale_reset();
        return true;
    }

    return false;
}

function typographyScale_initialize() {
    typographyScale_base = typographyScale_read();
    typographyScale_current = typographyScale_base;
}


/////////
///////// A Page object that describes the HTML version elements from a
///////// logical perspective.
/////////

/////////
///////// Nexus navigation: the compiled navigation graph.
/////////

function NexusGraph() {
    let str_help = `

        Reads the navigation graph the compiler emitted into an inert
        <script type="application/json"> element.

        This object derives nothing. Every fact it answers was computed
        at compile time, where the test suite can assert it. If a
        question cannot be answered from the graph, the answer is "no"
        rather than a guess.

    `;

    this.graph              = null;
    this.d_slideForAddress  = {};
    this.parse();
}

NexusGraph.prototype = {
    constructor:        NexusGraph,

    // Graph schemas this runtime understands. A deck compiled by a newer
    // slidedown is ignored rather than half-interpreted.
    SUPPORTED_VERSION:  1,

    parse:              function() {
        let str_help = `
            Load and validate the graph. Returns true when a usable
            graph was found.
        `;

        let el = document.getElementById('nexusGraph');
        if (!el) {
            return false;
        }

        try {
            this.graph = JSON.parse(el.textContent);
        } catch (err) {
            console.warn('nexus: navigation graph is not valid JSON', err);
            this.graph = null;
            return false;
        }

        if (!this.graph || this.graph.version !== this.SUPPORTED_VERSION) {
            console.warn(
                'nexus: unsupported graph version',
                this.graph ? this.graph.version : '(none)'
            );
            this.graph = null;
            return false;
        }

        this.d_slideForAddress = this.graph.slides || {};
        return true;
    },

    isLoaded:           function() {
        return this.graph !== null;
    },

    isNexusDeck:        function() {
        let str_help = `
            True when the deck places at least one nexus. A deck holding
            only inline cross-references is not a nexus deck and keeps
            its ordinary navigation behaviour.
        `;

        return this.isLoaded() && this.graph.isNexusDeck === true;
    },

    spokeFor:           function(a_slideIndex) {
        let str_help = `
            The spoke containing a slide, or null.
        `;

        if (!this.isLoaded() || !this.graph.spokes) {
            return null;
        }

        for (let i = 0; i < this.graph.spokes.length; i++) {
            let spoke = this.graph.spokes[i];
            if (a_slideIndex >= spoke.start && a_slideIndex <= spoke.end) {
                return spoke;
            }
        }
        return null;
    },

    spokeEndsAt:        function(a_slideIndex) {
        let str_help = `
            Whether a slide is the last slide of its spoke. This is the
            moment a jumped-into spoke hands back to its nexus.
        `;

        let spoke = this.spokeFor(a_slideIndex);
        return spoke !== null && spoke.end === a_slideIndex;
    },

    placementFor:       function(a_slideIndex) {
        let str_help = `
            The nexus placement sitting on a given slide, or null.

            Placements are distinct even when they share a nexus id: the
            same menu placed at both ends of a deck is two placements,
            and returning to the wrong one is disorienting.
        `;

        if (!this.isLoaded() || !this.graph.nexuses) {
            return null;
        }

        for (let i = 0; i < this.graph.nexuses.length; i++) {
            if (this.graph.nexuses[i].slide === a_slideIndex) {
                return this.graph.nexuses[i];
            }
        }
        return null;
    },

    placementBefore:    function(a_slideIndex) {
        let str_help = `
            The nearest nexus placement at or before a slide, as a slide
            number, or 0. Used when a deep link left no return history.
        `;

        if (!this.isLoaded() || !this.graph.nexuses) {
            return 0;
        }

        let index_best = 0;
        for (let i = 0; i < this.graph.nexuses.length; i++) {
            let slide = this.graph.nexuses[i].slide;
            if (slide <= a_slideIndex && slide > index_best) {
                index_best = slide;
            }
        }
        return index_best;
    },

    slideFor:           function(astr_address) {
        let str_help = `
            Resolve a slide address to its 1-based slide number.
            Returns 0 when the address is unknown.
        `;

        if (!astr_address) {
            return 0;
        }

        let index = this.d_slideForAddress[astr_address];
        return (typeof index === 'number') ? index : 0;
    }
}


function Page() {
    let str_help = `

        The Page object defines/interacts with the html page.

        The page element strings are "defined" here, and various
        DOM objects that can interact with these elements are also
        instantiated.

    `;

    this.currentSlide               = 1;
    this.nexus                      = new NexusGraph();
    // Where a jump departed from, so a spoke can hand back to the exact
    // nexus placement it was entered from — not merely to that nexus.
    this.l_returnStack              = [];
    // Spokes already covered, keyed by target address.
    this.d_visited                  = {};
    // Transition named by .meta{}, read from the DOM in init().
    this.str_transition             = "none";
    // Position within the current menu's revealed entries, 1-based.
    // Zero until the presenter asks for a cursor by pressing a key.
    this.index_cursor               = 0;
    // Finishers for zoom phases still in flight. A presenter working a
    // clicker outruns any animation, so a new move snaps these rather
    // than queueing behind them.
    this.l_zoomPending              = [];
    document.onkeydown              = this.checkForArrowKeyPress;
    document.onclick                = this.checkForMouseClick;


    // Keys parsed from the URL
    this.l_urlParamsBasic = [
        "slide",
    ];

    // DOM keys related to the slides
    this.l_slide                = [];   // Simple index of DOMslideIDs
    this.l_snippetsPerSlide     = [];   // Number of snippets per slide
    this.l_snippetPerSlideON    = [];   // Running count of ON snippets
    this.str_slideIDprefix      = "";
    this.init();
    this.visited_load();

    // DOM obj elements --  Each object has a specific list of page key
    //                      elements that it process to provide page
    //                      access functionality
    this.DOMurl         = new DOM(this.l_urlParams);
    this.DOMslide       = new DOM(this.l_slide);
    // object that parses the URL
    this.url            = new URL(this.DOMurl);

    // an object for housing typewriter functions
    this.d_typerDOM     = {};
    this.d_typewriter   = {};
    this.d_typewriterOriginalHTML = {};  // Store original HTML for reset
}

Page.prototype = {
    constructor:    Page,

    substr_count:                       function(astr_substr, astr_text) {
        let str_help = `
            Count and return the occurences of a substring in a string.
        `;
        return (astr_text.match(new RegExp(astr_substr, 'gi')) || []).length;
    },

    init:                               function() {
        let str_help = `
            Initialize some member variables based on meta data
            in the DOM.
        `;

        let prefixEl = document.getElementById('slideIDprefix');
        this.str_slideIDprefix = prefixEl ? prefixEl.innerHTML.trim() : 'slide-';
        let transitionEl = document.getElementById('slideTransition');
        this.str_transition = transitionEl
                                ? transitionEl.innerHTML.trim()
                                : 'none';
        let countEl = document.getElementById('numberOfSlides');
        let numberOfSlides = countEl ? parseInt(countEl.innerHTML) : 0;
        for(let i=1; i<=numberOfSlides; i++) {
            this.l_slide.push(this.str_slideIDprefix + i);
        }

        // Parse for snippets per slide
        for(const DOMslideID of this.l_slide) {
            let el = document.getElementById(DOMslideID);
            let snippetsPerSlide = 0;
            if (el) {
                snippetsPerSlide = el.getElementsByClassName('snippet').length;
            }
            this.l_snippetsPerSlide.push(snippetsPerSlide);
            this.l_snippetPerSlideON.push(0);
        }
    },

    setupTypewriter:                    function(t) {
        let str_help = `
            ///////// A typewriter effect object
            ///////// from https://codepen.io/stevn/pen/jEZvXa

        `;
        // Read from data-text attribute to bypass HTML entity parsing issues
        var HTML            = t.getAttribute('data-text') || t.innerHTML;
        t.innerHTML         = "";

        var cursorPosition  = 0,
            tag             = "",
            writingTag      = false,
            tagOpen         = false,
            typeSpeed       = 10,
            tempTypeSpeed   = 0,
            isActive        = true;  // Flag to cancel animation

        var type = function() {
            // CRITICAL: Check if this animation is still active
            // If cleanup happened, stop immediately
            if (!isActive) {
                return;
            }

            if (writingTag === true) {
                tag += HTML[cursorPosition];
            }

            if (HTML[cursorPosition] === "<") {
                tempTypeSpeed = 0;
                if (tagOpen) {
                    tagOpen = false;
                    writingTag = true;
                } else {
                    tag = "";
                    tagOpen = true;
                    writingTag = true;
                    tag += HTML[cursorPosition];
                }
            }
            if (!writingTag && tagOpen) {
                tag.innerHTML += HTML[cursorPosition];
            }
            if (!writingTag && !tagOpen) {
                if (HTML[cursorPosition] === " ") {
                    tempTypeSpeed = 0;
                }
                else {
                    tempTypeSpeed = (Math.random() * typeSpeed) + 50;
                }
                t.innerHTML += HTML[cursorPosition];
            }
            if (writingTag === true && HTML[cursorPosition] === ">") {
                tempTypeSpeed = (Math.random() * typeSpeed) + 50;
                writingTag = false;
                if (tagOpen) {
                    var newSpan = document.createElement("span");
                    t.appendChild(newSpan);
                    newSpan.innerHTML = tag;
                    tag = newSpan.firstChild;
                }
            }

            cursorPosition += 1;
            if (cursorPosition < HTML.length) {
                setTimeout(type, tempTypeSpeed);
            }

        };

        return {
            type: type,
            cancel: function() {
                isActive = false;  // Stop the animation
            }
        };
    },

    retreat_overSnippets:               function() {
        let thisSlide   = this.currentSlide-1;
        if(this.l_snippetPerSlideON[thisSlide] == 0)
            return true;

        let snippetToDisplayOFF = this.l_snippetPerSlideON[thisSlide];
        let DOMsnippet = document.getElementById('order-' + this.currentSlide + '-' + snippetToDisplayOFF);

        if (DOMsnippet) {
            DOMsnippet.classList.add('sl-hidden');
        }
        this.l_snippetPerSlideON[thisSlide] -= 1;
        return false;
    },

    advance_overSnippets:               function() {
        let thisSlide   = this.currentSlide-1;
        if(this.l_snippetPerSlideON[thisSlide] == this.l_snippetsPerSlide[thisSlide])
            return true;

        let snippetToDisplay = this.l_snippetPerSlideON[thisSlide] + 1;
        let DOMsnippet = document.getElementById('order-' + this.currentSlide + '-' + snippetToDisplay);

        if (DOMsnippet) {
            DOMsnippet.classList.remove('sl-hidden');
            
            // Trigger typewriter if present
            let typewriterInSnippet = DOMsnippet.querySelector('[id^="typewriter-"]');
            if (typewriterInSnippet) {
                let str_idRef = typewriterInSnippet.id;
                if (!this.d_typewriterOriginalHTML[str_idRef]) {
                    this.d_typewriterOriginalHTML[str_idRef] = typewriterInSnippet.getAttribute('data-text') || typewriterInSnippet.textContent;
                }
                this.d_typerDOM[str_idRef] = typewriterInSnippet;
                this.d_typewriter[str_idRef] = this.setupTypewriter(this.d_typerDOM[str_idRef]);
                this.d_typewriter[str_idRef].type();
            }
        }

        this.l_snippetPerSlideON[thisSlide] += 1;
        return false;
    },

    snippets_restoreTo:                 function(a_slideIndex, a_count) {
        let str_help = `
            Reveal the first N snippets of a slide and set its counter to
            match.

            Note that allSnippets_displaySet() zeroes the ON counter
            regardless of the state it applied, so the counter has to be
            set here rather than trusted.
        `;

        let snippets    = this.l_snippetsPerSlide[a_slideIndex - 1] || 0;
        let count       = Math.min(a_count, snippets);

        for(let snippet = 1; snippet <= count; snippet++) {
            let DOMsnippet = document.getElementById(
                'order-' + a_slideIndex + '-' + snippet
            );
            if (DOMsnippet) {
                DOMsnippet.classList.remove('sl-hidden');
            }
        }

        this.l_snippetPerSlideON[a_slideIndex - 1] = count;
    },

    allSnippets_displaySet:             function(astr_state, a_slideIndex) {
        let snippets = this.l_snippetsPerSlide[a_slideIndex-1];
        for(let snippet=1; snippet <= snippets; snippet++) {
            let DOMsnippet = document.getElementById('order-' + a_slideIndex + '-' + snippet);
            if (DOMsnippet) {
                if (astr_state === 'none') {
                    DOMsnippet.classList.add('sl-hidden');
                } else {
                    DOMsnippet.classList.remove('sl-hidden');
                }
            }
        }
        this.l_snippetPerSlideON[a_slideIndex-1] = 0;
    },

    slide_goto:                         function(a_slideIndex, options) {
        let str_help = `
            Navigate directly to a 1-based slide index.

            Returns true when the deck moved. Out-of-range indices and
            navigation to the current slide are no-ops, so callers may
            pass unvalidated input.

            'options' is handed to the transition untouched; a jump names
            the address it followed there, which is what the zoom needs
            to know where on the slide to move about.
        `;

        if (typeof a_slideIndex !== 'number' || !isFinite(a_slideIndex)) {
            return false;
        }
        if (a_slideIndex < 1 || a_slideIndex > this.l_slide.length) {
            return false;
        }
        if (a_slideIndex === this.currentSlide) {
            return false;
        }

        let index_currentSlide      = this.currentSlide;
        this.currentSlide           = a_slideIndex;
        this.slide_transition(index_currentSlide, a_slideIndex, options);
        return true;
    },

    startSlide_fromURL:                 function() {
        let str_help = `
            Resolve the ?slide= parameter to a starting slide index.

            Accepts either a slide number or a slide address, so a deck
            can be deep-linked by name. Falls back to slide 1.
        `;

        let params = new URLSearchParams(window.location.search);
        if (!params.has('slide')) {
            return 1;
        }

        let str_requested = (params.get('slide') || '').trim();
        if (!str_requested) {
            return 1;
        }

        if (/^\d+$/.test(str_requested)) {
            let index = parseInt(str_requested, 10);
            if (index >= 1 && index <= this.l_slide.length) {
                return index;
            }
            return 1;
        }

        return this.nexus.slideFor(str_requested) || 1;
    },

    visited_storageKey:                 function() {
        return 'slidedown:visited:' + window.location.pathname;
    },

    visited_load:                       function() {
        let str_help = `
            Restore which spokes have been visited.

            Kept in sessionStorage because a browser dying mid-talk is a
            real failure mode, and coming back to a menu that has
            forgotten what you already covered is worse than useless.
        `;

        try {
            let raw = window.sessionStorage.getItem(this.visited_storageKey());
            this.d_visited = raw ? JSON.parse(raw) : {};
        } catch (err) {
            // Private browsing, or storage disabled. Visited marking is a
            // convenience; losing it must not break navigation.
            this.d_visited = {};
        }
    },

    visited_mark:                       function(astr_address) {
        let str_help = `
            Record a spoke as covered.

            Keyed on the target, not on the placement it was reached
            from: "I have spent time on this topic" is a fact about the
            topic, so both menus in a sandwich agree.
        `;

        if (!astr_address) {
            return false;
        }

        this.d_visited[astr_address] = true;

        try {
            window.sessionStorage.setItem(
                this.visited_storageKey(), JSON.stringify(this.d_visited)
            );
        } catch (err) {
            // See visited_load().
        }
        return true;
    },

    visited_apply:                      function(a_slideIndex) {
        let str_help = `
            Reflect visited state onto the jumps of a slide.
        `;

        let slideEl = document.getElementById(
            this.str_slideIDprefix + a_slideIndex
        );
        if (!slideEl || !slideEl.querySelectorAll) {
            return 0;
        }

        let anchors = slideEl.querySelectorAll('.sd-jump');
        let count   = 0;
        for (let i = 0; i < anchors.length; i++) {
            let str_address = anchors[i].getAttribute('data-jump');
            if (this.d_visited[str_address]) {
                anchors[i].classList.add('sd-jump--visited');
                count++;
            } else {
                anchors[i].classList.remove('sd-jump--visited');
            }
        }
        return count;
    },

    return_push:                        function(astr_address) {
        let str_help = `
            Record the current slide as a departure point, if it is a
            nexus placement.

            The revealed-snippet count travels with it: coming back must
            restore the menu as the presenter left it, not replay a build
            the room already watched, and not reveal options that had not
            been announced when the jump was taken.

            The entry's box travels with it for a plainer reason. It can
            only be measured while the nexus is on screen, and by the
            time the return is taken the nexus is hidden and measures as
            nothing.
        `;

        if (!this.nexus.placementFor(this.currentSlide)) {
            return false;
        }

        this.l_returnStack.push({
            slide:      this.currentSlide,
            revealed:   this.l_snippetPerSlideON[this.currentSlide - 1] || 0,
            rect:       astr_address
                            ? this.zoom_anchorRect(
                                  this.currentSlide, astr_address
                              )
                            : null
        });
        return true;
    },

    return_process:                     function() {
        let str_help = `
            Hand back to the nexus placement this spoke was entered from.

            With nothing on the stack — a deep link dropped the viewer
            straight into a spoke — fall back to the nearest preceding
            placement. A return that silently does nothing reads as
            broken.
        `;

        let departure = this.l_returnStack.pop();

        if (!departure) {
            let index_fallback = this.nexus.placementBefore(this.currentSlide);
            if (!index_fallback) {
                return false;
            }
            departure = { slide: index_fallback, revealed: 0, rect: null };
        }

        let index_currentSlide      = this.currentSlide;
        this.currentSlide           = departure.slide;
        this.slide_transition(index_currentSlide, departure.slide, {
            restoreSnippets: departure.revealed,
            isReturn:        true,
            rect:            departure.rect || null
        });
        return true;
    },

    jump_isRevealed:                    function(a_anchor) {
        let str_help = `
            Whether a jump anchor is currently visible.

            A jump inside an unrevealed snippet is inert: sending the
            room to a topic they have not seen listed is never intended.
        `;

        if (!a_anchor || !a_anchor.closest) {
            return false;
        }

        let snippet = a_anchor.closest('.snippet');
        if (!snippet) {
            return true;
        }

        return !snippet.classList.contains('sl-hidden');
    },

    nexusDigit_process:                 function(a_digit) {
        let str_help = `
            Jump to the nth entry of the nexus on the current slide.

            Returns true when the digit was consumed. At a lectern with a
            clicker the presenter is not touching the screen, so this is
            the mechanism that actually gets used; clicking is a fallback.
        `;

        let placement = this.nexus.placementFor(this.currentSlide);
        if (!placement || !placement.jumps) {
            return false;
        }

        let str_address = placement.jumps[a_digit - 1];
        if (!str_address) {
            return false;
        }

        let slideEl = document.getElementById(
            this.str_slideIDprefix + this.currentSlide
        );
        let anchor = slideEl ? slideEl.querySelector(
            '.sd-jump[data-jump="' + str_address + '"]'
        ) : null;

        if (anchor && !this.jump_isRevealed(anchor)) {
            return false;
        }

        return this.jump_take(str_address);
    },

    jump_take:                          function(astr_address) {
        let str_help = `
            Follow a jump to an address.

            The one path a jump takes, however it was chosen: a digit, the
            cursor, or a click. Departure and visited state are recorded
            here so no caller can reach the destination without them.

            Returns true when the deck moved.
        `;

        let index = this.nexus.slideFor(astr_address);
        if (!index) {
            return false;
        }

        this.return_push(astr_address);
        this.visited_mark(astr_address);
        this.slide_goto(index, { jumpAddress: astr_address });
        return true;
    },

    nexusDigit_keyHandle:               function(e) {
        let str_help = `
            Route 1-9 to the current nexus.

            Capped at nine: 0, +, = and - already belong to the
            typography scale, and a nexus with more than nine entries is
            a problem with the deck rather than a gap in the engine.
        `;

        if (e.ctrlKey || e.metaKey || e.altKey) {
            return false;
        }
        if (activeElement_isTextEntry()) {
            return false;
        }
        if (!/^[1-9]$/.test(e.key)) {
            return false;
        }

        return page.nexusDigit_process(parseInt(e.key, 10));
    },

    cursorEntries_get:                  function(a_slideIndex) {
        let str_help = `
            The entries the cursor may sit on, in menu order.

            Only revealed ones. An unannounced entry is inert to the digit
            keys for the same reason it is inert to a click, and a cursor
            that could land on it would be offering the room a choice it
            has not been shown.
        `;

        let placement = this.nexus.placementFor(a_slideIndex);
        if (!placement || !placement.jumps) {
            return [];
        }

        let l_entry = [];
        for (let i = 0; i < placement.jumps.length; i++) {
            let str_address = placement.jumps[i];
            let anchor = this.jumpAnchor_find(a_slideIndex, str_address);
            if (anchor && this.jump_isRevealed(anchor)) {
                l_entry.push(str_address);
            }
        }
        return l_entry;
    },

    cursor_forget:                      function(a_slideIndex) {
        let str_help = `
            Drop the cursor, and take its mark off the slide it was on.

            Called as the deck leaves a slide: a cursor is a position
            within one menu, and means nothing on the next one.
        `;

        let l_entry = this.cursorEntries_get(a_slideIndex);
        for (let i = 0; i < l_entry.length; i++) {
            let anchor = this.jumpAnchor_find(a_slideIndex, l_entry[i]);
            if (anchor && anchor.classList) {
                anchor.classList.remove('sd-jump--cursor');
            }
        }
        this.index_cursor = 0;
    },

    cursor_apply:                       function() {
        let str_help = `
            Put the mark on the entry the cursor is on, and nowhere else.
        `;

        let l_entry = this.cursorEntries_get(this.currentSlide);
        for (let i = 0; i < l_entry.length; i++) {
            let anchor = this.jumpAnchor_find(this.currentSlide, l_entry[i]);
            if (!anchor || !anchor.classList) {
                continue;
            }
            if (i + 1 === this.index_cursor) {
                anchor.classList.add('sd-jump--cursor');
            } else {
                anchor.classList.remove('sd-jump--cursor');
            }
        }
    },

    cursor_move:                        function(a_delta) {
        let str_help = `
            Step the cursor through the current menu, wrapping at both
            ends.

            With no cursor yet, a step down lands on the first entry and
            a step up on the last, so the first key press does the
            obvious thing rather than requiring a second.

            Returns true when the key was consumed.
        `;

        let l_entry = this.cursorEntries_get(this.currentSlide);
        if (!l_entry.length) {
            return false;
        }

        if (!this.index_cursor) {
            this.index_cursor = (a_delta > 0) ? 1 : l_entry.length;
        } else {
            let index = this.index_cursor + a_delta;
            if (index < 1) {
                index = l_entry.length;
            } else if (index > l_entry.length) {
                index = 1;
            }
            this.index_cursor = index;
        }

        this.cursor_apply();
        return true;
    },

    cursor_activate:                    function() {
        let str_help = `
            Take the jump the cursor is sitting on.

            Returns true when the key was consumed.
        `;

        if (!this.index_cursor) {
            return false;
        }

        let l_entry = this.cursorEntries_get(this.currentSlide);
        let str_address = l_entry[this.index_cursor - 1];
        if (!str_address) {
            return false;
        }

        return this.jump_take(str_address);
    },

    nexusCursor_keyHandle:              function(e) {
        let str_help = `
            Route Up, Down and Enter to the current menu.

            The digit keys are the fast path and stop at nine, because 0,
            +, = and - belong to the typography scale. The cursor has no
            such ceiling, so a menu may hold as many entries as it likes
            and the first nine simply keep their shortcut.

            Up and Down already mean first-slide and last-slide, and go
            on meaning that everywhere except on a menu. A deck being
            driven as a graph has little use for "last slide" while the
            room is looking at a list of choices.
        `;

        if (e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) {
            return false;
        }
        if (activeElement_isTextEntry()) {
            return false;
        }
        if (!page.nexus.placementFor(page.currentSlide)) {
            return false;
        }

        if (e.key === 'ArrowDown' || e.keyCode === 40) {
            return page.cursor_move(1);
        }
        if (e.key === 'ArrowUp' || e.keyCode === 38) {
            return page.cursor_move(-1);
        }
        if (e.key === 'Enter' || e.keyCode === 13) {
            return page.cursor_activate();
        }

        return false;
    },

    jumpClick_process:                  function(e) {
        let str_help = `
            Handle a click on a .sd-jump anchor.

            Returns true when the click was a jump and has been handled,
            so the caller knows not to treat it as deck navigation.
        `;

        let target = e.target || e.srcElement;
        if (!target || !target.closest) {
            return false;
        }

        let anchor = target.closest('.sd-jump');
        if (!anchor) {
            return false;
        }

        e.preventDefault();

        let str_address = anchor.getAttribute('data-jump');
        let index = page.nexus.slideFor(str_address);
        if (index) {
            page.jump_take(str_address);
        }
        return true;
    },

    advance_toFirst:                    function() {
        let str_help = `
            Advance to first slide...
        `;
        let index_currentSlide      = this.currentSlide;
        let index_followingSlide    = 1;
        this.currentSlide           = index_followingSlide;
        this.slide_transition(index_currentSlide, index_followingSlide);
    },

    advance_toLast:                     function() {
        let str_help = `
            Advance to last slide...
        `;
        let index_currentSlide      = this.currentSlide;
        let index_followingSlide    = this.l_slide.length;
        this.currentSlide           = index_followingSlide;
        this.slide_transition(index_currentSlide, index_followingSlide);
    },

    advance_toNext:                     function() {
        let str_help = `
            Advance to next slide...
        `;
        let index_currentSlide      = this.currentSlide;
        let index_followingSlide    = index_currentSlide+1;
        if(index_followingSlide > this.l_slide.length) {
            index_followingSlide    = 1;
        }
        this.currentSlide           = index_followingSlide;
        this.slide_transition(index_currentSlide, index_followingSlide);
    },

    advance_toPrevious:                 function() {
        let str_help = `
            Advance to previous slide...
        `;
        let index_currentSlide      = this.currentSlide;
        let index_followingSlide    = index_currentSlide-1;
        if(index_followingSlide < 1) {
            index_followingSlide    = this.l_slide.length;
        }
        this.currentSlide           = index_followingSlide;
        this.slide_transition(index_currentSlide, index_followingSlide);
    },

    resetAllTypewritersOnSlide:         function(slideIndex) {
        let str_help = `
            Reset ALL typewriters on a slide regardless of location.
            Cancels running animations and restores original HTML.
            Called when entering a slide to ensure clean state.
        `;

        let slideElement = document.getElementById(this.str_slideIDprefix + slideIndex);
        if (!slideElement) return;

        // Find ALL typewriters on this slide (don't care where they are)
        let allTypewriters = slideElement.querySelectorAll('[id^="typewriter-"]');

        allTypewriters.forEach(typer => {
            let str_idRef = typer.id;

            // Cancel any running animation
            if (this.d_typewriter[str_idRef] && this.d_typewriter[str_idRef].cancel) {
                this.d_typewriter[str_idRef].cancel();
            }

            // Restore via data attribute if we have it
            if (this.d_typewriterOriginalHTML[str_idRef]) {
                typer.setAttribute('data-text', this.d_typewriterOriginalHTML[str_idRef]);
                typer.innerHTML = '';
            }
        });
    },

    startNonSnippetTypewriters:         function(slideIndex) {
        let str_help = `
            Start typewriters that are directly on the slide (not inside snippets).
            Called after slide entry and reset.
        `;

        let slideElement = document.getElementById(this.str_slideIDprefix + slideIndex);
        if (!slideElement) return;

        let allTypewriters = slideElement.querySelectorAll('[id^="typewriter-"]');

        allTypewriters.forEach(typer => {
            // Check if this typewriter is inside a snippet
            let isInSnippet = typer.closest('.snippet') !== null;
            if (!isInSnippet) {
                let str_idRef = typer.id;

                // Store original data-text attribute on first visit
                if (!this.d_typewriterOriginalHTML[str_idRef]) {
                    this.d_typewriterOriginalHTML[str_idRef] = typer.getAttribute('data-text') || typer.textContent;
                }

                this.d_typerDOM[str_idRef] = typer;
                this.d_typewriter[str_idRef] = this.setupTypewriter(this.d_typerDOM[str_idRef]);
                this.d_typewriter[str_idRef].type();
            }
        });
    },

    slide_commit:                       function(index_currentSlide,
                                                 index_followingSlide,
                                                 options,
                                                 ab_deferTypewriters) {
        let str_help = `
            Do the actual transition from one slide to another,
            as well as update the running slide counter in the footer.

            Also, on the next slide, process any typewriter effects.

            'options' is optional and defaults to the historical
            behaviour, in which entering a slide resets its reveals. Only
            a nexus return passes options.restoreSnippets, so every
            existing deck transitions exactly as it always has.

            'ab_deferTypewriters' holds the typing back for a caller that
            is still animating. Text racing a moving slide is legible as
            neither.
        `;

        let d_options = options || {};

        // A cursor is a position within one menu, so it does not survive
        // leaving that menu.
        this.cursor_forget(index_currentSlide);

        let DOMID_currentSlide      = document.getElementById(
                                            this.str_slideIDprefix + index_currentSlide
                                        );
        let DOMID_followingSlide    = document.getElementById(
                                            this.str_slideIDprefix + index_followingSlide
                                        );
        let DOMID_slideTitle        = document.getElementById(
                                            this.str_slideIDprefix + index_followingSlide +
                                            '-title');
        let DOMID_slideCounter      = document.getElementById('slideCounter');
        let DOMID_pageTitle         = document.getElementById('pageTitle');
        let DOMID_slideBar          = document.getElementById('slideBar');

        DOMID_currentSlide.style.display    = "none";
        DOMID_followingSlide.style.display  = "block";

        // Reset ALL typewriters on the slide we're entering
        this.resetAllTypewritersOnSlide(index_followingSlide);

        // Hide all snippets and reset counter
        this.allSnippets_displaySet('none', index_followingSlide);

        // Returning to a nexus restores it as the presenter left it.
        if (d_options.restoreSnippets > 0) {
            this.snippets_restoreTo(
                index_followingSlide, d_options.restoreSnippets
            );
        }

        // A menu should answer "what is left?" at a glance.
        this.visited_apply(index_followingSlide);

        // Start any typewriters that are directly on the slide (not in snippets)
        if (!ab_deferTypewriters) {
            this.startNonSnippetTypewriters(index_followingSlide);
        }
        if(DOMID_slideTitle !== null) {
            DOMID_pageTitle.innerHTML = DOMID_slideTitle.innerHTML.trim();
        } else {
            DOMID_pageTitle.innerHTML = " ";
        }

        // "Slide 4 of 9" is a false statement about a deck being driven
        // as a graph, so nexus decks carry no linear position readout.
        let b_showProgress = !this.nexus.isNexusDeck();

        // Update slide counter (default behavior)
        if (DOMID_slideCounter) {
            DOMID_slideCounter.innerHTML = b_showProgress
                ? ("slide " + this.currentSlide +
                   " / " + this.l_slide.length)
                : "";
        }

        // Update custom footer templates (if present)
        this.updateFooterTemplates();

        if (DOMID_slideBar) {
            progress = b_showProgress
                ? (this.currentSlide / this.l_slide.length * 100)
                : 0;
            DOMID_slideBar.style.width = progress + "%";
        }
    },

    motion_isReduced:                   function() {
        let str_help = `
            Whether the viewer has asked for reduced motion.

            Prezi's lasting lesson is that swooping movement makes some
            of the room ill. The setting is honoured absolutely: it
            returns the deck to the instant swap, not to a gentler zoom.
        `;

        if (typeof window === 'undefined' || !window.matchMedia) {
            return false;
        }

        try {
            return window.matchMedia(
                '(prefers-reduced-motion: reduce)'
            ).matches === true;
        } catch (err) {
            return false;
        }
    },

    viewport_scaleGet:                  function() {
        let str_help = `
            The scale scalePresentation() has applied to the viewport.

            Anchor geometry comes back from the browser in screen pixels,
            but transform-origin is read in the element's own untransformed
            pixels. Dividing by this converts between them.

            Returns 0 when the viewport cannot be measured, which callers
            treat as "do not animate".
        `;

        let el = document.querySelector
                    ? document.querySelector('.presentation-viewport')
                    : null;
        if (!el || !el.getBoundingClientRect) {
            return 0;
        }

        let width_layout = el.offsetWidth;
        if (!width_layout) {
            return 0;
        }

        let width_screen = el.getBoundingClientRect().width;
        return width_screen ? (width_screen / width_layout) : 0;
    },

    zoom_anchorRect:                    function(a_slideIndex, astr_address) {
        let str_help = `
            The box on screen occupied by the jump to an address.

            This is what the movement is anchored to. The spoke grows out
            of this box and later shrinks back into it, which is the
            claim the whole transition exists to make: the topic lives
            here, inside the menu that lists it.

            Returns null when the anchor cannot be measured, and the
            caller then does not animate at all.
        `;

        let slideEl = document.getElementById(
            this.str_slideIDprefix + a_slideIndex
        );
        if (!slideEl || !slideEl.querySelector) {
            return null;
        }

        let anchor = slideEl.querySelector(
            '.sd-jump[data-jump="' + astr_address + '"]'
        );
        if (!anchor || !anchor.getBoundingClientRect) {
            return null;
        }

        // An unannounced option is not a place the room can be taken
        // from, so there is nothing to grow out of later either.
        if (!this.jump_isRevealed(anchor)) {
            return null;
        }

        let rect = anchor.getBoundingClientRect();

        // A hidden or unlaid-out element measures zero on both axes.
        if (!rect.width || !rect.height) {
            return null;
        }

        return {
            left:   rect.left,
            top:    rect.top,
            width:  rect.width,
            height: rect.height
        };
    },

    zoom_rectResolve:                   function(a_fromSlide,
                                                 a_toSlide,
                                                 d_options) {
        let str_help = `
            The box this move should grow out of or shrink into, or null
            for the instant swap.

            Motion is confined to moves that assert containment: entering
            a spoke from its nexus, and backing out again. A plain
            advance is a step sideways, not a step inward, and animating
            it would say something untrue about the deck.
        `;

        if (this.str_transition !== 'zoom') {
            return null;
        }
        if (this.motion_isReduced()) {
            return null;
        }
        if (!this.nexus.isNexusDeck()) {
            return null;
        }
        if (a_fromSlide === a_toSlide) {
            return null;
        }

        // A return reuses the box measured when the jump was taken: the
        // nexus is hidden by now and would measure as nothing.
        if (d_options.isReturn) {
            return d_options.rect || null;
        }

        if (!d_options.jumpAddress) {
            return null;
        }

        return this.zoom_anchorRect(a_fromSlide, d_options.jumpAddress);
    },

    zoom_cancel:                        function() {
        let str_help = `
            Snap every in-flight phase straight to its end state.

            Finishing a phase can start the next one, which registers its
            own finisher, so this drains rather than iterates. The deck
            lands in exactly the state it would have reached anyway,
            immediately.
        `;

        let guard = 0;
        while (this.l_zoomPending.length && guard++ < 8) {
            (this.l_zoomPending.shift())();
        }
    },

    zoom_defer:                         function(a_el, a_ms, fn_done) {
        let str_help = `
            Run fn_done once the phase has finished, however it finishes.

            Whichever of transitionend or the timer arrives first wins,
            and the other is disarmed. The finisher is registered so that
            a presenter moving faster than the animation can snap it.
        `;

        let self     = this;
        let b_done   = false;
        let timer    = null;

        let finish = function() {
            if (b_done) {
                return;
            }
            b_done = true;
            if (timer !== null) {
                clearTimeout(timer);
            }
            if (a_el && a_el.removeEventListener) {
                a_el.removeEventListener('transitionend', onEnd);
            }
            let index = self.l_zoomPending.indexOf(finish);
            if (index >= 0) {
                self.l_zoomPending.splice(index, 1);
            }
            fn_done();
        };

        let onEnd = function(e) {
            if (!e || e.propertyName === 'transform') {
                finish();
            }
        };

        this.l_zoomPending.push(finish);

        if (a_el && a_el.addEventListener) {
            a_el.addEventListener('transitionend', onEnd);
        }

        // The slack covers a transitionend that never arrives. A plain
        // wait with no element to listen to needs no such allowance.
        timer = setTimeout(
            finish, a_el ? (a_ms + zoomTransition_SLACKMS) : a_ms
        );
    },

    hit_mark:                           function(a_slideIndex,
                                                 astr_address) {
        let str_help = `
            Light up the entry that was chosen.

            A presenter at a lectern presses a number and the room has no
            way of knowing which. Without this the deck simply starts
            moving, and the audience is left working out after the fact
            where it went. The mark also gives the eye somewhere to be
            when the movement begins, which is the place the movement
            begins from.

            Returns the anchor marked, or null.
        `;

        let anchor = this.jumpAnchor_find(a_slideIndex, astr_address);
        if (!anchor || !anchor.classList) {
            return null;
        }

        anchor.classList.add('sd-jump--selected');
        return anchor;
    },

    hit_clear:                          function(a_anchor) {
        let str_help = `
            Put the chosen entry back to its ordinary state.
        `;

        if (a_anchor && a_anchor.classList) {
            a_anchor.classList.remove('sd-jump--selected');
        }
    },

    jumpAnchor_find:                    function(a_slideIndex,
                                                 astr_address) {
        let str_help = `
            The anchor on a slide that jumps to an address, or null.
        `;

        let slideEl = document.getElementById(
            this.str_slideIDprefix + a_slideIndex
        );
        if (!slideEl || !slideEl.querySelector) {
            return null;
        }

        return slideEl.querySelector(
            '.sd-jump[data-jump="' + astr_address + '"]'
        );
    },

    heading_find:                       function(a_slideIndex) {
        let str_help = `
            The heading a spoke arrives as, or null.

            This is the other end of the shared element. The entry in the
            menu and the heading on the slide are the same thing said
            twice, so the transition can carry one into the other rather
            than replacing a picture of one with a picture of the other.
        `;

        let slideEl = document.getElementById(
            this.str_slideIDprefix + a_slideIndex
        );
        if (!slideEl || !slideEl.querySelector) {
            return null;
        }

        return slideEl.querySelector('h1');
    },

    rect_read:                          function(a_el) {
        let str_help = `
            An element's box, or null when it has none worth having.
        `;

        if (!a_el || !a_el.getBoundingClientRect) {
            return null;
        }

        let rect = a_el.getBoundingClientRect();
        if (!rect.width || !rect.height) {
            return null;
        }

        return {
            left:   rect.left,
            top:    rect.top,
            width:  rect.width,
            height: rect.height
        };
    },

    element_conceal:                    function(a_el) {
        let str_help = `
            Take an element out of sight while its stand-in flies.

            Concealed rather than removed: it keeps its place in the
            layout, so nothing around it moves while it is away.
        `;

        if (a_el && a_el.style) {
            a_el.style.visibility = 'hidden';
        }
    },

    element_reveal:                     function(a_el) {
        let str_help = `
            Put a concealed element back.
        `;

        if (a_el && a_el.style) {
            a_el.style.visibility = '';
        }
    },

    ghost_create:                       function(a_el, d_rect) {
        let str_help = `
            Build the flying copy of a single piece of text.

            This is the whole of the transition's cargo. Flying a
            miniature of the destination slide does not work: at the size
            of a menu entry a slide is an illegible grey rectangle, and
            it repaints as it lands. One line of text reads as text at
            every size on the way, and there is nothing to repaint
            because the real slide is what is underneath.

            The copy is fixed to the screen, so it lives outside the
            deck's layout and outside the scaled viewport. That last part
            means its type has to be scaled by hand: the styles it
            inherits are in the deck's baseline pixels, and on screen
            everything is smaller by the viewport's scale.

            Returns null when the copy cannot be made.
        `;

        if (!a_el || !a_el.cloneNode || !document.createElement) {
            return null;
        }

        let scale = this.viewport_scaleGet();
        if (!scale) {
            return null;
        }

        let d_style = this.ghost_styleRead(a_el);
        if (!d_style) {
            return null;
        }

        let ghost = a_el.cloneNode(true);
        if (!ghost.style) {
            return null;
        }

        this.ghost_idsStrip(ghost);

        ghost.className             = 'sd-ghost';
        ghost.style.position        = 'fixed';
        ghost.style.left            = d_rect.left + 'px';
        ghost.style.top             = d_rect.top + 'px';
        ghost.style.margin          = '0';
        ghost.style.padding         = '0';
        ghost.style.whiteSpace      = 'nowrap';
        ghost.style.pointerEvents   = 'none';
        ghost.style.zIndex          = '9999';
        ghost.style.transformOrigin = 'left center';
        ghost.style.willChange      = 'transform, opacity';

        // Type in screen pixels rather than baseline pixels, since the
        // copy is not inside the viewport that scales the deck.
        ghost.style.fontFamily      = d_style.fontFamily;
        ghost.style.fontWeight      = d_style.fontWeight;
        ghost.style.fontStyle       = d_style.fontStyle;
        ghost.style.color           = d_style.color;
        ghost.style.textTransform   = d_style.textTransform;
        ghost.style.fontSize        = (d_style.fontSize * scale) + 'px';
        ghost.style.lineHeight      = d_rect.height + 'px';

        document.body.appendChild(ghost);
        return ghost;
    },

    ghost_styleRead:                    function(a_el) {
        let str_help = `
            The type an element is set in, as numbers where it matters.
        `;

        if (typeof window === 'undefined' || !window.getComputedStyle) {
            return null;
        }

        try {
            let computed = window.getComputedStyle(a_el);
            return {
                fontFamily:     computed.fontFamily,
                fontWeight:     computed.fontWeight,
                fontStyle:      computed.fontStyle,
                color:          computed.color,
                textTransform:  computed.textTransform,
                fontSize:       parseFloat(computed.fontSize) || 16
            };
        } catch (err) {
            return null;
        }
    },

    ghost_idsStrip:                     function(a_el) {
        let str_help = `
            Remove every id from a cloned subtree.

            Two elements answering to one id is the kind of fault that
            surfaces later, somewhere else, as a slide driving the wrong
            reveals.
        `;

        if (!a_el || !a_el.removeAttribute) {
            return;
        }

        a_el.removeAttribute('id');
        if (!a_el.querySelectorAll) {
            return;
        }

        let l_withId = a_el.querySelectorAll('[id]');
        for (let i = 0; i < l_withId.length; i++) {
            l_withId[i].removeAttribute('id');
        }
    },

    ghost_destroy:                      function(a_ghost) {
        let str_help = `
            Take the flying copy back out of the document.
        `;

        if (a_ghost && a_ghost.parentNode) {
            a_ghost.parentNode.removeChild(a_ghost);
        }
    },

    ghost_fly:                          function(a_ghost,
                                                 d_from,
                                                 d_to,
                                                 fn_done) {
        let str_help = `
            Carry the copy from where it was written to where it is
            written next.

            Scaled by the ratio of the two heights rather than their
            widths: these are two phrasings of one thing and rarely the
            same length, but they are both a line of type, and it is the
            type that has to match at the end.
        `;

        if (!a_ghost || !a_ghost.style) {
            fn_done();
            return;
        }

        let scale = d_to.height / d_from.height;
        let x_shift = d_to.left - d_from.left;
        let y_shift = (d_to.top + d_to.height / 2)
                    - (d_from.top + d_from.height / 2);

        a_ghost.style.transition = 'none';
        a_ghost.style.transform  = 'translate(0px, 0px) scale(1)';

        // Read a layout property so the browser treats the setting above
        // as a start state rather than folding it into the end.
        void a_ghost.offsetWidth;

        a_ghost.style.transition = 'transform ' + zoomTransition_FLIGHTMS
                                 + 'ms ' + zoomTransition_EASE;
        a_ghost.style.transform  = 'translate(' + x_shift + 'px, '
                                 + y_shift + 'px) scale(' + scale + ')';

        this.zoom_defer(a_ghost, zoomTransition_FLIGHTMS, fn_done);
    },

    ghost_land:                         function(a_ghost, a_arriving,
                                                 fn_done) {
        let str_help = `
            Hand the flight back to the real element.

            An entry and the heading it becomes are usually not word for
            word the same, so the last moment is a short cross-fade
            rather than a swap. Where the two do read the same, there is
            nothing to see.
        `;

        if (a_arriving && a_arriving.style) {
            a_arriving.style.visibility = '';
            a_arriving.style.opacity    = '0';
            a_arriving.style.transition = 'opacity '
                                        + zoomTransition_CROSSMS + 'ms linear';
        }

        if (!a_ghost || !a_ghost.style) {
            fn_done();
            return;
        }

        void a_ghost.offsetWidth;

        if (a_arriving && a_arriving.style) {
            a_arriving.style.opacity = '1';
        }

        a_ghost.style.transition += ', opacity ' + zoomTransition_CROSSMS
                                  + 'ms linear';
        a_ghost.style.opacity = '0';

        this.zoom_defer(a_ghost, zoomTransition_CROSSMS, fn_done);
    },

    slide_detach:                       function(a_slideIndex) {
        let str_help = `
            Lift a slide out of the deck's flex flow without moving it.

            Two slides cannot both be shown while they are flex children
            of the viewport: they would sit one above the other. Pinning
            the outgoing one to the box it already occupies takes it out
            of the flow so the incoming one can lay out normally, and
            leaves it exactly where it was on screen.
        `;

        let slideEl = document.getElementById(
            this.str_slideIDprefix + a_slideIndex
        );
        if (!slideEl || !slideEl.style) {
            return;
        }

        // Layout coordinates, so unaffected by the viewport's scale.
        slideEl.style.left     = slideEl.offsetLeft + 'px';
        slideEl.style.top      = slideEl.offsetTop + 'px';
        slideEl.style.width    = slideEl.offsetWidth + 'px';
        slideEl.style.height   = slideEl.offsetHeight + 'px';
        slideEl.style.position = 'absolute';
    },

    slide_reattach:                     function(a_slideIndex) {
        let str_help = `
            Put a lifted slide back into the flow.
        `;

        let slideEl = document.getElementById(
            this.str_slideIDprefix + a_slideIndex
        );
        if (!slideEl || !slideEl.style) {
            return;
        }

        slideEl.style.position   = '';
        slideEl.style.left       = '';
        slideEl.style.top        = '';
        slideEl.style.width      = '';
        slideEl.style.height     = '';
        slideEl.style.opacity    = '';
        slideEl.style.transition = '';
        slideEl.style.willChange = '';
    },

    slide_fade:                         function(a_slideIndex, ab_in) {
        let str_help = `
            Cross the two slides over underneath the flying text.

            Opacity only. Everything the eye is meant to follow is
            already being carried by the copy in flight; the pages behind
            it should change without asking for attention.
        `;

        let slideEl = document.getElementById(
            this.str_slideIDprefix + a_slideIndex
        );
        if (!slideEl || !slideEl.style) {
            return;
        }

        slideEl.style.willChange = 'opacity';
        slideEl.style.transition = 'none';
        slideEl.style.opacity    = ab_in ? '0' : '1';

        void slideEl.offsetWidth;

        slideEl.style.transition = 'opacity ' + zoomTransition_FLIGHTMS
                                 + 'ms ' + zoomTransition_EASE;
        slideEl.style.opacity    = ab_in ? '1' : '0';
    },

    slide_transition:                   function(index_currentSlide,
                                                 index_followingSlide,
                                                 options) {
        let str_help = `
            Move the deck from one slide to another, carrying the chosen
            entry across as the heading it becomes when the deck has
            asked for it and the move is one that carry can describe.

            Every path that cannot or should not animate falls through to
            slide_commit unchanged, which is every path any existing deck
            takes.
        `;

        let d_options = options || {};

        // Measure nothing while a previous move is still in flight.
        this.zoom_cancel();

        let d_rect = this.zoom_rectResolve(
            index_currentSlide, index_followingSlide, d_options
        );

        if (!d_rect) {
            this.slide_commit(
                index_currentSlide, index_followingSlide, d_options
            );
            return;
        }

        let self = this;

        // The spoke is whichever end is not the nexus, and the heading is
        // the spoke's. Going in the entry becomes the heading; coming
        // back the heading becomes the entry again.
        let b_isReturn  = d_options.isReturn === true;
        let index_spoke = b_isReturn ? index_currentSlide
                                     : index_followingSlide;
        let index_nexus = b_isReturn ? index_followingSlide
                                     : index_currentSlide;

        let fly = function() {
            // A return carries no address of its own; the spoke it is
            // leaving names the entry it has to fly back into.
            let str_address = d_options.jumpAddress
                            || (self.nexus.spokeFor(index_spoke) || {}).address;

            let anchor = self.jumpAnchor_find(index_nexus, str_address);

            // Pin the outgoing slide out of the flex flow and swap before
            // measuring anything. Both slides are flex children, so with
            // the outgoing one still in the flow the incoming one lays
            // out beneath it — and a heading measured there is half a
            // page below where it will actually sit, which sends the
            // carry downwards instead of up.
            self.slide_detach(index_currentSlide);
            self.slide_commit(
                index_currentSlide, index_followingSlide, d_options, true
            );

            let leaving = document.getElementById(
                self.str_slideIDprefix + index_currentSlide
            );
            if (leaving && leaving.style) {
                leaving.style.display = 'block';
            }

            let heading = self.heading_find(index_spoke);
            let d_rectHeading = self.rect_read(heading);

            let d_from = b_isReturn ? d_rectHeading : d_rect;
            let d_to   = b_isReturn ? d_rect : d_rectHeading;
            let departing = b_isReturn ? heading : anchor;
            let arriving  = b_isReturn ? anchor : heading;

            let ghost = (heading && d_rectHeading && departing)
                            ? self.ghost_create(departing, d_from)
                            : null;

            if (!ghost) {
                // The swap has already happened; only the scaffolding
                // for the carry has to be taken back down.
                if (leaving && leaving.style) {
                    leaving.style.display = 'none';
                }
                self.slide_reattach(index_currentSlide);
                self.slide_reattach(index_followingSlide);
                self.startNonSnippetTypewriters(index_followingSlide);
                return;
            }

            // Both ends of the shared element step aside for the copy.
            self.element_conceal(departing);
            self.element_conceal(arriving);

            self.slide_fade(index_currentSlide, false);
            self.slide_fade(index_followingSlide, true);

            self.ghost_fly(ghost, d_from, d_to, function() {
                if (leaving && leaving.style) {
                    leaving.style.display = 'none';
                }
                self.slide_reattach(index_currentSlide);
                self.slide_reattach(index_followingSlide);
                self.element_reveal(departing);

                self.ghost_land(ghost, arriving, function() {
                    if (arriving && arriving.style) {
                        arriving.style.opacity    = '';
                        arriving.style.transition = '';
                    }
                    self.ghost_destroy(ghost);
                    self.startNonSnippetTypewriters(index_followingSlide);
                });
            });
        };

        if (b_isReturn) {
            fly();
            return;
        }

        // Going in, the room is shown what was chosen before anything
        // moves. Returning needs no such beat: nothing was selected.
        let anchor = this.hit_mark(index_nexus, d_options.jumpAddress);
        this.zoom_defer(null, zoomTransition_HITMS, function() {
            self.hit_clear(anchor);
            fly();
        });
    },

    updateFooterTemplates:              function() {
        let str_help = `
            Update footer and navbar elements that have counter templates.

            Looks for elements with data-template attribute and replaces
            {current} and {total} with actual slide numbers.
        `;

        // Helper function to update element with template
        const updateCounter = (element) => {
            if (element && element.dataset.template) {
                let template = element.dataset.template;
                let text = template
                    .replace('{current}', this.currentSlide)
                    .replace('{total}', this.l_slide.length);
                element.innerHTML = text;
            }
        };

        // Update footer elements
        updateCounter(document.getElementById('footerLeft'));
        updateCounter(document.getElementById('footerRight'));

        // Update navbar counter elements (by class)
        let navbarCounters = document.querySelectorAll('.navbar-counter');
        navbarCounters.forEach(counter => updateCounter(counter));
    },

    // Page
    FAinputButton_create:               function(astr_functionClickName,
                                                 astr_value,
                                                 astr_fname,
                                                 astr_baseSet = "fa") {
        let str_inputButton     = `<input type="button"   onclick="` + astr_functionClickName + `"
                                    value=" &#x` + astr_value + ` "
                                    style="padding: .1em .4em;"
                                    class=" pure-button
                                            pure-button-primary
                                            ` + astr_baseSet + ` ` + astr_baseSet + '-' + astr_fname + `">
                                  `;
        return(str_inputButton);
    },

    // Page
    rightArrow_inputButtonCreate:       function() {
        return(this.FAinputButton_create("page.rightArrow_process()",
                                         "f35a", "arrow-alt-circle-right"));
    },

    // Page
    rightArrow_process:                 function() {
        let str_help = `

            Process a right arrow event

            Call the next slide.

            The mirror rule: advancing past the end of a spoke that was
            entered by a jump hands back to the nexus it came from.
            A spoke walked into linearly falls through as normal, so a
            deck read start to finish behaves like an ordinary deck and
            no author-facing flag is needed.

        `;

        if(!this.advance_overSnippets())
            return;

        if(this.l_returnStack.length &&
           this.nexus.spokeEndsAt(this.currentSlide)) {
            this.return_process();
            return;
        }

        this.advance_toNext();
    },

    // Page
    leftArrow_inputButtonCreate:        function() {
        return(this.FAinputButton_create("page.leftArrow_process()",
                                         "f359", "arrow-alt-circle-left"));
    },

    // Page
    leftArrow_process:                  function() {
        let str_help = `

            Process a left arrow event

            Call the previous slide.
        `;
        if(this.retreat_overSnippets())
            this.advance_toPrevious();
    },

    // Page
    upArrow_inputButtonCreate:          function() {
        return(this.FAinputButton_create("page.upArrow_process()",
                                         "f35b", "arrow-alt-circle-up"));
    },

    // Page
    upArrow_process:                    function() {
        let str_help = `

            Process an up arrow event --

            Call the first slide.

        `;

        this.advance_toFirst();
    },

    // Page
    downArrow_inputButtonCreate:        function() {
        return(this.FAinputButton_create("page.downArrow_process()",
                                         "f358", "arrow-alt-circle-down"));
    },

    // Page
    downArrow_process:                  function() {
        let str_help = `

            Process a down arrow event

            Call the final slide.
        `;

        this.advance_toLast();
    },

    // Page
    checkForArrowKeyPress:          function(e) {
        let str_help = `

            The 'this' seems confused at this point. My guess is that
            since the event is defined on the "document" the 'this'
            retains that identify when executing here.

            Hence, we call the 'page' variable explicitly when resolving
            scope.

        `;

        e = e || window.event;

        if (typographyScale_keyHandle(e)) {
            return;
        }

        if (page.nexusDigit_keyHandle(e)) {
            return;
        }

        if (page.nexusCursor_keyHandle(e)) {
            return;
        }

        // Esc goes home from anywhere in a spoke, not only from its end.
        // A presenter who reads the room three slides into a topic should
        // not have to walk to the end of it first. This is the affordance
        // that separates a menu from a deck with shortcuts.
        if (e.key === 'Escape' && page.nexus.isNexusDeck()) {
            if (page.nexus.spokeFor(page.currentSlide)) {
                page.return_process();
                return;
            }
        }

        if (e.keyCode == '38') {
            // up arrow
            console.log('up arrow')
            page.upArrow_process();
        }
        else if (e.keyCode == '40') {
            // down arrow
            console.log('down arrow')
            page.downArrow_process();
        }
        else if (e.keyCode == '37') {
           // left arrow
           console.log('left arrow')
            page.leftArrow_process();
        }
        else if (e.keyCode == '39') {
           // right arrow
           console.log('right arrow')
            page.rightArrow_process();
        }
    },

    // Page
    checkForMouseClick:             function(e) {
        let str_help = `

            Handle mouse clicks for navigation.

            Click on left half of page -> go to previous slide
            Click on right half of page -> go to next slide

            Ignore clicks on buttons and interactive elements.

        `;

        e = e || window.event;

        // A jump is navigation in its own right; it must not also advance.
        if (page.jumpClick_process(e)) {
            return;
        }

        // Ignore clicks on buttons, links, and other interactive elements.
        // Tested with closest() rather than on e.target directly: a click
        // often lands on markup *inside* an anchor (a <strong> in a link
        // label, say), where the target itself is not the interactive
        // element but the click still belongs to it.
        let target = e.target || e.srcElement;
        if (target && target.closest &&
            target.closest('a, button, input, textarea, select')) {
            return;
        }

        // A nexus is a slide you park on. Click-to-advance there would
        // turn a near-miss on a jump into a silent skip into the next
        // slide, which is the worst possible failure on the one slide
        // the presenter is standing on. Arrow keys still work.
        if (page.nexus.placementFor(page.currentSlide)) {
            return;
        }

        // Get the click position relative to the window
        let clickX = e.clientX;
        let windowWidth = window.innerWidth;

        // Determine if click is on left or right half
        if (clickX < windowWidth / 2) {
            // Left half - go to previous slide
            console.log('mouse click: left half')
            page.leftArrow_process();
        } else {
            // Right half - go to next slide
            console.log('mouse click: right half')
            page.rightArrow_process();
        }
    },


    // Page
    fields_populateFromURL: function() {
        let str_help = `
            Populate various fields on the page from URL args
        `;
        this.url.parse();
    }
}

// ---------------------------------------------------------------------------------------------------------------
// ---------------------------------------------------------------------------------------------------------------

// Page object
var page            = new Page();


// The whole document
$body               = $("body");

// Presentation scaling for 2K baseline (2560x1440)
function scalePresentation() {
    const BASELINE_WIDTH = 2560;
    const BASELINE_HEIGHT = 1440;

    const viewport = document.querySelector('.presentation-viewport');
    if (!viewport) return;

    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    // Calculate scale to fit viewport while maintaining aspect ratio
    const scaleX = windowWidth / BASELINE_WIDTH;
    const scaleY = windowHeight / BASELINE_HEIGHT;
    const scale = Math.min(scaleX, scaleY);

    // Apply scale transform
    viewport.style.transform = `scale(${scale})`;

    // Center the presentation
    const scaledWidth = BASELINE_WIDTH * scale;
    const scaledHeight = BASELINE_HEIGHT * scale;
    const offsetX = (windowWidth - scaledWidth) / 2;
    const offsetY = (windowHeight - scaledHeight) / 2;

    viewport.style.left = `${offsetX}px`;
    viewport.style.top = `${offsetY}px`;
}

window.onload = function() {
    // Capture compiled deck typography baseline before runtime changes
    typographyScale_initialize();

    // Scale presentation to fit viewport
    scalePresentation();

    // Start where ?slide= asks, by number or by address; slide 1 otherwise.
    let index_start             = page.startSlide_fromURL();
    page.currentSlide           = index_start;
    page.slide_transition(index_start, index_start);
};

// Rescale on window resize
window.addEventListener('resize', scalePresentation);
