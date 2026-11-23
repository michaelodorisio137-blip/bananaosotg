#!/usr/bin/env python3
"""Runtime smoke test for expanded libretro mGBA using original tiny test ROMs.

Verifies GB and GBC ROMs load, output 320x204 and identify as the separate
expanded core. No copyrighted commercial game files required.
"""
import ctypes as C
import sys
from pathlib import Path

class Geometry(C.Structure):
    _fields_ = [("base_width", C.c_uint), ("base_height", C.c_uint),
                ("max_width", C.c_uint), ("max_height", C.c_uint),
                ("aspect_ratio", C.c_float)]
class Timing(C.Structure):
    _fields_ = [("fps", C.c_double), ("sample_rate", C.c_double)]
class AVInfo(C.Structure):
    _fields_ = [("geometry", Geometry), ("timing", Timing)]
class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p),
                ("size", C.c_size_t), ("meta", C.c_char_p)]
class SystemInfo(C.Structure):
    _fields_ = [("library_name", C.c_char_p), ("library_version", C.c_char_p),
                ("valid_extensions", C.c_char_p),
                ("need_fullpath", C.c_bool), ("block_extract", C.c_bool)]

lib = C.CDLL(sys.argv[1])
Env = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
Video = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
Poll = C.CFUNCTYPE(None)
Input = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)
AudioBatch = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
Audio = C.CFUNCTYPE(None, C.c_int16, C.c_int16)

@Env
def env(cmd, data):
    if cmd == 9:  # RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY
        C.cast(data, C.POINTER(C.c_char_p))[0] = b"/tmp"
        return True
    return False

captures = []
@Video
def video(data, w, h, pitch):
    if data:
        captures.append((int(w), int(h), int(pitch)))

@Poll
def poll(): pass
@Input
def input_(port, dev, idx, id_): return 0
@AudioBatch
def batch(buf, frames): return frames
@Audio
def audio(left, right): pass

lib.retro_set_environment.argtypes = [Env]
lib.retro_set_video_refresh.argtypes = [Video]
lib.retro_set_input_poll.argtypes = [Poll]
lib.retro_set_input_state.argtypes = [Input]
lib.retro_set_audio_sample_batch.argtypes = [AudioBatch]
lib.retro_set_audio_sample.argtypes = [Audio]
lib.retro_get_system_info.argtypes = [C.POINTER(SystemInfo)]
lib.retro_get_system_av_info.argtypes = [C.POINTER(AVInfo)]
lib.retro_load_game.argtypes = [C.POINTER(GameInfo)]
lib.retro_load_game.restype = C.c_bool

lib.retro_set_environment(env)
lib.retro_set_video_refresh(video)
lib.retro_set_input_poll(poll)
lib.retro_set_input_state(input_)
lib.retro_set_audio_sample_batch(batch)
lib.retro_set_audio_sample(audio)
lib.retro_init()
ident = SystemInfo()
lib.retro_get_system_info(C.byref(ident))
assert b"mGBA Expanded RGDS" == ident.library_name, ident.library_name

def make_rom(cgb, sgb=False):
    rom = bytearray(32768)
    # Distinct tiny custom test program; no proprietary retail ROM or BIOS.
    rom[0x100:0x103] = b"\xC3\x50\x01"   # JP $0150
    rom[0x104:0x108] = b"\x7C\xE7\xC0\x00"  # recognized minimal header
    rom[0x134:0x13D] = b"RGDS-TEST"
    rom[0x143] = 0xC0 if cgb else 0x00
    if sgb:
        rom[0x146] = 0x03
        rom[0x14B] = 0x33
    rom[0x147] = 0
    rom[0x148] = 0
    rom[0x149] = 0
    check = 0
    for b in rom[0x134:0x14D]:
        check = (check - b - 1) & 0xFF
    rom[0x14D] = check
    # The second small program remains entirely original.
    rom[0x150:0x153] = b"\xC3\x50\x01"  # JP $0150
    return C.create_string_buffer(bytes(rom), len(rom))

for name, cgb, sgb in (("GB", False, False), ("GBC", True, False), ("SGB-compatible GB", False, True)):
    captures.clear()
    rom = make_rom(cgb, sgb)
    info = GameInfo(b"test.gbc" if cgb else b"test.gb", C.cast(rom, C.c_void_p), len(rom), None)
    assert lib.retro_load_game(C.byref(info)), name + " load failed"
    av = AVInfo()
    lib.retro_get_system_av_info(C.byref(av))
    assert (av.geometry.base_width, av.geometry.base_height) == (320, 204), (cgb, av.geometry.base_width, av.geometry.base_height)
    assert (av.geometry.max_width, av.geometry.max_height) == (320, 204), (cgb, av.geometry.max_width, av.geometry.max_height)
    for _ in range(3):
        lib.retro_run()
    assert captures, "No video produced for " + name
    assert all((w, h) == (320, 204) for w, h, pitch in captures), (cgb, captures)
    assert all(pitch == 320 * 4 or pitch == 320 * 2 for w, h, pitch in captures), (cgb, captures)
    print(name + ": core mGBA Expanded RGDS, 320x204 video verified")
    lib.retro_unload_game()
lib.retro_deinit()
