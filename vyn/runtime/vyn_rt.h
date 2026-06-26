/* vyn_rt.h — Vyn Runtime Library Header
 * Master header for the Vyn native runtime.
 * Included by all Vyn-generated C code and runtime modules.
 */

#ifndef VYN_RT_H
#define VYN_RT_H

/* ─── C standard includes ────────────────────────────────────────────────── */
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#include <stdarg.h>
#include <time.h>
#include <errno.h>
#include <limits.h>

#ifdef _WIN32
#  include <windows.h>
#  include <io.h>
#else
#  include <unistd.h>
#  include <sys/time.h>
#  include <pthread.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* ═══════════════════════════════════════════════════════════════════════════
 *  Version
 * ═══════════════════════════════════════════════════════════════════════════ */

#define VYN_VERSION_MAJOR  1
#define VYN_VERSION_MINOR  0
#define VYN_VERSION_PATCH  0
#define VYN_VERSION_STR    "1.0.0"

/* ═══════════════════════════════════════════════════════════════════════════
 *  Primitive type aliases  (match Vyn language types)
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef int8_t    vyn_i8;
typedef int16_t   vyn_i16;
typedef int32_t   vyn_i32;
typedef int64_t   vyn_i64;
typedef uint8_t   vyn_u8;
typedef uint16_t  vyn_u16;
typedef uint32_t  vyn_u32;
typedef uint64_t  vyn_u64;
typedef float     vyn_f32;
typedef double    vyn_f64;
typedef bool      vyn_bool;
typedef uint32_t  vyn_char;   /* Unicode code point */
typedef size_t    vyn_usize;
typedef ptrdiff_t vyn_isize;

/* Pointer-sized integer */
typedef uintptr_t vyn_uptr;
typedef intptr_t  vyn_iptr;

/* ═══════════════════════════════════════════════════════════════════════════
 *  Utility macros
 * ═══════════════════════════════════════════════════════════════════════════ */

#define VYN_UNUSED(x)        ((void)(x))
#define VYN_ARRAY_LEN(a)     (sizeof(a) / sizeof((a)[0]))
#define VYN_ALIGN(n, a)      (((n) + (a) - 1) & ~((a) - 1))
#define VYN_MIN(a, b)        ((a) < (b) ? (a) : (b))
#define VYN_MAX(a, b)        ((a) > (b) ? (a) : (b))
#define VYN_CLAMP(v,lo,hi)   VYN_MIN(VYN_MAX((v),(lo)),(hi))
#define VYN_ABS(x)           ((x) < 0 ? -(x) : (x))

/* Branch prediction hints */
#if defined(__GNUC__) || defined(__clang__)
#  define VYN_LIKELY(x)    __builtin_expect(!!(x), 1)
#  define VYN_UNLIKELY(x)  __builtin_expect(!!(x), 0)
#else
#  define VYN_LIKELY(x)    (x)
#  define VYN_UNLIKELY(x)  (x)
#endif

/* Inline / force-inline */
#if defined(_MSC_VER)
#  define VYN_INLINE        __forceinline
#  define VYN_NOINLINE      __declspec(noinline)
#elif defined(__GNUC__) || defined(__clang__)
#  define VYN_INLINE        __attribute__((always_inline)) inline
#  define VYN_NOINLINE      __attribute__((noinline))
#else
#  define VYN_INLINE        inline
#  define VYN_NOINLINE
#endif

/* Noreturn */
#if defined(__GNUC__) || defined(__clang__)
#  define VYN_NORETURN  __attribute__((noreturn))
#elif defined(_MSC_VER)
#  define VYN_NORETURN  __declspec(noreturn)
#else
#  define VYN_NORETURN
#endif

/* Static assert */
#define VYN_STATIC_ASSERT(cond, msg)  _Static_assert(cond, msg)

/* ═══════════════════════════════════════════════════════════════════════════
 *  Error / panic
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Abort with a formatted message */
VYN_NORETURN void vyn_panic(const char *fmt, ...);

/* Check condition; panic if false */
#define VYN_ASSERT(cond, msg) \
    do { if (VYN_UNLIKELY(!(cond))) vyn_panic("[Assert] %s:%d: %s", __FILE__, __LINE__, (msg)); } while(0)

/* Out-of-memory panic */
VYN_NORETURN void vyn_oom(void);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Memory allocator interface
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef struct VynAllocator {
    void *(*alloc)  (struct VynAllocator *self, size_t size);
    void *(*realloc)(struct VynAllocator *self, void *ptr, size_t old_size, size_t new_size);
    void  (*free)   (struct VynAllocator *self, void *ptr, size_t size);
    void  *ctx;
} VynAllocator;

/* Default system allocator (malloc/realloc/free) */
VynAllocator *vyn_default_allocator(void);

/* Wrappers that panic on OOM */
void *vyn_alloc  (size_t size);
void *vyn_realloc(void *ptr, size_t new_size);
void  vyn_free   (void *ptr);
char *vyn_strdup (const char *s);

/* Zero-initialising alloc */
void *vyn_zalloc (size_t size);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Garbage Collector  (vyn_gc.h / vyn_gc.c)
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Object header — every GC-managed object starts with this */
typedef struct VynGcHeader {
    uint32_t             mark;       /* GC mark bit + colour */
    uint32_t             type_id;    /* user-defined type id */
    struct VynGcHeader  *next;       /* intrusive linked list */
    size_t               size;       /* allocation size in bytes */
    void               (*finalizer)(void *obj);  /* optional destructor */
} VynGcHeader;

/* GC type ids */
#define VYN_TID_STRING   1
#define VYN_TID_VEC      2
#define VYN_TID_HASHMAP  3
#define VYN_TID_CLOSURE  4
#define VYN_TID_STRUCT   5
#define VYN_TID_TUPLE    6
#define VYN_TID_USER     128   /* user-defined types start here */

/* GC state */
typedef struct VynGc {
    VynGcHeader *head;          /* list of all objects */
    size_t       allocated;     /* bytes currently allocated */
    size_t       threshold;     /* trigger collection when above this */
    size_t       collections;   /* number of collections run */
    /* root stack for conservative scanning */
    void       **roots;
    size_t       root_count;
    size_t       root_cap;
} VynGc;

/* Global GC instance */
extern VynGc *vyn_gc;

/* Initialise / shutdown */
void  vyn_gc_init   (size_t initial_threshold);
void  vyn_gc_shutdown(void);

/* Allocate a GC-managed object of given size and type */
void *vyn_gc_alloc  (size_t size, uint32_t type_id, void (*finalizer)(void *));

/* Trigger a collection */
void  vyn_gc_collect(void);

/* Push / pop roots */
void  vyn_gc_push_root(void **ref);
void  vyn_gc_pop_root (void **ref);

/* Convenience root guard (RAII-like for C) */
#define VYN_GC_ROOT(ptr) \
    void *_gc_root_##ptr = (void *)(ptr); \
    vyn_gc_push_root(&_gc_root_##ptr)
#define VYN_GC_UNROOT(ptr) \
    vyn_gc_pop_root(&_gc_root_##ptr)

/* ═══════════════════════════════════════════════════════════════════════════
 *  Dynamic String   VynStr
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Small-string optimisation: strings <= 22 bytes stored inline */
#define VYN_STR_SSO_CAP  22

typedef struct VynStr {
    VynGcHeader  gc;           /* must be first */
    size_t       len;          /* length in bytes (UTF-8) */
    size_t       cap;          /* capacity (0 = SSO) */
    union {
        char    *heap;         /* heap pointer when cap > SSO_CAP */
        char     sso[VYN_STR_SSO_CAP + 1];  /* inline storage */
    } data;
} VynStr;

/* Constructors */
VynStr *vyn_str_new     (void);
VynStr *vyn_str_from    (const char *cstr);
VynStr *vyn_str_from_n  (const char *buf, size_t len);
VynStr *vyn_str_from_i32(vyn_i32 n);
VynStr *vyn_str_from_f32(vyn_f32 f);
VynStr *vyn_str_from_f64(vyn_f64 f);
VynStr *vyn_str_from_char(vyn_char ch);
VynStr *vyn_str_clone   (const VynStr *s);

/* Access */
const char *vyn_str_cstr(const VynStr *s);
size_t      vyn_str_len (const VynStr *s);
bool        vyn_str_empty(const VynStr *s);
vyn_char    vyn_str_char_at(const VynStr *s, size_t idx);

/* Mutation */
void  vyn_str_push_char (VynStr *s, vyn_char ch);
void  vyn_str_push_cstr (VynStr *s, const char *cstr);
void  vyn_str_push_str  (VynStr *s, const VynStr *other);
void  vyn_str_clear     (VynStr *s);
void  vyn_str_reserve   (VynStr *s, size_t cap);

/* Operations */
VynStr *vyn_str_concat  (const VynStr *a, const VynStr *b);
VynStr *vyn_str_slice   (const VynStr *s, size_t start, size_t end);
VynStr *vyn_str_upper   (const VynStr *s);
VynStr *vyn_str_lower   (const VynStr *s);
VynStr *vyn_str_trim    (const VynStr *s);
VynStr *vyn_str_repeat  (const VynStr *s, size_t n);
VynStr *vyn_str_replace (const VynStr *s, const char *from, const char *to);
bool    vyn_str_contains(const VynStr *s, const char *needle);
bool    vyn_str_starts_with(const VynStr *s, const char *prefix);
bool    vyn_str_ends_with  (const VynStr *s, const char *suffix);
vyn_i32 vyn_str_find    (const VynStr *s, const char *needle);
vyn_i32 vyn_str_parse_i32(const VynStr *s);
vyn_f32 vyn_str_parse_f32(const VynStr *s);
int     vyn_str_cmp     (const VynStr *a, const VynStr *b);
bool    vyn_str_eq      (const VynStr *a, const VynStr *b);

/* Printf into a VynStr */
VynStr *vyn_str_fmt(const char *fmt, ...);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Dynamic Vector   VynVec
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef struct VynVec {
    VynGcHeader  gc;           /* must be first */
    void       **data;         /* array of pointers to elements */
    size_t       len;
    size_t       cap;
    uint32_t     elem_type;    /* type id of elements */
} VynVec;

/* Constructors */
VynVec *vyn_vec_new       (uint32_t elem_type);
VynVec *vyn_vec_with_cap  (uint32_t elem_type, size_t cap);
VynVec *vyn_vec_clone     (const VynVec *v);

/* Access */
void   *vyn_vec_get       (const VynVec *v, size_t idx);
void   *vyn_vec_get_unchecked(const VynVec *v, size_t idx);
size_t  vyn_vec_len       (const VynVec *v);
bool    vyn_vec_empty     (const VynVec *v);
void   *vyn_vec_first     (const VynVec *v);
void   *vyn_vec_last      (const VynVec *v);

/* Mutation */
void    vyn_vec_push      (VynVec *v, void *elem);
void   *vyn_vec_pop       (VynVec *v);
void    vyn_vec_set       (VynVec *v, size_t idx, void *elem);
void    vyn_vec_insert    (VynVec *v, size_t idx, void *elem);
void   *vyn_vec_remove    (VynVec *v, size_t idx);
void    vyn_vec_clear     (VynVec *v);
void    vyn_vec_reserve   (VynVec *v, size_t cap);
void    vyn_vec_shrink    (VynVec *v);

/* Search */
vyn_i32 vyn_vec_find      (const VynVec *v, void *elem,
                            int (*cmp)(const void *, const void *));
bool    vyn_vec_contains  (const VynVec *v, void *elem,
                            int (*cmp)(const void *, const void *));

/* Iteration helper */
typedef bool (*VynVecIterFn)(void *elem, void *userdata);
void    vyn_vec_foreach   (VynVec *v, VynVecIterFn fn, void *ud);

/* Sorting */
void    vyn_vec_sort      (VynVec *v, int (*cmp)(const void *, const void *));

/* Slice — returns a new vec with elements [start, end) */
VynVec *vyn_vec_slice     (const VynVec *v, size_t start, size_t end);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Hash Map   VynHashMap
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef struct VynHashEntry {
    uint64_t     hash;
    void        *key;
    void        *value;
    bool         occupied;
    bool         deleted;
} VynHashEntry;

typedef struct VynHashMap {
    VynGcHeader   gc;
    VynHashEntry *entries;
    size_t        cap;        /* must be power-of-two */
    size_t        len;        /* number of live entries */
    size_t        tombstones; /* deleted entries */
    uint32_t      key_type;
    uint32_t      val_type;
    uint64_t    (*hash_fn)(const void *key);
    int         (*eq_fn)  (const void *a, const void *b);
} VynHashMap;

/* Built-in hash functions */
uint64_t vyn_hash_str   (const void *key);   /* key = VynStr* */
uint64_t vyn_hash_i32   (const void *key);   /* key = vyn_i32* */
uint64_t vyn_hash_i64   (const void *key);
uint64_t vyn_hash_ptr   (const void *key);   /* identity hash */
uint64_t vyn_fnv1a      (const uint8_t *buf, size_t len);

/* Built-in equality functions */
int vyn_eq_str (const void *a, const void *b);
int vyn_eq_i32 (const void *a, const void *b);
int vyn_eq_i64 (const void *a, const void *b);
int vyn_eq_ptr (const void *a, const void *b);

/* Constructors */
VynHashMap *vyn_map_new    (uint32_t key_type, uint32_t val_type,
                             uint64_t (*hash_fn)(const void *),
                             int      (*eq_fn)  (const void *, const void *));
VynHashMap *vyn_map_new_str(void);      /* string → any */
VynHashMap *vyn_map_new_i32(void);      /* i32    → any */
VynHashMap *vyn_map_clone  (const VynHashMap *m);
void        vyn_map_free   (VynHashMap *m);

/* Operations */
bool        vyn_map_insert  (VynHashMap *m, void *key, void *value);
void       *vyn_map_get     (const VynHashMap *m, const void *key);
bool        vyn_map_contains(const VynHashMap *m, const void *key);
bool        vyn_map_remove  (VynHashMap *m, const void *key);
size_t      vyn_map_len     (const VynHashMap *m);
void        vyn_map_clear   (VynHashMap *m);

/* Iteration */
typedef bool (*VynMapIterFn)(void *key, void *value, void *userdata);
void        vyn_map_foreach (VynHashMap *m, VynMapIterFn fn, void *ud);

/* Keys / values as VynVec */
VynVec     *vyn_map_keys    (const VynHashMap *m);
VynVec     *vyn_map_values  (const VynHashMap *m);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Option<T>  and  Result<T,E>   (tagged unions for C)
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef struct VynOption {
    bool  has_value;
    void *value;
} VynOption;

typedef struct VynResult {
    bool  is_ok;
    void *value;    /* Ok value  or  Err value */
} VynResult;

VYN_INLINE VynOption vyn_some(void *v) { return (VynOption){ true,  v }; }
VYN_INLINE VynOption vyn_none(void)    { return (VynOption){ false, NULL }; }
VYN_INLINE VynResult vyn_ok  (void *v) { return (VynResult){ true,  v }; }
VYN_INLINE VynResult vyn_err (void *e) { return (VynResult){ false, e }; }

#define VYN_TRY(result_expr, err_label) \
    do { VynResult _r = (result_expr); if (!_r.is_ok) { goto err_label; } } while(0)

/* ═══════════════════════════════════════════════════════════════════════════
 *  Tuple  (fixed-size heterogeneous sequence)
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef struct VynTuple {
    VynGcHeader gc;
    size_t      arity;
    void       *elems[1];   /* flexible array (actual size = arity) */
} VynTuple;

VynTuple *vyn_tuple_new  (size_t arity);
void     *vyn_tuple_get  (const VynTuple *t, size_t idx);
void      vyn_tuple_set  (VynTuple *t, size_t idx, void *val);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Closure  (captured function + environment)
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef void *(*VynFnPtr)(void **args, size_t argc, void *env);

typedef struct VynClosure {
    VynGcHeader  gc;
    VynFnPtr     fn;        /* pointer to the actual function */
    void        *env;       /* captured environment (GC-managed struct) */
    size_t       arity;     /* expected number of arguments */
} VynClosure;

VynClosure *vyn_closure_new  (VynFnPtr fn, void *env, size_t arity);
void       *vyn_closure_call (VynClosure *cl, void **args, size_t argc);

/* ═══════════════════════════════════════════════════════════════════════════
 *  I/O  (vyn_rt.c)
 * ═══════════════════════════════════════════════════════════════════════════ */

void vyn_io_print_str  (const VynStr *s);
void vyn_io_println_str(const VynStr *s);
void vyn_io_print_cstr (const char   *s);
void vyn_io_print_i32  (vyn_i32 n);
void vyn_io_print_i64  (vyn_i64 n);
void vyn_io_print_f32  (vyn_f32 f);
void vyn_io_print_f64  (vyn_f64 f);
void vyn_io_print_bool (vyn_bool b);
void vyn_io_print_char (vyn_char c);

VynStr *vyn_io_readln  (void);
vyn_i32 vyn_io_read_i32(void);
vyn_f32 vyn_io_read_f32(void);

void    vyn_io_flush   (void);
void    vyn_io_eprint  (const char *fmt, ...);   /* stderr */

/* ═══════════════════════════════════════════════════════════════════════════
 *  Math  (vyn_rt.c)
 * ═══════════════════════════════════════════════════════════════════════════ */

vyn_f32 vyn_math_abs_f32  (vyn_f32 x);
vyn_f64 vyn_math_abs_f64  (vyn_f64 x);
vyn_f32 vyn_math_sqrt     (vyn_f32 x);
vyn_f32 vyn_math_pow      (vyn_f32 base, vyn_f32 exp);
vyn_f32 vyn_math_sin      (vyn_f32 x);
vyn_f32 vyn_math_cos      (vyn_f32 x);
vyn_f32 vyn_math_tan      (vyn_f32 x);
vyn_f32 vyn_math_floor    (vyn_f32 x);
vyn_f32 vyn_math_ceil     (vyn_f32 x);
vyn_f32 vyn_math_round    (vyn_f32 x);
vyn_f32 vyn_math_log      (vyn_f32 x);
vyn_f32 vyn_math_log2     (vyn_f32 x);
vyn_f32 vyn_math_log10    (vyn_f32 x);
vyn_f32 vyn_math_clamp    (vyn_f32 v, vyn_f32 lo, vyn_f32 hi);
vyn_f32 vyn_math_lerp     (vyn_f32 a, vyn_f32 b, vyn_f32 t);
vyn_f32 vyn_math_min_f32  (vyn_f32 a, vyn_f32 b);
vyn_f32 vyn_math_max_f32  (vyn_f32 a, vyn_f32 b);
vyn_i32 vyn_math_min_i32  (vyn_i32 a, vyn_i32 b);
vyn_i32 vyn_math_max_i32  (vyn_i32 a, vyn_i32 b);

#define VYN_PI   3.14159265358979323846f
#define VYN_E    2.71828182845904523536f
#define VYN_TAU  6.28318530717958647692f
#define VYN_INF  (1.0f / 0.0f)
#define VYN_NAN  (0.0f / 0.0f)

/* ═══════════════════════════════════════════════════════════════════════════
 *  System / OS
 * ═══════════════════════════════════════════════════════════════════════════ */

void     vyn_sys_sleep_ms  (vyn_i32 ms);
void     vyn_sys_sleep_us  (vyn_i64 us);
vyn_i64  vyn_sys_now_ms    (void);     /* milliseconds since epoch */
vyn_i64  vyn_sys_now_us    (void);     /* microseconds since epoch */
VynStr  *vyn_sys_env       (const char *name);
VynStr  *vyn_sys_cwd       (void);
VYN_NORETURN void vyn_sys_exit(vyn_i32 code);

/* ═══════════════════════════════════════════════════════════════════════════
 *  File system
 * ═══════════════════════════════════════════════════════════════════════════ */

VynStr  *vyn_fs_read       (const char *path);
bool     vyn_fs_write      (const char *path, const VynStr *content);
bool     vyn_fs_write_cstr (const char *path, const char *content);
bool     vyn_fs_exists     (const char *path);
bool     vyn_fs_remove     (const char *path);
bool     vyn_fs_mkdir      (const char *path);
bool     vyn_fs_is_dir     (const char *path);
bool     vyn_fs_is_file    (const char *path);
vyn_i64  vyn_fs_size       (const char *path);
VynVec  *vyn_fs_list_dir   (const char *path);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Profiling  (vyn_rt.c)
 * ═══════════════════════════════════════════════════════════════════════════ */

void    vyn_profile_begin  (const char *name);
void    vyn_profile_end    (const char *name);
void    vyn_profile_report (void);   /* prints all accumulated timings */

/* Scoped profiling (RAII-like) */
#define VYN_PROFILE_SCOPE(name) \
    vyn_profile_begin(name); \
    /* caller must call vyn_profile_end(name) at end of scope */

/* ═══════════════════════════════════════════════════════════════════════════
 *  Threads  (thin wrapper over pthreads / Win32 threads)
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef struct VynThread  VynThread;
typedef struct VynMutex   VynMutex;
typedef struct VynCondVar VynCondVar;

typedef void *(*VynThreadFn)(void *arg);

VynThread  *vyn_thread_spawn    (VynThreadFn fn, void *arg);
void       *vyn_thread_join     (VynThread *t);
void        vyn_thread_detach   (VynThread *t);
VynThread  *vyn_thread_current  (void);

VynMutex   *vyn_mutex_new       (void);
void        vyn_mutex_lock      (VynMutex *m);
bool        vyn_mutex_try_lock  (VynMutex *m);
void        vyn_mutex_unlock    (VynMutex *m);
void        vyn_mutex_free      (VynMutex *m);

VynCondVar *vyn_condvar_new     (void);
void        vyn_condvar_wait    (VynCondVar *cv, VynMutex *m);
bool        vyn_condvar_wait_ms (VynCondVar *cv, VynMutex *m, vyn_i32 ms);
void        vyn_condvar_signal  (VynCondVar *cv);
void        vyn_condvar_broadcast(VynCondVar *cv);
void        vyn_condvar_free    (VynCondVar *cv);

/* Atomic operations (subset) */
vyn_i32  vyn_atomic_load_i32  (volatile vyn_i32 *ptr);
void     vyn_atomic_store_i32 (volatile vyn_i32 *ptr, vyn_i32 val);
vyn_i32  vyn_atomic_add_i32   (volatile vyn_i32 *ptr, vyn_i32 delta);
vyn_i32  vyn_atomic_cas_i32   (volatile vyn_i32 *ptr, vyn_i32 expected, vyn_i32 desired);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Random  (xoshiro256** — fast, good quality)
 * ═══════════════════════════════════════════════════════════════════════════ */

void    vyn_rand_seed    (vyn_u64 seed);
vyn_u64 vyn_rand_u64     (void);
vyn_i32 vyn_rand_i32     (void);
vyn_f32 vyn_rand_f32     (void);   /* [0.0, 1.0) */
vyn_i32 vyn_rand_range   (vyn_i32 lo, vyn_i32 hi);  /* [lo, hi) */

/* ═══════════════════════════════════════════════════════════════════════════
 *  Hash utilities  (vyn_rt.c / vyn_hashmap.c)
 * ═══════════════════════════════════════════════════════════════════════════ */

vyn_u32  vyn_hash_crc32   (const uint8_t *buf, size_t len);
vyn_u64  vyn_hash_fnv1a_64(const uint8_t *buf, size_t len);
void     vyn_hash_sha256  (const uint8_t *buf, size_t len, uint8_t out[32]);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Crypto  (basic)
 * ═══════════════════════════════════════════════════════════════════════════ */

VynStr *vyn_crypto_sha256_hex   (const VynStr *input);
VynStr *vyn_crypto_base64_encode(const uint8_t *buf, size_t len);
bool    vyn_crypto_base64_decode(const char *src, uint8_t **out, size_t *out_len);

/* ═══════════════════════════════════════════════════════════════════════════
 *  FFI helpers
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Convert between Vyn types and C types for FFI */
vyn_i32  vyn_ffi_to_i32  (void *val);
vyn_f32  vyn_ffi_to_f32  (void *val);
vyn_bool vyn_ffi_to_bool (void *val);
VynStr  *vyn_ffi_to_str  (void *val);
void    *vyn_ffi_from_i32(vyn_i32 n);
void    *vyn_ffi_from_f32(vyn_f32 f);
void    *vyn_ffi_from_bool(vyn_bool b);
void    *vyn_ffi_from_str(const VynStr *s);

/* Dynamically load a shared library */
void    *vyn_ffi_dlopen  (const char *path);
void    *vyn_ffi_dlsym   (void *handle, const char *symbol);
void     vyn_ffi_dlclose (void *handle);

/* ═══════════════════════════════════════════════════════════════════════════
 *  Runtime initialisation
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Call once at program start. Sets up GC, allocator, random seed, etc. */
void vyn_runtime_init  (int argc, char **argv);

/* Call at program end. Runs finalizers, prints profiling report if enabled. */
void vyn_runtime_fini  (void);

/* argc / argv accessible globally */
extern int    vyn_argc;
extern char **vyn_argv;

/* ═══════════════════════════════════════════════════════════════════════════
 *  Generated code helpers
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Box a primitive into a GC-managed pointer */
vyn_i32 *vyn_box_i32  (vyn_i32 n);
vyn_f32 *vyn_box_f32  (vyn_f32 f);
vyn_bool*vyn_box_bool (vyn_bool b);

/* Unbox */
#define VYN_UNBOX_I32(p)   (*(vyn_i32 *)(p))
#define VYN_UNBOX_F32(p)   (*(vyn_f32 *)(p))
#define VYN_UNBOX_BOOL(p)  (*(vyn_bool*)(p))

/* Integer overflow-safe arithmetic (wrapping) */
VYN_INLINE vyn_i32 vyn_add_i32(vyn_i32 a, vyn_i32 b) { return a + b; }
VYN_INLINE vyn_i32 vyn_sub_i32(vyn_i32 a, vyn_i32 b) { return a - b; }
VYN_INLINE vyn_i32 vyn_mul_i32(vyn_i32 a, vyn_i32 b) { return a * b; }
VYN_INLINE vyn_i32 vyn_div_i32(vyn_i32 a, vyn_i32 b) {
    if (VYN_UNLIKELY(b == 0)) vyn_panic("division by zero");
    return a / b;
}
VYN_INLINE vyn_i32 vyn_mod_i32(vyn_i32 a, vyn_i32 b) {
    if (VYN_UNLIKELY(b == 0)) vyn_panic("modulo by zero");
    return a % b;
}

VYN_INLINE vyn_f32 vyn_div_f32(vyn_f32 a, vyn_f32 b) { return b != 0.0f ? a / b : 0.0f; }
VYN_INLINE vyn_f64 vyn_div_f64(vyn_f64 a, vyn_f64 b) { return b != 0.0  ? a / b : 0.0;  }

/* Bounds-checked array index */
VYN_INLINE void *vyn_array_get(void **arr, size_t len, size_t idx) {
    if (VYN_UNLIKELY(idx >= len))
        vyn_panic("array index %zu out of bounds (len=%zu)", idx, len);
    return arr[idx];
}

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* VYN_RT_H */