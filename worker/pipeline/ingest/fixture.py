"""Fixture scraper. Yields a fixed set of "raw" listings so the pipeline can
run end-to-end without network access. Replace with the real EURAXESS scraper
once the Phase-0 DevTools spike picks between JSON endpoint and JS-HTML."""

from collections.abc import Iterator

from worker.pipeline.ingest.base import RawListing

_FIXTURES: list[tuple[str, str]] = [
    (
        "fixture-eu-001",
        """
        title: PhD in Attosecond Photoelectron Spectroscopy
        institution: Max Planck Institute for the Structure and Dynamics of Matter
        country: Germany
        city: Hamburg
        field: ultrafast laser physics, attosecond science
        offer_type: PhD
        funding: Fully funded, 3 years, TVöD E13
        deadline: 2026-09-30
        contact_email: phd-recruit@mpsd.mpg.de
        application_url: https://example.org/apply/001
        required_docs: CV, Cover Letter, Transcripts, Two References
        description: Investigate attosecond photoionisation in solids. The successful candidate
        will work with high-harmonic generation sources, COLTRIMS detection, and develop
        TDDFT analysis pipelines in collaboration with the theory group.
        """.strip(),
    ),
    (
        "fixture-eu-002",
        """
        title: PhD position in Quantum Magnonics
        institution: Delft University of Technology
        country: Netherlands
        city: Delft
        field: condensed matter, quantum information
        offer_type: PhD
        funding: Fully funded, 4 years
        deadline: 2026-08-15
        contact_email: magnon-phd@tudelft.nl
        application_url: https://example.org/apply/002
        required_docs: CV, Research Statement, Transcripts
        description: Study coherent coupling of magnons to superconducting qubits.
        Strong cryogenic-microwave background preferred.
        """.strip(),
    ),
    (
        "fixture-eu-003",
        """
        title: PhD scholarship - Algorithmic Game Theory
        institution: ETH Zurich
        country: Switzerland
        city: Zurich
        field: theoretical computer science, economics
        offer_type: PhD
        funding: Fully funded, ETH salary scale
        deadline: 2026-12-01
        contact_email: agt-recruit@inf.ethz.ch
        application_url: https://example.org/apply/003
        required_docs: CV, Statement of Purpose, Transcripts, Three References
        description: Research mechanism design for online markets with strategic agents.
        Background in algorithms and probability required; auctions/matching a plus.
        """.strip(),
    ),
    (
        "fixture-eu-004",
        """
        title: Postdoctoral Researcher - Computational Plasma Physics
        institution: CEA Saclay
        country: France
        city: Gif-sur-Yvette
        field: plasma physics, computational science
        offer_type: Postdoc
        funding: 2-year contract
        deadline: 2026-07-20
        contact_email: postdoc-plasma@cea.fr
        application_url: https://example.org/apply/004
        required_docs: CV, Publication List, Two References
        description: Develop PIC codes for inertial confinement fusion targets.
        """.strip(),
    ),
    (
        "fixture-eu-005",
        """
        title: Trainee position - Generic administration role
        institution: Some Random Bureau
        country: Belgium
        city: Brussels
        field: administration
        offer_type: Trainee
        funding: Unfunded
        deadline: 2026-06-10
        contact_email: hr@example.org
        application_url: https://example.org/apply/005
        required_docs: CV, Cover Letter
        description: General office traineeship - unrelated to research.
        """.strip(),
    ),
]


class FixtureScraper:
    source = "fixture"

    def fetch(self) -> Iterator[RawListing]:
        for key, raw in _FIXTURES:
            yield RawListing(
                source=self.source,
                source_key=key,
                url=f"https://example.org/fixture/{key}",
                raw_text=raw,
            )
