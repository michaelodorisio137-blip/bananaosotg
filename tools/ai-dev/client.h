#pragma once
#include "azeezos_ai_cheats.h"
#include <random>
namespace banana::azdev {
inline constexpr const char* base="https://api.github.com/repos/michaelodorisio137-blip/bananaosotg";
struct Result {
    std::mutex lock;
    bool done=false,ok=false;
    std::string id,message,url;
};
inline std::string newId(){
    std::random_device r;
    char b[33];snprintf(b,sizeof b,"%08x%08x%08x%08x",unsigned(r()),unsigned(r()),unsigned(r()),unsigned(r()));
    return b;
}
inline bool validId(const std::string& id){
    return id.size()==32&&id.find_first_not_of("0123456789abcdef")==std::string::npos;
}
inline std::string api(const std::string& path,const std::string& request,long& status){
    const char* key=getenv("AZEEZOS_GITHUB_TOKEN");
    if(!key||!*key||std::string(key).find_first_of("\r\n")!=std::string::npos)throw std::runtime_error("Configure scoped GitHub Actions token.");
    Curl c;if(!c.load())throw std::runtime_error("HTTPS unavailable");
    void* lib=dlopen("libcurl.so.4",RTLD_NOW|RTLD_LOCAL);
    if(!lib)throw std::runtime_error("HTTPS unavailable");
    auto append=reinterpret_cast<void*(*)(void*,const char*)>(dlsym(lib,"curl_slist_append"));
    auto freeList=reinterpret_cast<void(*)(void*)>(dlsym(lib,"curl_slist_free_all"));
    void* h=c.init();
    if(!append||!freeList||!h){if(h)c.cleanup(h);dlclose(lib);throw std::runtime_error("HTTPS initialization failed");}
    std::string auth="Authorization: Bearer "+std::string(key),url=std::string(base)+path,body;
    void* headers=nullptr;
    for(const char* line:{auth.c_str(),static_cast<const char*>("Accept: application/vnd.github+json"),static_cast<const char*>("Content-Type: application/json"),static_cast<const char*>("X-GitHub-Api-Version: 2022-11-28")}){
        void* p=append(headers,line);
        if(!p){if(headers)freeList(headers);c.cleanup(h);dlclose(lib);throw std::runtime_error("HTTPS header allocation failed");}
        headers=p;
    }
    c.setopt(h,10002,url.c_str());c.setopt(h,10023,headers);
    c.setopt(h,10018,"AzeezOS-RGDS");c.setopt(h,10001,&body);c.setopt(h,20011,aicheat::bounded);
    c.setopt(h,13,25L);c.setopt(h,78,10L);c.setopt(h,99,1L);c.setopt(h,64,1L);c.setopt(h,81,2L);
    if(!request.empty())c.setopt(h,10015,request.c_str());
    int rc=c.perform(h);c.getinfo(h,0x200002,&status);
    c.cleanup(h);freeList(headers);dlclose(lib);
    if(rc)throw std::runtime_error("GitHub connection failed");
    return body;
}
inline std::shared_ptr<Result> submit(std::string feature){
    auto r=std::make_shared<Result>();
    std::thread([r,feature]{
        std::string id,message;bool ok=false;
        try{
            if(feature.empty()||feature.size()>800)throw std::runtime_error("Feature request must be 1-800 characters.");
            id=newId();long status=0;
            std::string payload="{\"ref\":\"azeezos-2.0\",\"inputs\":{\"feature_request\":"+aicheat::quoted(feature)+",\"request_id\":"+aicheat::quoted(id)+"}}";
            api("/actions/workflows/validate-custom.yml/dispatches",payload,status);
            if(status!=204&&status!=200)throw std::runtime_error("Request rejected (HTTP "+std::to_string(status)+"). Check token and workflow.");
            ok=true;message="Submitted. Tap Status for actual build progress.";
        }catch(const std::exception& e){message=e.what();}
        std::lock_guard<std::mutex> l(r->lock);r->id=ok?id:"";r->ok=ok;r->message=message;r->done=true;
    }).detach();return r;
}
inline std::shared_ptr<Result> poll(std::string id){
    auto r=std::make_shared<Result>();
    std::thread([r,id]{
        std::string message,url;bool ok=false;
        try{
            if(!validId(id))throw std::runtime_error("No active feature request");
            long status=0;
            auto body=api("/actions/workflows/validate-custom.yml/runs?branch=azeezos-2.0&event=workflow_dispatch&per_page=30","",status);
            if(status!=200)throw std::runtime_error("Status request failed (HTTP "+std::to_string(status)+")");
            auto j=parseJson(body);auto runs=j?j->get("workflow_runs"):nullptr;
            if(!runs||!runs->isArr())throw std::runtime_error("Invalid GitHub reply");
            message="Request accepted; waiting for GitHub to list it.";
            for(auto& w:runs->arr){
                if(!w||w->str("display_title")!="AzeezOS AI "+id)continue;
                auto st=w->str("status"),result=w->str("conclusion");
                url=w->str("html_url");
                if(url.rfind("https://github.com/michaelodorisio137-blip/bananaosotg/actions/runs/",0)!=0)url.clear();
                message=st=="completed"?(result=="success"?"Build passed. Review proposal before installing.":"Build ended: "+result):"GitHub: "+st;
                break;
            }
            ok=true;
        }catch(const std::exception& e){message=e.what();}
        std::lock_guard<std::mutex> l(r->lock);r->id=id;r->ok=ok;r->message=message;r->url=url;r->done=true;
    }).detach();return r;
}
}
