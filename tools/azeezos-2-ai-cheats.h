#pragma once
// AzeezOS 2.0 development preview: source-backed cheat research.
// This module never executes an AI response or writes emulator memory.
#include "json.h"
#include "settings_curl.h"
#include <zlib.h>
#include <atomic>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <sys/stat.h>
#include <unistd.h>

namespace banana { namespace aicheat {
struct Result {
    std::mutex lock;
    bool ready = false, ok = false;
    std::string text, fingerprint, request, game, system;
};
inline std::string quoted(const std::string& s) {
    std::string out = "\"";
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { out += '\\'; out += char(c); }
        else if (c < 32) {
            char b[7]; snprintf(b, sizeof b, "\\u%04x", unsigned(c)); out += b;
        } else out += char(c);
    }
    return out + '"';
}
inline std::string fingerprint(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return "";
    char buf[32768];
    uLong crc = crc32(0L, Z_NULL, 0);
    unsigned long long n = 0;
    while (f) {
        f.read(buf, sizeof buf);
        auto got = f.gcount();
        if (got > 0) { crc = crc32(crc, reinterpret_cast<const Bytef*>(buf), static_cast<uInt>(got)); n += got; }
    }
    if (f.bad() || !n) return "";
    std::ostringstream s; s << std::hex << std::setw(8) << std::setfill('0') << crc << "-" << std::dec << n;
    return s.str(); // file CRC32 + byte count; ZIP/disc container is NOT a ROM checksum
}
inline std::string answer(const std::string& body) {
    JPtr j = parseJson(body);
    if (!j || j->str("status") != "completed") return "";
    auto o = j->get("output");
    if (!o || !o->isArr()) return "";
    std::string out;
    for (auto& m : o->arr) {
        if (!m || m->str("type") != "message") continue;
        auto c = m->get("content");
        if (!c || !c->isArr()) continue;
        for (auto& p : c->arr) {
            if (!p || p->str("type") != "output_text") continue;
            if (!out.empty()) out += "\n";
            out += p->str("text");
            auto ann = p->get("annotations");
            if (ann && ann->isArr()) for (auto& a : ann->arr) {
                if (a && a->str("type") == "url_citation") {
                    auto url = a->str("url");
                    if (!url.empty() && out.find(url) == std::string::npos) out += "\n" + url;
                }
            }
        }
    }
    if (out.size() > 8000) out.resize(8000);
    return out;
}
inline size_t bounded(char* p, size_t sz, size_t n, void* u) {
    auto& s = *static_cast<std::string*>(u);
    size_t len = sz*n;
    if (len > 524288 || s.size() > 524288-len) return 0;
    s.append(p, len); return len;
}
inline std::string online(const std::string& prompt, std::string& error) {
    const char* key = getenv("AZEEZOS_OPENAI_API_KEY");
    if (!key || !*key) key = getenv("OPENAI_API_KEY");
    if (!key || !*key) { error = "AI service is not configured. Set an API credential in the service environment."; return ""; }
    std::string token(key);
    if (token.find_first_of("\r\n") != std::string::npos) { error="Invalid AI credential."; return ""; }
    const char* mdl = getenv("AZEEZOS_AI_MODEL");
    Curl c;
    if (!c.load()) { error="HTTPS library unavailable."; return ""; }
    void* lib = dlopen("libcurl.so.4", RTLD_NOW | RTLD_LOCAL);
    if (!lib) { error="HTTPS library unavailable."; return ""; }
    using Append = void* (*)(void*, const char*);
    using Free = void (*)(void*);
    auto append = reinterpret_cast<Append>(dlsym(lib,"curl_slist_append"));
    auto freeList = reinterpret_cast<Free>(dlsym(lib,"curl_slist_free_all"));
    if (!append || !freeList) { dlclose(lib); error="HTTPS header support unavailable."; return ""; }
    auto h = c.init();
    if (!h) { dlclose(lib); error="HTTPS initialization failed."; return ""; }
    std::string auth = "Authorization: Bearer " + token;
    void* headers = append(nullptr, auth.c_str());
    void* next = headers ? append(headers,"Content-Type: application/json") : nullptr;
    if (!next) { if(headers) freeList(headers); c.cleanup(h); dlclose(lib); error="HTTPS header allocation failed."; return ""; }
    headers = next;
    std::string body, req = "{\"model\":"+quoted(mdl && *mdl ? mdl : "gpt-5-mini")+
        ",\"store\":false,\"tools\":[{\"type\":\"web_search\"}],\"tool_choice\":\"required\",\"max_output_tokens\":1800,\"input\":"+quoted(prompt)+"}";
    // Standard libcurl option IDs, same dynamic interface as settings_curl.h.
    c.setopt(h,10002,"https://api.openai.com/v1/responses");
    c.setopt(h,10023,headers); c.setopt(h,10015,req.c_str());
    c.setopt(h,10001,&body); c.setopt(h,20011,bounded);
    c.setopt(h,13,90L); c.setopt(h,78,15L); c.setopt(h,99,1L);
    c.setopt(h,64,1L); c.setopt(h,81,2L);
    int rc=c.perform(h); long status=0; c.getinfo(h,0x200002,&status);
    c.cleanup(h); freeList(headers); dlclose(lib);
    if (rc || status != 200) { error="AI request failed (HTTP "+std::to_string(status)+"). Check Wi-Fi, API access and billing."; return ""; }
    auto out=answer(body);
    if (out.empty()) error="AI returned no completed candidate. Try again.";
    return out;
}
inline std::shared_ptr<Result> search(std::string rom, std::string game, std::string system, std::string request) {
    auto r=std::make_shared<Result>();
    r->request=request; r->game=game; r->system=system;
    std::thread([r,rom,game,system,request] {
        std::string id=fingerprint(rom), err, found;
        if (id.empty()) err="Cannot read this game's file.";
        else {
            std::string basename=rom.substr(rom.find_last_of('/')+1);
            found=online("Research a cheat for an offline emulator game. Use web search for the exact game and revision. "
                "Return a concise candidate, code format, full code, source URL, revision evidence, and test instructions. "
                "If not found, explicitly say so. Do not invent addresses or claim compatibility without evidence. "
                "The following file CRC32-size may identify a compressed container, not the ROM inside. "
                "Do not request credentials or provide shell commands.\nGame: "+game+"\nSystem: "+system+
                "\nFilename: "+basename+"\nFile fingerprint: "+id+"\nRequested effect: "+request,err);
        }
        std::lock_guard<std::mutex> l(r->lock);
        r->fingerprint=id; r->ok=!found.empty(); r->text=r->ok?found:err; r->ready=true;
    }).detach();
    return r;
}
inline bool saveDraft(const std::string& data, const Result& r) {
    if (!r.ready || !r.ok || r.fingerprint.empty()) return false;
    std::string dir=data+"/ai-cheats";
    if (mkdir(dir.c_str(),0700) != 0) { struct stat st{}; if (stat(dir.c_str(),&st) || !S_ISDIR(st.st_mode)) return false; }
    std::string path=dir+"/"+r.fingerprint+"-XXXXXX";
    int fd=mkstemp(&path[0]); if(fd<0) return false;
    std::string doc="{\"status\":\"unverified-draft\",\"file_fingerprint\":"+quoted(r.fingerprint)+
        ",\"game\":"+quoted(r.game)+",\"system\":"+quoted(r.system)+",\"request\":"+quoted(r.request)+",\"research\":"+quoted(r.text)+"}\n";
    size_t at=0; while(at<doc.size()) { auto n=write(fd,doc.data()+at,doc.size()-at); if(n<=0) break; at+=n; }
    bool ok=at==doc.size() && fsync(fd)==0;
    if(close(fd)!=0) ok=false;
    if(!ok) unlink(path.c_str());
    return ok;
}
}}
