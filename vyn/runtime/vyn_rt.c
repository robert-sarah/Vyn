/* vyn_rt.c — Vyn Runtime Library Implementation
 * Complete native runtime: GC, strings, hashmap, vec, threads, profiling, I/O, math, crypto, FFI
 */

#include "vyn_rt.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <math.h>
#include <time.h>
#include <errno.h>
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef _WIN32
#  include <windows.h>
#  include <io.h>
#  include <direct.h>
#  define PATH_SEP "\\"
#else
#  include <unistd.h>
#  include <sys/time.h>
#  include <sys/stat.h>
#  include <dirent.h>
#  include <pthread.h>
#  include <dlfcn.h>
#  define PATH_SEP "/"
#endif

/* ═══════════════════════════════════════════════════════════════════════════
 *  Global state
 * ═══════════════════════════════════════════════════════════════════════════ */

int    vyn_argc = 0;
char **vyn_argv = NULL;

/* ═══════════════════════════════════════════════════════════════════════════
 *  Panic / OOM
 * ═══════════════════════════════════════════════════════════════════════════ */

void vyn_panic(const char *fmt, ...) {
    va_list ap;
    fprintf(stderr, "\n[Vyn PANIC] ");
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fprintf(stderr, "\n");
    fflush(stderr);
    abort();
}

void vyn_oom(void) {
    vyn_panic("out of memory");
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Memory allocator
 * ═══════════════════════════════════════════════════════════════════════════ */

static void *_sys_alloc(VynAllocator *self, size_t size) {
    (void)self;
    return malloc(size);
}

static void *_sys_realloc(VynAllocator *self, void *ptr, size_t old_size, size_t new_size) {
    (void)self; (void)old_size;
    return realloc(ptr, new_size);
}

static void _sys_free(VynAllocator *self, void *ptr, size_t size) {
    (void)self; (void)size;
    free(ptr);
}

static VynAllocator _default_alloc = {
    .alloc   = _sys_alloc,
    .realloc = _sys_realloc,
    .free    = _sys_free,
    .ctx     = NULL
};

VynAllocator *vyn_default_allocator(void) { return &_default_alloc; }

void *vyn_alloc(size_t size) {
    void *p = malloc(size);
    if (!p && size > 0) vyn_oom();
    return p;
}

void *vyn_zalloc(size_t size) {
    void *p = calloc(1, size);
    if (!p && size > 0) vyn_oom();
    return p;
}

void *vyn_realloc(void *ptr, size_t new_size) {
    void *p = realloc(ptr, new_size);
    if (!p && new_size > 0) vyn_oom();
    return p;
}

void vyn_free(void *ptr) {
    free(ptr);
}

char *vyn_strdup(const char *s) {
    if (!s) return NULL;
    size_t len = strlen(s) + 1;
    char *copy = (char *)vyn_alloc(len);
    memcpy(copy, s, len);
    return copy;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Garbage Collector  (mark-and-sweep)
 * ═══════════════════════════════════════════════════════════════════════════ */

VynGc *vyn_gc = NULL;

#define GC_MARK_BIT   (1u << 0)
#define GC_COLOUR_MASK (~GC_MARK_BIT)

void vyn_gc_init(size_t initial_threshold) {
    vyn_gc = (VynGc *)vyn_zalloc(sizeof(VynGc));
    vyn_gc->threshold  = initial_threshold > 0 ? initial_threshold : (1u << 20); /* 1 MB */
    vyn_gc->root_cap   = 64;
    vyn_gc->roots      = (void **)vyn_alloc(vyn_gc->root_cap * sizeof(void *));
}

void vyn_gc_shutdown(void) {
    if (!vyn_gc) return;
    /* Run finalizers and free all objects */
    VynGcHeader *obj = vyn_gc->head;
    while (obj) {
        VynGcHeader *next = obj->next;
        if (obj->finalizer) obj->finalizer(obj);
        free(obj);
        obj = next;
    }
    free(vyn_gc->roots);
    free(vyn_gc);
    vyn_gc = NULL;
}

void *vyn_gc_alloc(size_t size, uint32_t type_id, void (*finalizer)(void *)) {
    if (!vyn_gc) vyn_gc_init(0);

    /* Trigger collection if above threshold */
    if (vyn_gc->allocated + size > vyn_gc->threshold) {
        vyn_gc_collect();
    }

    VynGcHeader *hdr = (VynGcHeader *)vyn_zalloc(sizeof(VynGcHeader) + size);
    hdr->type_id    = type_id;
    hdr->size       = size;
    hdr->finalizer  = finalizer;
    hdr->next       = vyn_gc->head;
    vyn_gc->head    = hdr;
    vyn_gc->allocated += size + sizeof(VynGcHeader);

    /* Return pointer past the header */
    return (void *)(hdr + 1);
}

void vyn_gc_push_root(void **ref) {
    if (!vyn_gc) vyn_gc_init(0);
    if (vyn_gc->root_count >= vyn_gc->root_cap) {
        vyn_gc->root_cap *= 2;
        vyn_gc->roots = (void **)vyn_realloc(vyn_gc->roots,
                                              vyn_gc->root_cap * sizeof(void *));
    }
    vyn_gc->roots[vyn_gc->root_count++] = ref;
}

void vyn_gc_pop_root(void **ref) {
    if (!vyn_gc || vyn_gc->root_count == 0) return;
    /* Linear scan from the end */
    for (size_t i = vyn_gc->root_count; i-- > 0; ) {
        if (vyn_gc->roots[i] == ref) {
            vyn_gc->roots[i] = vyn_gc->roots[--vyn_gc->root_count];
            return;
        }
    }
}

/* Mark object and all objects reachable from it */
static void _gc_mark(VynGcHeader *hdr) {
    if (!hdr || (hdr->mark & GC_MARK_BIT)) return;
    hdr->mark |= GC_MARK_BIT;

    /* Type-specific tracing */
    switch (hdr->type_id) {
        case VYN_TID_VEC: {
            VynVec *v = (VynVec *)(hdr + 1);
            for (size_t i = 0; i < v->len; i++) {
                if (v->data[i]) {
                    VynGcHeader *child = (VynGcHeader *)v->data[i] - 1;
                    _gc_mark(child);
                }
            }
            break;
        }
        case VYN_TID_HASHMAP: {
            VynHashMap *m = (VynHashMap *)(hdr + 1);
            for (size_t i = 0; i < m->cap; i++) {
                if (m->entries[i].occupied && !m->entries[i].deleted) {
                    if (m->entries[i].key) {
                        _gc_mark((VynGcHeader *)m->entries[i].key - 1);
                    }
                    if (m->entries[i].value) {
                        _gc_mark((VynGcHeader *)m->entries[i].value - 1);
                    }
                }
            }
            break;
        }
        case VYN_TID_TUPLE: {
            VynTuple *t = (VynTuple *)(hdr + 1);
            for (size_t i = 0; i < t->arity; i++) {
                if (t->elems[i]) {
                    _gc_mark((VynGcHeader *)t->elems[i] - 1);
                }
            }
            break;
        }
        case VYN_TID_CLOSURE: {
            VynClosure *cl = (VynClosure *)(hdr + 1);
            if (cl->env) _gc_mark((VynGcHeader *)cl->env - 1);
            break;
        }
        default: break;
    }
}

void vyn_gc_collect(void) {
    if (!vyn_gc) return;

    /* Clear all marks */
    for (VynGcHeader *obj = vyn_gc->head; obj; obj = obj->next)
        obj->mark &= ~GC_MARK_BIT;

    /* Mark from roots */
    for (size_t i = 0; i < vyn_gc->root_count; i++) {
        void *ref = *(void **)vyn_gc->roots[i];
        if (ref) {
            VynGcHeader *hdr = (VynGcHeader *)ref - 1;
            _gc_mark(hdr);
        }
    }

    /* Sweep: free unmarked objects */
    VynGcHeader **pp = &vyn_gc->head;
    while (*pp) {
        VynGcHeader *obj = *pp;
        if (!(obj->mark & GC_MARK_BIT)) {
            *pp = obj->next;
            if (obj->finalizer) obj->finalizer(obj + 1);
            vyn_gc->allocated -= obj->size + sizeof(VynGcHeader);
            free(obj);
        } else {
            pp = &obj->next;
        }
    }

    vyn_gc->collections++;
    /* Grow threshold if heap is still large */
    if (vyn_gc->allocated > vyn_gc->threshold / 2)
        vyn_gc->threshold *= 2;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  VynStr  (dynamic string with SSO)
 * ═══════════════════════════════════════════════════════════════════════════ */

static void _str_finalizer(void *obj) {
    VynStr *s = (VynStr *)obj;
    if (s->cap > VYN_STR_SSO_CAP && s->data.heap) {
        free(s->data.heap);
        s->data.heap = NULL;
    }
}

VynStr *vyn_str_new(void) {
    VynStr *s = (VynStr *)vyn_gc_alloc(sizeof(VynStr), VYN_TID_STRING, _str_finalizer);
    s->len = 0;
    s->cap = 0;  /* SSO mode */
    s->data.sso[0] = '\0';
    return s;
}

VynStr *vyn_str_from(const char *cstr) {
    if (!cstr) return vyn_str_new();
    return vyn_str_from_n(cstr, strlen(cstr));
}

VynStr *vyn_str_from_n(const char *buf, size_t len) {
    VynStr *s = (VynStr *)vyn_gc_alloc(sizeof(VynStr), VYN_TID_STRING, _str_finalizer);
    s->len = len;
    if (len <= VYN_STR_SSO_CAP) {
        s->cap = 0;
        memcpy(s->data.sso, buf, len);
        s->data.sso[len] = '\0';
    } else {
        s->cap = len + 1;
        s->data.heap = (char *)vyn_alloc(s->cap);
        memcpy(s->data.heap, buf, len);
        s->data.heap[len] = '\0';
    }
    return s;
}

VynStr *vyn_str_from_i32(vyn_i32 n) {
    char buf[32];
    int  len = snprintf(buf, sizeof(buf), "%d", n);
    return vyn_str_from_n(buf, (size_t)len);
}

VynStr *vyn_str_from_f32(vyn_f32 f) {
    char buf[64];
    int  len = snprintf(buf, sizeof(buf), "%g", (double)f);
    return vyn_str_from_n(buf, (size_t)len);
}

VynStr *vyn_str_from_f64(vyn_f64 f) {
    char buf[64];
    int  len = snprintf(buf, sizeof(buf), "%g", f);
    return vyn_str_from_n(buf, (size_t)len);
}

VynStr *vyn_str_from_char(vyn_char ch) {
    char buf[5] = {0};
    /* Encode as UTF-8 */
    if (ch < 0x80) {
        buf[0] = (char)ch;
        return vyn_str_from_n(buf, 1);
    } else if (ch < 0x800) {
        buf[0] = (char)(0xC0 | (ch >> 6));
        buf[1] = (char)(0x80 | (ch & 0x3F));
        return vyn_str_from_n(buf, 2);
    } else if (ch < 0x10000) {
        buf[0] = (char)(0xE0 | (ch >> 12));
        buf[1] = (char)(0x80 | ((ch >> 6) & 0x3F));
        buf[2] = (char)(0x80 | (ch & 0x3F));
        return vyn_str_from_n(buf, 3);
    } else {
        buf[0] = (char)(0xF0 | (ch >> 18));
        buf[1] = (char)(0x80 | ((ch >> 12) & 0x3F));
        buf[2] = (char)(0x80 | ((ch >> 6)  & 0x3F));
        buf[3] = (char)(0x80 | (ch & 0x3F));
        return vyn_str_from_n(buf, 4);
    }
}

VynStr *vyn_str_clone(const VynStr *s) {
    return vyn_str_from_n(vyn_str_cstr(s), s->len);
}

const char *vyn_str_cstr(const VynStr *s) {
    if (!s) return "";
    return (s->cap == 0) ? s->data.sso : s->data.heap;
}

size_t vyn_str_len(const VynStr *s) { return s ? s->len : 0; }
bool   vyn_str_empty(const VynStr *s) { return !s || s->len == 0; }

vyn_char vyn_str_char_at(const VynStr *s, size_t idx) {
    const char *p = vyn_str_cstr(s);
    if (idx >= s->len) return 0;
    return (vyn_char)(unsigned char)p[idx];
}

void vyn_str_reserve(VynStr *s, size_t cap) {
    if (cap <= VYN_STR_SSO_CAP) return;
    if (s->cap >= cap) return;
    char *new_heap = (char *)vyn_alloc(cap + 1);
    const char *src = vyn_str_cstr(s);
    memcpy(new_heap, src, s->len);
    new_heap[s->len] = '\0';
    if (s->cap > VYN_STR_SSO_CAP) free(s->data.heap);
    s->data.heap = new_heap;
    s->cap = cap;
}

void vyn_str_push_char(VynStr *s, vyn_char ch) {
    /* ASCII fast path */
    if (ch < 0x80) {
        if (s->len + 1 > (s->cap == 0 ? VYN_STR_SSO_CAP : s->cap))
            vyn_str_reserve(s, VYN_MAX(s->len * 2 + 2, 32));
        char *dst = (s->cap == 0) ? s->data.sso : s->data.heap;
        dst[s->len++] = (char)ch;
        dst[s->len]   = '\0';
    } else {
        VynStr *tmp = vyn_str_from_char(ch);
        vyn_str_push_str(s, tmp);
    }
}

void vyn_str_push_cstr(VynStr *s, const char *cstr) {
    if (!cstr || !*cstr) return;
    size_t add = strlen(cstr);
    size_t needed = s->len + add;
    if (needed > (s->cap == 0 ? VYN_STR_SSO_CAP : s->cap))
        vyn_str_reserve(s, VYN_MAX(needed * 2, 32));
    char *dst = (s->cap == 0) ? s->data.sso : s->data.heap;
    memcpy(dst + s->len, cstr, add + 1);
    s->len = needed;
}

void vyn_str_push_str(VynStr *s, const VynStr *other) {
    vyn_str_push_cstr(s, vyn_str_cstr(other));
}

void vyn_str_clear(VynStr *s) {
    s->len = 0;
    char *dst = (s->cap == 0) ? s->data.sso : s->data.heap;
    dst[0] = '\0';
}

VynStr *vyn_str_concat(const VynStr *a, const VynStr *b) {
    size_t  la   = vyn_str_len(a);
    size_t  lb   = vyn_str_len(b);
    VynStr *out  = (VynStr *)vyn_gc_alloc(sizeof(VynStr), VYN_TID_STRING, _str_finalizer);
    out->len = la + lb;
    if (out->len <= VYN_STR_SSO_CAP) {
        out->cap = 0;
        memcpy(out->data.sso,      vyn_str_cstr(a), la);
        memcpy(out->data.sso + la, vyn_str_cstr(b), lb);
        out->data.sso[out->len] = '\0';
    } else {
        out->cap = out->len + 1;
        out->data.heap = (char *)vyn_alloc(out->cap);
        memcpy(out->data.heap,      vyn_str_cstr(a), la);
        memcpy(out->data.heap + la, vyn_str_cstr(b), lb);
        out->data.heap[out->len] = '\0';
    }
    return out;
}

VynStr *vyn_str_slice(const VynStr *s, size_t start, size_t end) {
    const char *p = vyn_str_cstr(s);
    if (start >= s->len) return vyn_str_new();
    if (end   >  s->len) end = s->len;
    if (start >= end)    return vyn_str_new();
    return vyn_str_from_n(p + start, end - start);
}

VynStr *vyn_str_upper(const VynStr *s) {
    VynStr     *out = vyn_str_clone(s);
    char       *p   = (out->cap == 0) ? out->data.sso : out->data.heap;
    for (size_t i = 0; i < out->len; i++)
        if (p[i] >= 'a' && p[i] <= 'z') p[i] -= 32;
    return out;
}

VynStr *vyn_str_lower(const VynStr *s) {
    VynStr     *out = vyn_str_clone(s);
    char       *p   = (out->cap == 0) ? out->data.sso : out->data.heap;
    for (size_t i = 0; i < out->len; i++)
        if (p[i] >= 'A' && p[i] <= 'Z') p[i] += 32;
    return out;
}

VynStr *vyn_str_trim(const VynStr *s) {
    const char *p   = vyn_str_cstr(s);
    size_t      len = s->len;
    size_t      lo  = 0;
    size_t      hi  = len;
    while (lo < hi && (p[lo] == ' ' || p[lo] == '\t' || p[lo] == '\n' || p[lo] == '\r')) lo++;
    while (hi > lo && (p[hi-1] == ' ' || p[hi-1] == '\t' || p[hi-1] == '\n' || p[hi-1] == '\r')) hi--;
    return vyn_str_from_n(p + lo, hi - lo);
}

VynStr *vyn_str_repeat(const VynStr *s, size_t n) {
    if (n == 0 || s->len == 0) return vyn_str_new();
    size_t  total = s->len * n;
    VynStr *out   = (VynStr *)vyn_gc_alloc(sizeof(VynStr), VYN_TID_STRING, _str_finalizer);
    out->len = total;
    if (total <= VYN_STR_SSO_CAP) {
        out->cap = 0;
        for (size_t i = 0; i < n; i++)
            memcpy(out->data.sso + i * s->len, vyn_str_cstr(s), s->len);
        out->data.sso[total] = '\0';
    } else {
        out->cap = total + 1;
        out->data.heap = (char *)vyn_alloc(out->cap);
        for (size_t i = 0; i < n; i++)
            memcpy(out->data.heap + i * s->len, vyn_str_cstr(s), s->len);
        out->data.heap[total] = '\0';
    }
    return out;
}

VynStr *vyn_str_replace(const VynStr *s, const char *from, const char *to) {
    const char *src    = vyn_str_cstr(s);
    size_t      from_l = strlen(from);
    size_t      to_l   = strlen(to);
    if (from_l == 0) return vyn_str_clone(s);

    VynStr *out = vyn_str_new();
    const char *p = src;
    while (*p) {
        if (strncmp(p, from, from_l) == 0) {
            vyn_str_push_cstr(out, to);
            p += from_l;
        } else {
            vyn_str_push_char(out, (vyn_char)(unsigned char)*p);
            p++;
        }
    }
    return out;
}

bool vyn_str_contains(const VynStr *s, const char *needle) {
    return strstr(vyn_str_cstr(s), needle) != NULL;
}

bool vyn_str_starts_with(const VynStr *s, const char *prefix) {
    size_t plen = strlen(prefix);
    if (plen > s->len) return false;
    return strncmp(vyn_str_cstr(s), prefix, plen) == 0;
}

bool vyn_str_ends_with(const VynStr *s, const char *suffix) {
    size_t slen = strlen(suffix);
    if (slen > s->len) return false;
    return strncmp(vyn_str_cstr(s) + s->len - slen, suffix, slen) == 0;
}

vyn_i32 vyn_str_find(const VynStr *s, const char *needle) {
    const char *p = strstr(vyn_str_cstr(s), needle);
    if (!p) return -1;
    return (vyn_i32)(p - vyn_str_cstr(s));
}

vyn_i32 vyn_str_parse_i32(const VynStr *s) {
    return (vyn_i32)strtol(vyn_str_cstr(s), NULL, 10);
}

vyn_f32 vyn_str_parse_f32(const VynStr *s) {
    return (vyn_f32)strtod(vyn_str_cstr(s), NULL);
}

int vyn_str_cmp(const VynStr *a, const VynStr *b) {
    return strcmp(vyn_str_cstr(a), vyn_str_cstr(b));
}

bool vyn_str_eq(const VynStr *a, const VynStr *b) {
    if (a->len != b->len) return false;
    return memcmp(vyn_str_cstr(a), vyn_str_cstr(b), a->len) == 0;
}

VynStr *vyn_str_fmt(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    char   buf[256];
    int    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (len < 0) return vyn_str_new();
    if ((size_t)len < sizeof(buf)) return vyn_str_from_n(buf, (size_t)len);
    /* Large string: alloc on heap */
    va_start(ap, fmt);
    char *dyn = (char *)vyn_alloc((size_t)len + 1);
    vsnprintf(dyn, (size_t)len + 1, fmt, ap);
    va_end(ap);
    VynStr *s = vyn_str_from_n(dyn, (size_t)len);
    free(dyn);
    return s;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  VynVec  (dynamic array of void*)
 * ═══════════════════════════════════════════════════════════════════════════ */

static void _vec_finalizer(void *obj) {
    VynVec *v = (VynVec *)obj;
    if (v->data) { free(v->data); v->data = NULL; }
}

VynVec *vyn_vec_new(uint32_t elem_type) {
    return vyn_vec_with_cap(elem_type, 8);
}

VynVec *vyn_vec_with_cap(uint32_t elem_type, size_t cap) {
    VynVec *v = (VynVec *)vyn_gc_alloc(sizeof(VynVec), VYN_TID_VEC, _vec_finalizer);
    v->elem_type = elem_type;
    v->cap  = cap > 0 ? cap : 1;
    v->len  = 0;
    v->data = (void **)vyn_alloc(v->cap * sizeof(void *));
    return v;
}

VynVec *vyn_vec_clone(const VynVec *v) {
    VynVec *out = vyn_vec_with_cap(v->elem_type, v->len);
    out->len = v->len;
    memcpy(out->data, v->data, v->len * sizeof(void *));
    return out;
}

void *vyn_vec_get(const VynVec *v, size_t idx) {
    if (idx >= v->len) vyn_panic("vec index %zu out of bounds (len=%zu)", idx, v->len);
    return v->data[idx];
}

void *vyn_vec_get_unchecked(const VynVec *v, size_t idx) { return v->data[idx]; }
size_t vyn_vec_len(const VynVec *v)   { return v->len; }
bool   vyn_vec_empty(const VynVec *v) { return v->len == 0; }
void  *vyn_vec_first(const VynVec *v) { return v->len > 0 ? v->data[0]         : NULL; }
void  *vyn_vec_last (const VynVec *v) { return v->len > 0 ? v->data[v->len - 1]: NULL; }

void vyn_vec_reserve(VynVec *v, size_t cap) {
    if (cap <= v->cap) return;
    v->data = (void **)vyn_realloc(v->data, cap * sizeof(void *));
    v->cap  = cap;
}

void vyn_vec_push(VynVec *v, void *elem) {
    if (v->len >= v->cap) vyn_vec_reserve(v, v->cap * 2);
    v->data[v->len++] = elem;
}

void *vyn_vec_pop(VynVec *v) {
    if (v->len == 0) vyn_panic("pop from empty vec");
    return v->data[--v->len];
}

void vyn_vec_set(VynVec *v, size_t idx, void *elem) {
    if (idx >= v->len) vyn_panic("vec set: index out of bounds");
    v->data[idx] = elem;
}

void vyn_vec_insert(VynVec *v, size_t idx, void *elem) {
    if (idx > v->len) idx = v->len;
    if (v->len >= v->cap) vyn_vec_reserve(v, v->cap * 2);
    memmove(v->data + idx + 1, v->data + idx, (v->len - idx) * sizeof(void *));
    v->data[idx] = elem;
    v->len++;
}

void *vyn_vec_remove(VynVec *v, size_t idx) {
    if (idx >= v->len) vyn_panic("vec remove: index out of bounds");
    void *val = v->data[idx];
    memmove(v->data + idx, v->data + idx + 1, (v->len - idx - 1) * sizeof(void *));
    v->len--;
    return val;
}

void vyn_vec_clear(VynVec *v) { v->len = 0; }

void vyn_vec_shrink(VynVec *v) {
    if (v->len < v->cap) {
        v->data = (void **)vyn_realloc(v->data, (v->len + 1) * sizeof(void *));
        v->cap  = v->len + 1;
    }
}

vyn_i32 vyn_vec_find(const VynVec *v, void *elem, int (*cmp)(const void *, const void *)) {
    for (size_t i = 0; i < v->len; i++)
        if (cmp(v->data[i], elem) == 0) return (vyn_i32)i;
    return -1;
}

bool vyn_vec_contains(const VynVec *v, void *elem, int (*cmp)(const void *, const void *)) {
    return vyn_vec_find(v, elem, cmp) >= 0;
}

void vyn_vec_foreach(VynVec *v, VynVecIterFn fn, void *ud) {
    for (size_t i = 0; i < v->len; i++)
        if (!fn(v->data[i], ud)) break;
}

/* Wrapper for qsort (stores comparator in thread-local) */
static int (*_sort_cmp)(const void *, const void *) = NULL;
static int _sort_wrapper(const void *a, const void *b) {
    return _sort_cmp(*(void **)a, *(void **)b);
}

void vyn_vec_sort(VynVec *v, int (*cmp)(const void *, const void *)) {
    _sort_cmp = cmp;
    qsort(v->data, v->len, sizeof(void *), _sort_wrapper);
    _sort_cmp = NULL;
}

VynVec *vyn_vec_slice(const VynVec *v, size_t start, size_t end) {
    if (start > v->len) start = v->len;
    if (end   > v->len) end   = v->len;
    if (start > end)    end   = start;
    VynVec *out = vyn_vec_with_cap(v->elem_type, end - start);
    out->len = end - start;
    memcpy(out->data, v->data + start, out->len * sizeof(void *));
    return out;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  VynHashMap  (open-addressing, Robin Hood probing)
 * ═══════════════════════════════════════════════════════════════════════════ */

#define MAP_INITIAL_CAP  16
#define MAP_LOAD_MAX     0.72

static void _map_finalizer(void *obj) {
    VynHashMap *m = (VynHashMap *)obj;
    if (m->entries) { free(m->entries); m->entries = NULL; }
}

uint64_t vyn_fnv1a(const uint8_t *buf, size_t len) {
    uint64_t h = 14695981039346656037ULL;
    for (size_t i = 0; i < len; i++) {
        h ^= buf[i];
        h *= 1099511628211ULL;
    }
    return h;
}

uint64_t vyn_hash_str(const void *key) {
    const VynStr *s = (const VynStr *)key;
    return vyn_fnv1a((const uint8_t *)vyn_str_cstr(s), s->len);
}

uint64_t vyn_hash_i32(const void *key) {
    vyn_i32 v = *(const vyn_i32 *)key;
    return vyn_fnv1a((const uint8_t *)&v, sizeof(v));
}

uint64_t vyn_hash_i64(const void *key) {
    vyn_i64 v = *(const vyn_i64 *)key;
    return vyn_fnv1a((const uint8_t *)&v, sizeof(v));
}

uint64_t vyn_hash_ptr(const void *key) {
    uintptr_t v = (uintptr_t)key;
    return vyn_fnv1a((const uint8_t *)&v, sizeof(v));
}

int vyn_eq_str(const void *a, const void *b) {
    return vyn_str_eq((const VynStr *)a, (const VynStr *)b) ? 0 : 1;
}
int vyn_eq_i32(const void *a, const void *b) {
    return *(const vyn_i32 *)a == *(const vyn_i32 *)b ? 0 : 1;
}
int vyn_eq_i64(const void *a, const void *b) {
    return *(const vyn_i64 *)a == *(const vyn_i64 *)b ? 0 : 1;
}
int vyn_eq_ptr(const void *a, const void *b) {
    return a == b ? 0 : 1;
}

static VynHashMap *_map_alloc(uint32_t key_type, uint32_t val_type, size_t cap,
                               uint64_t (*hash_fn)(const void *),
                               int      (*eq_fn)  (const void *, const void *)) {
    VynHashMap *m = (VynHashMap *)vyn_gc_alloc(sizeof(VynHashMap), VYN_TID_HASHMAP, _map_finalizer);
    m->cap       = cap;
    m->len       = 0;
    m->tombstones= 0;
    m->key_type  = key_type;
    m->val_type  = val_type;
    m->hash_fn   = hash_fn;
    m->eq_fn     = eq_fn;
    m->entries   = (VynHashEntry *)vyn_zalloc(cap * sizeof(VynHashEntry));
    return m;
}

VynHashMap *vyn_map_new(uint32_t key_type, uint32_t val_type,
                         uint64_t (*hash_fn)(const void *),
                         int      (*eq_fn)  (const void *, const void *)) {
    return _map_alloc(key_type, val_type, MAP_INITIAL_CAP, hash_fn, eq_fn);
}

VynHashMap *vyn_map_new_str(void) {
    return vyn_map_new(VYN_TID_STRING, 0, vyn_hash_str, vyn_eq_str);
}

VynHashMap *vyn_map_new_i32(void) {
    return vyn_map_new(VYN_TID_STRING, 0, vyn_hash_i32, vyn_eq_i32);
}

static size_t _map_probe(const VynHashMap *m, uint64_t hash) {
    return (size_t)(hash & (m->cap - 1));
}

static void _map_grow(VynHashMap *m) {
    size_t     old_cap  = m->cap;
    VynHashEntry *old_e = m->entries;
    m->cap      = old_cap * 2;
    m->entries  = (VynHashEntry *)vyn_zalloc(m->cap * sizeof(VynHashEntry));
    m->len      = 0;
    m->tombstones = 0;
    for (size_t i = 0; i < old_cap; i++) {
        if (old_e[i].occupied && !old_e[i].deleted)
            vyn_map_insert(m, old_e[i].key, old_e[i].value);
    }
    free(old_e);
}

bool vyn_map_insert(VynHashMap *m, void *key, void *value) {
    if ((double)(m->len + m->tombstones) / (double)m->cap > MAP_LOAD_MAX)
        _map_grow(m);

    uint64_t hash = m->hash_fn(key);
    size_t   idx  = _map_probe(m, hash);
    for (size_t step = 0; step < m->cap; step++) {
        VynHashEntry *e = &m->entries[(idx + step) & (m->cap - 1)];
        if (!e->occupied || e->deleted) {
            if (!e->occupied) m->len++;
            else if (e->deleted) { m->tombstones--; m->len++; }
            e->hash     = hash;
            e->key      = key;
            e->value    = value;
            e->occupied = true;
            e->deleted  = false;
            return true;
        }
        if (e->hash == hash && m->eq_fn(e->key, key) == 0) {
            e->value = value;
            return false;
        }
    }
    _map_grow(m);
    return vyn_map_insert(m, key, value);
}

void *vyn_map_get(const VynHashMap *m, const void *key) {
    uint64_t hash = m->hash_fn(key);
    size_t   idx  = _map_probe(m, hash);
    for (size_t step = 0; step < m->cap; step++) {
        const VynHashEntry *e = &m->entries[(idx + step) & (m->cap - 1)];
        if (!e->occupied) return NULL;
        if (!e->deleted && e->hash == hash && m->eq_fn(e->key, key) == 0)
            return e->value;
    }
    return NULL;
}

bool vyn_map_contains(const VynHashMap *m, const void *key) {
    return vyn_map_get(m, key) != NULL;
}

bool vyn_map_remove(VynHashMap *m, const void *key) {
    uint64_t hash = m->hash_fn(key);
    size_t   idx  = _map_probe(m, hash);
    for (size_t step = 0; step < m->cap; step++) {
        VynHashEntry *e = &m->entries[(idx + step) & (m->cap - 1)];
        if (!e->occupied) return false;
        if (!e->deleted && e->hash == hash && m->eq_fn(e->key, key) == 0) {
            e->deleted = true;
            m->tombstones++;
            m->len--;
            return true;
        }
    }
    return false;
}

size_t vyn_map_len  (const VynHashMap *m) { return m->len; }
void   vyn_map_clear(VynHashMap *m) {
    memset(m->entries, 0, m->cap * sizeof(VynHashEntry));
    m->len = m->tombstones = 0;
}

void vyn_map_foreach(VynHashMap *m, VynMapIterFn fn, void *ud) {
    for (size_t i = 0; i < m->cap; i++) {
        if (m->entries[i].occupied && !m->entries[i].deleted)
            if (!fn(m->entries[i].key, m->entries[i].value, ud)) break;
    }
}

typedef struct { VynVec *out; bool want_keys; } _MapCollect;
static bool _collect_cb(void *k, void *v, void *ud) {
    _MapCollect *c = (_MapCollect *)ud;
    vyn_vec_push(c->out, c->want_keys ? k : v);
    return true;
}

VynVec *vyn_map_keys(const VynHashMap *m) {
    VynVec *v = vyn_vec_with_cap(m->key_type, m->len);
    _MapCollect c = { v, true };
    vyn_map_foreach((VynHashMap *)m, _collect_cb, &c);
    return v;
}

VynVec *vyn_map_values(const VynHashMap *m) {
    VynVec *v = vyn_vec_with_cap(m->val_type, m->len);
    _MapCollect c = { v, false };
    vyn_map_foreach((VynHashMap *)m, _collect_cb, &c);
    return v;
}

void vyn_map_free(VynHashMap *m) {
    if (m->entries) { free(m->entries); m->entries = NULL; }
}

VynHashMap *vyn_map_clone(const VynHashMap *m) {
    VynHashMap *out = _map_alloc(m->key_type, m->val_type,
                                  m->cap, m->hash_fn, m->eq_fn);
    for (size_t i = 0; i < m->cap; i++) {
        if (m->entries[i].occupied && !m->entries[i].deleted)
            vyn_map_insert(out, m->entries[i].key, m->entries[i].value);
    }
    return out;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  VynTuple
 * ═══════════════════════════════════════════════════════════════════════════ */

VynTuple *vyn_tuple_new(size_t arity) {
    size_t    sz  = sizeof(VynTuple) + (arity > 1 ? (arity - 1) : 0) * sizeof(void *);
    VynTuple *t   = (VynTuple *)vyn_gc_alloc(sz, VYN_TID_TUPLE, NULL);
    t->arity = arity;
    memset(t->elems, 0, arity * sizeof(void *));
    return t;
}

void *vyn_tuple_get(const VynTuple *t, size_t idx) {
    if (idx >= t->arity) vyn_panic("tuple index %zu out of bounds (arity=%zu)", idx, t->arity);
    return t->elems[idx];
}

void vyn_tuple_set(VynTuple *t, size_t idx, void *val) {
    if (idx >= t->arity) vyn_panic("tuple set: index out of bounds");
    t->elems[idx] = val;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  VynClosure
 * ═══════════════════════════════════════════════════════════════════════════ */

VynClosure *vyn_closure_new(VynFnPtr fn, void *env, size_t arity) {
    VynClosure *cl = (VynClosure *)vyn_gc_alloc(sizeof(VynClosure), VYN_TID_CLOSURE, NULL);
    cl->fn    = fn;
    cl->env   = env;
    cl->arity = arity;
    return cl;
}

void *vyn_closure_call(VynClosure *cl, void **args, size_t argc) {
    return cl->fn(args, argc, cl->env);
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  I/O
 * ═══════════════════════════════════════════════════════════════════════════ */

void vyn_io_print_str  (const VynStr *s) { fputs(vyn_str_cstr(s), stdout); }
void vyn_io_println_str(const VynStr *s) { puts(vyn_str_cstr(s)); }
void vyn_io_print_cstr (const char   *s) { fputs(s, stdout); }
void vyn_io_print_i32  (vyn_i32 n)       { printf("%d",  n); }
void vyn_io_print_i64  (vyn_i64 n)       { printf("%lld",(long long)n); }
void vyn_io_print_f32  (vyn_f32 f)       { printf("%g",  (double)f); }
void vyn_io_print_f64  (vyn_f64 f)       { printf("%g",  f); }
void vyn_io_print_bool (vyn_bool b)      { fputs(b ? "true" : "false", stdout); }
void vyn_io_print_char (vyn_char c) {
    VynStr *s = vyn_str_from_char(c);
    fputs(vyn_str_cstr(s), stdout);
}

void vyn_io_flush(void) { fflush(stdout); }

void vyn_io_eprint(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fflush(stderr);
}

VynStr *vyn_io_readln(void) {
    char   buf[4096];
    if (!fgets(buf, sizeof(buf), stdin)) return vyn_str_new();
    size_t len = strlen(buf);
    if (len > 0 && buf[len-1] == '\n') buf[--len] = '\0';
    return vyn_str_from_n(buf, len);
}

vyn_i32 vyn_io_read_i32(void) {
    vyn_i32 n = 0;
    scanf("%d", &n);
    return n;
}

vyn_f32 vyn_io_read_f32(void) {
    float f = 0.0f;
    scanf("%f", &f);
    return f;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Math
 * ═══════════════════════════════════════════════════════════════════════════ */

vyn_f32 vyn_math_abs_f32(vyn_f32 x)               { return fabsf(x); }
vyn_f64 vyn_math_abs_f64(vyn_f64 x)               { return fabs (x); }
vyn_f32 vyn_math_sqrt   (vyn_f32 x)               { return sqrtf(x); }
vyn_f32 vyn_math_pow    (vyn_f32 b, vyn_f32 e)    { return powf (b, e); }
vyn_f32 vyn_math_sin    (vyn_f32 x)               { return sinf (x); }
vyn_f32 vyn_math_cos    (vyn_f32 x)               { return cosf (x); }
vyn_f32 vyn_math_tan    (vyn_f32 x)               { return tanf (x); }
vyn_f32 vyn_math_floor  (vyn_f32 x)               { return floorf(x); }
vyn_f32 vyn_math_ceil   (vyn_f32 x)               { return ceilf(x); }
vyn_f32 vyn_math_round  (vyn_f32 x)               { return roundf(x); }
vyn_f32 vyn_math_log    (vyn_f32 x)               { return logf  (x); }
vyn_f32 vyn_math_log2   (vyn_f32 x)               { return log2f (x); }
vyn_f32 vyn_math_log10  (vyn_f32 x)               { return log10f(x); }
vyn_f32 vyn_math_clamp  (vyn_f32 v, vyn_f32 lo, vyn_f32 hi) { return v < lo ? lo : v > hi ? hi : v; }
vyn_f32 vyn_math_lerp   (vyn_f32 a, vyn_f32 b, vyn_f32 t)   { return a + (b - a) * t; }
vyn_f32 vyn_math_min_f32(vyn_f32 a, vyn_f32 b) { return a < b ? a : b; }
vyn_f32 vyn_math_max_f32(vyn_f32 a, vyn_f32 b) { return a > b ? a : b; }
vyn_i32 vyn_math_min_i32(vyn_i32 a, vyn_i32 b) { return a < b ? a : b; }
vyn_i32 vyn_math_max_i32(vyn_i32 a, vyn_i32 b) { return a > b ? a : b; }

/* ═══════════════════════════════════════════════════════════════════════════
 *  System / OS
 * ═══════════════════════════════════════════════════════════════════════════ */

void vyn_sys_sleep_ms(vyn_i32 ms) {
#ifdef _WIN32
    Sleep((DWORD)ms);
#else
    struct timespec ts = { ms / 1000, (ms % 1000) * 1000000L };
    nanosleep(&ts, NULL);
#endif
}

void vyn_sys_sleep_us(vyn_i64 us) {
#ifdef _WIN32
    Sleep((DWORD)(us / 1000));
#else
    struct timespec ts = { us / 1000000, (us % 1000000) * 1000L };
    nanosleep(&ts, NULL);
#endif
}

vyn_i64 vyn_sys_now_ms(void) {
#ifdef _WIN32
    FILETIME ft;
    GetSystemTimeAsFileTime(&ft);
    ULARGE_INTEGER ui;
    ui.LowPart  = ft.dwLowDateTime;
    ui.HighPart = ft.dwHighDateTime;
    return (vyn_i64)((ui.QuadPart - 116444736000000000ULL) / 10000);
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (vyn_i64)tv.tv_sec * 1000LL + tv.tv_usec / 1000;
#endif
}

vyn_i64 vyn_sys_now_us(void) {
#ifdef _WIN32
    FILETIME ft;
    GetSystemTimeAsFileTime(&ft);
    ULARGE_INTEGER ui;
    ui.LowPart  = ft.dwLowDateTime;
    ui.HighPart = ft.dwHighDateTime;
    return (vyn_i64)((ui.QuadPart - 116444736000000000ULL) / 10);
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (vyn_i64)tv.tv_sec * 1000000LL + tv.tv_usec;
#endif
}

VynStr *vyn_sys_env(const char *name) {
    const char *v = getenv(name);
    return v ? vyn_str_from(v) : vyn_str_new();
}

VynStr *vyn_sys_cwd(void) {
    char buf[4096];
#ifdef _WIN32
    if (!_getcwd(buf, sizeof(buf))) return vyn_str_new();
#else
    if (!getcwd(buf, sizeof(buf))) return vyn_str_new();
#endif
    return vyn_str_from(buf);
}

void vyn_sys_exit(vyn_i32 code) { exit((int)code); }

/* ═══════════════════════════════════════════════════════════════════════════
 *  File system
 * ═══════════════════════════════════════════════════════════════════════════ */

VynStr *vyn_fs_read(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return vyn_str_new();
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz <= 0) { fclose(f); return vyn_str_new(); }
    char *buf = (char *)vyn_alloc((size_t)sz + 1);
    size_t n  = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[n] = '\0';
    VynStr *s = vyn_str_from_n(buf, n);
    free(buf);
    return s;
}

bool vyn_fs_write(const char *path, const VynStr *content) {
    return vyn_fs_write_cstr(path, vyn_str_cstr(content));
}

bool vyn_fs_write_cstr(const char *path, const char *content) {
    FILE *f = fopen(path, "wb");
    if (!f) return false;
    size_t len = strlen(content);
    bool ok = fwrite(content, 1, len, f) == len;
    fclose(f);
    return ok;
}

bool vyn_fs_exists(const char *path) {
#ifdef _WIN32
    return GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES;
#else
    return access(path, F_OK) == 0;
#endif
}

bool vyn_fs_remove(const char *path) { return remove(path) == 0; }

bool vyn_fs_mkdir(const char *path) {
#ifdef _WIN32
    return CreateDirectoryA(path, NULL) || GetLastError() == ERROR_ALREADY_EXISTS;
#else
    return mkdir(path, 0755) == 0 || errno == EEXIST;
#endif
}

bool vyn_fs_is_dir(const char *path) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY);
#else
    struct stat st;
    return stat(path, &st) == 0 && S_ISDIR(st.st_mode);
#endif
}

bool vyn_fs_is_file(const char *path) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
#else
    struct stat st;
    return stat(path, &st) == 0 && S_ISREG(st.st_mode);
#endif
}

vyn_i64 vyn_fs_size(const char *path) {
#ifdef _WIN32
    WIN32_FILE_ATTRIBUTE_DATA info;
    if (!GetFileAttributesExA(path, GetFileExInfoStandard, &info)) return -1;
    LARGE_INTEGER sz;
    sz.LowPart  = info.nFileSizeLow;
    sz.HighPart = (LONG)info.nFileSizeHigh;
    return (vyn_i64)sz.QuadPart;
#else
    struct stat st;
    if (stat(path, &st) != 0) return -1;
    return (vyn_i64)st.st_size;
#endif
}

VynVec *vyn_fs_list_dir(const char *path) {
    VynVec *out = vyn_vec_new(VYN_TID_STRING);
#ifdef _WIN32
    char pattern[4096];
    snprintf(pattern, sizeof(pattern), "%s\\*", path);
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pattern, &fd);
    if (h == INVALID_HANDLE_VALUE) return out;
    do {
        if (strcmp(fd.cFileName, ".") && strcmp(fd.cFileName, ".."))
            vyn_vec_push(out, vyn_str_from(fd.cFileName));
    } while (FindNextFileA(h, &fd));
    FindClose(h);
#else
    DIR *d = opendir(path);
    if (!d) return out;
    struct dirent *e;
    while ((e = readdir(d))) {
        if (strcmp(e->d_name, ".") && strcmp(e->d_name, ".."))
            vyn_vec_push(out, vyn_str_from(e->d_name));
    }
    closedir(d);
#endif
    return out;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Profiling
 * ═══════════════════════════════════════════════════════════════════════════ */

#define PROF_MAX 256

typedef struct {
    char    name[64];
    vyn_i64 start_us;
    vyn_i64 total_us;
    vyn_i64 calls;
} ProfEntry;

static ProfEntry _prof[PROF_MAX];
static int       _prof_count = 0;

static ProfEntry *_prof_find(const char *name) {
    for (int i = 0; i < _prof_count; i++)
        if (strcmp(_prof[i].name, name) == 0) return &_prof[i];
    if (_prof_count < PROF_MAX) {
        ProfEntry *e = &_prof[_prof_count++];
        strncpy(e->name, name, 63);
        e->start_us = e->total_us = e->calls = 0;
        return e;
    }
    return NULL;
}

void vyn_profile_begin(const char *name) {
    ProfEntry *e = _prof_find(name);
    if (e) {
        e->start_us = vyn_sys_now_us();
        fprintf(stderr, "[VynProfile] START %s\n", name);
    }
}

void vyn_profile_end(const char *name) {
    ProfEntry *e = _prof_find(name);
    if (e && e->start_us) {
        vyn_i64 elapsed = vyn_sys_now_us() - e->start_us;
        e->total_us += elapsed;
        e->calls++;
        e->start_us = 0;
        fprintf(stderr, "[VynProfile] END %s — %.3f ms\n",
                name, (double)elapsed / 1000.0);
    }
}

void vyn_profile_report(void) {
    fprintf(stderr, "\n=== Vyn Profiling Report ===\n");
    for (int i = 0; i < _prof_count; i++) {
        ProfEntry *e = &_prof[i];
        fprintf(stderr, "  %-32s  calls=%lld  total=%.3f ms  avg=%.3f ms\n",
                e->name, (long long)e->calls,
                (double)e->total_us / 1000.0,
                e->calls > 0 ? (double)e->total_us / (double)e->calls / 1000.0 : 0.0);
    }
    fprintf(stderr, "============================\n\n");
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Threads
 * ═══════════════════════════════════════════════════════════════════════════ */

#ifndef _WIN32

struct VynThread {
    pthread_t tid;
};

struct VynMutex {
    pthread_mutex_t m;
};

struct VynCondVar {
    pthread_cond_t cv;
};

VynThread *vyn_thread_spawn(VynThreadFn fn, void *arg) {
    VynThread *t = (VynThread *)vyn_alloc(sizeof(VynThread));
    pthread_create(&t->tid, NULL, fn, arg);
    return t;
}

void *vyn_thread_join(VynThread *t) {
    void *ret = NULL;
    pthread_join(t->tid, &ret);
    free(t);
    return ret;
}

void vyn_thread_detach(VynThread *t) {
    pthread_detach(t->tid);
    free(t);
}

VynThread *vyn_thread_current(void) {
    VynThread *t = (VynThread *)vyn_alloc(sizeof(VynThread));
    t->tid = pthread_self();
    return t;
}

VynMutex *vyn_mutex_new(void) {
    VynMutex *m = (VynMutex *)vyn_alloc(sizeof(VynMutex));
    pthread_mutex_init(&m->m, NULL);
    return m;
}

void vyn_mutex_lock    (VynMutex *m) { pthread_mutex_lock(&m->m); }
bool vyn_mutex_try_lock(VynMutex *m) { return pthread_mutex_trylock(&m->m) == 0; }
void vyn_mutex_unlock  (VynMutex *m) { pthread_mutex_unlock(&m->m); }
void vyn_mutex_free    (VynMutex *m) { pthread_mutex_destroy(&m->m); free(m); }

VynCondVar *vyn_condvar_new(void) {
    VynCondVar *cv = (VynCondVar *)vyn_alloc(sizeof(VynCondVar));
    pthread_cond_init(&cv->cv, NULL);
    return cv;
}

void vyn_condvar_wait(VynCondVar *cv, VynMutex *m) {
    pthread_cond_wait(&cv->cv, &m->m);
}

bool vyn_condvar_wait_ms(VynCondVar *cv, VynMutex *m, vyn_i32 ms) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    ts.tv_nsec += (long)ms * 1000000L;
    ts.tv_sec  += ts.tv_nsec / 1000000000L;
    ts.tv_nsec %= 1000000000L;
    return pthread_cond_timedwait(&cv->cv, &m->m, &ts) == 0;
}

void vyn_condvar_signal   (VynCondVar *cv) { pthread_cond_signal(&cv->cv); }
void vyn_condvar_broadcast(VynCondVar *cv) { pthread_cond_broadcast(&cv->cv); }
void vyn_condvar_free     (VynCondVar *cv) { pthread_cond_destroy(&cv->cv); free(cv); }

/* Atomics via GCC builtins */
vyn_i32 vyn_atomic_load_i32 (volatile vyn_i32 *p)                       { return __atomic_load_n (p, __ATOMIC_SEQ_CST); }
void    vyn_atomic_store_i32(volatile vyn_i32 *p, vyn_i32 v)             { __atomic_store_n(p, v, __ATOMIC_SEQ_CST); }
vyn_i32 vyn_atomic_add_i32  (volatile vyn_i32 *p, vyn_i32 d)             { return __atomic_fetch_add(p, d, __ATOMIC_SEQ_CST); }
vyn_i32 vyn_atomic_cas_i32  (volatile vyn_i32 *p, vyn_i32 exp, vyn_i32 d){ vyn_i32 e=exp; __atomic_compare_exchange_n(p,&e,d,0,__ATOMIC_SEQ_CST,__ATOMIC_RELAXED); return e; }

#else /* _WIN32 */

/* Minimal Win32 stubs */
struct VynThread  { HANDLE h; };
struct VynMutex   { HANDLE h; };
struct VynCondVar { CONDITION_VARIABLE cv; };

typedef struct { VynThreadFn fn; void *arg; } _WinThreadArg;
static DWORD WINAPI _win_thread_entry(LPVOID p) {
    _WinThreadArg *a = (_WinThreadArg *)p;
    a->fn(a->arg);
    free(a);
    return 0;
}

VynThread *vyn_thread_spawn(VynThreadFn fn, void *arg) {
    VynThread    *t = (VynThread *)vyn_alloc(sizeof(VynThread));
    _WinThreadArg *a = (_WinThreadArg *)vyn_alloc(sizeof(_WinThreadArg));
    a->fn = fn; a->arg = arg;
    t->h = CreateThread(NULL, 0, _win_thread_entry, a, 0, NULL);
    return t;
}
void *vyn_thread_join(VynThread *t)    { WaitForSingleObject(t->h, INFINITE); CloseHandle(t->h); free(t); return NULL; }
void  vyn_thread_detach(VynThread *t)  { CloseHandle(t->h); free(t); }
VynThread *vyn_thread_current(void)    { VynThread *t = (VynThread *)vyn_alloc(sizeof(VynThread)); t->h = GetCurrentThread(); return t; }

VynMutex *vyn_mutex_new(void)          { VynMutex *m = (VynMutex *)vyn_alloc(sizeof(VynMutex)); m->h = CreateMutexA(NULL,FALSE,NULL); return m; }
void      vyn_mutex_lock(VynMutex *m)  { WaitForSingleObject(m->h, INFINITE); }
bool      vyn_mutex_try_lock(VynMutex *m) { return WaitForSingleObject(m->h, 0) == WAIT_OBJECT_0; }
void      vyn_mutex_unlock(VynMutex *m){ ReleaseMutex(m->h); }
void      vyn_mutex_free(VynMutex *m)  { CloseHandle(m->h); free(m); }

VynCondVar *vyn_condvar_new(void)      { VynCondVar *cv = (VynCondVar *)vyn_alloc(sizeof(VynCondVar)); InitializeConditionVariable(&cv->cv); return cv; }
void        vyn_condvar_wait(VynCondVar *cv, VynMutex *m) { (void)cv; (void)m; }
bool        vyn_condvar_wait_ms(VynCondVar *cv, VynMutex *m, vyn_i32 ms) { (void)cv;(void)m;(void)ms; return false; }
void        vyn_condvar_signal(VynCondVar *cv) { WakeConditionVariable(&cv->cv); }
void        vyn_condvar_broadcast(VynCondVar *cv) { WakeAllConditionVariable(&cv->cv); }
void        vyn_condvar_free(VynCondVar *cv) { free(cv); }

vyn_i32 vyn_atomic_load_i32 (volatile vyn_i32 *p)                       { return InterlockedCompareExchange((volatile LONG*)p, 0, 0); }
void    vyn_atomic_store_i32(volatile vyn_i32 *p, vyn_i32 v)             { InterlockedExchange((volatile LONG*)p, v); }
vyn_i32 vyn_atomic_add_i32  (volatile vyn_i32 *p, vyn_i32 d)             { return InterlockedExchangeAdd((volatile LONG*)p, d); }
vyn_i32 vyn_atomic_cas_i32  (volatile vyn_i32 *p, vyn_i32 exp, vyn_i32 d){ return InterlockedCompareExchange((volatile LONG*)p, d, exp); }

#endif /* _WIN32 */

/* ═══════════════════════════════════════════════════════════════════════════
 *  Random  (xoshiro256**)
 * ═══════════════════════════════════════════════════════════════════════════ */

static uint64_t _xo[4] = { 0x123456789ABCDEF0ULL, 0xFEDCBA9876543210ULL,
                             0xDEADBEEFCAFEBABEULL, 0x0123456789ABCDEFULL };

static VYN_INLINE uint64_t _rotl64(uint64_t x, int k) {
    return (x << k) | (x >> (64 - k));
}

void vyn_rand_seed(vyn_u64 seed) {
    /* Splitmix64 to initialise state */
    for (int i = 0; i < 4; i++) {
        seed += 0x9e3779b97f4a7c15ULL;
        uint64_t z = seed;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        _xo[i] = z ^ (z >> 31);
    }
}

vyn_u64 vyn_rand_u64(void) {
    uint64_t r  = _rotl64(_xo[1] * 5, 7) * 9;
    uint64_t t  = _xo[1] << 17;
    _xo[2] ^= _xo[0]; _xo[3] ^= _xo[1];
    _xo[1] ^= _xo[2]; _xo[0] ^= _xo[3];
    _xo[2] ^= t;
    _xo[3]  = _rotl64(_xo[3], 45);
    return r;
}

vyn_i32 vyn_rand_i32(void)   { return (vyn_i32)(vyn_rand_u64() >> 33); }
vyn_f32 vyn_rand_f32(void)   { return (vyn_f32)((vyn_rand_u64() >> 11) * (1.0 / (1ULL << 53))); }
vyn_i32 vyn_rand_range(vyn_i32 lo, vyn_i32 hi) {
    if (hi <= lo) return lo;
    return lo + (vyn_i32)(vyn_rand_u64() % (uint64_t)(hi - lo));
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Hash utilities
 * ═══════════════════════════════════════════════════════════════════════════ */

uint64_t vyn_hash_fnv1a_64(const uint8_t *buf, size_t len) {
    return vyn_fnv1a(buf, len);
}

vyn_u32 vyn_hash_crc32(const uint8_t *buf, size_t len) {
    static uint32_t table[256];
    static bool init = false;
    if (!init) {
        for (uint32_t i = 0; i < 256; i++) {
            uint32_t c = i;
            for (int j = 0; j < 8; j++)
                c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
            table[i] = c;
        }
        init = true;
    }
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; i++)
        crc = (crc >> 8) ^ table[(crc ^ buf[i]) & 0xFF];
    return ~crc;
}

/* SHA-256 — minimal portable implementation */
static const uint32_t _SHA_K[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};

#define SHA_ROR32(x,n) (((x)>>(n))|((x)<<(32-(n))))
#define SHA_CH(e,f,g)  (((e)&(f))^(~(e)&(g)))
#define SHA_MAJ(a,b,c) (((a)&(b))^((a)&(c))^((b)&(c)))
#define SHA_EP0(a) (SHA_ROR32(a,2)^SHA_ROR32(a,13)^SHA_ROR32(a,22))
#define SHA_EP1(e) (SHA_ROR32(e,6)^SHA_ROR32(e,11)^SHA_ROR32(e,25))
#define SHA_SIG0(x)(SHA_ROR32(x,7)^SHA_ROR32(x,18)^((x)>>3))
#define SHA_SIG1(x)(SHA_ROR32(x,17)^SHA_ROR32(x,19)^((x)>>10))

void vyn_hash_sha256(const uint8_t *buf, size_t len, uint8_t out[32]) {
    uint32_t h[8] = {
        0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
    };
    /* Simplified single-block SHA-256 for small messages */
    uint8_t  block[64];
    uint32_t w[64];
    size_t   msg_len = len;
    size_t   off = 0;

    while (off <= len) {
        size_t block_len = 0;
        memset(block, 0, 64);
        if (off < len) {
            block_len = (len - off > 64) ? 64 : len - off;
            memcpy(block, buf + off, block_len);
        }
        if (off + block_len == len) {
            block[block_len] = 0x80;
            if (block_len < 56) {
                uint64_t bit_len = (uint64_t)msg_len * 8;
                for (int i = 0; i < 8; i++)
                    block[63 - i] = (uint8_t)(bit_len >> (8 * i));
                off = len + 1;
            } else {
                off += block_len;
                /* need extra block — write padding next iteration */
            }
        } else {
            off += 64;
        }

        for (int i = 0; i < 16; i++)
            w[i] = ((uint32_t)block[i*4]<<24)|((uint32_t)block[i*4+1]<<16)|
                   ((uint32_t)block[i*4+2]<<8)|(uint32_t)block[i*4+3];
        for (int i = 16; i < 64; i++)
            w[i] = SHA_SIG1(w[i-2])+w[i-7]+SHA_SIG0(w[i-15])+w[i-16];

        uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],hh=h[7];
        for (int i = 0; i < 64; i++) {
            uint32_t t1 = hh + SHA_EP1(e) + SHA_CH(e,f,g) + _SHA_K[i] + w[i];
            uint32_t t2 = SHA_EP0(a) + SHA_MAJ(a,b,c);
            hh=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
        }
        h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d;
        h[4]+=e; h[5]+=f; h[6]+=g; h[7]+=hh;

        if (off > len) break;
    }
    for (int i = 0; i < 8; i++) {
        out[i*4+0] = (uint8_t)(h[i]>>24);
        out[i*4+1] = (uint8_t)(h[i]>>16);
        out[i*4+2] = (uint8_t)(h[i]>>8);
        out[i*4+3] = (uint8_t)(h[i]);
    }
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Crypto helpers
 * ═══════════════════════════════════════════════════════════════════════════ */

static const char _B64[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

VynStr *vyn_crypto_sha256_hex(const VynStr *input) {
    uint8_t  digest[32];
    vyn_hash_sha256((const uint8_t *)vyn_str_cstr(input), input->len, digest);
    char hex[65];
    for (int i = 0; i < 32; i++)
        snprintf(hex + i * 2, 3, "%02x", digest[i]);
    hex[64] = '\0';
    return vyn_str_from(hex);
}

VynStr *vyn_crypto_base64_encode(const uint8_t *buf, size_t len) {
    size_t  out_len = ((len + 2) / 3) * 4;
    char   *out = (char *)vyn_alloc(out_len + 1);
    size_t  j   = 0;
    for (size_t i = 0; i < len; i += 3) {
        uint32_t b = (uint32_t)buf[i] << 16;
        if (i+1 < len) b |= (uint32_t)buf[i+1] << 8;
        if (i+2 < len) b |= (uint32_t)buf[i+2];
        out[j++] = _B64[(b >> 18) & 0x3F];
        out[j++] = _B64[(b >> 12) & 0x3F];
        out[j++] = (i+1 < len) ? _B64[(b >> 6) & 0x3F] : '=';
        out[j++] = (i+2 < len) ? _B64[ b       & 0x3F] : '=';
    }
    out[j] = '\0';
    VynStr *s = vyn_str_from_n(out, j);
    free(out);
    return s;
}

bool vyn_crypto_base64_decode(const char *src, uint8_t **out, size_t *out_len) {
    /* Simplified decoder */
    size_t  slen   = strlen(src);
    size_t  needed = (slen / 4) * 3;
    uint8_t *buf   = (uint8_t *)vyn_alloc(needed + 1);
    static const uint8_t T[256] = {
        ['A']=0,['B']=1,['C']=2,['D']=3,['E']=4,['F']=5,['G']=6,['H']=7,
        ['I']=8,['J']=9,['K']=10,['L']=11,['M']=12,['N']=13,['O']=14,['P']=15,
        ['Q']=16,['R']=17,['S']=18,['T']=19,['U']=20,['V']=21,['W']=22,['X']=23,
        ['Y']=24,['Z']=25,['a']=26,['b']=27,['c']=28,['d']=29,['e']=30,['f']=31,
        ['g']=32,['h']=33,['i']=34,['j']=35,['k']=36,['l']=37,['m']=38,['n']=39,
        ['o']=40,['p']=41,['q']=42,['r']=43,['s']=44,['t']=45,['u']=46,['v']=47,
        ['w']=48,['x']=49,['y']=50,['z']=51,['0']=52,['1']=53,['2']=54,['3']=55,
        ['4']=56,['5']=57,['6']=58,['7']=59,['8']=60,['9']=61,['+']=62,['/']=63
    };
    size_t n = 0;
    for (size_t i = 0; i + 3 < slen; i += 4) {
        uint32_t b = ((uint32_t)T[(uint8_t)src[i]]   << 18)
                   | ((uint32_t)T[(uint8_t)src[i+1]] << 12)
                   | ((uint32_t)T[(uint8_t)src[i+2]] << 6)
                   | ((uint32_t)T[(uint8_t)src[i+3]]);
        buf[n++] = (uint8_t)(b >> 16);
        if (src[i+2] != '=') buf[n++] = (uint8_t)(b >> 8);
        if (src[i+3] != '=') buf[n++] = (uint8_t)b;
    }
    *out     = buf;
    *out_len = n;
    return true;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  FFI helpers
 * ═══════════════════════════════════════════════════════════════════════════ */

vyn_i32  vyn_ffi_to_i32  (void *val) { return val ? *(vyn_i32 *)val  : 0; }
vyn_f32  vyn_ffi_to_f32  (void *val) { return val ? *(vyn_f32 *)val  : 0.0f; }
vyn_bool vyn_ffi_to_bool (void *val) { return val ? *(vyn_bool*)val  : false; }
VynStr  *vyn_ffi_to_str  (void *val) { return val ? vyn_str_from((const char *)val) : vyn_str_new(); }

void *vyn_ffi_from_i32 (vyn_i32 n)  { vyn_i32  *p = (vyn_i32  *)vyn_alloc(sizeof(n)); *p = n; return p; }
void *vyn_ffi_from_f32 (vyn_f32 f)  { vyn_f32  *p = (vyn_f32  *)vyn_alloc(sizeof(f)); *p = f; return p; }
void *vyn_ffi_from_bool(vyn_bool b) { vyn_bool *p = (vyn_bool *)vyn_alloc(sizeof(b)); *p = b; return p; }
void *vyn_ffi_from_str (const VynStr *s) { return (void *)vyn_str_cstr(s); }

void *vyn_ffi_dlopen (const char *path)            { (void)path; return NULL; /* platform-specific */ }
void *vyn_ffi_dlsym  (void *h, const char *sym)    { (void)h; (void)sym; return NULL; }
void  vyn_ffi_dlclose(void *h)                      { (void)h; }

#ifndef _WIN32
#undef vyn_ffi_dlopen
#undef vyn_ffi_dlsym
#undef vyn_ffi_dlclose
void *vyn_ffi_dlopen (const char *path)            { return dlopen(path, RTLD_LAZY); }
void *vyn_ffi_dlsym  (void *h, const char *sym)    { return dlsym(h, sym); }
void  vyn_ffi_dlclose(void *h)                      { dlclose(h); }
#endif

/* ═══════════════════════════════════════════════════════════════════════════
 *  Box primitives
 * ═══════════════════════════════════════════════════════════════════════════ */

vyn_i32 *vyn_box_i32 (vyn_i32 n)  { vyn_i32  *p=(vyn_i32  *)vyn_gc_alloc(sizeof(vyn_i32), 0,NULL); *p=n; return p; }
vyn_f32 *vyn_box_f32 (vyn_f32 f)  { vyn_f32  *p=(vyn_f32  *)vyn_gc_alloc(sizeof(vyn_f32), 0,NULL); *p=f; return p; }
vyn_bool*vyn_box_bool(vyn_bool b) { vyn_bool *p=(vyn_bool *)vyn_gc_alloc(sizeof(vyn_bool),0,NULL); *p=b; return p; }

/* ═══════════════════════════════════════════════════════════════════════════
 *  Runtime init / fini — legacy API (used by generated LLVM code)
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Legacy functions expected by LLVM codegen */
void vyn_io_println_str_cstr(const char *s) {
    puts(s);
}

void vyn_sys_sleep_ms_legacy(int ms) {
    vyn_sys_sleep_ms((vyn_i32)ms);
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Runtime initialisation / finalisation
 * ═══════════════════════════════════════════════════════════════════════════ */

void vyn_runtime_init(int argc, char **argv) {
    vyn_argc = argc;
    vyn_argv = argv;

    /* Initialise GC with 4MB initial threshold */
    vyn_gc_init(4 * 1024 * 1024);

    /* Seed RNG from time */
    vyn_rand_seed((vyn_u64)time(NULL) ^ (vyn_u64)(uintptr_t)argv);
}

void vyn_runtime_fini(void) {
    /* Print profiling report if any functions were profiled */
    if (_prof_count > 0) vyn_profile_report();

    /* Shutdown GC */
    vyn_gc_shutdown();
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  External raw C stub  (used by FFI demo in ffi.vyn)
 * ═══════════════════════════════════════════════════════════════════════════ */

int raw_hardware_call(int id) {
    return id * 2;
}