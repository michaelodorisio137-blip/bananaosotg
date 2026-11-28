#!/usr/bin/env python3
"""Explicit RG DS single-screen touchscreen bring-up. Keep desktop path unchanged."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/"native/src/app/linux/game_main_linux.cpp"
s=p.read_text()
anchor='    SDL_SetAppMetadata("Open City Builder", nullptr, kAppId);'
if s.count(anchor)!=1: raise SystemExit("Upstream host anchor changed")
s=s.replace(anchor,'''    const bool rgds = std::getenv("AZEEZ_SC4_RGDS") != nullptr;
    if (rgds) {
        SDL_SetHint(SDL_HINT_TOUCH_MOUSE_EVENTS, "1");
        SDL_SetHint(SDL_HINT_MOUSE_TOUCH_EVENTS, "0");
        windowW = 640; windowH = 480; uiScale = 1; fullscreen = true;
    }
'''+anchor)
p.write_text(s)
