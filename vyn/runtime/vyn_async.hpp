/* vyn_async.hpp — Vyn Async Runtime (C++)
 * Coroutines, event loop, tasks, futures, channels
 * Compatible with C++20 coroutines and fallback for C++17
 */

#pragma once
#ifndef VYN_ASYNC_HPP
#define VYN_ASYNC_HPP

#include <functional>
#include <memory>
#include <vector>
#include <queue>
#include <deque>
#include <unordered_map>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <atomic>
#include <chrono>
#include <string>
#include <stdexcept>
#include <optional>
#include <variant>
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <algorithm>
#include <future>
#include <type_traits>

extern "C" {
#include "vyn_rt.h"
}

// ─── Version / Feature detection ──────────────────────────────────────────

#if __cplusplus >= 202002L
#  define VYN_HAS_COROUTINES 1
#  include <coroutine>
#else
#  define VYN_HAS_COROUTINES 0
#endif

namespace vyn {
namespace async {

// ═══════════════════════════════════════════════════════════════════════════
//  Forward declarations
// ═══════════════════════════════════════════════════════════════════════════

class EventLoop;
class Task;
class Timer;
template<typename T> class Future;
template<typename T> class Promise;
template<typename T, typename U> class Channel;

// Global event loop accessor
EventLoop& loop();

// ═══════════════════════════════════════════════════════════════════════════
//  Time utilities
// ═══════════════════════════════════════════════════════════════════════════

using Clock     = std::chrono::steady_clock;
using TimePoint = Clock::time_point;
using Duration  = std::chrono::duration<double, std::milli>;  // milliseconds

inline TimePoint now() { return Clock::now(); }

inline double elapsed_ms(TimePoint start) {
    return std::chrono::duration<double, std::milli>(now() - start).count();
}

// ═══════════════════════════════════════════════════════════════════════════
//  Task state
// ═══════════════════════════════════════════════════════════════════════════

enum class TaskState {
    Pending,
    Running,
    Suspended,
    Completed,
    Cancelled,
    Failed,
};

// ═══════════════════════════════════════════════════════════════════════════
//  Callable wrapper (type-erased async work unit)
// ═══════════════════════════════════════════════════════════════════════════

using WorkFn = std::function<void()>;

// ═══════════════════════════════════════════════════════════════════════════
//  Promise / Future  (simple one-shot)
// ═══════════════════════════════════════════════════════════════════════════

template<typename T>
class SharedState {
public:
    std::mutex              mtx;
    std::condition_variable cv;
    std::optional<T>        value;
    std::optional<std::string> error;
    std::vector<WorkFn>     continuations;
    bool                    ready = false;

    void set_value(T v) {
        std::vector<WorkFn> cbs;
        {
            std::lock_guard<std::mutex> lk(mtx);
            value = std::move(v);
            ready = true;
            cbs   = std::move(continuations);
        }
        cv.notify_all();
        for (auto& cb : cbs) cb();
    }

    void set_error(std::string msg) {
        std::vector<WorkFn> cbs;
        {
            std::lock_guard<std::mutex> lk(mtx);
            error = std::move(msg);
            ready = true;
            cbs   = std::move(continuations);
        }
        cv.notify_all();
        for (auto& cb : cbs) cb();
    }

    T get() {
        std::unique_lock<std::mutex> lk(mtx);
        cv.wait(lk, [&]{ return ready; });
        if (error) throw std::runtime_error(*error);
        return *value;
    }

    bool is_ready() const { return ready; }

    void then(WorkFn cb) {
        bool fire = false;
        {
            std::lock_guard<std::mutex> lk(mtx);
            if (ready) fire = true;
            else       continuations.push_back(cb);
        }
        if (fire) cb();
    }
};

template<typename T>
class Future {
public:
    using ValueType = T;

    explicit Future(std::shared_ptr<SharedState<T>> state)
        : state_(std::move(state)) {}

    Future() = default;
    Future(const Future&) = default;
    Future(Future&&)      = default;
    Future& operator=(const Future&) = default;
    Future& operator=(Future&&)      = default;

    bool   is_ready() const { return state_ && state_->is_ready(); }
    T      get()      const { return state_->get(); }

    // Register a continuation (runs when value is available)
    void then(WorkFn cb) { if (state_) state_->then(std::move(cb)); }

    // Block until ready and return value
    T await() { return get(); }

    // Transform value
    template<typename F>
    auto map(F&& fn) -> Future<std::invoke_result_t<F, T>> {
        using R = std::invoke_result_t<F, T>;
        auto [promise, future] = make_promise_future<R>();
        then([p = std::move(promise), fn = std::forward<F>(fn), st = state_]() mutable {
            try { p.set_value(fn(st->get())); }
            catch(std::exception& e) { p.set_error(e.what()); }
        });
        return future;
    }

    std::shared_ptr<SharedState<T>> state_;
};

template<typename T>
class Promise {
public:
    Promise() : state_(std::make_shared<SharedState<T>>()) {}

    Promise(const Promise&) = delete;
    Promise(Promise&&)      = default;

    Future<T> get_future() { return Future<T>(state_); }

    void set_value(T v) { state_->set_value(std::move(v)); }
    void set_error(std::string msg) { state_->set_error(std::move(msg)); }

    std::shared_ptr<SharedState<T>> state_;
};

template<typename T>
std::pair<Promise<T>, Future<T>> make_promise_future() {
    Promise<T> p;
    Future<T>  f = p.get_future();
    return { std::move(p), std::move(f) };
}

// Specialisation for void
template<>
class SharedState<void> {
public:
    std::mutex              mtx;
    std::condition_variable cv;
    std::optional<std::string> error;
    std::vector<WorkFn>     continuations;
    bool                    ready = false;

    void set_value() {
        std::vector<WorkFn> cbs;
        {
            std::lock_guard<std::mutex> lk(mtx);
            ready = true;
            cbs   = std::move(continuations);
        }
        cv.notify_all();
        for (auto& cb : cbs) cb();
    }

    void set_error(std::string msg) {
        std::vector<WorkFn> cbs;
        {
            std::lock_guard<std::mutex> lk(mtx);
            error = std::move(msg);
            ready = true;
            cbs   = std::move(continuations);
        }
        cv.notify_all();
        for (auto& cb : cbs) cb();
    }

    void get() {
        std::unique_lock<std::mutex> lk(mtx);
        cv.wait(lk, [&]{ return ready; });
        if (error) throw std::runtime_error(*error);
    }

    bool is_ready() const { return ready; }

    void then(WorkFn cb) {
        bool fire = false;
        {
            std::lock_guard<std::mutex> lk(mtx);
            if (ready) fire = true;
            else       continuations.push_back(cb);
        }
        if (fire) cb();
    }
};

template<>
class Future<void> {
public:
    explicit Future(std::shared_ptr<SharedState<void>> state)
        : state_(std::move(state)) {}
    Future() = default;

    bool is_ready() const { return state_ && state_->is_ready(); }
    void get()      const { if (state_) state_->get(); }
    void then(WorkFn cb)  { if (state_) state_->then(std::move(cb)); }
    void await()          { get(); }

    std::shared_ptr<SharedState<void>> state_;
};

template<>
class Promise<void> {
public:
    Promise() : state_(std::make_shared<SharedState<void>>()) {}
    Promise(Promise&&) = default;

    Future<void> get_future() { return Future<void>(state_); }
    void set_value()           { state_->set_value(); }
    void set_error(std::string msg) { state_->set_error(std::move(msg)); }

    std::shared_ptr<SharedState<void>> state_;
};

// ═══════════════════════════════════════════════════════════════════════════
//  Timer entry (for scheduled tasks)
// ═══════════════════════════════════════════════════════════════════════════

struct TimerEntry {
    TimePoint   fire_at;
    WorkFn      callback;
    uint64_t    id;
    bool        repeat;
    double      interval_ms;

    bool operator>(const TimerEntry& o) const { return fire_at > o.fire_at; }
};

// ═══════════════════════════════════════════════════════════════════════════
//  Task (unit of async work)
// ═══════════════════════════════════════════════════════════════════════════

class Task {
public:
    using Id = uint64_t;

    Task(Id id, std::string name, WorkFn fn)
        : id_(id), name_(std::move(name)), fn_(std::move(fn)),
          state_(TaskState::Pending) {}

    Task(const Task&) = delete;
    Task(Task&&)      = default;

    Id           id()    const { return id_; }
    const std::string& name() const { return name_; }
    TaskState    state() const { return state_.load(); }

    void run() {
        state_.store(TaskState::Running);
        try {
            fn_();
            state_.store(TaskState::Completed);
        } catch (std::exception& e) {
            error_ = e.what();
            state_.store(TaskState::Failed);
        }
    }

    bool is_done() const {
        auto s = state_.load();
        return s == TaskState::Completed || s == TaskState::Failed || s == TaskState::Cancelled;
    }

    const std::string& error() const { return error_; }

    void cancel() { state_.store(TaskState::Cancelled); }

private:
    Id                    id_;
    std::string           name_;
    WorkFn                fn_;
    std::atomic<TaskState> state_;
    std::string           error_;
};

// ═══════════════════════════════════════════════════════════════════════════
//  Thread Pool (worker threads for CPU-bound tasks)
// ═══════════════════════════════════════════════════════════════════════════

class ThreadPool {
public:
    explicit ThreadPool(size_t num_threads = 0) {
        if (num_threads == 0)
            num_threads = std::max(1u, std::thread::hardware_concurrency());
        for (size_t i = 0; i < num_threads; ++i)
            workers_.emplace_back([this]{ worker_loop(); });
    }

    ~ThreadPool() {
        {
            std::lock_guard<std::mutex> lk(mtx_);
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& t : workers_) {
            if (t.joinable()) t.join();
        }
    }

    template<typename F>
    std::future<std::invoke_result_t<F>> submit(F&& fn) {
        using R = std::invoke_result_t<F>;
        auto task = std::make_shared<std::packaged_task<R()>>(std::forward<F>(fn));
        auto fut  = task->get_future();
        {
            std::lock_guard<std::mutex> lk(mtx_);
            if (stop_) throw std::runtime_error("ThreadPool is stopped");
            queue_.emplace([task]{ (*task)(); });
        }
        cv_.notify_one();
        return fut;
    }

    void submit_void(WorkFn fn) {
        std::lock_guard<std::mutex> lk(mtx_);
        if (!stop_) {
            queue_.push(std::move(fn));
            cv_.notify_one();
        }
    }

    size_t pending()    const { std::lock_guard<std::mutex> lk(mtx_); return queue_.size(); }
    size_t num_threads()const { return workers_.size(); }

private:
    void worker_loop() {
        for (;;) {
            WorkFn task;
            {
                std::unique_lock<std::mutex> lk(mtx_);
                cv_.wait(lk, [&]{ return stop_ || !queue_.empty(); });
                if (stop_ && queue_.empty()) return;
                task = std::move(queue_.front());
                queue_.pop();
            }
            try { task(); } catch (...) {}
        }
    }

    std::vector<std::thread>   workers_;
    std::queue<WorkFn>         queue_;
    mutable std::mutex         mtx_;
    std::condition_variable    cv_;
    bool                       stop_ = false;
};

// ═══════════════════════════════════════════════════════════════════════════
//  Channel<T>  (bounded / unbounded MPSC channel)
// ═══════════════════════════════════════════════════════════════════════════

template<typename T>
class Channel {
public:
    explicit Channel(size_t capacity = 0)  // 0 = unbounded
        : capacity_(capacity), closed_(false) {}

    ~Channel() { close(); }

    // Send a value (blocks if bounded and full)
    bool send(T value) {
        std::unique_lock<std::mutex> lk(mtx_);
        if (closed_) return false;
        if (capacity_ > 0) {
            not_full_.wait(lk, [&]{ return closed_ || buf_.size() < capacity_; });
            if (closed_) return false;
        }
        buf_.push_back(std::move(value));
        not_empty_.notify_one();
        return true;
    }

    // Try to send without blocking
    bool try_send(T value) {
        std::lock_guard<std::mutex> lk(mtx_);
        if (closed_) return false;
        if (capacity_ > 0 && buf_.size() >= capacity_) return false;
        buf_.push_back(std::move(value));
        not_empty_.notify_one();
        return true;
    }

    // Receive (blocks until value available or channel closed)
    std::optional<T> recv() {
        std::unique_lock<std::mutex> lk(mtx_);
        not_empty_.wait(lk, [&]{ return closed_ || !buf_.empty(); });
        if (buf_.empty()) return std::nullopt;
        T val = std::move(buf_.front());
        buf_.pop_front();
        not_full_.notify_one();
        return val;
    }

    // Try receive without blocking
    std::optional<T> try_recv() {
        std::lock_guard<std::mutex> lk(mtx_);
        if (buf_.empty()) return std::nullopt;
        T val = std::move(buf_.front());
        buf_.pop_front();
        not_full_.notify_one();
        return val;
    }

    // Receive with timeout (ms)
    std::optional<T> recv_timeout(double timeout_ms) {
        std::unique_lock<std::mutex> lk(mtx_);
        auto deadline = Clock::now() + std::chrono::duration<double, std::milli>(timeout_ms);
        not_empty_.wait_until(lk, deadline, [&]{ return closed_ || !buf_.empty(); });
        if (buf_.empty()) return std::nullopt;
        T val = std::move(buf_.front());
        buf_.pop_front();
        not_full_.notify_one();
        return val;
    }

    void close() {
        std::lock_guard<std::mutex> lk(mtx_);
        closed_ = true;
        not_empty_.notify_all();
        not_full_.notify_all();
    }

    bool is_closed() const {
        std::lock_guard<std::mutex> lk(mtx_);
        return closed_;
    }

    size_t size() const {
        std::lock_guard<std::mutex> lk(mtx_);
        return buf_.size();
    }

    bool empty() const {
        std::lock_guard<std::mutex> lk(mtx_);
        return buf_.empty();
    }

private:
    std::deque<T>           buf_;
    size_t                  capacity_;
    bool                    closed_;
    mutable std::mutex      mtx_;
    std::condition_variable not_empty_;
    std::condition_variable not_full_;
};

// ═══════════════════════════════════════════════════════════════════════════
//  EventLoop  (single-threaded event loop like Node.js / Tokio)
// ═══════════════════════════════════════════════════════════════════════════

class EventLoop {
public:
    EventLoop() : running_(false), next_id_(1) {
        pool_ = std::make_unique<ThreadPool>();
    }

    ~EventLoop() { stop(); }

    // ── Scheduling ──────────────────────────────────────────────────────────

    // Post a callback to run on the next iteration
    uint64_t post(WorkFn fn) {
        uint64_t id = next_id_++;
        std::lock_guard<std::mutex> lk(queue_mtx_);
        ready_.push({ id, std::move(fn) });
        return id;
    }

    // Defer: run after current callbacks drain
    void defer(WorkFn fn) { post(std::move(fn)); }

    // Schedule a timer callback
    uint64_t set_timeout(double delay_ms, WorkFn fn) {
        uint64_t id = next_id_++;
        TimerEntry e;
        e.id          = id;
        e.fire_at     = now() + std::chrono::duration<double, std::milli>(delay_ms);
        e.callback    = std::move(fn);
        e.repeat      = false;
        e.interval_ms = delay_ms;
        std::lock_guard<std::mutex> lk(timer_mtx_);
        timers_.push_back(std::move(e));
        std::sort(timers_.begin(), timers_.end(),
                  [](const TimerEntry& a, const TimerEntry& b){ return a.fire_at < b.fire_at; });
        return id;
    }

    // Repeating timer
    uint64_t set_interval(double interval_ms, WorkFn fn) {
        uint64_t id = next_id_++;
        TimerEntry e;
        e.id          = id;
        e.fire_at     = now() + std::chrono::duration<double, std::milli>(interval_ms);
        e.callback    = fn;
        e.repeat      = true;
        e.interval_ms = interval_ms;
        std::lock_guard<std::mutex> lk(timer_mtx_);
        timers_.push_back(std::move(e));
        std::sort(timers_.begin(), timers_.end(),
                  [](const TimerEntry& a, const TimerEntry& b){ return a.fire_at < b.fire_at; });
        return id;
    }

    // Cancel a timer or queued callback
    void cancel(uint64_t id) {
        cancelled_.insert(id);
    }

    // Clear timeout/interval
    void clear_timeout (uint64_t id) { cancel(id); }
    void clear_interval(uint64_t id) { cancel(id); }

    // ── Async spawn ──────────────────────────────────────────────────────────

    // Run fn on the thread pool, resolve a future when done
    template<typename F>
    Future<std::invoke_result_t<F>> spawn(F&& fn) {
        using R = std::invoke_result_t<F>;
        auto [promise, future] = make_promise_future<R>();
        pool_->submit_void([p = std::move(promise), fn = std::forward<F>(fn)]() mutable {
            try { p.set_value(fn()); }
            catch(std::exception& e) { p.set_error(e.what()); }
        });
        return future;
    }

    // Spawn void task
    void spawn_void(WorkFn fn) { pool_->submit_void(std::move(fn)); }

    // ── Sleep / delay ────────────────────────────────────────────────────────

    // Returns a future that resolves after delay_ms
    Future<void> sleep(double delay_ms) {
        auto [promise, future] = make_promise_future<void>();
        set_timeout(delay_ms, [p = std::make_shared<Promise<void>>(std::move(promise))]() mutable {
            p->set_value();
        });
        return future;
    }

    // ── Run / stop ───────────────────────────────────────────────────────────

    // Run the event loop until stop() is called
    void run() {
        running_ = true;
        while (running_) {
            tick();
            if (ready_empty() && timers_empty()) {
                std::this_thread::sleep_for(std::chrono::microseconds(100));
            }
        }
    }

    // Run until all pending work is done
    void run_until_complete() {
        running_ = true;
        while (running_) {
            tick();
            if (ready_empty() && timers_empty() && pool_->pending() == 0) break;
            if (ready_empty()) {
                auto next = next_timer_fire();
                if (next) {
                    auto delay = *next - now();
                    if (delay.count() > 0)
                        std::this_thread::sleep_for(std::min(delay, std::chrono::milliseconds(10)));
                } else {
                    std::this_thread::sleep_for(std::chrono::microseconds(100));
                }
            }
        }
        running_ = false;
    }

    // Run a single iteration
    void tick() {
        // Fire due timers
        fire_timers();

        // Execute ready queue (one pass)
        size_t max_work = 256;
        for (size_t i = 0; i < max_work; ++i) {
            std::optional<std::pair<uint64_t, WorkFn>> item;
            {
                std::lock_guard<std::mutex> lk(queue_mtx_);
                if (ready_.empty()) break;
                item = std::move(ready_.front());
                ready_.pop();
            }
            if (cancelled_.count(item->first)) {
                cancelled_.erase(item->first);
                continue;
            }
            try { item->second(); } catch (...) {}
        }
    }

    void stop() { running_ = false; }

    bool is_running() const { return running_.load(); }

    // ── Stats ────────────────────────────────────────────────────────────────

    size_t pending_timers() const {
        std::lock_guard<std::mutex> lk(timer_mtx_);
        return timers_.size();
    }

    size_t pending_callbacks() const {
        std::lock_guard<std::mutex> lk(queue_mtx_);
        return ready_.size();
    }

    ThreadPool& thread_pool() { return *pool_; }

private:
    struct ReadyItem {
        uint64_t id;
        WorkFn   fn;
    };

    void fire_timers() {
        auto tp = now();
        std::vector<TimerEntry> fired;
        std::vector<TimerEntry> reschedule;
        {
            std::lock_guard<std::mutex> lk(timer_mtx_);
            while (!timers_.empty() && timers_.front().fire_at <= tp) {
                fired.push_back(std::move(timers_.front()));
                timers_.erase(timers_.begin());
            }
        }
        for (auto& e : fired) {
            if (cancelled_.count(e.id)) {
                cancelled_.erase(e.id);
                continue;
            }
            try { e.callback(); } catch (...) {}
            if (e.repeat) {
                TimerEntry r = e;
                r.fire_at = now() + std::chrono::duration<double, std::milli>(r.interval_ms);
                reschedule.push_back(std::move(r));
            }
        }
        if (!reschedule.empty()) {
            std::lock_guard<std::mutex> lk(timer_mtx_);
            for (auto& r : reschedule) timers_.push_back(std::move(r));
            std::sort(timers_.begin(), timers_.end(),
                      [](const TimerEntry& a, const TimerEntry& b){ return a.fire_at < b.fire_at; });
        }
    }

    bool ready_empty() const {
        std::lock_guard<std::mutex> lk(queue_mtx_);
        return ready_.empty();
    }

    bool timers_empty() const {
        std::lock_guard<std::mutex> lk(timer_mtx_);
        return timers_.empty();
    }

    std::optional<TimePoint> next_timer_fire() const {
        std::lock_guard<std::mutex> lk(timer_mtx_);
        if (timers_.empty()) return std::nullopt;
        return timers_.front().fire_at;
    }

    std::queue<std::pair<uint64_t, WorkFn>> ready_;
    mutable std::mutex                       queue_mtx_;

    std::vector<TimerEntry>                  timers_;
    mutable std::mutex                       timer_mtx_;

    std::unordered_map<uint64_t, bool>       cancelled_;

    std::unique_ptr<ThreadPool>              pool_;
    std::atomic<bool>                        running_;
    std::atomic<uint64_t>                    next_id_;
};

// ═══════════════════════════════════════════════════════════════════════════
//  Global event loop
// ═══════════════════════════════════════════════════════════════════════════

namespace detail {
    inline EventLoop& global_loop() {
        static EventLoop instance;
        return instance;
    }
}

inline EventLoop& loop() { return detail::global_loop(); }

// ═══════════════════════════════════════════════════════════════════════════
//  Convenient free functions (Vyn stdlib interface)
// ═══════════════════════════════════════════════════════════════════════════

// defer_ms: schedule callback after delay
inline uint64_t defer_ms(double ms, WorkFn fn) {
    return loop().set_timeout(ms, std::move(fn));
}

// yield: post to next tick
inline void yield_now(WorkFn fn) {
    loop().post(std::move(fn));
}

// sleep_ms: async sleep returning a future
inline Future<void> sleep_ms(double ms) {
    return loop().sleep(ms);
}

// run_async: spawn on thread pool
template<typename F>
auto run_async(F&& fn) {
    return loop().spawn(std::forward<F>(fn));
}

// await_all: wait for multiple futures
template<typename T>
std::vector<T> await_all(std::vector<Future<T>>& futures) {
    std::vector<T> results;
    results.reserve(futures.size());
    for (auto& f : futures) results.push_back(f.get());
    return results;
}

// ═══════════════════════════════════════════════════════════════════════════
//  C++ coroutine support  (C++20 only)
// ═══════════════════════════════════════════════════════════════════════════

#if VYN_HAS_COROUTINES

template<typename T = void>
class Coroutine {
public:
    struct promise_type {
        std::optional<T>    value;
        std::exception_ptr  exc;

        Coroutine<T> get_return_object() {
            return Coroutine<T>{ std::coroutine_handle<promise_type>::from_promise(*this) };
        }

        std::suspend_always initial_suspend() noexcept { return {}; }
        std::suspend_always final_suspend  () noexcept { return {}; }

        void return_value(T v)  { value = std::move(v); }
        void unhandled_exception() { exc = std::current_exception(); }
    };

    using Handle = std::coroutine_handle<promise_type>;

    explicit Coroutine(Handle h) : handle_(h) {}
    Coroutine(Coroutine&& o) noexcept : handle_(std::exchange(o.handle_, {})) {}
    ~Coroutine() { if (handle_) handle_.destroy(); }

    bool resume() {
        if (!handle_ || handle_.done()) return false;
        handle_.resume();
        return !handle_.done();
    }

    bool done() const { return !handle_ || handle_.done(); }

    T get() {
        if (handle_.promise().exc) std::rethrow_exception(handle_.promise().exc);
        return *handle_.promise().value;
    }

    // Awaitable for nested coroutines
    bool await_ready()                  { return done(); }
    void await_suspend(std::coroutine_handle<> h) {
        loop().post([this, h]() mutable {
            resume();
            if (!done()) loop().post([this, h]() mutable { h.resume(); });
            else         h.resume();
        });
    }
    T await_resume() { return get(); }

private:
    Handle handle_;
};

template<>
class Coroutine<void> {
public:
    struct promise_type {
        std::exception_ptr exc;

        Coroutine<void> get_return_object() {
            return Coroutine<void>{ std::coroutine_handle<promise_type>::from_promise(*this) };
        }

        std::suspend_always initial_suspend() noexcept { return {}; }
        std::suspend_always final_suspend  () noexcept { return {}; }
        void return_void() {}
        void unhandled_exception() { exc = std::current_exception(); }
    };

    using Handle = std::coroutine_handle<promise_type>;

    explicit Coroutine(Handle h) : handle_(h) {}
    Coroutine(Coroutine&& o) noexcept : handle_(std::exchange(o.handle_, {})) {}
    ~Coroutine() { if (handle_) handle_.destroy(); }

    bool resume() {
        if (!handle_ || handle_.done()) return false;
        handle_.resume();
        return !handle_.done();
    }

    bool done() const { return !handle_ || handle_.done(); }
    void get()  {
        if (handle_.promise().exc) std::rethrow_exception(handle_.promise().exc);
    }

    bool await_ready()  { return done(); }
    void await_suspend(std::coroutine_handle<> h) {
        loop().post([this, h]() mutable {
            resume();
            if (!done()) loop().post([this, h]() mutable { h.resume(); });
            else         h.resume();
        });
    }
    void await_resume() { get(); }

private:
    Handle handle_;
};

// Awaitable sleep (for use with co_await)
struct SleepAwaitable {
    double ms;
    bool   ready_ = false;

    bool await_ready() { return ms <= 0; }
    void await_suspend(std::coroutine_handle<> h) {
        loop().set_timeout(ms, [h]() mutable { h.resume(); });
    }
    void await_resume() {}
};

inline SleepAwaitable co_sleep(double ms) { return { ms }; }

// Yield awaitable (co_await yield_now())
struct YieldAwaitable {
    bool await_ready() { return false; }
    void await_suspend(std::coroutine_handle<> h) {
        loop().post([h]() mutable { h.resume(); });
    }
    void await_resume() {}
};

inline YieldAwaitable co_yield_now() { return {}; }

#endif // VYN_HAS_COROUTINES

// ═══════════════════════════════════════════════════════════════════════════
//  C-compatible API  (called from Python / Vyn interpreter via ctypes)
// ═══════════════════════════════════════════════════════════════════════════

extern "C" {

void   vyn_async_init  (void);
void   vyn_async_run   (void);
void   vyn_async_stop  (void);
void   vyn_async_tick  (void);

uint64_t vyn_async_defer_ms   (double ms, void (*fn)(void *), void *userdata);
uint64_t vyn_async_set_interval(double ms, void (*fn)(void *), void *userdata);
void     vyn_async_cancel      (uint64_t id);

void   vyn_async_spawn_void(void (*fn)(void *), void *userdata);

} // extern "C"

} // namespace async
} // namespace vyn

#endif // VYN_ASYNC_HPP