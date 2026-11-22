#!/usr/bin/env python3
"""Original RG DS: replace the banana intro with the DUNGEON O dual-panel boot.

Pure C++ pixel renderer: no PNG codec or additional runtime dependencies.
Only the original RG DS 640x480 panel size takes the new path.
On the Plus, the upstream splash stays unchanged.
"""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-boot-patch.py /path/to/BananaLinux")
root = Path(sys.argv[1])
p = root / "ui/src/splash.cpp"
s = p.read_text()
anchor = "\tvoid Splash::draw(uint32_t* top, uint32_t* bot, double t, bool ready)\n\t{\n"
mark = "// RG DS DUNGEON O custom dual-panel startup"
if mark in s:
    sys.exit(0)
if s.count(anchor) != 1:
    sys.exit("Unexpected upstream Splash::draw signature")
intro = r'''        // RG DS DUNGEON O custom dual-panel startup.
        // White DS-style intro; final O is the dual-square DS mark.
        // Dedicated original RG DS screen (640x480). Preserve Plus splash.
        if (W <= 640)
        {
            const uint32_t white = 0xfffafafau, ink = 0xff242424u, grey = 0xff878787u;
            std::fill(top, top + (size_t)W * H, white);
            std::fill(bot, bot + (size_t)W * H, white);
            auto rectangle = [&](uint32_t* d, int x, int y, int w, int h, int thick, uint32_t colour)
            {
                fill(d, x, y, w, thick, colour);
                fill(d, x, y + h - thick, w, thick, colour);
                fill(d, x, y, thick, h, colour);
                fill(d, x + w - thick, y, thick, h, colour);
            };
            auto glyph = [&](uint32_t* d, char c, int x, int y, int k, uint32_t colour)
            {
                // Single-stroke 5x7 uppercase block font for the fixed wordmark.
                static const uint8_t D[] = {30,17,17,17,17,17,30};
                static const uint8_t U[] = {17,17,17,17,17,17,14};
                static const uint8_t N[] = {17,25,21,19,17,17,17};
                static const uint8_t G[] = {15,16,16,23,17,17,15};
                static const uint8_t E[] = {31,16,16,30,16,16,31};
                static const uint8_t O[] = {14,17,17,17,17,17,14};
                const uint8_t* rows = c == 'D' ? D : c == 'U' ? U : c == 'N' ? N :
                                      c == 'G' ? G : c == 'E' ? E : O;
                for (int yy = 0; yy < 7; ++yy)
                    for (int xx = 0; xx < 5; ++xx)
                        if (rows[yy] & (1u << (4 - xx)))
                            fill(d, x + xx * k, y + yy * k, k, k, colour);
            };
            // The two square screens move together, echoing the original DS cue.
            const double move = std::max(0.0, std::min(1.0, (t - 130.0) / 520.0));
            const double ease = move * move * (3.0 - 2.0 * move);
            const int size = X(36), y = H / 2 - X(118);
            const int halfgap = X(27 + 120 * (1.0 - ease));
            const int left = W / 2 - halfgap - size;
            const int right = W / 2 + halfgap;
            if (t >= 120)
            {
                rectangle(top, left, y, size, size, std::max(2, X(4)), ink);
                rectangle(top, right, y, size, size, std::max(2, X(4)), ink);
            }
            if (t >= 710)
            {
                // DUNGEON in letterforms; final O as the DS twin-screen device.
                const char* title = "DUNGEON";
                const int k = std::max(2, X(4));
                const int step = 6 * k;
                const int x0 = (W - (7 * step + X(44))) / 2;
                const int wordY = H / 2 - X(22);
                const int letters = std::min(7, 1 + (int)((t - 710.0) / 55.0));
                for (int i = 0; i < letters; ++i)
                    glyph(top, title[i], x0 + i * step, wordY, k, ink);
                if (t >= 710 + 7 * 55)
                {
                    int markX = x0 + 7 * step + X(5), my = wordY + X(1);
                    // Dual, joined outline squares instead of a normal letter O.
                    int sq = X(19);
                    rectangle(top, markX, my, sq, sq, std::max(2, X(3)), ink);
                    rectangle(top, markX + X(15), my + X(11), sq, sq, std::max(2, X(3)), ink);
                }
            }
            if (t >= 520 && !cued)
            {
                cued = true;
                if (onCue) onCue("insert"); // normal boot cue remains compatible
            }
            (void)ready;
            return;
        }
'''
s=s.replace(anchor,anchor+intro,1)
p.write_text(s)
print("Added native DUNGEON O two-screen boot for original RG DS.")
