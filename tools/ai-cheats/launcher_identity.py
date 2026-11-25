#!/usr/bin/env python3
"""Add a session identity to the actual RetroArch launcher without replacing its other patches."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/"usr/libexec/banana/run-retroarch"
s=p.read_text()
anchor='    rm -f /run/banana/retroarch.log\n'
addition='''    # Only the actual RetroArch process (not BananaFront) publishes a cheat identity.
    case "$BANANA_SYSTEM" in
    gba|gb|gbc)
        if [ -n "$BANANA_RA_OUT" ] && [ -p "$BANANA_RA_OUT" ]; then
            rh=$(sha256sum "$2" | cut -d' ' -f1)
            ch=$(sha256sum "$CORE" | cut -d' ' -f1)
            if [ "${#rh}" = 64 ] && [ "${#ch}" = 64 ]; then
                (umask 077; printf '%s %s\\n' "$rh" "$ch" > /run/banana/azeez-cheat-session.tmp) &&
                    mv /run/banana/azeez-cheat-session.tmp /run/banana/azeez-cheat-session
            fi
        fi ;;
    esac
'''
if s.count(anchor)!=1:raise SystemExit("RetroArch launcher identity anchor mismatch")
p.write_text(s.replace(anchor,anchor+addition))
