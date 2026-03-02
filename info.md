Adds support for **Monoprice Blackbird 8x8** matrices over RS-232:

- **PN 44568** – 18G 8x8 HDBaseT 150M: set `model: 44568`, default baud **115200**.
- **PN 39670** – 4K 8x8 HDBaseT: set `model: 39670`, default baud 9600.
- **Legacy** – Omit `model` or use `model: legacy` for pyblackbird (4x4-style, serial or host).
