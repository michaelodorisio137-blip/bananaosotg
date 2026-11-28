#!/usr/bin/env python3
"""Install RG DS chime -> vocal sample -> looping menu music support."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-audio-patch.py /path/to/BananaLinux")
root = Path(sys.argv[1])
snd = root / "ui/src/sound.cpp"
main = root / "ui/src/main.cpp"
if not (snd.is_file() and main.is_file()):
    sys.exit("Missing banana-ui audio source")

def sub(path, old, new):
    text = path.read_text()
    if new in text:
        return
    if old not in text:
        sys.exit("RG DS audio source mismatch in " + str(path) + ": " + old[:90])
    path.write_text(text.replace(old, new, 1))

# A shared stereo 48-kHz stream is required to mix effects and looping music.
anchor = '\tSound::Sound(const std::string& dir)\n'
stereo = r'''#ifdef BANANA_ALSA
    static void toStereo(std::vector<int16_t>& pcm, int& channels)
    {
        if (channels == 2) return;
        const size_t frames = pcm.size() / (size_t)channels;
        std::vector<int16_t> stereo(frames * 2);
        for (size_t i = 0; i < frames; i++)
        {
            stereo[i * 2] = pcm[i * channels];
            stereo[i * 2 + 1] = channels == 1 ? pcm[i] : pcm[i * channels + 1];
        }
        pcm.swap(stereo);
        channels = 2;
    }
#endif

'''
sub(snd, anchor, stereo + anchor)
sub(snd,
    '\t\t\t\tto48k(c.pcm, c.rate, c.channels);\n',
    '\t\t\t\tto48k(c.pcm, c.rate, c.channels);\n\t\t\t\ttoStereo(c.pcm, c.channels);\n')
anchor = '\t\tth = std::thread([this] { run(); });'
load = r'''        // The three media files are user supplied; do not package copyrighted
        // recordings in the firmware. Missing clips are simply skipped.
        for (auto spec : { std::pair<const char*, const char*>("ds-chime", "/data/banana/music/ds-chime.wav"),
                           {"oh-oh", "/data/banana/music/oh-oh.wav"},
                           {"menu-loop", "/data/banana/music/menu-loop.wav"} })
        {
            Clip clip;
            if (!loadWav(spec.second, clip.pcm, clip.rate, clip.channels)) continue;
#ifdef BANANA_ALSA
            to48k(clip.pcm, clip.rate, clip.channels);
            toStereo(clip.pcm, clip.channels);
#endif
            if (clip.channels == 2 && clip.rate == 48000 && clip.pcm.size() >= 960)
                clips[spec.first] = std::move(clip);
        }
        if (clips.count("ds-chime") || clips.count("oh-oh") || clips.count("menu-loop"))
        {
            Clip cue;
            cue.rate = 48000; cue.channels = 2;
            cue.pcm.assign(960, 0); // silent cue opens the same audio stream
            clips["rgds-startup"] = std::move(cue);
        }
'''
sub(snd, anchor, load + anchor)

anchor = '\t\tauto lastSound = std::chrono::steady_clock::now();'
musicstate = r'''
        // Independent, low-overhead music layer. Segments crossfade by 100 ms.
        // They play through the same PCM stream as menu effects.
        int musicStage = -1;  // 0: chime, 1: oh-oh, 2: menu loop
        size_t musicPos = 0;
        auto musicClip = [&](int stage) -> const Clip*
        {
            const char* name = stage == 0 ? "ds-chime" : stage == 1 ? "oh-oh" : "menu-loop";
            auto i = clips.find(name);
            return i == clips.end() ? nullptr : &i->second;
        };
        auto musicNext = [&](int stage) -> int
        {
            for (int s = stage + 1; s <= 2; s++) if (musicClip(s)) return s;
            return stage == 2 && musicClip(2) ? 2 : -1;
        };
        std::vector<int16_t> musicMix;
'''
sub(snd, anchor, musicstate + anchor)
anchor = '\t\t\t\tif (closeNow)\t// a game is starting: the device closed, after the sound still playing (the chime)\n\t\t\t\t{'
sub(snd, anchor, anchor + '\n                    musicStage = -1; // stop music before releasing ALSA to a game')
anchor = '\t\t\tif (name.empty() && !cur && !under && tail == 0)'
insert = r'''            if (name == "rgds-startup")
            {
                musicStage = musicClip(0) ? 0 : musicClip(1) ? 1 : musicClip(2) ? 2 : -1;
                musicPos = 0;
            }
'''
sub(snd, anchor, insert + '\t\t\tif (name.empty() && !cur && !under && tail == 0 && musicStage < 0)')
sub(snd,
    'else if (!cur && !under && now - lastSound >= QUIET) { closeDev(); continue; }',
    'else if (!cur && !under && musicStage < 0 && now - lastSound >= QUIET) { closeDev(); continue; }')
anchor = '\t\t\twhile (frames > 0)\n\t\t\t{'
blend = r'''            // Add two-channel music under normal menu effects without interrupting
            // selections, scroll sounds or the cartridge-click cue.
            if (musicStage >= 0 && pcm && frames > 0 && openRate == 48000 && openCh == 2)
            {
                musicMix.assign(p, p + (size_t)frames * 2);
                for (size_t f = 0; f < (size_t)frames; f++)
                {
                    const Clip* a = musicClip(musicStage);
                    if (!a) { musicStage = -1; break; }
                    const size_t length = a->pcm.size() / 2;
                    int next = musicNext(musicStage);
                    const Clip* b = next >= 0 ? musicClip(next) : nullptr;
                    const size_t bLength = b ? b->pcm.size() / 2 : 0;
                    const size_t fade = b ? std::min({size_t(4800), length / 3, bLength / 3}) : 0;
                    const bool overlapping = fade && musicPos >= length - fade;
                    const size_t bf = overlapping ? musicPos - (length - fade) : 0;
                    const float v = overlapping ? float(bf + 1) / float(fade) : 0.0f;
                    for (int channel = 0; channel < 2; channel++)
                    {
                        const float one = a->pcm[musicPos * 2 + channel];
                        const float two = overlapping ? b->pcm[bf * 2 + channel] : 0.0f;
                        const float background = 0.65f * (one * (1.0f - v) + two * v);
                        const int sample = int(p[f * 2 + channel] + background);
                        musicMix[f * 2 + channel] = int16_t(std::min(32767, std::max(-32768, sample)));
                    }
                    if (++musicPos >= length)
                    {
                        musicStage = next;
                        musicPos = next >= 0 ? fade : 0; // overlap already consumed
                    }
                }
                p = musicMix.data();
            }
'''
sub(snd, anchor, blend + anchor)
# Trigger the special mixer cue as the boot animation starts.
anchor = '\tgSplash.onCue = [&sound](const std::string& n) { sound.play(n); };'
sub(main, anchor, anchor + '\n\tsound.play("rgds-startup");')

# Stack Challenge audio: only use separately verified user-local ROM captures.
# Preserve original theme sounds whenever a verified clip is unavailable.
stack_anchor = '\t\tth = std::thread([this] { run(); });'
stack_audio = r'''        // Stack Challenge cue pack; optional local assets, no ROM bundled.
        bool stackSelect = false, stackReady = false;
        for (auto spec : { std::pair<const char*, const char*>("scroll", "move.wav"),
                           {"select", "line-clear.wav"}, {"stack-tetris", "tetris.wav"} })
        {
            Clip c;
            if (!loadWav(std::string("/data/banana/stack-challenge/") + spec.second,
                         c.pcm, c.rate, c.channels)) continue;
#ifdef BANANA_ALSA
            to48k(c.pcm, c.rate, c.channels);
            toStereo(c.pcm, c.channels);
#endif
            if (c.rate != 48000 || c.channels != 2 || c.pcm.empty() ||
                c.pcm.size() % 2 || c.pcm.size() > 48000u * 2u * 5u) continue;
            clips[spec.first] = std::move(c);
            if (std::string(spec.first) == "select") stackSelect = true;
            if (std::string(spec.first) == "stack-tetris") stackReady = true;
        }
        if (stackSelect && stackReady)
        {
            Clip c = clips.at("select");
            c.pcm.insert(c.pcm.end(), 4800, 0); // 50 ms pause, stereo
            const auto& next = clips.at("stack-tetris").pcm;
            c.pcm.insert(c.pcm.end(), next.begin(), next.end());
            clips["stack-launch"] = std::move(c);
        }
'''
sub(snd, stack_anchor, stack_audio + stack_anchor)
# One queued composite cue ensures selection is not overwritten by loading.
sub(snd, '\t\tif (!enabled || !clips.count(name)) return;',
    '\t\tconst std::string cue = name == "stack-launch" && !clips.count(name) ? "ready" : name;\n\t\tif (!enabled || !clips.count(cue)) return;')
sub(snd, '\t\t\tqueued = name;', '\t\t\tqueued = cue;')
sub(main, 'return after == rnds::UI::LAUNCH && before != rnds::UI::LAUNCH ? "ready" : "select";',
    'return after == rnds::UI::LAUNCH && before != rnds::UI::LAUNCH ? "stack-launch" : "select";')

print("RG DS startup audio: chime -> oh-oh -> loop, with 100-ms crossfades.")
