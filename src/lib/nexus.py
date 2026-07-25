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

import re

from ..models.compiler import SlideAddresses


class SlideAddressCollision(ValueError):
    """Two slides resolved to the same address."""


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
