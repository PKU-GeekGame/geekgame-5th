#include <bits/stdc++.h>
#include <openssl/evp.h>
#include <random>
#include <gmp.h>
#include <chrono>
#include <omp.h>
#include <fstream>
using namespace std;
using ull = unsigned long long;

// ---------- 参数（可调） ----------
const int MAX_BLOCK_BITS = 20; // 每块最大位数（安全上限）
const int L_REP = 8;          // 每个 mask 最多保留多少代表索引（经验值）
// -----------------------------------

// 全局日志文件输出流
ofstream log_file;

// 日志输出函数 - 支持详细模式和静默模式
template<typename... Args>
void log_output(bool verbose, Args&&... args) {
    if (verbose) {
        // 详细模式：输出到控制台
        ((cout << args), ...);
    } else {
        // 静默模式：输出到日志文件
        if (log_file.is_open()) {
            ((log_file << args), ...);
        }
    }
}

// 特殊的进度条输出函数
void log_progress(bool verbose, const string& progress_line) {
    if (verbose) {
        cout << progress_line << flush;
    }
    // 静默模式下不输出进度条到日志（避免大量重复信息）
}

// WOTS 相关常量
const int m = 256;
const int w = 21;
const int n = 128;
const int l1 = (int)ceil(m / log2(w));
const int l2 = (int)floor(log2(l1*(w-1)) / log2(w)) + 1;
const int l = l1 + l2;

enum HashType {
    MSG = 0,
    WOTS_PK = 1,
    WOTS_CHAIN = 2,
    TREE_NODE = 3
};

// SHAKE-128 哈希函数
vector<uint8_t> F(const vector<uint8_t>& data, const vector<uint8_t>& seed, int length, int type) {
    vector<uint8_t> input;
    input.insert(input.end(), seed.begin(), seed.end());
    input.push_back((uint8_t)type);
    input.insert(input.end(), data.begin(), data.end());
    
    vector<uint8_t> output(length);
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    EVP_DigestInit_ex(ctx, EVP_shake128(), nullptr);
    EVP_DigestUpdate(ctx, input.data(), input.size());
    EVP_DigestFinalXOF(ctx, output.data(), length);
    EVP_MD_CTX_free(ctx);
    
    return output;
}

// 数字打包函数（使用 GMP 处理大整数）
vector<int> pack(const vector<uint8_t>& bytes, int length, int base) {
    // 将字节数组转换为 GMP 大整数
    mpz_t num;
    mpz_init(num);
    mpz_import(num, bytes.size(), 1, 1, 1, 0, bytes.data());
    
    vector<int> packed;
    mpz_t temp, remainder;
    mpz_init(temp);
    mpz_init(remainder);
    
    mpz_set(temp, num);
    
    while (mpz_cmp_ui(temp, 0) > 0) {
        mpz_mod_ui(remainder, temp, base);
        packed.push_back(mpz_get_ui(remainder));
        mpz_div_ui(temp, temp, base);
    }
    
    if ((int)packed.size() < length) {
        packed.resize(length, 0);
    }
    
    mpz_clear(num);
    mpz_clear(temp);
    mpz_clear(remainder);
    
    return packed;
}

// 链操作函数
vector<uint8_t> chain(vector<uint8_t> x, int n, const vector<uint8_t>& seed) {
    if (n == 0) return x;
    x = F(x, seed, 16, WOTS_CHAIN);
    return chain(x, n - 1, seed);
}

// bytes_to_long 功能 - 删除这个函数，因为现在直接用字节数组

// 获取打包数据
vector<int> get_packed(const vector<uint8_t>& msg, const vector<uint8_t>& seed, bool include_checksum = true) {
    vector<uint8_t> digest = F(msg, seed, 32, MSG);
    vector<int> d1 = pack(digest, l1, w);
    
    if (!include_checksum) {
        // 不包含校验和模式，只返回 d1
        return d1;
    }
    
    int checksum = 0;
    for (int i : d1) {
        checksum += w - 1 - i;
    }
    
    // 将 checksum 转换为字节数组
    vector<uint8_t> checksum_bytes;
    int temp_checksum = checksum;
    if (temp_checksum == 0) {
        checksum_bytes.push_back(0);
    } else {
        while (temp_checksum > 0) {
            checksum_bytes.insert(checksum_bytes.begin(), temp_checksum & 0xFF);
            temp_checksum >>= 8;
        }
    }
    
    vector<int> d2 = pack(checksum_bytes, l2, w);
    vector<int> d = d1;
    d.insert(d.end(), d2.begin(), d2.end());
    
    return d;
}

// 生成随机字节
vector<uint8_t> random_bytes(int length) {
    static random_device rd;
    static mt19937 gen(rd());
    static uniform_int_distribution<> dis(0, 255);
    
    vector<uint8_t> result(length);
    for (int i = 0; i < length; ++i) {
        result[i] = dis(gen);
    }
    return result;
}

// 从十六进制字符串转换为字节数组
vector<uint8_t> hex_to_bytes(const string& hex) {
    vector<uint8_t> bytes;
    for (size_t i = 0; i < hex.length(); i += 2) {
        string byte_str = hex.substr(i, 2);
        uint8_t byte = (uint8_t)strtol(byte_str.c_str(), nullptr, 16);
        bytes.push_back(byte);
    }
    return bytes;
}

// 打印使用帮助
void print_usage(const char* program_name) {
    cout << "Usage: " << program_name << " [OPTIONS]\n";
    cout << "\nOptions:\n";
    cout << "  -g, --generate          Generate WOTS data internally (default mode)\n";
    cout << "  -r, --read              Read from stdin (original behavior)\n";
    cout << "  -n, --samples N         Number of samples to generate (default: 10000)\n";
    cout << "  -k, --bits K            Bit width (default: " << l << " for WOTS)\n";
    cout << "  -s, --seed SEED         Hex seed (32 chars for 16 bytes, default: random)\n";
    cout << "  --no-checksum           Skip checksum calculation (only use first " << l1 << " bits)\n";
    cout << "  --no-verbose            Only output final result (two numbers)\n";
    cout << "  -j, --threads N         Number of threads for parallel generation (default: auto)\n";
    cout << "  -h, --help              Show this help message\n";
    cout << "\nExamples:\n";
    cout << "  " << program_name << " -g -n 1000 -k 64\n";
    cout << "  " << program_name << " -g -s 0123456789abcdef0123456789abcdef\n";
    cout << "  " << program_name << " -g --no-checksum -k " << l1 << "\n";
    cout << "  " << program_name << " -g -n 1000000 -j 8  # Use 8 threads\n";
    cout << "  " << program_name << " -g --no-verbose -n 10000  # Quiet mode\n";
    cout << "  " << program_name << " -r < input.txt\n";
}

// 显示进度条
void show_progress(int current, int total, int attempt, 
                  chrono::steady_clock::time_point start_time, 
                  const string& prefix = "Progress", bool verbose = true) {
    const int bar_width = 50;
    float progress = (float)current / total;
    int pos = (int)(bar_width * progress);
    
    // 计算时间信息
    auto now = chrono::steady_clock::now();
    auto elapsed = chrono::duration_cast<chrono::seconds>(now - start_time);
    
    stringstream progress_line;
    progress_line << "\r" << prefix << ": [";
    for (int i = 0; i < bar_width; ++i) {
        if (i < pos) progress_line << "=";
        else if (i == pos) progress_line << ">";
        else progress_line << " ";
    }
    progress_line << "] " << (int)(progress * 100.0) << "% ";
    progress_line << "(" << current << "/" << total << ")";
    
    if (attempt > 0) {
        progress_line << " attempts: " << attempt;
    }
    
    // 显示时间信息
    if (current > 0 && progress > 0.01) { // 至少1%进度时才显示时间估计
        auto estimated_total = elapsed.count() / progress;
        auto remaining = (int)(estimated_total - elapsed.count());
        
        progress_line << " | " << elapsed.count() << "s elapsed";
        if (remaining > 0) {
            progress_line << ", ~" << remaining << "s remaining";
        }
    }
    
    log_progress(verbose, progress_line.str());
}

// 生成输入数据的核心函数（并行版本）
vector<ull> generate_wots_data(int num_samples, int k, const vector<uint8_t>& seed, bool include_checksum = true, int num_threads = 0, bool verbose = true) {
    // 目标消息 "Give me the flag"
    string destiny_str = "Give me the flag";
    vector<uint8_t> destiny(destiny_str.begin(), destiny_str.end());
    vector<int> destiny_packed = get_packed(destiny, seed, include_checksum);
    
    if (verbose) {
        cout << "destiny_packed: ";
        for (int i = 0; i < (int)destiny_packed.size(); ++i) {
            cout << destiny_packed[i] << " ";
        }
        cout << endl;
        
        if (!include_checksum) {
            cout << "No-checksum mode: using only " << l1 << " bits (skipping " << l2 << " checksum bits)" << endl;
        }
    } else {
        log_output(verbose, "destiny_packed: ");
        for (int i = 0; i < (int)destiny_packed.size(); ++i) {
            log_output(verbose, destiny_packed[i], " ");
        }
        log_output(verbose, "\n");
        
        if (!include_checksum) {
            log_output(verbose, "No-checksum mode: using only ", l1, " bits (skipping ", l2, " checksum bits)\n");
        }
    }
    
    // 设置线程数
    if (num_threads <= 0) {
        num_threads = omp_get_max_threads();
    }
    omp_set_num_threads(num_threads);
    if (verbose) {
        cout << "Using " << num_threads << " threads for parallel generation" << endl;
    } else {
        log_output(verbose, "Using ", num_threads, " threads for parallel generation\n");
    }
    
    vector<ull> results(num_samples);
    atomic<int> completed_samples(0);
    atomic<int> total_attempts(0);
    
    auto start_time = chrono::steady_clock::time_point();
    if (verbose) {
        start_time = chrono::steady_clock::now();
        cout << "Generating WOTS data..." << endl;
        show_progress(0, num_samples, 0, start_time, "Generating", verbose);
    } else {
        start_time = chrono::steady_clock::now();
        log_output(verbose, "Generating WOTS data...\n");
    }
    
    // 如果样本数小于等于10，输出详细调试信息
    bool debug_mode = (num_samples <= 10);
    
    // 并行生成数据
    #pragma omp parallel for schedule(dynamic, 100)
    for (int i = 0; i < num_samples; ++i) {
        int attempt = i + 1;  // 从 1 开始计数，保持与原版本一致
        
        // 将 attempt 转换为字符串然后 ASCII 编码
        string attempt_str = to_string(attempt);
        vector<uint8_t> msg(attempt_str.begin(), attempt_str.end());
        
        vector<int> packed = get_packed(msg, seed, include_checksum);
        
        // 调试输出前几个样本
        if (debug_mode && i < 10) {
            #pragma omp critical
            {
                cout << "Sample " << i << ": attempt=" << attempt << ", string='" << attempt_str << "', bytes=[";
                for (size_t b = 0; b < msg.size(); ++b) {
                    if (b > 0) cout << ", ";
                    cout << (int)msg[b];
                }
                cout << "]" << endl;
            }
        }
        
        // 生成二进制块：如果 packed[j] >= destiny_packed[j] 则设置第 j 位
        ull chunk = 0;
        for (int j = 0; j < min(k, (int)packed.size()); ++j) {
            if (packed[j] >= destiny_packed[j]) {
                chunk |= (1ULL << j);
            }
        }
        
        results[i] = chunk;
        
        // 调试输出结果
        if (debug_mode && i < 10) {
            #pragma omp critical
            {
                cout << "    result: " << bitset<64>(chunk) << " (0x" << hex << chunk << dec << ")" << endl;
            }
        }
        
        if (verbose) {
            // 更新进度（每个线程独立更新计数器）
            int current_completed = completed_samples.fetch_add(1) + 1;
            total_attempts.fetch_add(1);
            
            // 定期更新进度显示（减少锁竞争）
            if (current_completed % 1000 == 0 || current_completed == num_samples) {
                #pragma omp critical
                {
                    static int last_displayed = 0;
                    if (current_completed - last_displayed >= 1000 || current_completed == num_samples) {
                        show_progress(current_completed, num_samples, total_attempts.load(), start_time, "Generating", verbose);
                        last_displayed = current_completed;
                    }
                }
            }
        } else {
            completed_samples.fetch_add(1);
            total_attempts.fetch_add(1);
        }
    }
    
    if (verbose) {
        // 确保最终进度显示
        show_progress(num_samples, num_samples, total_attempts.load(), start_time, "Generating", verbose);
        cout << endl; // 换行，完成进度条
        cout << "Total attempts: " << total_attempts.load() << ", generated: " << num_samples << endl;
    } else {
        log_output(verbose, "Total attempts: ", total_attempts.load(), ", generated: ", num_samples, "\n");
    }
    
    return results;
}

ull parse_num(const string &s) {
    // 如果全是 '0'/'1'，按二进制解析；否则用 stoull 自动识别十进制/0x 十六进制等
    bool is_bin = true;
    for (char c : s) if (c != '0' && c != '1') { is_bin = false; break; }
    if (is_bin) {
        ull x = 0;
        for (char c : s) { x = (x << 1) | (ull)(c == '1'); }
        return x;
    } else {
        return stoull(s, nullptr, 0);
    }
}

// 合并 B 到 A（保持 A 中元素唯一），最多保留 up_to 个元素
inline void merge_trunc(vector<int> &A, const vector<int> &B, int up_to) {
    if ((int)A.size() >= up_to) return;
    for (int x : B) {
        if ((int)A.size() >= up_to) break;
        bool dup = false;
        for (int y : A) if (y == x) { dup = true; break; }
        if (!dup) A.push_back(x);
    }
}

// 核心函数：返回一对索引或 {-1,-1}
pair<int,int> find_pair_block_sos(const vector<ull>& a, int k) {
    int n = (int)a.size();
    if (n < 2) return {-1,-1};
    ull all_ones = (k == 64) ? ~0ULL : ((1ULL<<k) - 1ULL);

    // 快速检查：重复值 / 全 1 掩码
    unordered_map<ull,int> seen;
    seen.reserve(n*2);
    int first_allones = -1;
    for (int i = 0; i < n; ++i) {
        if (a[i] == all_ones) {
            if (first_allones != -1) return {first_allones, i};
            first_allones = i;
        }
        auto it = seen.find(a[i]);
        if (it != seen.end()) {
            int j = it->second;
            if ((a[i] | a[j]) == all_ones) return {j, i};
        } else seen[a[i]] = i;
    }

    // c[i] = 补集（a 中为 0 的位）——我们要找 c[i] & c[j] == 0
    vector<ull> c(n);
    for (int i = 0; i < n; ++i) c[i] = (~a[i]) & all_ones;

    // 选块宽 b：大致取 log2(n)，但限制在 [1, MAX_BLOCK_BITS]
    int approx_b = max(1, (int)floor(log2(max(2, n))));
    int b = min(MAX_BLOCK_BITS, max(1, approx_b));
    int t = (k + b - 1) / b; // 块数
    vector<int> block_bits(t, b);
    // 最后一个块可能不满 b
    int last_bits = k - (t-1)*b;
    if (last_bits > 0) block_bits[t-1] = last_bits;
    vector<int> block_shift(t);
    for (int s = 0; s < t; ++s) block_shift[s] = s * b;

    // reps[s][mask] : up to L_REP 索引，初始为 exact block-value
    vector< vector< vector<int> > > reps(t);
    for (int s = 0; s < t; ++s) {
        int bs = block_bits[s];
        int M = 1 << bs;
        reps[s].assign(M, vector<int>());
    }

    // 填充 exact bucket（block 的值等于 bval）
    for (int i = 0; i < n; ++i) {
        ull xi = c[i];
        for (int s = 0; s < t; ++s) {
            int shift = block_shift[s];
            int bs = block_bits[s];
            ull mask = (bs == 64) ? (xi >> shift) : ((xi >> shift) & ((1ULL<<bs)-1));
            int v = (int)mask;
            auto &vec = reps[s][v];
            if ((int)vec.size() < L_REP) vec.push_back(i);
        }
    }

    // 对每个块做 SOS DP，使 reps[s][mask] 包含所有子掩码（submask）对应的索引
    // 这样 reps[s][M] 就是所有 bval_j 子集于 M 的 j（我们需要 M 为 inv = ~bval_i）
    for (int s = 0; s < t; ++s) {
        int bs = block_bits[s];
        int M = 1 << bs;
        for (int bit = 0; bit < bs; ++bit) {
            for (int mask = 0; mask < M; ++mask) {
                if (mask & (1 << bit)) {
                    // mask 含该位，则把 mask^(1<<bit) 的元素合并到 mask
                    merge_trunc(reps[s][mask], reps[s][mask ^ (1<<bit)], L_REP);
                }
            }
        }
    }

    // 对每个 i，计算每块需要的 inv（j 的块值必须是 inv 的子集），选最短候选列表搜索
    for (int i = 0; i < n; ++i) {
        ull ci = c[i];
        int best_s = -1;
        size_t best_sz = SIZE_MAX;
        vector<int> need_mask(t);
        for (int s = 0; s < t; ++s) {
            int shift = block_shift[s];
            int bs = block_bits[s];
            ull block_val = (bs == 64) ? (ci >> shift) : ((ci >> shift) & ((1ULL<<bs)-1));
            int mask_all = (1<<bs) - 1;
            int inv = (~(int)block_val) & mask_all; // j.block 必须是 inv 的子集
            need_mask[s] = inv;
            size_t sz = reps[s][inv].size();
            if (sz < best_sz) { best_sz = sz; best_s = s; }
        }
        if (best_s == -1 || best_sz == 0) continue;
        // 在最短候选列表里精验
        const auto &cands = reps[best_s][need_mask[best_s]];
        for (int j : cands) {
            if (j == i) continue;
            if ( (c[i] & c[j]) == 0 ) return {i, j};
        }
    }
    return {-1,-1};
}

int main(int argc, char* argv[]) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // 默认参数
    bool generate_mode = true;  // 默认生成模式
    bool no_checksum = false;   // 是否跳过校验和
    bool verbose = true;        // 是否输出详细信息
    int n = 10000;
    int k = l;  // 使用 WOTS 的 l 值
    int num_threads = 0;  // 0 表示自动检测
    string seed_hex = "";
    
    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        string arg = argv[i];
        
        if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            return 0;
        }
        else if (arg == "-g" || arg == "--generate") {
            generate_mode = true;
        }
        else if (arg == "-r" || arg == "--read") {
            generate_mode = false;
        }
        else if (arg == "--no-checksum") {
            no_checksum = true;
            // 如果启用 no-checksum 模式且用户没有指定 k，则默认使用 l1
            if (k == l) {
                k = l1;
            }
        }
        else if (arg == "--no-verbose") {
            verbose = false;
        }
        else if (arg == "-n" || arg == "--samples") {
            if (i + 1 < argc) {
                n = stoi(argv[++i]);
            } else {
                cerr << "Error: " << arg << " requires a number\n";
                return 1;
            }
        }
        else if (arg == "-k" || arg == "--bits") {
            if (i + 1 < argc) {
                k = stoi(argv[++i]);
            } else {
                cerr << "Error: " << arg << " requires a number\n";
                return 1;
            }
        }
        else if (arg == "-j" || arg == "--threads") {
            if (i + 1 < argc) {
                num_threads = stoi(argv[++i]);
                if (num_threads < 1) {
                    cerr << "Error: number of threads must be positive\n";
                    return 1;
                }
            } else {
                cerr << "Error: " << arg << " requires a number\n";
                return 1;
            }
        }
        else if (arg == "-s" || arg == "--seed") {
            if (i + 1 < argc) {
                seed_hex = argv[++i];
                if (seed_hex.length() != 32) {
                    cerr << "Error: seed must be 32 hex characters (16 bytes)\n";
                    return 1;
                }
            } else {
                cerr << "Error: " << arg << " requires a hex string\n";
                return 1;
            }
        }
        else {
            cerr << "Error: unknown option " << arg << "\n";
            print_usage(argv[0]);
            return 1;
        }
    }
    
    // 如果是静默模式，设置日志文件
    if (!verbose) {
        // 生成日志文件名（基于时间戳）
        auto now = chrono::system_clock::now();
        auto time_t = chrono::system_clock::to_time_t(now);
        auto ms = chrono::duration_cast<chrono::milliseconds>(now.time_since_epoch()) % 1000;
        
        stringstream log_filename;
        log_filename << "wots_log_" << put_time(localtime(&time_t), "%Y%m%d_%H%M%S") 
                     << "_" << setfill('0') << setw(3) << ms.count() << ".txt";
        
        log_file.open(log_filename.str());
        if (!log_file.is_open()) {
            cerr << "Error: cannot create log file " << log_filename.str() << "\n";
            return 1;
        }
        
        // 记录程序开始时间和命令行参数
        log_file << "=== WOTS Program Log ===" << endl;
        log_file << "Start time: " << put_time(localtime(&time_t), "%Y-%m-%d %H:%M:%S") << endl;
        log_file << "Command line: ";
        for (int i = 0; i < argc; ++i) {
            log_file << argv[i];
            if (i < argc - 1) log_file << " ";
        }
        log_file << endl;
        log_file << "Parameters:" << endl;
        log_file << "  - Generate mode: " << (generate_mode ? "true" : "false") << endl;
        log_file << "  - Samples (n): " << n << endl;
        log_file << "  - Bits (k): " << k << endl;
        log_file << "  - No checksum: " << (no_checksum ? "true" : "false") << endl;
        log_file << "  - Threads: " << (num_threads > 0 ? to_string(num_threads) : "auto") << endl;
        log_file << "  - Seed: " << (seed_hex.empty() ? "random" : seed_hex) << endl;
        log_file << "=========================" << endl << endl;
    }
    
    vector<ull> a;
    
    if (generate_mode) {
        // 生成模式
        if (verbose) {
            cout << "Generate mode: n=" << n << ", k=" << k;
            if (no_checksum) {
                cout << " (no-checksum)";
            }
            cout << endl;
        } else {
            log_output(verbose, "Generate mode: n=", n, ", k=", k);
            if (no_checksum) {
                log_output(verbose, " (no-checksum)");
            }
            log_output(verbose, "\n");
        }
        
        // 获取种子
        vector<uint8_t> seed;
        if (seed_hex.empty()) {
            seed = random_bytes(16);
            if (verbose) {
                cout << "Generated random seed." << endl;
            } else {
                log_output(verbose, "Generated random seed.\n");
            }
        } else {
            seed = hex_to_bytes(seed_hex);
            if (verbose) {
                cout << "Using provided seed: " << seed_hex << endl;
            } else {
                log_output(verbose, "Using provided seed: ", seed_hex, "\n");
            }
        }
        
        // 生成 WOTS 数据
        a = generate_wots_data(n, k, seed, !no_checksum, num_threads, verbose);
        
    } else {
        // 原始读取模式
        if (verbose) {
            cout << "Read mode: reading from stdin..." << endl;
        } else {
            log_output(verbose, "Read mode: reading from stdin...\n");
        }
        if (!(cin >> n >> k)) {
            cerr << "Error: expected n k on first line\n";
            return 1;
        }
        if (verbose) {
            cout << "Read parameters: n=" << n << ", k=" << k << endl;
        } else {
            log_output(verbose, "Read parameters: n=", n, ", k=", k, "\n");
        }
        
        a.resize(n);
        for (int i = 0; i < n; ++i) {
            string s; 
            if (!(cin >> s)) {
                cerr << "Error: expected " << n << " numbers\n";
                return 1;
            }
            a[i] = parse_num(s);
        }
    }
    
    // 统计每个位的计数
    vector<int> bit_count(k, 0);
    for (int i = 0; i < n; ++i) {
        for (int b = 0; b < k; ++b) {
            if ((a[i] >> b) & 1) bit_count[b]++;
        }
    }
    
    if (verbose) {
        cout << "\nBit statistics:" << endl;
        for (int b = k - 1; b >= 0; --b) {
            cout << "bit " << k - 1 - b << ": " << bit_count[b] << "\n";
        }
        
        // 运行原来的查找算法
        cout << "\nSearching for pair..." << endl;
    } else {
        log_output(verbose, "\nBit statistics:\n");
        for (int b = k - 1; b >= 0; --b) {
            log_output(verbose, "bit ", k - 1 - b, ": ", bit_count[b], "\n");
        }
        
        // 运行原来的查找算法
        log_output(verbose, "\nSearching for pair...\n");
    }
    
    auto ans = find_pair_block_sos(a, k);
    
    if (verbose) {
        cout << "Result: " << ans.first << " " << ans.second << "\n";
        
        if (ans.first != -1 && ans.second != -1) {
            cout << "Found pair! a[" << ans.first << "] | a[" << ans.second << "] = all ones" << endl;
            cout << "a[" << ans.first << "] = " << bitset<64>(a[ans.first]) << endl;
            cout << "a[" << ans.second << "] = " << bitset<64>(a[ans.second]) << endl;
            cout << "OR result =  " << bitset<64>(a[ans.first] | a[ans.second]) << endl;
        } else {
            cout << "No pair found." << endl;
        }
    } else {
        // 静默模式：记录详细结果到日志文件，只向控制台输出两个数字
        log_output(verbose, "Result: ", ans.first, " ", ans.second, "\n");
        
        if (ans.first != -1 && ans.second != -1) {
            log_output(verbose, "Found pair! a[", ans.first, "] | a[", ans.second, "] = all ones\n");
            log_output(verbose, "a[", ans.first, "] = ", bitset<64>(a[ans.first]), "\n");
            log_output(verbose, "a[", ans.second, "] = ", bitset<64>(a[ans.second]), "\n");
            log_output(verbose, "OR result =  ", bitset<64>(a[ans.first] | a[ans.second]), "\n");
        } else {
            log_output(verbose, "No pair found.\n");
        }
        
        // 记录程序结束时间
        auto end_time = chrono::system_clock::now();
        auto end_time_t = chrono::system_clock::to_time_t(end_time);
        log_output(verbose, "\nProgram finished at: ", put_time(localtime(&end_time_t), "%Y-%m-%d %H:%M:%S"), "\n");
        
        // 控制台只输出结果
        cout << ans.first << " " << ans.second << endl;
        
        // 关闭日志文件
        if (log_file.is_open()) {
            log_file.close();
        }
    }
    
    return 0;
}
