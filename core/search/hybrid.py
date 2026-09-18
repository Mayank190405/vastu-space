"""
Hybrid Spatial Search Engine:
Executes the full 5-stage search pipeline:
Query -> Lexical Matching -> Semantic Matching -> Spatial Filtering -> Ranking -> Result Coordinates
Resolves exact names, typos, architectural concepts, and relational queries (e.g. 'chairs near reception')
into authoritative 3D coordinates, room containment, confidence, and preview metadata.
"""

import re
import time
import uuid
import difflib
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
import numpy as np

from core.schemas.poi import PointOfInterest
from core.schemas.search import (
    SpatialSearchQuery,
    SearchResultItem,
    SearchPreviewMetadata,
    SpatialSearchResponse
)
from core.poi.service import POIService

logger = logging.getLogger("vastu.search.hybrid")

# Architectural & Furniture Semantic Taxonomy
SEMANTIC_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "sofa": {
        "categories": ["FURNITURE", "SEATING", "LOUNGE"],
        "synonyms": ["sofa", "sofas", "couch", "couches", "settee", "lounge", "3-seater", "2-seater", "sectional"],
        "attributes": ["3-seater", "2-seater", "leather", "fabric", "cushion"]
    },
    "chair": {
        "categories": ["FURNITURE", "SEATING"],
        "synonyms": ["chair", "chairs", "armchair", "seat", "seats", "stool", "swivel chair", "desk chair"],
        "attributes": ["ergonomic", "mesh", "wooden", "swivel", "office"]
    },
    "table": {
        "categories": ["FURNITURE", "SURFACE"],
        "synonyms": ["table", "tables", "desk", "desks", "workstation", "boardroom table", "counter"],
        "attributes": ["conference", "dining", "standing", "coffee table"]
    },
    "room": {
        "categories": ["ROOM", "SPACE", "ZONE"],
        "synonyms": ["room", "rooms", "conference", "boardroom", "meeting", "office", "hall", "lobby", "huddle"],
        "attributes": ["meeting", "conference", "executive", "huddle", "boardroom"]
    },
    "screen": {
        "categories": ["AV_EQUIPMENT", "ELECTRONICS"],
        "synonyms": ["screen", "screens", "tv", "monitor", "display", "projector", "television"],
        "attributes": ["4k", "oled", "smart", "hdmi", "zoom"]
    },
    "reception": {
        "categories": ["ZONE", "ENTRANCE", "LOBBY"],
        "synonyms": ["reception", "front desk", "lobby", "entrance", "concierge", "welcome desk"],
        "attributes": ["entry", "front", "main"]
    },
    "exit": {
        "categories": ["SAFETY", "EGRESS", "DOOR"],
        "synonyms": ["exit", "exits", "fire exit", "egress", "emergency exit", "door", "stairwell"],
        "attributes": ["emergency", "fire", "north", "south", "east", "west"]
    }
}

class HybridSpatialSearchEngine:
    """
    Multi-stage hybrid spatial search engine for 3D digital twins.
    """
    def __init__(self, poi_service: Optional[POIService] = None):
        self.poi_service = poi_service or POIService()

    def search(self, query: SpatialSearchQuery) -> SpatialSearchResponse:
        """Executes the complete 5-stage search pipeline."""
        start_time = time.perf_counter()
        raw_query = query.query.strip()

        # Step 1: Query Intent Parsing & Preposition Detection
        target_text, anchor_text, room_filter = self._parse_query_intent(raw_query)
        if query.room_filter:
            room_filter = query.room_filter

        # Fetch candidate POIs from service
        all_candidates = self.poi_service.list_pois(model_version=query.model_version)
        if query.project_id:
            all_candidates = [p for p in all_candidates if p.project_id == query.project_id]

        if not all_candidates:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return SpatialSearchResponse(
                query=raw_query,
                parsed_target=target_text,
                parsed_anchor=anchor_text,
                total_results=0,
                results=[],
                model_version=query.model_version,
                execution_time_ms=round(elapsed_ms, 2)
            )

        # Step 2 & 3: Resolve Anchor if spatial relation exists
        anchor_poi = None
        anchor_coords: Optional[List[float]] = None
        if anchor_text:
            anchor_poi = self._resolve_anchor_entity(anchor_text, all_candidates)
            if anchor_poi is not None:
                anchor_coords = [
                    anchor_poi.coordinates.x,
                    anchor_poi.coordinates.y,
                    anchor_poi.coordinates.z
                ]

        # Step 4: Multi-Stage Scoring (Lexical + Semantic + Spatial)
        scored_items: List[SearchResultItem] = []

        for poi in all_candidates:
            # If candidate IS the anchor itself, don't include it as the target unless exact match
            if anchor_poi is not None and poi.id == anchor_poi.id and target_text != anchor_text:
                continue

            # Stage 2: Lexical Matching
            lex_score, is_exact = self._compute_lexical_score(target_text, poi)

            # Stage 3: Semantic Matching
            sem_score, sem_explanation = self._compute_semantic_score(target_text, poi)

            # Stage 4: Spatial Filtering & Proximity
            spatial_score, distance_to_anchor = self._compute_spatial_score(
                poi,
                anchor_coords=anchor_coords,
                user_location=query.user_location,
                max_distance_m=query.max_distance_meters
            )

            # Room filter check
            if room_filter:
                poi_room = (poi.room or "").lower()
                if room_filter.lower() not in poi_room:
                    # Deprecate or filter out
                    spatial_score *= 0.1

            # Determine match type & primary explanation
            match_type = "EXACT" if is_exact else (
                "SPATIAL_PROXIMITY" if (anchor_coords is not None and spatial_score > 0.60 and (lex_score > 0.3 or sem_score > 0.3)) else (
                    "SEMANTIC" if sem_score > lex_score and sem_score > 0.40 else "FUZZY"
                )
            )

            # Stage 5: Multi-Criteria Ranking Combination
            poi_conf = float(poi.confidence)
            if anchor_coords is not None:
                # Spatial relational query ("chairs near reception")
                # Weight spatial proximity heavily
                composite = (
                    0.25 * lex_score +
                    0.35 * sem_score +
                    0.30 * spatial_score +
                    0.10 * poi_conf
                )
                match_expl = (
                    f"Found '{poi.name}' within {distance_to_anchor:.1f}m of '{anchor_poi.name if anchor_poi else anchor_text}' "
                    f"with {sem_explanation or 'semantic similarity'}."
                )
            else:
                # Non-spatial query ("Meeting Room 4", "3-seater sofas")
                composite = (
                    0.45 * lex_score +
                    0.40 * sem_score +
                    0.15 * poi_conf
                )
                match_expl = (
                    f"Exact name match on '{poi.name}'" if is_exact else
                    (f"Semantic match: {sem_explanation}" if sem_score >= lex_score else f"Fuzzy lexical match on '{poi.name}'")
                )

            # Threshold to filter noise
            if composite >= 0.28:
                preview = SearchPreviewMetadata(
                    match_type=match_type,
                    category=poi.category,
                    match_explanation=match_expl,
                    distance_to_anchor_m=distance_to_anchor,
                    anchor_name=anchor_poi.name if anchor_poi else (anchor_text if anchor_coords else None),
                    lexical_score=round(float(lex_score), 3),
                    semantic_score=round(float(sem_score), 3),
                    spatial_score=round(float(spatial_score), 3),
                    composite_rank_score=round(float(composite), 3)
                )

                item = SearchResultItem(
                    poi=poi,
                    confidence=round(float(composite), 3),
                    location=[poi.coordinates.x, poi.coordinates.y, poi.coordinates.z],
                    room=poi.room or "Unassigned Room",
                    preview_metadata=preview
                )
                scored_items.append(item)

        # Sort descending by composite rank score
        scored_items.sort(key=lambda x: x.preview_metadata.composite_rank_score, reverse=True)
        final_results = scored_items[:query.limit]

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return SpatialSearchResponse(
            query=raw_query,
            parsed_target=target_text,
            parsed_anchor=anchor_text,
            total_results=len(final_results),
            results=final_results,
            model_version=query.model_version,
            execution_time_ms=round(elapsed_ms, 2)
        )

    def _parse_query_intent(self, query_str: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Parses user query into target phrase, spatial anchor, and room filter.
        Example:
        - "chairs near reception" -> ("chairs", "reception", None)
        - "desks in Conference Room 1" -> ("desks", None, "Conference Room 1")
        - "Meeting Room 4" -> ("Meeting Room 4", None, None)
        """
        q = query_str.strip()

        # Check for relational prepositions ("near", "close to", "around", "next to", "adjacent to")
        near_pattern = r"^(.*?)\s+(?:near|close to|around|next to|adjacent to)\s+(.+)$"
        match_near = re.match(near_pattern, q, re.IGNORECASE)
        if match_near:
            target = match_near.group(1).strip()
            anchor = match_near.group(2).strip()
            return target, anchor, None

        # Check for containment prepositions ("in", "inside", "within")
        in_pattern = r"^(.*?)\s+(?:in|inside|within)\s+(.+)$"
        match_in = re.match(in_pattern, q, re.IGNORECASE)
        if match_in:
            target = match_in.group(1).strip()
            room = match_in.group(2).strip()
            return target, None, room

        return q, None, None

    def _resolve_anchor_entity(self, anchor_text: str, candidates: List[PointOfInterest]) -> Optional[PointOfInterest]:
        """Finds the most relevant POI to act as a 3D spatial anchor."""
        norm_anchor = anchor_text.lower().strip()
        best_poi = None
        best_score = -1.0

        for poi in candidates:
            # Exact match
            if norm_anchor == poi.name.lower() or norm_anchor in [a.lower() for a in poi.aliases]:
                return poi

            # Substring match
            if norm_anchor in poi.name.lower() or any(norm_anchor in a.lower() for a in poi.aliases):
                score = 0.90
            else:
                score = difflib.SequenceMatcher(None, norm_anchor, poi.name.lower()).ratio()

            if score > best_score and score > 0.45:
                best_score = score
                best_poi = poi

        return best_poi

    def _compute_lexical_score(self, target_text: str, poi: PointOfInterest) -> Tuple[float, bool]:
        """Calculates exact and fuzzy token matching scores."""
        t_clean = target_text.lower().strip()
        name_clean = poi.name.lower().strip()
        aliases_clean = [a.lower().strip() for a in poi.aliases]

        # Exact Match
        if t_clean == name_clean or any(t_clean == a for a in aliases_clean):
            return 1.0, True

        # Normalized Substring match
        if t_clean in name_clean:
            ratio = len(t_clean) / max(1, len(name_clean))
            return max(0.85, 0.70 + 0.30 * ratio), False

        for a in aliases_clean:
            if t_clean in a:
                return 0.85, False

        # Fuzzy string similarity (Levenshtein ratio)
        name_ratio = difflib.SequenceMatcher(None, t_clean, name_clean).ratio()
        alias_ratios = [difflib.SequenceMatcher(None, t_clean, a).ratio() for a in aliases_clean]
        best_ratio = max([name_ratio] + alias_ratios)

        # Word token overlap
        t_tokens = set(re.findall(r"\w+", t_clean))
        poi_tokens = set(re.findall(r"\w+", name_clean))
        for a in aliases_clean:
            poi_tokens.update(re.findall(r"\w+", a))

        jaccard = len(t_tokens & poi_tokens) / max(1, len(t_tokens | poi_tokens))
        fuzzy_score = max(best_ratio, jaccard)

        return float(round(fuzzy_score, 3)), False

    def _compute_semantic_score(self, target_text: str, poi: PointOfInterest) -> Tuple[float, str]:
        """
        Maps natural language concepts into architectural categories and attributes.
        e.g. '3-seater sofas' -> sofa concept, 3-seater attribute.
        """
        t_clean = target_text.lower().strip()
        target_tokens = set(re.findall(r"\w+", t_clean))

        poi_text = f"{poi.name} {poi.category} {poi.room or ''} {' '.join(poi.aliases)} {' '.join(str(v) for v in poi.metadata.values())}".lower()
        poi_tokens = set(re.findall(r"\w+", poi_text))

        best_score = 0.0
        best_explanation = ""

        for concept_name, concept_data in SEMANTIC_TAXONOMY.items():
            synonyms = set(concept_data["synonyms"])
            categories = set(c.lower() for c in concept_data["categories"])
            attributes = set(concept_data.get("attributes", []))

            # Did the user query mention this concept?
            matched_synonyms = target_tokens & synonyms
            if matched_synonyms:
                # User is searching for this concept (e.g. "sofas", "chairs", "meeting rooms")
                concept_weight = 0.50
                poi_matches_concept = False

                # Does the POI belong to this category or have matching synonyms?
                if poi.category.lower() in categories or (poi_tokens & synonyms):
                    poi_matches_concept = True

                if poi_matches_concept:
                    # Check for attribute alignment (e.g. "3-seater", "conference")
                    matched_attrs = target_tokens & attributes & poi_tokens
                    target_attrs = target_tokens & attributes

                    if target_attrs:
                        if matched_attrs:
                            score = 0.95
                            explanation = f"Matched concept '{concept_name}' and attribute '{', '.join(matched_attrs)}'"
                        else:
                            # User wanted "3-seater", but POI doesn't match attribute
                            score = 0.65
                            explanation = f"Matched concept '{concept_name}', generic attributes"
                    else:
                        score = 0.85
                        explanation = f"Matched architectural concept '{concept_name}'"

                    if score > best_score:
                        best_score = score
                        best_explanation = explanation

        # Direct token overlap with category
        cat_match = poi.category.lower() in t_clean
        if cat_match and best_score < 0.80:
            best_score = 0.80
            best_explanation = f"Matched category '{poi.category}'"

        return round(float(best_score), 3), best_explanation

    def _compute_spatial_score(
        self,
        poi: PointOfInterest,
        anchor_coords: Optional[List[float]],
        user_location: Optional[List[float]],
        max_distance_m: float
    ) -> Tuple[float, Optional[float]]:
        """
        Calculates 3D metric spatial proximity to anchor coordinates or user location.
        """
        reference = anchor_coords if anchor_coords is not None else user_location
        if reference is None:
            return 1.0, None

        poi_xyz = np.array([poi.coordinates.x, poi.coordinates.y, poi.coordinates.z], dtype=np.float64)
        ref_xyz = np.array(reference, dtype=np.float64)

        dist = float(np.linalg.norm(poi_xyz - ref_xyz))
        dist_clamped = min(dist, max_distance_m)

        # Decay function: 1.0 at 0m, decaying to 0.0 at max_distance_m
        score = max(0.0, 1.0 - (dist_clamped / max_distance_m))

        # Quadratic proximity boost for very close objects (< 3m)
        if dist <= 3.0:
            score = max(score, 0.90)

        return round(float(score), 3), round(dist, 2)
