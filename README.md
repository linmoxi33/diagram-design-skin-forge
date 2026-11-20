# diagram-design-skin-forge

Compile a five-color brand palette into a complete light+dark diagram-design skin, with every text role proven to clear 4.5:1 before you paste it into `style-guide.md`. It exists because upstream ships exactly one skin, so a custom brand currently means hand-editing hex values and manually re-checking contrast.

Upstream: https://github.com/cathrynlavery/diagram-design

## What upstream is and what it lacks

[diagram-design](https://github.com/cathrynlavery/diagram-design) is a 69k-star agent skill that renders editorial diagrams as self-contained HTML/SVG. Its `skills/diagram-design/references/style-guide.md` defines a semantic token system (`paper`, `ink`, `muted`, `soft`, `accent`, `link`, …) for a light and a dark skin, and states the derivation rules in prose: the raw brand accent is darkened until it clears 4.5:1, translucent rules are `rgba(ink, 0.12)`, and dark mode flips the surfaces.

Two gaps are verifiable, not assumed:

- Open issue [#497](https://github.com/cathrynlavery/diagram-design/issues/497) ("more built-in visual skins (presets), not just `default`", 0 comments, no linked PR) reports that hard-coded hex is still spread over the reference set — 182 occurrences across 15 files — and that every user reinvents the same palettes by hand.
- The repository ships `scripts/verify-contrast.py` (checks the *declared* tokens) and `scripts/lint-skin.py` (checks examples against the *current* skin), but no code turns a new brand input into a token set. `references/onboarding.md` extracts colors from a URL/folder and then hands mapping + contrast to the agent, with the explicit note "Automated checks do not replace this review."

So: upstream can check a skin, and can describe how to derive one, but cannot produce one deterministically.

## What this tool does

`skin-forge compile brand.json` applies the documented derivation rules as code and returns ten semantic roles for light and dark:

| Role | Light derivation | Dark derivation |
|---|---|---|
| `paper` / `paper-2` | brand paper / 4% toward ink | brand ink / 6% toward paper |
| `ink` | brand ink, darkened only if needed | brand paper, lightened only if needed |
| `muted` / `soft` | brand slate / 18% toward paper | brand silver / 22% toward paper |
| `rule` / `rule-solid` | `rgba(ink,0.12)` / brand silver | `rgba(ink,0.12)` / `rgba(silver,0.25)` |
| `accent` | darkened in HSL, hue+sat fixed, until ≥4.5:1 | lightened the same way |
| `accent-tint` | `rgba(accent,0.08)` | `rgba(accent,0.10)` |
| `link` | slate hue +12°, saturation ×1.25, until ≥4.5:1 | same hue shift, lightened |

`skin-forge check skin.json` validates any existing skin (including one produced by the upstream onboarding flow) and names each failing role with its measured ratio.

It does **not** rewrite `style-guide.md`, generate HTML/SVG diagrams, or replace the upstream linters. It is the missing generator step before them.

## Install and run

Requires Python 3.10+ and nothing else (standard library only).

```bash
git clone git@github-linmoxi33:linmoxi33/diagram-design-skin-forge.git
cd diagram-design-skin-forge
python3 bin/skin-forge compile examples/in/brand-editorial.json
```

```text
skin: editorial
  light:
    paper        #f5f5f5
    ...
    contract: worst text role 4.50:1 (min 4.5:1)
```

Machine output and a ready-to-commit file:

```bash
python3 bin/skin-forge compile examples/in/brand-harbor.json --json --out skin.json
python3 bin/skin-forge check skin.json --json
```

`--json` is parsed directly by `json.load`; the compile result carries `skins.light`, `skins.dark`, per-role `checks`, and a `summary.violations` count.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every text role clears 4.5:1 (compile) / checked skin is valid |
| 1 | at least one role fails the contract (compile) / invalid skin (check) |
| 2 | usage or input error: unreadable file, bad JSON, missing role, non-hex color |

## What this proves

`tests/test_skin_forge.py` (18 tests, all green) includes an oracle cross-check: the WCAG engine recomputes the seven ratios that the upstream style guide publishes for its shipped tokens — light `accent` 4.71:1, `soft` 5.34:1, `link` 6.13:1, `muted` 6.11:1; dark `accent` 5.21:1, `soft` 4.78:1, `link` 4.76:1 — and every one matches to two decimals (delta 0.00). The compiler's own output is then held to the same 4.5:1 bar; the raw `#ff5a36` accent measures 2.85:1 on `#f5f5f5`, and the compiled value clears 4.50:1 with its hue preserved.

## 本轮创新

First deterministic brand→skin compiler for diagram-design: it turns the style guide's prose derivation and 4.5:1 contract into an executable generator, so adding a preset no longer means re-inventing 20 tokens by hand. Verified against the upstream's own seven published ratios (exact) rather than self-invented thresholds.

## 与同类项目的差异

A GitHub search for design-token drift tools found one 0-star repo, `edilec/design-token-drift-auditor`, which finds hard-coded values that bypass declared tokens. That is a *detector* over an existing token file. This tool is a *generator*: it takes raw brand colors and emits a complete, contract-checked light+dark skin, including the dark-mode inversion and translucent rules. Upstream's own `lint-skin.py`/`verify-contrast.py` check existing files; neither derives a new skin.

## Limits

- The derivation is opinionated: it keeps brand hue and saturation and moves lightness only. A brand whose accent cannot reach 4.5:1 at any lightness will still fail, and the tool reports it rather than inventing a different hue.
- It covers the ten color roles named above, not typography, series palette, or the terminal skin.
- It does not read or write `style-guide.md`; copying the emitted table into that file remains a manual step.
