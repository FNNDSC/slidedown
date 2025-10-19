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
    var HTML = t.innerHTML;

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
///////// A Page object that describes the HTML version elements from a
///////// logical perspective.
/////////

function Page() {
    let str_help = `

        The Page object defines/interacts with the html page.

        The page element strings are "defined" here, and various
        DOM objects that can interact with these elements are also
        instantiated.

    `;

    this.currentSlide               = 1;
    document.onkeydown              = this.checkForArrowKeyPress;


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

        this.str_slideIDprefix  = document.getElementById('slideIDprefix').innerHTML;
        let numberOfSlides      = document.getElementById('numberOfSlides').innerHTML;
        for(let i=1; i<=numberOfSlides; i++) {
            this.l_slide.push(this.str_slideIDprefix + i);
        }

        // Parse for snippets per slide
        for(const DOMslideID of this.l_slide) {
            str_slide           = document.getElementById(DOMslideID).outerHTML;
            snippetsPerSlide    = this.substr_count('snippet', str_slide);
            this.l_snippetsPerSlide.push(snippetsPerSlide);
            this.l_snippetPerSlideON.push(0);
        }
    },

    setupTypewriter:                    function(t) {
        let str_help = `
            ///////// A typewriter effect object
            ///////// from https://codepen.io/stevn/pen/jEZvXa

        `;
        var HTML            = t.innerHTML;
        t.innerHTML         = "";

        var cursorPosition  = 0,
            tag             = "",
            writingTag      = false,
            tagOpen         = false,
            typeSpeed       = 10,
            tempTypeSpeed   = 0;

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
    },

    retreat_overSnippets:               function() {
        let str_help = `
            For a given slide, this retreats over the snippets, turning
            each current snippet OFF.

            Return:
            true:       All snippets have been toggled to display: none
            false:      Some snippets still ON
        `;
        let thisSlide   = this.currentSlide-1
        // Check if all snippets are OFF, and if so, return with a true
        if(this.l_snippetPerSlideON[thisSlide] == 0)
            return true;

        let snippetToDisplayOFF         = this.l_snippetPerSlideON[thisSlide];
        let DOMsnippet                  = document.getElementById(
                                            'order-' + this.currentSlide +
                                            '-' + snippetToDisplayOFF
                                            );
        DOMsnippet.style.display        = 'none';
        this.l_snippetPerSlideON[thisSlide] -= 1;
        return false;

    },

    advance_overSnippets:               function() {
        let str_help = `
            For a given slide, this advances over the snippets, turning
            each current snippet ON.

            Return:
            true:       All snippets have been toggled to display: block
            false:      Some snippets still OFF
        `;
        let thisSlide   = this.currentSlide-1
        // Check if all snippets are ON, and if so, return with a true
        if(this.l_snippetPerSlideON[thisSlide] ==
            this.l_snippetsPerSlide[thisSlide])
            return true;

        let snippetToDisplay            = this.l_snippetPerSlideON[thisSlide] + 1;
        let DOMsnippet                  = document.getElementById(
                                                'order-' + this.currentSlide +
                                                '-' + snippetToDisplay
                                            );
        DOMsnippet.style.display        = 'block';
        this.l_snippetPerSlideON[thisSlide]    += 1;
        return false;
    },

    allSnippets_displaySet:             function(astr_state, a_slideIndex) {
        let str_help = `
            For a given slide <a_slideIndex> set the display state of (any)
            snippet elements to <astr_state>. Note that the <a_slideIndex>
            counts starting from 1 not 0.
        `;
        snippets    = this.l_snippetsPerSlide[a_slideIndex-1];
        for(let snippet=1; snippet <= snippets; snippet++) {
            DOMsnippet = document.getElementById(
                            'order-' + a_slideIndex +
                            '-' + snippet
            );
            DOMsnippet.style.display =  astr_state;
        }
        this.l_snippetPerSlideON[a_slideIndex-1] = 0;
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

    slide_typewriterEffectProcess:      function(index_slide) {
        let str_help = `
            Run the typewriter effect on tags, in order, that
            might be displayed.
        `;

        let str_idRef   = 'typewriter-' + index_slide;
        let typer       = document.getElementById(str_idRef);
        if(typer) {
            this.d_typerDOM[str_idRef]      = typer;
            this.d_typewriter[str_idRef]    = this.setupTypewriter(
                                                    this.d_typerDOM[str_idRef]
                                                );
            this.d_typewriter[str_idRef].type();
        }
    },

    slide_transition:                   function(index_currentSlide,
                                                 index_followingSlide) {
        let str_help = `
            Do the actual transition from one slide to another,
            as well as update the running slide counter in the footer.

            Also, on the next slide, process any typewriter effects.
        `;

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
        this.slide_typewriterEffectProcess(index_followingSlide);
        // this.allSnippets_displaySet('none', index_followingSlide);
        if(DOMID_slideTitle !== null) {
            DOMID_pageTitle.innerHTML = DOMID_slideTitle.innerHTML;
        } else {
            DOMID_pageTitle.innerHTML = " ";
        }
        DOMID_slideCounter.innerHTML = "slide "                 +
                                        this.currentSlide       +
                                        " / " + this.l_slide.length;
        progress = this.currentSlide / this.l_slide.length * 100;
        DOMID_slideBar.style.width = progress + "%";
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

        `;

        if(this.advance_overSnippets())
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
let page            = new Page();


// The whole document
$body               = $("body");

window.onload = function() {
    // Start on the first slide
    page.advance_toFirst();
};


