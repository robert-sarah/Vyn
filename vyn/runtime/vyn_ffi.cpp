/* vyn_ffi.cpp — Vyn FFI Bridge Implementation
 * DynLib, StructLayout, FfiCaller, FfiRegistry, PythonBridge, C-API
 */

#include "vyn_ffi.hpp"
#include <cstring>
#include <cstdio>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <stdexcept>

// ─── DynLib ───────────────────────────────────────────────────────────────────

namespace vyn { namespace ffi {

DynLib::DynLib(const std::string& path) : path_(path) {
#ifdef _WIN32
    handle_ = (void *)LoadLibraryA(path.c_str());
    if (!handle_) {
        char buf[256];
        snprintf(buf, sizeof(buf), "LoadLibrary failed: %lu", GetLastError());
        error_ = buf;
    }
#else
    handle_ = dlopen(path.c_str(), RTLD_LAZY | RTLD_LOCAL);
    if (!handle_) {
        const char *e = dlerror();
        error_ = e ? e : "unknown error";
    }
#endif
}

DynLib::~DynLib() {
    if (handle_) {
#ifdef _WIN32
        FreeLibrary((HMODULE)handle_);
#else
        dlclose(handle_);
#endif
        handle_ = nullptr;
    }
}

DynLib::DynLib(DynLib&& o) noexcept
    : handle_(o.handle_), path_(std::move(o.path_)), error_(std::move(o.error_)) {
    o.handle_ = nullptr;
}

void *DynLib::sym(const std::string& name) const {
    if (!handle_) return nullptr;
#ifdef _WIN32
    return (void *)GetProcAddress((HMODULE)handle_, name.c_str());
#else
    return dlsym(handle_, name.c_str());
#endif
}

void *DynLib::sym_required(const std::string& name) const {
    void *p = sym(name);
    if (!p) throw std::runtime_error("Symbol not found: " + name);
    return p;
}

// ─── StructLayout ─────────────────────────────────────────────────────────────

StructLayout StructLayout::build(const std::string& name,
    const std::vector<std::pair<std::string, FfiKind>>& fields)
{
    StructLayout layout;
    layout.name      = name;
    size_t offset    = 0;
    size_t max_align = 1;

    for (auto& [fname, kind] : fields) {
        size_t sz    = ffi_kind_size(kind);
        size_t align = ffi_kind_align(kind);
        if (align > max_align) max_align = align;

        // Pad to alignment
        if (align > 0 && offset % align != 0)
            offset += align - (offset % align);

        StructField f;
        f.name   = fname;
        f.kind   = kind;
        f.offset = offset;
        f.size   = sz;
        layout.fields.push_back(f);
        offset += sz;
    }

    // Final padding to struct alignment
    if (max_align > 0 && offset % max_align != 0)
        offset += max_align - (offset % max_align);

    layout.total_size = offset;
    layout.alignment  = max_align;
    return layout;
}

FfiValue StructLayout::read_field(const void *buf, const std::string& field_name) const {
    for (auto& f : fields) {
        if (f.name != field_name) continue;
        const uint8_t *p = (const uint8_t *)buf + f.offset;
        switch (f.kind) {
            case FfiKind::I8:   { int8_t  v; memcpy(&v,p,1); return FfiValue::from_i8(v);  }
            case FfiKind::I16:  { int16_t v; memcpy(&v,p,2); return FfiValue::from_i16(v); }
            case FfiKind::I32:  { int32_t v; memcpy(&v,p,4); return FfiValue::from_i32(v); }
            case FfiKind::I64:  { int64_t v; memcpy(&v,p,8); return FfiValue::from_i64(v); }
            case FfiKind::U8:   { uint8_t  v; memcpy(&v,p,1); return FfiValue::from_u8(v);  }
            case FfiKind::U16:  { uint16_t v; memcpy(&v,p,2); return FfiValue::from_u16(v); }
            case FfiKind::U32:  { uint32_t v; memcpy(&v,p,4); return FfiValue::from_u32(v); }
            case FfiKind::U64:  { uint64_t v; memcpy(&v,p,8); return FfiValue::from_u64(v); }
            case FfiKind::F32:  { float  v; memcpy(&v,p,4); return FfiValue::from_f32(v); }
            case FfiKind::F64:  { double v; memcpy(&v,p,8); return FfiValue::from_f64(v); }
            case FfiKind::Bool: { bool v = *(p) != 0; return FfiValue::from_bool(v); }
            case FfiKind::Ptr:
            case FfiKind::Str:
            case FfiKind::Callback: {
                void *v; memcpy(&v,p,sizeof(void*));
                return (f.kind == FfiKind::Str)
                    ? FfiValue::from_str((const char*)v)
                    : FfiValue::from_ptr(v);
            }
            default: return FfiValue::from_void();
        }
    }
    return FfiValue::from_void();
}

void StructLayout::write_field(void *buf, const std::string& field_name, FfiValue val) const {
    for (auto& f : fields) {
        if (f.name != field_name) continue;
        uint8_t *p = (uint8_t *)buf + f.offset;
        switch (f.kind) {
            case FfiKind::I8:   { int8_t  v=(int8_t)val.as_i32();  memcpy(p,&v,1); break; }
            case FfiKind::I16:  { int16_t v=(int16_t)val.as_i32(); memcpy(p,&v,2); break; }
            case FfiKind::I32:  { int32_t v=val.as_i32();          memcpy(p,&v,4); break; }
            case FfiKind::I64:  { int64_t v=val.as_i64();          memcpy(p,&v,8); break; }
            case FfiKind::U8:   { uint8_t  v=(uint8_t)val.as_u32();  memcpy(p,&v,1); break; }
            case FfiKind::U16:  { uint16_t v=(uint16_t)val.as_u32(); memcpy(p,&v,2); break; }
            case FfiKind::U32:  { uint32_t v=val.as_u32();           memcpy(p,&v,4); break; }
            case FfiKind::U64:  { uint64_t v=val.as_u64();           memcpy(p,&v,8); break; }
            case FfiKind::F32:  { float  v=val.as_f32(); memcpy(p,&v,4); break; }
            case FfiKind::F64:  { double v=val.as_f64(); memcpy(p,&v,8); break; }
            case FfiKind::Bool: { bool v=val.as_bool(); *p=(uint8_t)v;  break; }
            case FfiKind::Ptr:
            case FfiKind::Str:
            case FfiKind::Callback: {
                void *v=val.as_ptr(); memcpy(p,&v,sizeof(void*)); break;
            }
            default: break;
        }
        return;
    }
}

void *StructLayout::alloc() const {
    return calloc(1, total_size > 0 ? total_size : 1);
}

void StructLayout::free_buf(void *buf) const {
    free(buf);
}

// ─── FfiCaller (portable 0–4 arg dispatch) ────────────────────────────────────

// We implement a manual dispatcher for common signatures.
// For production use, libffi would be used instead.

using Fn0_i64  = int64_t(*)();
using Fn1_i64  = int64_t(*)(int64_t);
using Fn2_i64  = int64_t(*)(int64_t,int64_t);
using Fn3_i64  = int64_t(*)(int64_t,int64_t,int64_t);
using Fn4_i64  = int64_t(*)(int64_t,int64_t,int64_t,int64_t);
using Fn5_i64  = int64_t(*)(int64_t,int64_t,int64_t,int64_t,int64_t);
using Fn6_i64  = int64_t(*)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);
using Fn7_i64  = int64_t(*)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);
using Fn8_i64  = int64_t(*)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);

using Fn0_f64  = double(*)();
using Fn1_f64  = double(*)(double);
using Fn2_f64  = double(*)(double,double);
using Fn3_f64  = double(*)(double,double,double);

using Fn0_ptr  = void*(*)();
using Fn1_ptr  = void*(*)(void*);
using Fn2_ptr  = void*(*)(void*,void*);
using Fn3_ptr  = void*(*)(void*,void*,void*);

using Fn0_void = void(*)();
using Fn1_void = void(*)(int64_t);
using Fn2_void = void(*)(int64_t,int64_t);
using Fn3_void = void(*)(int64_t,int64_t,int64_t);
using Fn4_void = void(*)(int64_t,int64_t,int64_t,int64_t);

static int64_t arg_as_i64(const FfiValue& v) {
    switch (v.kind) {
        case FfiKind::I8:   return v.data.i8;
        case FfiKind::I16:  return v.data.i16;
        case FfiKind::I32:  return v.data.i32;
        case FfiKind::I64:  return v.data.i64;
        case FfiKind::U8:   return v.data.u8;
        case FfiKind::U16:  return v.data.u16;
        case FfiKind::U32:  return v.data.u32;
        case FfiKind::U64:  return (int64_t)v.data.u64;
        case FfiKind::F32:  { int32_t r; memcpy(&r,&v.data.f32,4); return r; }
        case FfiKind::F64:  { int64_t r; memcpy(&r,&v.data.f64,8); return r; }
        case FfiKind::Bool: return v.data.b ? 1 : 0;
        case FfiKind::Ptr:
        case FfiKind::Str:
        case FfiKind::Callback: return (int64_t)(uintptr_t)v.data.ptr;
        default: return 0;
    }
}

FfiValue FfiCaller::call_i64_ret(void *fn, const std::vector<FfiValue>& args) {
    int64_t a[8] = {};
    size_t n = std::min(args.size(), (size_t)8);
    for (size_t i = 0; i < n; i++) a[i] = arg_as_i64(args[i]);

    int64_t result = 0;
    switch (n) {
        case 0: result = ((Fn0_i64)fn)(); break;
        case 1: result = ((Fn1_i64)fn)(a[0]); break;
        case 2: result = ((Fn2_i64)fn)(a[0],a[1]); break;
        case 3: result = ((Fn3_i64)fn)(a[0],a[1],a[2]); break;
        case 4: result = ((Fn4_i64)fn)(a[0],a[1],a[2],a[3]); break;
        case 5: result = ((Fn5_i64)fn)(a[0],a[1],a[2],a[3],a[4]); break;
        case 6: result = ((Fn6_i64)fn)(a[0],a[1],a[2],a[3],a[4],a[5]); break;
        case 7: result = ((Fn7_i64)fn)(a[0],a[1],a[2],a[3],a[4],a[5],a[6]); break;
        default: result = ((Fn8_i64)fn)(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7]); break;
    }
    return FfiValue::from_i64(result);
}

FfiValue FfiCaller::call_f64_ret(void *fn, const std::vector<FfiValue>& args) {
    double result = 0.0;
    size_t n = args.size();
    if (n == 0)      result = ((Fn0_f64)fn)();
    else if (n == 1) result = ((Fn1_f64)fn)(args[0].as_f64());
    else if (n == 2) result = ((Fn2_f64)fn)(args[0].as_f64(), args[1].as_f64());
    else if (n >= 3) result = ((Fn3_f64)fn)(args[0].as_f64(), args[1].as_f64(), args[2].as_f64());
    return FfiValue::from_f64(result);
}

FfiValue FfiCaller::call_ptr_ret(void *fn, const std::vector<FfiValue>& args) {
    void *result = nullptr;
    size_t n = args.size();
    if (n == 0)      result = ((Fn0_ptr)fn)();
    else if (n == 1) result = ((Fn1_ptr)fn)(args[0].as_ptr());
    else if (n == 2) result = ((Fn2_ptr)fn)(args[0].as_ptr(), args[1].as_ptr());
    else if (n >= 3) result = ((Fn3_ptr)fn)(args[0].as_ptr(), args[1].as_ptr(), args[2].as_ptr());
    return FfiValue::from_ptr(result);
}

FfiValue FfiCaller::call_void_ret(void *fn, const std::vector<FfiValue>& args) {
    int64_t a[8] = {};
    size_t n = std::min(args.size(), (size_t)8);
    for (size_t i = 0; i < n; i++) a[i] = arg_as_i64(args[i]);
    switch (n) {
        case 0: ((Fn0_void)fn)(); break;
        case 1: ((Fn1_void)fn)(a[0]); break;
        case 2: ((Fn2_void)fn)(a[0],a[1]); break;
        case 3: ((Fn3_void)fn)(a[0],a[1],a[2]); break;
        default: ((Fn4_void)fn)(a[0],a[1],a[2],a[3]); break;
    }
    return FfiValue::from_void();
}

FfiValue FfiCaller::call(void *fn_ptr, const FfiSignature& sig,
                          const std::vector<FfiValue>& args) {
    if (!fn_ptr) return FfiValue::from_void();
    switch (sig.return_kind) {
        case FfiKind::Void:                 return call_void_ret(fn_ptr, args);
        case FfiKind::F32:
        case FfiKind::F64:                  return call_f64_ret(fn_ptr, args);
        case FfiKind::Ptr:
        case FfiKind::Str:
        case FfiKind::Callback:             return call_ptr_ret(fn_ptr, args);
        default:                            return call_i64_ret(fn_ptr, args);
    }
}

// ─── CallbackRegistry ─────────────────────────────────────────────────────────

CallbackRegistry& CallbackRegistry::instance() {
    static CallbackRegistry inst;
    return inst;
}

uint64_t CallbackRegistry::register_callback(CallbackFn fn, FfiKind ret,
                                               const std::vector<FfiKind>& params) {
    std::lock_guard<std::mutex> lk(mtx_);
    uint64_t id = next_id_++;
    thunks_[id] = CallbackThunk{ id, std::move(fn), ret, params };
    return id;
}

void CallbackRegistry::unregister(uint64_t id) {
    std::lock_guard<std::mutex> lk(mtx_);
    thunks_.erase(id);
}

CallbackThunk *CallbackRegistry::get(uint64_t id) {
    std::lock_guard<std::mutex> lk(mtx_);
    auto it = thunks_.find(id);
    return it != thunks_.end() ? &it->second : nullptr;
}

void *CallbackRegistry::get_fn_ptr(uint64_t) {
    // Static thunks require platform-specific trampolines or libffi closures.
    // For now, return nullptr — callers should use the registry-based dispatch.
    return nullptr;
}

// ─── FfiRegistry ──────────────────────────────────────────────────────────────

FfiRegistry& FfiRegistry::instance() {
    static FfiRegistry inst;
    return inst;
}

bool FfiRegistry::load_lib(const std::string& path,
    const std::vector<std::pair<std::string, FfiSignature>>& exports)
{
    std::lock_guard<std::mutex> lk(mtx_);
    if (libs_.find(path) == libs_.end()) {
        auto *lib = new DynLib(path);
        if (!lib->is_open()) {
            delete lib;
            return false;
        }
        libs_[path] = lib;
    }
    DynLib *lib = libs_[path];
    for (auto& [name, sig] : exports) {
        void *sym = lib->sym(name);
        if (sym) {
            entries_[name] = FfiEntry{ name, sym, sig, path };
        }
    }
    return true;
}

void FfiRegistry::register_fn(const std::string& name, void *fn_ptr, FfiSignature sig) {
    std::lock_guard<std::mutex> lk(mtx_);
    entries_[name] = FfiEntry{ name, fn_ptr, std::move(sig), "" };
}

const FfiEntry *FfiRegistry::find(const std::string& name) const {
    std::lock_guard<std::mutex> lk(mtx_);
    auto it = entries_.find(name);
    return it != entries_.end() ? &it->second : nullptr;
}

FfiValue FfiRegistry::call(const std::string& name, const std::vector<FfiValue>& args) {
    const FfiEntry *e = find(name);
    if (!e) throw std::runtime_error("FFI function not found: " + name);
    return FfiCaller::call(e->fn_ptr, e->sig, args);
}

std::vector<std::string> FfiRegistry::list_fns() const {
    std::lock_guard<std::mutex> lk(mtx_);
    std::vector<std::string> names;
    names.reserve(entries_.size());
    for (auto& [k,v] : entries_) names.push_back(k);
    return names;
}

void FfiRegistry::register_struct(const StructLayout& layout) {
    std::lock_guard<std::mutex> lk(mtx_);
    structs_[layout.name] = layout;
}

const StructLayout *FfiRegistry::find_struct(const std::string& name) const {
    std::lock_guard<std::mutex> lk(mtx_);
    auto it = structs_.find(name);
    return it != structs_.end() ? &it->second : nullptr;
}

// ─── VynVec marshal helper ────────────────────────────────────────────────────

VynVec *marshal_vec_from_c(void **data, size_t len, uint32_t elem_type) {
    VynVec *v = vyn_vec_with_cap(elem_type, len);
    v->len = len;
    memcpy(v->data, data, len * sizeof(void *));
    return v;
}

void **marshal_map_to_c(const VynHashMap *m, size_t *out_pair_count) {
    size_t n = vyn_map_len(m);
    void **arr = (void **)malloc(n * 2 * sizeof(void *));
    if (!arr) { if (out_pair_count) *out_pair_count = 0; return nullptr; }
    struct Ctx { void **arr; size_t idx; };
    Ctx ctx{ arr, 0 };
    vyn_map_foreach((VynHashMap*)m, [](void *k, void *v, void *ud) -> bool {
        Ctx *c = (Ctx*)ud;
        c->arr[c->idx++] = k;
        c->arr[c->idx++] = v;
        return true;
    }, &ctx);
    if (out_pair_count) *out_pair_count = n;
    return arr;
}

// ─── PythonBridge ─────────────────────────────────────────────────────────────

PythonBridge& PythonBridge::instance() {
    static PythonBridge inst;
    return inst;
}

uint64_t PythonBridge::register_py_fn(const std::string& name, void *fn_ptr, FfiSignature sig) {
    std::lock_guard<std::mutex> lk(mtx_);
    entries_[name] = PyEntry{ name, fn_ptr, std::move(sig) };
    return 1;
}

FfiValue PythonBridge::call_py(const std::string& name, const std::vector<FfiValue>& args) {
    std::lock_guard<std::mutex> lk(mtx_);
    auto it = entries_.find(name);
    if (it == entries_.end()) throw std::runtime_error("Python fn not found: " + name);
    return FfiCaller::call(it->second.fn_ptr, it->second.sig, args);
}

bool PythonBridge::has(const std::string& name) const {
    std::lock_guard<std::mutex> lk(mtx_);
    return entries_.count(name) > 0;
}

void PythonBridge::unregister(const std::string& name) {
    std::lock_guard<std::mutex> lk(mtx_);
    entries_.erase(name);
}

// ─── C-API ────────────────────────────────────────────────────────────────────

extern "C" {

// ── struct descriptors indexed by id ─────────────────────────────────────────
static std::unordered_map<uint64_t, StructLayout> _struct_registry;
static std::unordered_map<uint64_t, DynLib*>      _lib_registry;
static uint64_t _next_struct_id = 1;
static uint64_t _next_lib_id    = 1;

// ── Library loading ───────────────────────────────────────────────────────────

uint64_t vyn_ffi_load_lib(const char *path) {
    DynLib *lib = new DynLib(path);
    if (!lib->is_open()) { delete lib; return 0; }
    uint64_t id = _next_lib_id++;
    _lib_registry[id] = lib;
    return id;
}

void vyn_ffi_unload_lib(uint64_t id) {
    auto it = _lib_registry.find(id);
    if (it != _lib_registry.end()) {
        delete it->second;
        _lib_registry.erase(it);
    }
}

void *vyn_ffi_get_sym(uint64_t handle_id, const char *symbol) {
    auto it = _lib_registry.find(handle_id);
    if (it == _lib_registry.end()) return nullptr;
    return it->second->sym(symbol);
}

// ── Simplified call API ───────────────────────────────────────────────────────

static std::vector<FfiValue> build_args(const uint8_t *arg_kinds, const int64_t *args, size_t argc) {
    std::vector<FfiValue> ffi_args;
    ffi_args.reserve(argc);
    for (size_t i = 0; i < argc; i++) {
        FfiKind k = (FfiKind)arg_kinds[i];
        switch (k) {
            case FfiKind::F32: { float f; memcpy(&f, &args[i], 4); ffi_args.push_back(FfiValue::from_f32(f)); break; }
            case FfiKind::F64: { double f; memcpy(&f, &args[i], 8); ffi_args.push_back(FfiValue::from_f64(f)); break; }
            case FfiKind::Ptr:
            case FfiKind::Str:
            case FfiKind::Callback: ffi_args.push_back(FfiValue::from_ptr((void*)(uintptr_t)args[i])); break;
            case FfiKind::Bool: ffi_args.push_back(FfiValue::from_bool(args[i] != 0)); break;
            default: ffi_args.push_back(FfiValue::from_i64(args[i])); break;
        }
    }
    return ffi_args;
}

int64_t vyn_ffi_call_i64(void *fn_ptr, const uint8_t *kinds, const int64_t *args, size_t argc) {
    if (!fn_ptr) return 0;
    auto ffi_args = build_args(kinds, args, argc);
    FfiSignature sig;
    sig.return_kind = FfiKind::I64;
    for (size_t i = 0; i < argc; i++) sig.param_kinds.push_back((FfiKind)kinds[i]);
    return FfiCaller::call(fn_ptr, sig, ffi_args).as_i64();
}

double vyn_ffi_call_f64(void *fn_ptr, const uint8_t *kinds, const int64_t *args, size_t argc) {
    if (!fn_ptr) return 0.0;
    auto ffi_args = build_args(kinds, args, argc);
    FfiSignature sig;
    sig.return_kind = FfiKind::F64;
    for (size_t i = 0; i < argc; i++) sig.param_kinds.push_back((FfiKind)kinds[i]);
    return FfiCaller::call(fn_ptr, sig, ffi_args).as_f64();
}

void *vyn_ffi_call_ptr(void *fn_ptr, const uint8_t *kinds, const int64_t *args, size_t argc) {
    if (!fn_ptr) return nullptr;
    auto ffi_args = build_args(kinds, args, argc);
    FfiSignature sig;
    sig.return_kind = FfiKind::Ptr;
    for (size_t i = 0; i < argc; i++) sig.param_kinds.push_back((FfiKind)kinds[i]);
    return FfiCaller::call(fn_ptr, sig, ffi_args).as_ptr();
}

void vyn_ffi_call_void(void *fn_ptr, const uint8_t *kinds, const int64_t *args, size_t argc) {
    if (!fn_ptr) return;
    auto ffi_args = build_args(kinds, args, argc);
    FfiSignature sig;
    sig.return_kind = FfiKind::Void;
    for (size_t i = 0; i < argc; i++) sig.param_kinds.push_back((FfiKind)kinds[i]);
    FfiCaller::call(fn_ptr, sig, ffi_args);
}

// ── Struct layout ─────────────────────────────────────────────────────────────

uint64_t vyn_ffi_struct_define(const char *name, const char **field_names,
                                const uint8_t *field_kinds, size_t field_count) {
    std::vector<std::pair<std::string, FfiKind>> fields;
    for (size_t i = 0; i < field_count; i++)
        fields.emplace_back(field_names[i], (FfiKind)field_kinds[i]);

    StructLayout layout = StructLayout::build(name ? name : "", fields);
    uint64_t id = _next_struct_id++;
    _struct_registry[id] = std::move(layout);
    return id;
}

void *vyn_ffi_struct_alloc(uint64_t struct_id) {
    auto it = _struct_registry.find(struct_id);
    if (it == _struct_registry.end()) return nullptr;
    return it->second.alloc();
}

void vyn_ffi_struct_free(void *buf) {
    free(buf);
}

static const StructLayout *find_struct(uint64_t id) {
    auto it = _struct_registry.find(id);
    return it != _struct_registry.end() ? &it->second : nullptr;
}

int64_t vyn_ffi_struct_get_i64(void *buf, uint64_t sid, const char *field) {
    auto *l = find_struct(sid);
    return l ? l->read_field(buf, field).as_i64() : 0;
}

double vyn_ffi_struct_get_f64(void *buf, uint64_t sid, const char *field) {
    auto *l = find_struct(sid);
    return l ? l->read_field(buf, field).as_f64() : 0.0;
}

void *vyn_ffi_struct_get_ptr(void *buf, uint64_t sid, const char *field) {
    auto *l = find_struct(sid);
    return l ? l->read_field(buf, field).as_ptr() : nullptr;
}

void vyn_ffi_struct_set_i64(void *buf, uint64_t sid, const char *field, int64_t val) {
    auto *l = find_struct(sid);
    if (l) l->write_field(buf, field, FfiValue::from_i64(val));
}

void vyn_ffi_struct_set_f64(void *buf, uint64_t sid, const char *field, double val) {
    auto *l = find_struct(sid);
    if (l) l->write_field(buf, field, FfiValue::from_f64(val));
}

void vyn_ffi_struct_set_ptr(void *buf, uint64_t sid, const char *field, void *val) {
    auto *l = find_struct(sid);
    if (l) l->write_field(buf, field, FfiValue::from_ptr(val));
}

// ── Python bridge ─────────────────────────────────────────────────────────────

void vyn_ffi_py_register(const char *name, void *fn_ptr, uint8_t ret_kind,
                          const uint8_t *param_kinds, size_t param_count) {
    FfiSignature sig;
    sig.name        = name;
    sig.return_kind = (FfiKind)ret_kind;
    for (size_t i = 0; i < param_count; i++)
        sig.param_kinds.push_back((FfiKind)param_kinds[i]);
    PythonBridge::instance().register_py_fn(name, fn_ptr, std::move(sig));
}

int64_t vyn_ffi_py_call_i64(const char *name, const int64_t *args, size_t argc) {
    std::vector<FfiValue> ffi_args;
    for (size_t i = 0; i < argc; i++) ffi_args.push_back(FfiValue::from_i64(args[i]));
    try {
        return PythonBridge::instance().call_py(name, ffi_args).as_i64();
    } catch (...) { return 0; }
}

double vyn_ffi_py_call_f64(const char *name, const int64_t *args, size_t argc) {
    std::vector<FfiValue> ffi_args;
    for (size_t i = 0; i < argc; i++) {
        double f; memcpy(&f, &args[i], 8);
        ffi_args.push_back(FfiValue::from_f64(f));
    }
    try {
        return PythonBridge::instance().call_py(name, ffi_args).as_f64();
    } catch (...) { return 0.0; }
}

// ── Marshal helpers ───────────────────────────────────────────────────────────

char *vyn_ffi_vynstr_to_cstr(VynStr *s) {
    if (!s) return nullptr;
    const char *src = vyn_str_cstr(s);
    size_t len = vyn_str_len(s);
    char *copy = (char *)malloc(len + 1);
    if (copy) { memcpy(copy, src, len); copy[len] = '\0'; }
    return copy;
}

void vyn_ffi_cstr_free(char *s) { free(s); }

VynStr *vyn_ffi_cstr_to_vynstr(const char *s) { return vyn_str_from(s); }

// ── Version ───────────────────────────────────────────────────────────────────

const char *vyn_ffi_version(void) { return "vyn_ffi 1.0.0 (Vyn Runtime)"; }

} // extern "C"

} // namespace ffi
} // namespace vyn