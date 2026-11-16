"""The print palette (EXA-135): every colour a server-drawn figure may use.

Real school papers are photocopied, so figures are black line art on white with at most a light
grey tint; nothing is told apart by hue. Every value here is a neutral grey (r == g == b), and
``tests/test_monochrome_print.py`` holds every rendered paper, key and figure to that. The print
stylesheet (``assets/print.css``) mirrors these values as CSS custom properties.
"""

INK = "#1a1a1a"  # text, outlines, axes, ticks
ANSWER = "#000000"  # what the answer key adds to a figure (drawn with a heavier stroke)
PAPER = "#ffffff"  # unshaded areas (bar-model bars, empty fraction parts, pie sectors)
GRID = "#bdbdbd"  # grid backdrops and chart gridlines
SHADE = "#d0d0d0"  # a shaded part (fraction shading, shaded geometry regions)
TINT = "#f0f0f0"  # lightest face tint (top faces, water surface)
TINT_MID = "#dcdcdc"  # mid face tint (cube left faces, water body)
TINT_DARK = "#b4b4b4"  # darkest face tint (cube right faces)

# Bar-chart series fills: tones far enough apart to survive a photocopier, starting with the
# light grey a single-series chart uses. A legend names each one.
SERIES = ("#d0d0d0", "#ffffff", "#6e6e6e", "#1a1a1a", "#e6e6e6", "#999999")
