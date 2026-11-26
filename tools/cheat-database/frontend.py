#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[2])
def rep(rel,a,b):
    p=root/rel;s=p.read_text()
    if b in s:return
    if s.count(a)!=1:raise SystemExit("cheat source anchor "+rel+" "+repr(a[:90]))
    p.write_text(s.replace(a,b,1))
if sys.argv[1]=="ra":
    rep("command.c","   const char *arg = NULL;\n   unsigned index  = 0;",
        """#ifdef HAVE_CHEATS
   if (strcmp(tok,"AZEEZ_CHEATS_APPLY")==0) {
#ifdef HAVE_CHEEVOS
      if (rcheevos_hardcore_active()) return;
#endif
#ifdef HAVE_NETWORKING
      if (netplay_driver_ctl(RARCH_NETPLAY_CTL_IS_DATA_INITED,NULL)) return;
#endif
      cheat_manager_alloc_if_empty();
      if (cheat_manager_load("/run/banana/azeez-db-active.cht",false))
         cheat_manager_apply_cheats(false);
      return;
   }
#endif
   const char *arg = NULL;
   unsigned index  = 0;""")
elif sys.argv[1]=="bf":
    rep("src/bf.h","    void (*reset)(void);",
        """    void (*reset)(void);
    void (*cheat_reset)(void);
    void (*cheat_set)(unsigned,bool,const char*);""")
    rep("src/core.c","    SYM(unserialize); SYM(load_game);",
        """    *(void**)&g_core.cheat_reset=dlsym(g_core.dl,"retro_cheat_reset");
    *(void**)&g_core.cheat_set=dlsym(g_core.dl,"retro_cheat_set");
    SYM(unserialize); SYM(load_game);""")
    rep("src/main.c","void bf_command(const char* line)",r"""
static void az_cheats_apply(void)
{
    if (ra_hardcore() || !g_core.cheat_reset || !g_core.cheat_set) return;
    FILE* f=fopen("/run/banana/azeez-db-active.cht","r");
    if(!f) return;
    char *line=NULL; size_t cap=0;
    struct az_row { char *code; bool enabled; unsigned handler; };
    struct az_row *rows=calloc(4096,sizeof *rows);
    if(!rows){fclose(f);return;}
    unsigned count=0;
    while(getline(&line,&cap,f)>=0){
        unsigned idx; int pos=0;
        if(sscanf(line,"cheat%u_%n",&idx,&pos)!=1 || pos<=0 || idx>=4096)continue;
        char *eq=strchr(line,'=');if(!eq)continue;
        char *v=eq+1;while(*v==' '||*v=='\t'||*v=='"')v++;
        v[strcspn(v,"\"\r\n")]=0;
        if(!strncmp(line+pos,"code",4)){free(rows[idx].code);rows[idx].code=strdup(v);}
        else if(!strncmp(line+pos,"enable",6))rows[idx].enabled=!strcmp(v,"true")||!strcmp(v,"1");
        else if(!strncmp(line+pos,"handler",7))rows[idx].handler=(unsigned)strtoul(v,NULL,10);
        if(idx>=count)count=idx+1;
    }
    fclose(f);free(line);
    g_core.cheat_reset();
    for(unsigned i=0;i<count;i++){
        if(rows[i].enabled && rows[i].code && *rows[i].code && rows[i].handler==0)
            g_core.cheat_set(i,true,rows[i].code);
        free(rows[i].code);
    }
    free(rows);
}
void bf_command(const char* line)""")
    rep("src/main.c",'    if (!strcmp(w, "QUIT")) quit = true;',
        '''    if (!strcmp(w,"AZEEZ_CHEATS_APPLY")) az_cheats_apply();
    else if (!strcmp(w, "QUIT")) quit = true;''')
else:raise SystemExit("bad frontend")
