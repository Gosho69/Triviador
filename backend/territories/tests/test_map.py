from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from territories.checks import check_project_map
from territories.map import (
    ADJACENCIES,
    MAP_SIZE_MAX,
    MAP_SIZE_MIN,
    MAP_SIZE_STEP,
    MIN_NEIGHBORS,
    TERRITORIES,
    build_neighbor_map,
    has_capital_triple,
    validate_map,
)


def ring(size):
    """A valid-size cycle: connected, two neighbours each, has independent triples."""
    territories = [(f"t{i}", f"Територия {i}") for i in range(size)]
    adjacencies = [(f"t{i}", f"t{(i + 1) % size}") for i in range(size)]
    return territories, adjacencies


class ProjectMapTests(SimpleTestCase):
    def test_project_map_is_valid(self):
        validate_map(TERRITORIES, ADJACENCIES)
        self.assertEqual(check_project_map(None), [])

    def test_system_check_reports_broken_map(self):
        with mock.patch("territories.checks.ADJACENCIES", ADJACENCIES[:-1] + (("skali", "skali"),)):
            errors = check_project_map(None)

        self.assertTrue(errors)
        self.assertEqual({error.id for error in errors}, {"territories.E001"})

    def test_project_map_size_is_allowed(self):
        size = len(TERRITORIES)
        self.assertEqual(size, 18)
        self.assertTrue(MAP_SIZE_MIN <= size <= MAP_SIZE_MAX)
        self.assertEqual(size % MAP_SIZE_STEP, 0)

    def test_project_map_graph_rules(self):
        slugs = [slug for slug, _ in TERRITORIES]
        neighbor_map = build_neighbor_map(slugs, ADJACENCIES)

        self.assertEqual(len({frozenset(pair) for pair in ADJACENCIES}), len(ADJACENCIES))
        for slug, neighbors in neighbor_map.items():
            with self.subTest(slug):
                self.assertNotIn(slug, neighbors)
                self.assertGreaterEqual(len(neighbors), MIN_NEIGHBORS)
                for neighbor in neighbors:
                    self.assertIn(slug, neighbor_map[neighbor])
        self.assertTrue(has_capital_triple(neighbor_map))

    def test_project_map_neighbours_match_definition(self):
        neighbor_map = build_neighbor_map([slug for slug, _ in TERRITORIES], ADJACENCIES)

        self.assertEqual(neighbor_map["skali"], {"dunaviya", "sredets"})
        self.assertEqual(neighbor_map["balkania"], {"sredets", "rozova-dolina", "dunaviya", "ezera", "kukeri"})
        self.assertEqual(neighbor_map["tsarevo"], {"karakachan", "slanchevo"})


class MapValidationTests(SimpleTestCase):
    def assert_invalid(self, territories, adjacencies, code):
        with self.assertRaises(ValidationError) as context:
            validate_map(territories, adjacencies)
        self.assertIn(code, [error.code for error in context.exception.error_list])

    def test_allowed_sizes_are_accepted(self):
        for size in (9, 12, 15, 18, 21):
            with self.subTest(size):
                validate_map(*ring(size))

    def test_invalid_sizes_are_rejected(self):
        for size in (6, 10, 20, 24):
            with self.subTest(size):
                self.assert_invalid(*ring(size), "invalid_size")

    def test_duplicate_slug_and_name_are_rejected(self):
        territories, adjacencies = ring(9)

        self.assert_invalid([*territories[:-1], ("t0", "Друга")], adjacencies, "duplicate_slug")
        self.assert_invalid([*territories[:-1], ("t8", territories[0][1])], adjacencies, "duplicate_name")

    def test_invalid_borders_are_rejected(self):
        territories, adjacencies = ring(9)
        cases = {
            "self_adjacency": [*adjacencies, ("t0", "t0")],
            "duplicate_adjacency": [*adjacencies, ("t0", "t1")],
            "unknown_territory": [*adjacencies, ("t0", "missing")],
        }
        for code, invalid in cases.items():
            with self.subTest(code):
                self.assert_invalid(territories, invalid, code)

    def test_reversed_border_counts_as_duplicate(self):
        territories, adjacencies = ring(9)

        self.assert_invalid(territories, [*adjacencies, ("t1", "t0")], "duplicate_adjacency")

    def test_territory_with_one_neighbour_is_rejected(self):
        territories, adjacencies = ring(9)
        path = [pair for pair in adjacencies if pair != ("t8", "t0")]

        self.assert_invalid(territories, path, "too_few_neighbors")

    def test_disconnected_map_is_rejected(self):
        territories = [(f"t{i}", f"Територия {i}") for i in range(9)]
        two_rings = [
            ("t0", "t1"), ("t1", "t2"), ("t2", "t3"), ("t3", "t0"),
            ("t4", "t5"), ("t5", "t6"), ("t6", "t7"), ("t7", "t8"), ("t8", "t4"),
        ]

        self.assert_invalid(territories, two_rings, "disconnected")

    def test_map_without_capital_triple_is_rejected(self):
        # Two cliques joined by one border: any three territories include two from the same clique.
        territories = [(f"t{i}", f"Територия {i}") for i in range(9)]
        cliques = [range(0, 5), range(5, 9)]
        adjacencies = [
            (f"t{a}", f"t{b}") for clique in cliques for a in clique for b in clique if a < b
        ] + [("t0", "t5")]

        self.assertFalse(has_capital_triple(build_neighbor_map([s for s, _ in territories], adjacencies)))
        self.assert_invalid(territories, adjacencies, "no_capital_triple")
