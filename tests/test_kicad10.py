"""KiCad 10 format regressions, with legacy-format coverage."""

import unittest

from kiutils.items.schitems import PolyLine, RuleArea
from kiutils.schematic import Schematic
from kiutils.utils.sexpr import parse_sexp


class Tests_RuleArea(unittest.TestCase):
    OUTLINE = '(polyline (pts (xy 1 2) (xy 3 4)) (stroke (width 0) (type default)) (uuid "outline"))'

    def test_component_flags_round_trip(self):
        source = parse_sexp('(rule_area (exclude_from_sim yes) (in_bom no) (on_board no) (dnp yes) ' + self.OUTLINE + ')')
        area = RuleArea.from_sexpr(source)
        self.assertIsInstance(area, PolyLine)
        self.assertTrue(area.exclude_from_sim)
        self.assertFalse(area.in_bom)
        self.assertEqual(area.uuid, "outline")
        self.assertEqual(parse_sexp(area.to_sexpr()), source)
        area.in_bom = True
        self.assertTrue(RuleArea.from_sexpr(parse_sexp(area.to_sexpr())).in_bom)

    def test_legacy_rule_area_round_trip(self):
        source = parse_sexp('(rule_area ' + self.OUTLINE + ')')
        self.assertEqual(parse_sexp(RuleArea.from_sexpr(source).to_sexpr()), source)
        schematic = Schematic()
        schematic.rule_areas.append(PolyLine.from_sexpr(parse_sexp(self.OUTLINE)))
        restored = Schematic.from_sexpr(parse_sexp(schematic.to_sexpr()))
        self.assertEqual(restored.rule_areas[0].uuid, "outline")

    def test_schematic_retains_rule_area_flags(self):
        source = parse_sexp('(kicad_sch (version 20260101) (generator "eeschema") (rule_area (in_bom no) ' + self.OUTLINE + '))')
        schematic = Schematic.from_sexpr(source)
        restored = Schematic.from_sexpr(parse_sexp(schematic.to_sexpr()))
        self.assertFalse(restored.rule_areas[0].in_bom)
        self.assertEqual(len(restored.rule_areas[0].points), 2)

    def test_missing_outline_is_rejected(self):
        with self.assertRaises(ValueError):
            RuleArea.from_sexpr(["rule_area", ["in_bom", "yes"]])
