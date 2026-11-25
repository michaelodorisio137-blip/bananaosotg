#include "trial.h"
#include <cassert>
#include <iostream>
using azeez::Trial;
static void reply(Trial& t,const std::string& s){t.feed(s.data(),s.size());}
static void applied(Trial& t){
    assert(t.begin(0xc010,99));
    assert(t.request(0)=="READ_CORE_MEMORY c010 1\n");
    reply(t,"READ_CORE_MEMORY c010 03\n");
    assert(t.request(1)=="WRITE_CORE_MEMORY c010 63\n");
    reply(t,"WRITE_CORE_MEMORY c010 1\n");
    assert(t.request(2)=="READ_CORE_MEMORY c010 1\n");
    reply(t,"READ_CORE_MEMORY c010 63\n");
    assert(t.state()==Trial::AwaitUser && !t.canSave());
}
int main(){
    Trial t;
    applied(t);assert(t.confirm() && t.canSave());
    applied(t);assert(t.undo());
    assert(t.request(3)=="READ_CORE_MEMORY c010 1\n");
    reply(t,"READ_CORE_MEMORY c010 63\n");
    assert(t.request(4)=="WRITE_CORE_MEMORY c010 03\n");
    reply(t,"WRITE_CORE_MEMORY c010 1\n");
    assert(t.request(5)=="READ_CORE_MEMORY c010 1\n");
    reply(t,"READ_CORE_MEMORY c010 03\n");assert(t.state()==Trial::Reverted);
    applied(t);assert(t.undo());assert(!t.request(3).empty());
    reply(t,"READ_CORE_MEMORY c010 22\n");
    assert(t.state()==Trial::Unknown && t.request(4).empty() && !t.canSave());
    Trial timeout;assert(timeout.begin(0xc010,99));assert(!timeout.request(0).empty());
    reply(timeout,"READ_CORE_MEMORY c010 03\n");assert(!timeout.request(1).empty());
    assert(timeout.request(3000).empty() && timeout.state()==Trial::Unknown);
    assert(timeout.undo());assert(!timeout.request(3001).empty());
    reply(timeout,"READ_CORE_MEMORY c010 03\n");assert(timeout.state()==Trial::Reverted);
    Trial same;assert(same.begin(0xc010,3));assert(!same.request(0).empty());
    reply(same,"READ_CORE_MEMORY c010 03\n");assert(same.state()==Trial::Failed);
    assert(!same.begin(0xc010,256));
    std::cout<<"PASS: one-shot trial, readback, explicit confirm, conditional undo, timeout recovery\n";
}
