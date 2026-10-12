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


class Tests_PcbMetadata(unittest.TestCase):
    def test_footprint_units_and_jumpers_round_trip(self):
        from kiutils.footprint import Footprint
        tokens = parse_sexp('(metadata (units (unit (name "A") (pins "1" "2")) (unit (name "B") (pins "3" "4"))) (duplicate_pad_numbers_are_jumpers no) (jumper_pad_groups ("1" "2") ("3" "4")))')[1:]
        footprint = Footprint.from_sexpr(["footprint", "test"] + tokens)
        self.assertEqual(footprint.units[1].pins, ["3", "4"])
        self.assertFalse(footprint.duplicate_pad_numbers_are_jumpers)
        output = parse_sexp(footprint.to_sexpr())
        keys = {x[0] for x in tokens}
        self.assertEqual([x for x in output[2:] if isinstance(x, list) and x[0] in keys], tokens)
        self.assertEqual(Footprint.from_sexpr(output).jumper_pad_groups, [["1", "2"], ["3", "4"]])

    def test_zone_defaults_round_trip(self):
        from kiutils.items.brditems import SetupData
        for token in ('(zone_defaults)', '(zone_defaults (property (layer "F.Cu") (hatch_position (xy 1.25 2.5))))'):
            with self.subTest(token=token):
                source = parse_sexp(token)
                setup = SetupData.from_sexpr(["setup", source])
                output = parse_sexp(setup.to_sexpr())
                self.assertIn(source, output)
                self.assertEqual(SetupData.from_sexpr(output).zone_defaults, setup.zone_defaults)
        self.assertIsNone(SetupData().zone_defaults)
        self.assertNotIn("zone_defaults", SetupData().to_sexpr())

    def test_legacy_footprint_omits_new_metadata(self):
        from kiutils.footprint import Footprint
        footprint = Footprint()
        footprint.libId = "test"
        text = footprint.to_sexpr()
        self.assertNotIn("units", text)
        self.assertNotIn("duplicate_pad_numbers_are_jumpers", text)
        self.assertNotIn("jumper_pad_groups", text)


class Tests_PowerScope(unittest.TestCase):
    def test_scoped_and_legacy_power_symbols(self):
        from kiutils.symbol import Symbol
        for token, scope in (("(power)", None), ("(power global)", "global"), ("(power local)", "local")):
            with self.subTest(token=token):
                symbol = Symbol.from_sexpr(parse_sexp('(symbol "PWR" ' + token + ')'))
                self.assertTrue(symbol.isPower)
                self.assertEqual(symbol.power_type, scope)
                self.assertIn(parse_sexp(token), parse_sexp(symbol.to_sexpr()))
                restored = Symbol.from_sexpr(parse_sexp(symbol.to_sexpr()))
                self.assertTrue(restored.isPower)
                self.assertEqual(restored.power_type, scope)
                symbol.isPower = False
                self.assertNotIn("power", symbol.to_sexpr())


class Tests_SymbolMetadata(unittest.TestCase):
    def test_body_styles_and_pin_jumpers_do_not_drop_library_symbols(self):
        from kiutils.symbol import SymbolLib
        for styles in ('(body_styles demorgan)', '(body_styles "Standard" "Alternate view")'):
            with self.subTest(styles=styles):
                tokens = parse_sexp('(metadata ' + styles + ' (jumper_pin_groups ("1" "2") ("3" "4")))')[1:]
                source = ["kicad_symbol_lib", ["version", 20260101], ["generator", "eeschema"], ["symbol", "test"] + tokens]
                lib = SymbolLib.from_sexpr(source)
                self.assertEqual(len(lib.symbols), 1)
                output = parse_sexp(lib.symbols[0].to_sexpr())
                self.assertEqual([x for x in output[2:] if isinstance(x, list) and x[0] in ("body_styles", "jumper_pin_groups")], tokens)
                restored = SymbolLib.from_sexpr(parse_sexp(lib.to_sexpr()))
                self.assertEqual(len(restored.symbols), 1)
                self.assertEqual(restored.symbols[0].body_styles, lib.symbols[0].body_styles)
