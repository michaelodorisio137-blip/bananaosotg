#!/usr/bin/env python3
"""Original E0C6200 ROM runner; SDL2 front end and emulated buzzer."""
import ctypes as C, ctypes.util, json, math, os, sys, time, wave, array
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from cores.E0C6200 import E0C6200
CLOCK=2000000
RATE=48000
KEYS={'left':('K0',1),'down':('K0',2),'right':('K0',4),'rotate':('K0',8),'pause':('K1',2),'sound':('K1',4),'power':('K1',1)}
class Machine:
    def __init__(self,rom):
        self.cycles=0; self.events=[]; self.tone=None; self.phase=0; self.samplepos=0
        self.cpu=E0C6200({'rom_path':str(rom),'port_pullup':{'K0':15,'K1':15},'p3_dedicated':0},CLOCK,self)
    def register_pin_device(self,dev): pass
    def emit_port(self,*args): pass
    def emit_audio(self,channel,data):
        if data!=self.tone:
            self.tone=data
            self.events.append((self.cycles,data))
    def button(self,key,pressed):
        p,m=KEYS[key]; self.cpu.pin_handler(p,m,0 if pressed else -1)
    def run(self,cycles):
        end=self.cycles+cycles
        while self.cycles<end:
            self.cycles+=self.cpu.clock()
    def sound(self):
        end=int(self.cycles*RATE/CLOCK)
        pcm=array.array('h')
        events=self.events
        tone=getattr(self,'render_tone',None); j=0
        for i in range(self.samplepos,end):
            while j<len(events) and events[j][0]*RATE<=i*CLOCK:
                tone=events[j][1];j+=1
            if tone and tone[0]>0:
                self.phase=(self.phase+tone[0]/RATE)%1.0
                # Bipolar piezo-like waveform; frequency and envelope from ROM.
                amp=max(0,min(1,tone[2]/5))
                pcm.append(int((1 if self.phase<.5 else -1)*amp*6500))
            else: pcm.append(0)
        self.events=events[j:];self.render_tone=tone;self.samplepos=end
        return pcm
def wav(path,pcm):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(pcm.tobytes())
def capture(rom,out):
    """Capture only actual ROM buzzer events, including during active gameplay."""
    import hashlib
    out.mkdir(parents=True,exist_ok=True)
    m=Machine(rom)
    def step(seconds):
        m.run(int(seconds*CLOCK));return m.sound()
    def tap(key,hold=.12,after=.45):
        m.button(key,True);a=step(hold);m.button(key,False);a.extend(step(after));return a
    report={}; attempts=[]; seen={}
    def record(key,a):
        nz=[i for i,v in enumerate(a) if v]
        attempts.append({"action":key,"audible":bool(nz),"samples":len(a)})
        if not nz: return
        a=a[max(0,nz[0]-240):min(len(a),nz[-1]+241)]
        digest=hashlib.sha256(a.tobytes()).hexdigest()
        if digest in seen:
            attempts[-1]["duplicate_of"]=seen[digest];return
        name=key; i=2
        while name in report:
            name=f"{key}-{i}";i+=1
        wav(out/(name+".wav"),a)
        seen[digest]=name
        report[name]={"action":key,"samples":len(a),"rate":RATE,"pcm_sha256":digest}
    step(.5)
    record("power",tap("power",after=1.2))
    record("rotate",tap("rotate",after=1.2))
    record("idle",step(2.0))
    # Exercise actual play before using the sound toggle. Do not infer a
    # landing or line clear solely from the down button.
    for cycle in range(5):
        for key in ("left","right","rotate","down","down"):
            record(key,tap(key,hold=.20 if key=="down" else .12,after=.35))
        record("idle",step(1.0))
    record("pause",tap("pause"))
    record("pause",tap("pause"))
    record("sound",tap("sound"))
    record("sound",tap("sound"))
    (out/"capture.json").write_text(json.dumps(report,indent=2))
    (out/"attempts.json").write_text(json.dumps(attempts,indent=2))
    if not report: raise RuntimeError("No buzzer output captured; inspect ROM/input sequence")
    print(json.dumps(report))
def sdlgame(rom):
    s=C.CDLL(ctypes.util.find_library('SDL2') or 'libSDL2-2.0.so.0')
    def bind(n,r,*a):
        f=getattr(s,n);f.restype=r;f.argtypes=a;return f
    P=C.c_void_p; I=C.c_int; U=C.c_uint32
    class Rect(C.Structure): _fields_=[('x',I),('y',I),('w',I),('h',I)]
    class Audio(C.Structure):
        _fields_=[('freq',I),('format',C.c_uint16),('channels',C.c_uint8),('silence',C.c_uint8),('samples',C.c_uint16),('padding',C.c_uint16),('size',U),('callback',P),('userdata',P)]
    init=bind('SDL_Init',I,U); quit=bind('SDL_Quit',None)
    err=bind('SDL_GetError',C.c_char_p)
    win=bind('SDL_CreateWindow',P,C.c_char_p,I,I,I,I,U)
    rend=bind('SDL_CreateRenderer',P,P,I,U)
    color=bind('SDL_SetRenderDrawColor',I,P,C.c_uint8,C.c_uint8,C.c_uint8,C.c_uint8)
    clear=bind('SDL_RenderClear',I,P);present=bind('SDL_RenderPresent',None,P)
    surface=bind('SDL_CreateRGBSurfaceFrom',P,P,I,I,I,I,U,U,U,U)
    freesu=bind('SDL_FreeSurface',None,P)
    tex=bind('SDL_CreateTextureFromSurface',P,P,P)
    copy=bind('SDL_RenderCopy',I,P,P,P,C.POINTER(Rect))
    poll=bind('SDL_PollEvent',I,P)
    openaudio=bind('SDL_OpenAudioDevice',U,C.c_char_p,I,C.POINTER(Audio),C.POINTER(Audio),I)
    pauseaudio=bind('SDL_PauseAudioDevice',None,U,I)
    queue=bind('SDL_QueueAudio',I,U,P,U)
    queued=bind('SDL_GetQueuedAudioSize',U,U)
    clearq=bind('SDL_ClearQueuedAudio',None,U)
    joycount=bind('SDL_NumJoysticks',I);joyopen=bind('SDL_JoystickOpen',P,I)
    if init(0x20|0x10|0x200):raise RuntimeError(err())
    try:
        w=win(b'Stack Challenge',0,0,640,480,0x1001)
        if not w:raise RuntimeError(err())
        r=rend(w,-1,2)
        if not r:r=rend(w,-1,1)
        if not r:raise RuntimeError(err())
        logical=bind('SDL_RenderSetLogicalSize',I,P,I,I);logical(r,640,480)
        a=Audio(RATE,0x8010,1,0,512,0,0,None,None)
        dev=openaudio(None,0,C.byref(a),None,0)
        if not dev:raise RuntimeError(err())
        pauseaudio(dev,0)
        for i in range(joycount()):joyopen(i)
        m=Machine(rom)
        manifest=json.loads((ROOT/'display.json').read_text())
        def texture(item):
            x,y,w,h=item['rect']; raw=(ROOT/item['file']).read_bytes()
            b=C.create_string_buffer(raw)
            su=surface(b,w,h,32,w*4,0xff,0xff00,0xff0000,0xff000000)
            if not su:raise RuntimeError(err())
            t=tex(r,su);freesu(su)
            if not t:raise RuntimeError(err())
            return t,Rect(x,y,w,h)
        bg=texture(manifest['background'])
        segments=[(v['index'],v['bit'],texture(v)) for v in manifest['segments']]
        keymap={1073741904:'left',1073741903:'right',1073741905:'down',1073741906:'rotate',32:'rotate',13:'power',112:'pause',115:'sound'}
        # SDL raw joystick defaults, configurable for actual RG DS mapping.
        jmap={int(k):v for k,v in json.loads(os.getenv('STACK_BUTTONS','{"0":"rotate","1":"rotate","6":"sound","7":"power","9":"pause","11":"left","12":"right","13":"down","14":"rotate"}')).items()}
        ev=C.create_string_buffer(56);running=True;oldhat=0;deadline=time.monotonic()
        while running:
            while poll(ev):
                raw=ev.raw;typ=int.from_bytes(raw[:4],'little')
                if typ==0x100:running=False
                elif typ in (0x300,0x301):
                    key=int.from_bytes(raw[20:24],'little',signed=True)
                    if key==27:running=False
                    elif key in keymap:m.button(keymap[key],typ==0x300)
                elif typ in (0x603,0x604):
                    key=jmap.get(raw[12])
                    if key=='exit' and typ==0x603:running=False
                    elif key in KEYS:m.button(key,typ==0x603)
                elif typ==0x602:
                    hat=raw[13]
                    for bit,key in ((1,'rotate'),(2,'right'),(4,'down'),(8,'left')):
                        if (hat^oldhat)&bit:m.button(key,bool(hat&bit))
                    oldhat=hat
            m.run(CLOCK/60);pcm=m.sound()
            if queued(dev)>RATE//5*2:clearq(dev)
            if pcm:queue(dev,pcm.tobytes(),len(pcm)*2)
            color(r,24,26,28,255);clear(r);copy(r,bg[0],None,C.byref(bg[1]))
            vram=m.cpu.get_VRAM()
            for index,bit,(t,rect) in segments:
                if index<len(vram) and (vram[index]>>bit)&1:copy(r,t,None,C.byref(rect))
            present(r)
            deadline+=1/60
            delay=deadline-time.monotonic()
            if delay>0:time.sleep(delay)
            elif delay<-.15:deadline=time.monotonic()
    finally:quit()
if __name__=='__main__':
    rom=Path(os.getenv('STACK_ROM',str(ROOT/'RadioShackStackChallenge.bin')))
    if not rom.is_file() or rom.stat().st_size!=12288:sys.exit('Supply original 12288-byte RadioShackStackChallenge.bin via STACK_ROM')
    if len(sys.argv)>1 and sys.argv[1]=='--capture':capture(rom,Path(sys.argv[2]))
    else:sdlgame(rom)
