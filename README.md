# PrintQuote: 3D print price calculator

Drop in sliced G-code and get a price per print from your real costs: filament, electricity, machine wear, labor, failed-print allowance, markup and marketplace fees. Batch many files, set quantities, export CSV or a printable quote.

Reads filament weight and print time from OrcaSlicer, PrusaSlicer, Bambu Studio and Cura G-code comments.

## Run from source (free)

Python 3.8+ with tkinter, no other dependencies:

    python printquote.py

## Windows exe

Prefer a double-click program? Get the ready-built Windows exe for $9: https://spectre5.gumroad.com/l/PLACEHOLDER

## How the price is built

cost = (filament + power + wear + labor) x (1 + failure allowance)
price = cost x (1 + markup), then grossed up for the marketplace fee so the fee does not eat your margin.

More tools: https://patreon.com/123black
