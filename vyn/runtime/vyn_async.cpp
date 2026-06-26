/* vyn_async.cpp — Vyn Async Runtime C-compatible implementation */

#include "vyn_async.hpp"
#include <cstdio>

using namespace vyn::async;

// ─── C-API implementation ────────────────────────────────────────────────────

extern "C" {

void vyn_async_init(void) {
    // Global loop is lazily initialized via detail::global_loop()
    // Nothing explicit needed here
}

void vyn_async_run(void) {
    loop().run();
}

void vyn_async_stop(void) {
    loop().stop();
}

void vyn_async_tick(void) {
    loop().tick();
}

struct CallbackWrapper {
    void (*fn)(void *);
    void  *userdata;
};

uint64_t vyn_async_defer_ms(double ms, void (*fn)(void *), void *userdata) {
    auto *w = new CallbackWrapper{ fn, userdata };
    return loop().set_timeout(ms, [w]() {
        w->fn(w->userdata);
        delete w;
    });
}

uint64_t vyn_async_set_interval(double ms, void (*fn)(void *), void *userdata) {
    auto *w = new CallbackWrapper{ fn, userdata };
    return loop().set_interval(ms, [w]() {
        w->fn(w->userdata);
    });
}

void vyn_async_cancel(uint64_t id) {
    loop().cancel(id);
}

void vyn_async_spawn_void(void (*fn)(void *), void *userdata) {
    auto *w = new CallbackWrapper{ fn, userdata };
    loop().spawn_void([w]() {
        w->fn(w->userdata);
        delete w;
    });
}

} // extern "C"