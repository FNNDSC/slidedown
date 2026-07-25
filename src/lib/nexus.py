"""
Nexus navigation: slide addressing and the hub-and-spokes graph

Slides acquire stable, human-meaningful names so that later navigation
features can refer to them without using slide numbers, which break the
moment a slide is inserted.

An address comes from an explicit ``.id{}`` child on ``.slide{}``, or is
slugified from the slide's ``.title{}`` when no ``.id{}`` is present.
Explicit ids win. Duplicate addresses are a compilation error, on the
principle that a compiler holding enough information to reject a mistake
should reject it at build time rather than at the lectern.

See ``docs/nexus-navigation.adoc`` for the full design.
"""

from __future__ import annotations

import json
import re

from ..models.compiler import (
    JumpRefs,
    NexusPlacements,
    SlideAddresses,
    SlideCounters,
)

# Schema version for the emitted navigation graph. The runtime reads this
# and refuses graphs it does not understand rather than guessing.
GRAPH_VERSION = 1

GRAPH_ELEMENT_ID = "nexusGraph"


class SlideAddressCollision(ValueError):
    """Two slides resolved to the same address."""


class UnresolvedJumpTarget(ValueError):
    """A .jump{} names a slide address that no slide claims."""


class UnresolvedNexusRef(ValueError):
    """A .nexus{.ref{}} names a nexus that has not been defined."""


# Per-slide element ids embedded in compiled HTML. A nexus placed a second
# time carries its original slide's ids and must be rebased.
SNIPPET_ID_PATTERN = re.compile(r'id="order-\d+-\d+"')
TYPEWRITER_ID_PATTERN = re.compile(r'id="typewriter-\d+-\d+"')
JUMP_ADDRESS_PATTERN = re.compile(r'data-jump="([^"]+)"')


def titleSlug_make(title: str) -> str:
    """
    Slugify a slide title into an address.

    Lowercases, collapses runs of non-alphanumeric characters to single
    hyphens, and trims leading/trailing hyphens.

    Args:
        title: Raw ``.title{}`` content.

    Returns:
        Slug suitable for use as an address, or an empty string when the
        title contains no alphanumeric characters.

    Example:
        >>> titleSlug_make("Does It Survive a Re-Run?")
        'does-it-survive-a-re-run'
    """
    slug: str = re.sub(r"[^a-z0-9]+", "-", title.strip().lower())
    return slug.strip("-")


def slideAddress_resolve(explicit_id: str, title: str) -> str:
    """
    Determine a slide's address from its explicit id or its title.

    Args:
        explicit_id: Content of the slide's ``.id{}`` child, if any.
        title: Content of the slide's ``.title{}`` child, if any.

    Returns:
        The resolved address, or an empty string when the slide has
        neither an explicit id nor a sluggable title. Such slides are
        simply not addressable; that is not an error.
    """
    explicit: str = explicit_id.strip()
    if explicit:
        return titleSlug_make(explicit)

    return titleSlug_make(title)


def slideAddress_register(
    addresses: SlideAddresses, address: str, slide_num: int
) -> None:
    """
    Record a slide address, rejecting collisions.

    Args:
        addresses: Address map being accumulated (address → slide number).
        address: Address to record; empty addresses are ignored.
        slide_num: 1-based slide number owning this address.

    Raises:
        SlideAddressCollision: Another slide already claims this address.
    """
    if not address:
        return

    existing: int | None = addresses.get(address)
    if existing is not None and existing != slide_num:
        raise SlideAddressCollision(
            f"Address '{address}' is claimed by both slide {existing} and "
            f"slide {slide_num}. Give one of them an explicit .id{{}} to "
            f"disambiguate."
        )

    addresses[address] = slide_num


def jumpRefs_validate(
    jump_refs: JumpRefs, addresses: SlideAddresses
) -> None:
    """
    Reject jumps whose target address no slide claims.

    Runs after the compile walk, when every address is known, so a jump may
    legitimately point forward to a slide compiled later than itself.

    Args:
        jump_refs: Recorded (target_address, source_slide) pairs.
        addresses: Completed address map.

    Raises:
        UnresolvedJumpTarget: A jump names an address that does not exist.
    """
    for target, source_slide in jump_refs:
        if target in addresses:
            continue

        known: str = ", ".join(sorted(addresses)) or "(none)"
        raise UnresolvedJumpTarget(
            f".jump{{}} on slide {source_slide} targets '{target}', which "
            f"no slide claims. Known addresses: {known}"
        )


def nexusBody_rebase(
    body_html: str,
    to_slide: int,
    snippet_counters: SlideCounters,
    typewriter_counters: SlideCounters,
) -> str:
    """
    Rewrite per-slide element ids so a re-placed nexus drives its own slide.

    Snippet and typewriter ids encode the slide they were compiled on.
    Copying a nexus verbatim onto a second slide would duplicate those ids
    and point the reveal machinery at the original slide, so each id is
    reissued against the destination slide's counters.

    Args:
        body_html: Compiled HTML of the nexus body.
        to_slide: Slide number the copy is being placed on.
        snippet_counters: Per-slide snippet counters, updated in place.
        typewriter_counters: Per-slide typewriter counters, updated in place.

    Returns:
        Body HTML with ids rebased onto ``to_slide``.
    """

    def snippet_rewrite(_match: re.Match[str]) -> str:
        snippet_counters[to_slide] = snippet_counters.get(to_slide, 0) + 1
        return f'id="order-{to_slide}-{snippet_counters[to_slide]}"'

    def typewriter_rewrite(_match: re.Match[str]) -> str:
        typewriter_counters[to_slide] = (
            typewriter_counters.get(to_slide, 0) + 1
        )
        return f'id="typewriter-{to_slide}-{typewriter_counters[to_slide]}"'

    rebased: str = SNIPPET_ID_PATTERN.sub(snippet_rewrite, body_html)
    return TYPEWRITER_ID_PATTERN.sub(typewriter_rewrite, rebased)


def jumpAddresses_extract(body_html: str) -> list[str]:
    """
    Read the ordered jump addresses out of a compiled nexus body.

    Order is document order, which is the order the author wrote them and
    therefore the order the digit keys must follow.

    Args:
        body_html: Compiled HTML of the nexus body.

    Returns:
        Jump target addresses, in order, without duplicates.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for address in JUMP_ADDRESS_PATTERN.findall(body_html):
        if address not in seen:
            seen.add(address)
            ordered.append(address)

    return ordered


def spokes_compute(
    addresses: SlideAddresses,
    jump_refs: JumpRefs,
    placements: NexusPlacements,
    slide_count: int,
) -> list[dict[str, object]]:
    """
    Determine the extent of every spoke in the deck.

    A spoke begins at a slide that some jump targets, and ends immediately
    before the next slide that is itself a jump target or a nexus
    placement. Single-slide spokes — the common case — fall out of the
    rule naturally.

    This is load-bearing rather than bookkeeping: the runtime needs to know
    when advancing has reached the end of a spoke, because that is the
    moment a jumped-into spoke returns to the nexus it came from.

    Args:
        addresses: Completed address map.
        jump_refs: Recorded (target_address, source_slide) pairs.
        placements: Nexus placements.
        slide_count: Total slides in the deck.

    Returns:
        Spoke descriptions, ordered by starting slide.
    """
    target_slides: dict[int, str] = {}
    for target, _source in jump_refs:
        slide = addresses.get(target)
        if slide is not None:
            target_slides.setdefault(slide, target)

    placement_slides: set[int] = {slide for _id, slide, _j in placements}
    boundaries: list[int] = sorted(set(target_slides) | placement_slides)

    spokes: list[dict[str, object]] = []
    for start in sorted(target_slides):
        later = [b for b in boundaries if b > start]
        end: int = (later[0] - 1) if later else slide_count
        spokes.append(
            {"address": target_slides[start], "start": start, "end": end}
        )

    return spokes


def navigationGraph_build(
    addresses: SlideAddresses,
    jump_refs: JumpRefs,
    slide_count: int,
    placements: NexusPlacements | None = None,
) -> dict[str, object]:
    """
    Assemble the navigation graph consumed by the runtime.

    The graph is deliberately explicit rather than compact: every fact the
    runtime needs is stated here, where the compiler's tests can assert it,
    rather than derived in JavaScript where nothing covers it.

    Args:
        addresses: Completed address map.
        jump_refs: Recorded (target_address, source_slide) pairs.
        slide_count: Total slides in the deck.
        placements: Nexus placements, in document order.

    Returns:
        JSON-serialisable graph description.
    """
    nexus_placements: NexusPlacements = placements or []

    return {
        "version": GRAPH_VERSION,
        "slideCount": slide_count,
        "slides": dict(addresses),
        "jumps": [
            {"target": target, "targetSlide": addresses[target], "from": src}
            for target, src in jump_refs
        ],
        # A deck is a nexus deck when it places at least one nexus. A deck
        # containing only inline cross-references is not, and keeps its
        # ordinary navigation behaviour.
        "isNexusDeck": bool(nexus_placements),
        "nexuses": [
            {"id": nexus_id, "slide": slide, "jumps": list(jumps)}
            for nexus_id, slide, jumps in nexus_placements
        ],
        "spokes": spokes_compute(
            addresses, jump_refs, nexus_placements, slide_count
        ),
    }


def navigationGraph_htmlEmit(
    addresses: SlideAddresses,
    jump_refs: JumpRefs,
    slide_count: int,
    placements: NexusPlacements | None = None,
) -> str:
    """
    Render the navigation graph as an inert JSON script element.

    Uses ``type="application/json"`` so the browser does not execute it;
    the runtime parses it at startup.

    Args:
        addresses: Completed address map.
        jump_refs: Recorded (target_address, source_slide) pairs.
        slide_count: Total slides in the deck.

    Returns:
        HTML for the graph element, or an empty string when the deck has
        no addresses at all.
    """
    if not addresses:
        return ""

    graph = navigationGraph_build(
        addresses, jump_refs, slide_count, placements
    )
    payload: str = json.dumps(graph, separators=(",", ":"), sort_keys=True)

    # A script element has a raw-text content model: the browser will not
    # decode HTML entities inside it, so escaping "<" as an entity would
    # corrupt the payload. Escaping it as < is valid JSON, decodes
    # back to "<", and makes "</script>" unrepresentable.
    return (
        f'    <script type="application/json" id="{GRAPH_ELEMENT_ID}">'
        f'{payload.replace("<", chr(92) + "u003c")}</script>'
    )
