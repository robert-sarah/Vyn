/* vyn_ffi.hpp — Vyn FFI Bridge (C++)
 * Complete Foreign Function Interface: dynamic loading, type marshaling,
 * C/C++ interop, Python bridge, struct layout, callback support
 */

#pragma once
#ifndef VYN_FFI_HPP
#define VYN_FFI_HPP

#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <memory>
#include <variant>
#include <optional>
#include <stdexcept>
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <type_traits>

extern "C" {
#include "vyn_rt.h"
}

#ifdef _WIN32
#  include <windows.h>
#  define VYN_SOEXT ".dll"
#  define VYN_SOPREFIX ""
#else
#  include <dlfcn.h>
#  ifdef __APPLE__
#    define VYN_SOEXT ".dylib"
#  else
#    define VYN_SOEXT ".so"
#  endif
#  define VYN_SOPREFIX "lib"
#endif

namespace vyn {
namespace ffi {

// ═══════════════════════════════════════════════════════════════════════════
//  FFI Type System
// ═══════════════════════════════════════════════════════════════════════════

enum class FfiKind : uint8_t {
    Void,
    I8, I16, I32, I64,
    U8, U16, U32, U64,
    F32, F64,
    Bool,
    Ptr,          // raw pointer (void*)
    Str,          // null-terminated C string (char*)
    Struct,       // by-value struct (layout described separately)
    Callback,     // function pointer
    Array,        // pointer + length
};

// A single FFI value (discriminated union)
struct FfiValue {
    FfiKind kind = FfiKind::Void;

    union Data {
        int8_t   i8;
        int16_t  i16;
        int32_t  i32;
        int64_t  i64;
        uint8_t  u8;
        uint16_t u16;
        uint32_t u32;
        uint64_t u64;
        float    f32;
        double   f64;
        bool     b;
        void    *ptr;
        const char *cstr;
    } data{};

    // ── Constructors ───────────────────────────────────────────────────────
    static FfiValue from_void()         { return { FfiKind::Void,   {} }; }
    static FfiValue from_i8  (int8_t v) { FfiValue r; r.kind=FfiKind::I8;  r.data.i8 =v; return r; }
    static FfiValue from_i16 (int16_t v){ FfiValue r; r.kind=FfiKind::I16; r.data.i16=v; return r; }
    static FfiValue from_i32 (int32_t v){ FfiValue r; r.kind=FfiKind::I32; r.data.i32=v; return r; }
    static FfiValue from_i64 (int64_t v){ FfiValue r; r.kind=FfiKind::I64; r.data.i64=v; return r; }
    static FfiValue from_u8  (uint8_t v){ FfiValue r; r.kind=FfiKind::U8;  r.data.u8 =v; return r; }
    static FfiValue from_u16 (uint16_t v){FfiValue r; r.kind=FfiKind::U16; r.data.u16=v; return r; }
    static FfiValue from_u32 (uint32_t v){FfiValue r; r.kind=FfiKind::U32; r.data.u32=v; return r; }
    static FfiValue from_u64 (uint64_t v){FfiValue r; r.kind=FfiKind::U64; r.data.u64=v; return r; }
    static FfiValue from_f32 (float v)  { FfiValue r; r.kind=FfiKind::F32; r.data.f32=v; return r; }
    static FfiValue from_f64 (double v) { FfiValue r; r.kind=FfiKind::F64; r.data.f64=v; return r; }
    static FfiValue from_bool(bool v)   { FfiValue r; r.kind=FfiKind::Bool;r.data.b  =v; return r; }
    static FfiValue from_ptr (void *v)  { FfiValue r; r.kind=FfiKind::Ptr; r.data.ptr=v; return r; }
    static FfiValue from_str (const char *v){ FfiValue r; r.kind=FfiKind::Str; r.data.cstr=v; return r; }

    // ── Extractors ─────────────────────────────────────────────────────────
    int32_t  as_i32()  const { return (kind==FfiKind::I32)?data.i32:(int32_t)data.i64; }
    int64_t  as_i64()  const { return (kind==FfiKind::I64)?data.i64:(int64_t)data.i32; }
    uint32_t as_u32()  const { return (kind==FfiKind::U32)?data.u32:(uint32_t)data.u64;}
    uint64_t as_u64()  const { return (kind==FfiKind::U64)?data.u64:(uint64_t)data.u32;}
    float    as_f32()  const { return (kind==FfiKind::F32)?data.f32:(float)data.f64;   }
    double   as_f64()  const { return (kind==FfiKind::F64)?data.f64:(double)data.f32;  }
    bool     as_bool() const { return data.b; }
    void    *as_ptr()  const { return data.ptr; }
    const char *as_str() const { return data.cstr ? data.cstr : ""; }

    bool is_numeric() const {
        return kind >= FfiKind::I8 && kind <= FfiKind::F64;
    }
    bool is_void() const { return kind == FfiKind::Void; }
};

// ═══════════════════════════════════════════════════════════════════════════
//  Struct Layout Descriptor
// ═══════════════════════════════════════════════════════════════════════════

struct StructField {
    std::string name;
    FfiKind     kind;
    size_t      offset;   // byte offset within struct
    size_t      size;     // byte size
};

struct StructLayout {
    std::string              name;
    size_t                   total_size;
    size_t                   alignment;
    std::vector<StructField> fields;

    // Build a layout from field descriptions (automatic alignment)
    static StructLayout build(const std::string& name,
                               const std::vector<std::pair<std::string, FfiKind>>& fields);

    // Read / write a field
    FfiValue read_field (const void *buf, const std::string& field_name) const;
    void     write_field(void *buf, const std::string& field_name, FfiValue val) const;

    // Allocate a zeroed struct on the heap
    void *alloc() const;
    void  free_buf(void *buf) const;
};

// Field size helper
inline size_t ffi_kind_size(FfiKind k) {
    switch (k) {
        case FfiKind::Void:     return 0;
        case FfiKind::I8:
        case FfiKind::U8:
        case FfiKind::Bool:     return 1;
        case FfiKind::I16:
        case FfiKind::U16:      return 2;
        case FfiKind::I32:
        case FfiKind::U32:
        case FfiKind::F32:      return 4;
        case FfiKind::I64:
        case FfiKind::U64:
        case FfiKind::F64:
        case FfiKind::Ptr:
        case FfiKind::Str:
        case FfiKind::Callback: return 8;
        default:                return 0;
    }
}

inline size_t ffi_kind_align(FfiKind k) {
    size_t sz = ffi_kind_size(k);
    return sz == 0 ? 1 : sz;
}

// ═══════════════════════════════════════════════════════════════════════════
//  Function Signature Descriptor
// ═══════════════════════════════════════════════════════════════════════════

struct FfiSignature {
    FfiKind              return_kind;
    std::vector<FfiKind> param_kinds;
    std::string          name;
    bool                 variadic = false;

    size_t arity() const { return param_kinds.size(); }
};

// ═══════════════════════════════════════════════════════════════════════════
//  Dynamic Library Handle
// ═══════════════════════════════════════════════════════════════════════════

class DynLib {
public:
    explicit DynLib(const std::string& path);
    ~DynLib();

    DynLib(const DynLib&) = delete;
    DynLib(DynLib&& o) noexcept;

    // Look up a symbol
    void *sym(const std::string& name) const;

    // Look up with error on failure
    void *sym_required(const std::string& name) const;

    bool      is_open()  const { return handle_ != nullptr; }
    const std::string& path() const { return path_; }
    const std::string& error() const { return error_; }

private:
    void       *handle_ = nullptr;
    std::string path_;
    std::string error_;
};

// ═══════════════════════════════════════════════════════════════════════════
//  FFI Caller  (portable call dispatcher using platform ABI)
// ═══════════════════════════════════════════════════════════════════════════

// We use a simple approach: libffi if available, otherwise manual for common
// cases. For the Vyn interpreter we provide a simpler trampoline.

class FfiCaller {
public:
    // Call a C function with the given signature and arguments
    // fn_ptr  : raw function pointer (from dlsym or static link)
    // sig     : function signature
    // args    : argument values
    // returns : FfiValue with the return value
    static FfiValue call(void *fn_ptr, const FfiSignature& sig,
                          const std::vector<FfiValue>& args);

private:
    // Platform-specific call implementations
    static FfiValue call_i32_ret(void *fn, const std::vector<FfiValue>& args);
    static FfiValue call_i64_ret(void *fn, const std::vector<FfiValue>& args);
    static FfiValue call_f32_ret(void *fn, const std::vector<FfiValue>& args);
    static FfiValue call_f64_ret(void *fn, const std::vector<FfiValue>& args);
    static FfiValue call_ptr_ret(void *fn, const std::vector<FfiValue>& args);
    static FfiValue call_void_ret(void *fn, const std::vector<FfiValue>& args);
};

// ═══════════════════════════════════════════════════════════════════════════
//  Callback support (C → Vyn)
// ═══════════════════════════════════════════════════════════════════════════

// Callback thunk: wraps a std::function and provides a C-callable pointer
// Limited to a set of fixed arities (0–4 arguments).

using CallbackFn = std::function<FfiValue(std::vector<FfiValue>)>;

struct CallbackThunk {
    uint64_t   id;
    CallbackFn fn;
    FfiKind    ret_kind;
    std::vector<FfiKind> param_kinds;
};

// Registry of active callback thunks
class CallbackRegistry {
public:
    static CallbackRegistry& instance();

    uint64_t register_callback(CallbackFn fn, FfiKind ret,
                                const std::vector<FfiKind>& params);
    void     unregister(uint64_t id);

    CallbackThunk *get(uint64_t id);

    // Get a C function pointer for the thunk (only for fixed signatures)
    void *get_fn_ptr(uint64_t id);

private:
    std::unordered_map<uint64_t, CallbackThunk> thunks_;
    uint64_t next_id_ = 1;
    std::mutex mtx_;
};

// ═══════════════════════════════════════════════════════════════════════════
//  FFI Registry  (named functions across loaded libraries)
// ═══════════════════════════════════════════════════════════════════════════

struct FfiEntry {
    std::string   name;
    void         *fn_ptr;
    FfiSignature  sig;
    std::string   lib_path;
};

class FfiRegistry {
public:
    static FfiRegistry& instance();

    // Load a shared library and register all explicitly declared functions
    bool load_lib(const std::string& path,
                  const std::vector<std::pair<std::string, FfiSignature>>& exports);

    // Register a static (already linked) function
    void register_fn(const std::string& name, void *fn_ptr, FfiSignature sig);

    // Look up by name
    const FfiEntry *find(const std::string& name) const;

    // Call by name
    FfiValue call(const std::string& name, const std::vector<FfiValue>& args);

    // List all registered function names
    std::vector<std::string> list_fns() const;

    // Register a struct layout
    void register_struct(const StructLayout& layout);
    const StructLayout *find_struct(const std::string& name) const;

private:
    std::unordered_map<std::string, FfiEntry>  entries_;
    std::unordered_map<std::string, DynLib*>   libs_;
    std::unordered_map<std::string, StructLayout> structs_;
    mutable std::mutex mtx_;
};

// ═══════════════════════════════════════════════════════════════════════════
//  Type marshaling helpers (Vyn ↔ C)
// ═══════════════════════════════════════════════════════════════════════════

// Convert a VynStr* to a const char* (borrows the internal buffer)
inline const char *marshal_str_to_c(const VynStr *s) {
    return vyn_str_cstr(s);
}

// Convert a C string to a VynStr*
inline VynStr *marshal_str_from_c(const char *s) {
    return vyn_str_from(s);
}

// Convert a VynVec* to a raw C array (returns pointer to data and fills len)
inline void **marshal_vec_to_c(const VynVec *v, size_t *out_len) {
    if (out_len) *out_len = v->len;
    return v->data;
}

// Wrap a C array as a VynVec (copies pointers, does NOT copy data)
VynVec *marshal_vec_from_c(void **data, size_t len, uint32_t elem_type);

// Marshal a VynHashMap* to a flat key-value C array
// Returns: [key0, val0, key1, val1, ...] as void** with len = 2 * map->len
void **marshal_map_to_c(const VynHashMap *m, size_t *out_pair_count);

// ═══════════════════════════════════════════════════════════════════════════
//  Python bridge (call Python functions from Vyn via ctypes/cffi)
// ═══════════════════════════════════════════════════════════════════════════

// Python function pointer (called via ctypes trampoline)
using PythonFn = FfiValue(*)(const std::vector<FfiValue>&);

class PythonBridge {
public:
    static PythonBridge& instance();

    // Register a Python-side callable (provided as a function pointer via ctypes)
    uint64_t register_py_fn(const std::string& name, void *fn_ptr, FfiSignature sig);

    // Call a Python function by name
    FfiValue call_py(const std::string& name, const std::vector<FfiValue>& args);

    // Check if a Python function is registered
    bool has(const std::string& name) const;

    // Unregister
    void unregister(const std::string& name);

private:
    struct PyEntry {
        std::string  name;
        void        *fn_ptr;
        FfiSignature sig;
    };
    std::unordered_map<std::string, PyEntry> entries_;
    mutable std::mutex mtx_;
};

// ═══════════════════════════════════════════════════════════════════════════
//  C-compatible API  (used from Python via ctypes)
// ═══════════════════════════════════════════════════════════════════════════

extern "C" {

// ── Library loading ──────────────────────────────────────────────────────

// Load a shared library, returns handle id (0 on failure)
uint64_t vyn_ffi_load_lib     (const char *path);
void     vyn_ffi_unload_lib   (uint64_t handle_id);

// Get function pointer from loaded library
void    *vyn_ffi_get_sym      (uint64_t handle_id, const char *symbol);

// ── Simplified call API ──────────────────────────────────────────────────

// Call a C function with up to 8 arguments, returning i64
// arg_kinds: array of FfiKind values for each argument
// args_i64:  argument values as int64_t (cast from actual type)
int64_t  vyn_ffi_call_i64(void *fn_ptr,
                            const uint8_t *arg_kinds, const int64_t *args,
                            size_t argc);

double   vyn_ffi_call_f64(void *fn_ptr,
                            const uint8_t *arg_kinds, const int64_t *args,
                            size_t argc);

void    *vyn_ffi_call_ptr(void *fn_ptr,
                            const uint8_t *arg_kinds, const int64_t *args,
                            size_t argc);

void     vyn_ffi_call_void(void *fn_ptr,
                            const uint8_t *arg_kinds, const int64_t *args,
                            size_t argc);

// ── Struct layout ────────────────────────────────────────────────────────

uint64_t vyn_ffi_struct_define  (const char *name, const char **field_names,
                                  const uint8_t *field_kinds, size_t field_count);
void    *vyn_ffi_struct_alloc   (uint64_t struct_id);
void     vyn_ffi_struct_free    (void *buf);
int64_t  vyn_ffi_struct_get_i64 (void *buf, uint64_t struct_id, const char *field);
double   vyn_ffi_struct_get_f64 (void *buf, uint64_t struct_id, const char *field);
void    *vyn_ffi_struct_get_ptr (void *buf, uint64_t struct_id, const char *field);
void     vyn_ffi_struct_set_i64 (void *buf, uint64_t struct_id, const char *field, int64_t val);
void     vyn_ffi_struct_set_f64 (void *buf, uint64_t struct_id, const char *field, double val);
void     vyn_ffi_struct_set_ptr (void *buf, uint64_t struct_id, const char *field, void *val);

// ── Python bridge ────────────────────────────────────────────────────────

void     vyn_ffi_py_register(const char *name, void *fn_ptr,
                               uint8_t ret_kind,
                               const uint8_t *param_kinds, size_t param_count);
int64_t  vyn_ffi_py_call_i64(const char *name,
                               const int64_t *args, size_t argc);
double   vyn_ffi_py_call_f64(const char *name,
                               const int64_t *args, size_t argc);

// ── Marshal helpers ──────────────────────────────────────────────────────

// Allocate a C string copy (caller must free with vyn_ffi_cstr_free)
char    *vyn_ffi_vynstr_to_cstr(VynStr *s);
void     vyn_ffi_cstr_free     (char *s);
VynStr  *vyn_ffi_cstr_to_vynstr(const char *s);

// ── Inspect ──────────────────────────────────────────────────────────────

const char *vyn_ffi_version(void);

} // extern "C"

// ═══════════════════════════════════════════════════════════════════════════
//  Convenience macros for declaring FFI imports in Vyn codegen
// ═══════════════════════════════════════════════════════════════════════════

// Usage in generated C++ code:
//   VYN_EXTERN_FN(sin, FfiKind::F64, {FfiKind::F64});
#define VYN_EXTERN_FN(name, ret_kind, param_kinds_init)  \
    do {                                                  \
        static bool _reg_##name = false;                  \
        if (!_reg_##name) {                               \
            vyn::ffi::FfiSignature sig;                   \
            sig.name        = #name;                      \
            sig.return_kind = (ret_kind);                 \
            sig.param_kinds = (param_kinds_init);         \
            vyn::ffi::FfiRegistry::instance().register_fn(\
                #name, (void *)(&name), sig);             \
            _reg_##name = true;                           \
        }                                                 \
    } while(0)

// ═══════════════════════════════════════════════════════════════════════════
//  RAII guard for loaded libraries
// ═══════════════════════════════════════════════════════════════════════════

class LibGuard {
public:
    explicit LibGuard(const std::string& path) : lib_(path) {}
    ~LibGuard() = default;

    bool      ok()    const { return lib_.is_open(); }
    void     *sym(const std::string& name) { return lib_.sym(name); }
    DynLib&   lib()         { return lib_; }

private:
    DynLib lib_;
};

} // namespace ffi
} // namespace vyn

#endif // VYN_FFI_HPP