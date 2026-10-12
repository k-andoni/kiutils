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


class Tests_NamedNets(unittest.TestCase):
    def test_pad_net_formats(self):
        from kiutils.items.common import Net
        from kiutils.footprint import Pad
        for token in ('(net 1 "GND")', '(net "GND")', '(net "1")', '(net "")', '(net "a \"b\"")'):
            with self.subTest(token=token):
                source = parse_sexp(token)
                net = Net.from_sexpr(source)
                self.assertEqual(parse_sexp(net.to_sexpr()), source)
                pad = Pad.from_sexpr(parse_sexp('(pad "1" smd rect (layers "F.Cu") ' + token + ')'))
                restored = Pad.from_sexpr(parse_sexp(pad.to_sexpr()))
                self.assertEqual(restored.net, net)
        self.assertIsNone(Net.from_sexpr(["net", "GND"]).number)
        self.assertEqual(Net.from_sexpr(["net", 1, "GND"]).number, 1)

    def test_track_net_formats(self):
        from kiutils.items.brditems import Segment, Via, Arc
        for cls in (Segment, Via, Arc):
            for value in (1, "GND", "1", "", 'a "b"'):
                with self.subTest(cls=cls.__name__, value=value):
                    obj = cls(net=value)
                    if cls is Via:
                        obj.layers = ["F.Cu", "B.Cu"]
                    restored = cls.from_sexpr(parse_sexp(obj.to_sexpr()))
                    self.assertEqual(restored.net, value)

    def test_zone_net_formats(self):
        from kiutils.items.zones import Zone
        for token in ('(net 1) (net_name "GND")', '(net "GND")', ''):
            with self.subTest(token=token):
                zone = Zone.from_sexpr(parse_sexp('(zone (layer "F.Cu") ' + token + ')'))
                output = parse_sexp(zone.to_sexpr())
                self.assertEqual([x for x in output[1:] if isinstance(x, list) and x[0] in ("net", "net_name")], parse_sexp('(nets ' + token + ')')[1:])
                restored = Zone.from_sexpr(output)
                self.assertEqual(restored.net, zone.net)
                self.assertEqual(restored.netName, zone.netName)

    def test_graphic_net_formats(self):
        from kiutils.items.gritems import GrText, GrLine, GrRect, GrCircle, GrArc, GrPoly, GrCurve
        for cls in (GrText, GrLine, GrRect, GrCircle, GrArc, GrPoly, GrCurve):
            for value in (1, "GND", "1", 'a "b"'):
                with self.subTest(cls=cls.__name__, value=value):
                    obj = cls(net=value)
                    if cls in (GrPoly, GrCurve):
                        from kiutils.items.common import Position
                        obj.coordinates = [Position(X=i, Y=i) for i in range(4)]
                    restored = cls.from_sexpr(parse_sexp(obj.to_sexpr()))
                    self.assertEqual(restored.net, value)
