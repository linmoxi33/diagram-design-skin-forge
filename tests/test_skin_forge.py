#!/usr/bin/env python3
"""Tests for diagram-design-skin-forge.  Run: python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "skin-forge"
sf = SourceFileLoader("skin_forge", str(BIN)).load_module()


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BIN), *args],
                          capture_output=True, text=True, check=False)


class ContrastMath(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(
            sf.contrast(sf.parse_hex("#000000"), sf.parse_hex("#ffffff")), 21.0)

    def test_contrast_is_symmetric(self):
        a, b = sf.parse_hex("#2d3142"), sf.parse_hex("#f5f5f5")
        self.assertAlmostEqual(sf.contrast(a, b), sf.contrast(b, a))

    def test_three_digit_hex(self):
        self.assertEqual(sf.parse_hex("#abc"), (0xaa, 0xbb, 0xcc))

    def test_invalid_hex_raises(self):
        with self.assertRaises(sf.InputError):
            sf.parse_hex("#12345")

    def test_documented_ratios_reproduce(self):
        # The six ratios printed in style-guide.md "Contrast contract" and the
        # default accent row must come out of this engine unchanged.
        cases = [("#bf4520", "#f5f5f5", 4.71), ("#5a6580", "#f5f5f5", 5.34),
                 ("#2e5aa8", "#f5f5f5", 6.13), ("#4f5d75", "#f5f5f5", 6.11),
                 ("#f08a59", "#2d3142", 5.21), ("#949eb2", "#2d3142", 4.78),
                 ("#739fdf", "#2d3142", 4.76)]
        for fg, bg, expected in cases:
            got = round(sf.contrast(sf.parse_hex(fg), sf.parse_hex(bg)), 2)
            self.assertAlmostEqual(got, expected, places=2, msg=f"{fg} on {bg}")


class Compile(unittest.TestCase):
    def brand(self, name="editorial"):
        return json.loads((ROOT / "examples" / "in" / f"brand-{name}.json").read_text())

    def test_light_text_roles_clear_contract(self):
        skins = sf.compile_skin(self.brand())
        report = sf.check_skin(skins)
        for role, row in report["light"].items():
            self.assertTrue(row["pass"], f"light.{role} {row['ratio']}")

    def test_dark_text_roles_clear_contract(self):
        skins = sf.compile_skin(self.brand())
        report = sf.check_skin(skins)
        for role, row in report["dark"].items():
            self.assertTrue(row["pass"], f"dark.{role} {row['ratio']}")

    def test_accent_keeps_brand_hue(self):
        import colorsys
        skins = sf.compile_skin(self.brand())
        raw = sf.parse_hex(self.brand()["accent"])
        got = sf.parse_hex(skins["light"]["accent"])
        h1 = colorsys.rgb_to_hls(*(c / 255 for c in raw))[0]
        h2 = colorsys.rgb_to_hls(*(c / 255 for c in got))[0]
        self.assertLess(min(abs(h1 - h2), 1 - abs(h1 - h2)), 0.01)

    def test_compile_is_deterministic(self):
        a = json.dumps(sf.compile_skin(self.brand()), sort_keys=True)
        b = json.dumps(sf.compile_skin(self.brand()), sort_keys=True)
        self.assertEqual(a, b)

    def test_missing_brand_key_is_input_error(self):
        brand = self.brand()
        del brand["accent"]
        with self.assertRaises(sf.InputError):
            sf.compile_skin(brand)

    def test_check_catches_low_contrast(self):
        skin = json.loads((ROOT / "examples" / "in" / "skin-broken.json").read_text())
        report = sf.check_skin(skin)
        self.assertTrue(any(not r["pass"] for r in report["light"].values()))

    def test_check_rejects_missing_role(self):
        skin = {"light": {"paper": "#ffffff"}, "dark": {"paper": "#000000"}}
        with self.assertRaises(sf.InputError):
            sf.check_skin(skin)


class CLI(unittest.TestCase):
    def test_compile_json_is_parseable(self):
        proc = run("compile", str(ROOT / "examples/in/brand-editorial.json"), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["summary"]["violations"], 0)
        self.assertEqual(set(data["skins"]), {"light", "dark"})

    def test_compile_writes_out_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "skin.json"
            proc = run("compile", str(ROOT / "examples/in/brand-harbor.json"),
                       "--json", "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out.exists())
            json.loads(out.read_text())

    def test_missing_file_exits_2(self):
        proc = run("compile", "/nonexistent/brand.json")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cannot read", proc.stderr)

    def test_bad_json_exits_2(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{not json")
            path = fh.name
        proc = run("compile", path)
        self.assertEqual(proc.returncode, 2)

    def test_check_broken_skin_exits_1(self):
        proc = run("check", str(ROOT / "examples/in/skin-broken.json"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL", proc.stdout)

    def test_check_good_skin_exits_0(self):
        proc = run("check", str(ROOT / "examples/out/skin-editorial.json"), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["summary"]["violations"], 0)


if __name__ == "__main__":
    unittest.main()
