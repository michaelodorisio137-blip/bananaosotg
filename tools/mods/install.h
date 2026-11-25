#pragma once
#include "patch.h"
#include <fstream>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <cerrno>
#include <sys/syscall.h>
namespace azeez::mods {
inline Bytes readFile(const std::string& path){
    struct stat st{};
    if(stat(path.c_str(),&st)||!S_ISREG(st.st_mode)||st.st_size<0||uint64_t(st.st_size)>Limit)
        throw std::runtime_error("missing or oversized file");
    Bytes bytes(size_t(st.st_size));
    std::ifstream f(path,std::ios::binary);
    if(!f||(!bytes.empty()&&!f.read(reinterpret_cast<char*>(bytes.data()),bytes.size()))||f.peek()!=EOF)
        throw std::runtime_error("input changed or could not read");
    return bytes;
}
// Both patch and original revision CRCs must be independently supplied by
// the catalog or operator. BPS additionally validates its embedded CRCs.
inline void install(const std::string& source,const std::string& patch,
                    const std::string& destination,uint32_t expectedSource,uint32_t expectedPatch){
    auto src=readFile(source),p=readFile(patch);
    if(crc(src,src.size())!=expectedSource||crc(p,p.size())!=expectedPatch)
        throw std::runtime_error("revision or patch checksum mismatch");
    auto out=azeez::mods::apply(src,p);
    if(out.empty())throw std::runtime_error("empty ROM");
    // Publish atomically without replacing a pre-existing file, including FAT/exFAT.
    // If neither no-replace rename nor hard links are supported, fail closed.
    std::string tmp=destination+".partial.XXXXXX";
    int fd=mkstemp(&tmp[0]);
    if(fd<0)throw std::runtime_error("could not create temporary ROM");
    auto writeAll=[&](int f){
        size_t at=0;
        while(at<out.size()){
            ssize_t n=write(f,out.data()+at,out.size()-at);
            if(n<0&&errno==EINTR)continue;
            if(n<=0)return false;
            at+=size_t(n);
        }
        return fsync(f)==0;
    };
    bool ok=writeAll(fd);
    if(close(fd)!=0)ok=false;
    if(!ok){unlink(tmp.c_str());throw std::runtime_error("could not write patched ROM");}
#ifdef SYS_renameat2
    if(syscall(SYS_renameat2,AT_FDCWD,tmp.c_str(),AT_FDCWD,destination.c_str(),1)==0)return;
    if(errno==EEXIST){unlink(tmp.c_str());throw std::runtime_error("destination already exists");}
#endif
    if(link(tmp.c_str(),destination.c_str())==0){unlink(tmp.c_str());return;}
    unlink(tmp.c_str());
    throw std::runtime_error("cannot publish atomically without replacing an existing file");
}
}
