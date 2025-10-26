#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cctype>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <optional>
#include <iostream>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
#include <vector>

namespace {

inline uint32_t rotl32(uint32_t v, unsigned s) {
  return (v << s) | (v >> (32 - s));
}

inline uint16_t sha1_first16_5bytes(const uint8_t* data) {
  uint32_t w[80];
  auto make_word = [](uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3) {
    return (static_cast<uint32_t>(b0) << 24) |
           (static_cast<uint32_t>(b1) << 16) |
           (static_cast<uint32_t>(b2) << 8) |
           static_cast<uint32_t>(b3);
  };

  w[0] = make_word(data[0], data[1], data[2], data[3]);
  w[1] = make_word(data[4], 0x80, 0x00, 0x00);
  for (int i = 2; i < 14; ++i) {
    w[i] = 0;
  }
  w[14] = 0;
  w[15] = 40;  // 5 bytes * 8 bits

  for (int i = 16; i < 80; ++i) {
    w[i] = rotl32(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
  }

  uint32_t a = 0x67452301u;
  uint32_t b = 0xEFCDAB89u;
  uint32_t c = 0x98BADCFEu;
  uint32_t d = 0x10325476u;
  uint32_t e = 0xC3D2E1F0u;

  for (int i = 0; i < 80; ++i) {
    uint32_t f, k;
    if (i < 20) {
      f = (b & c) | ((~b) & d);
      k = 0x5A827999u;
    } else if (i < 40) {
      f = b ^ c ^ d;
      k = 0x6ED9EBA1u;
    } else if (i < 60) {
      f = (b & c) | (b & d) | (c & d);
      k = 0x8F1BBCDCu;
    } else {
      f = b ^ c ^ d;
      k = 0xCA62C1D6u;
    }
    uint32_t temp = rotl32(a, 5) + f + e + k + w[i];
    e = d;
    d = c;
    c = rotl32(b, 30);
    b = a;
    a = temp;
  }

  uint32_t h0 = 0x67452301u + a;
  uint32_t result = ((h0 >> 24) & 0xFFu) << 8 | ((h0 >> 16) & 0xFFu);
  return static_cast<uint16_t>(result);
}

template <std::size_t N>
std::array<uint8_t, N> hex_to_bytes(const std::string& hex) {
  if (hex.size() != 2 * N) {
    throw std::invalid_argument("unexpected hex length");
  }
  std::array<uint8_t, N> out{};
  for (std::size_t i = 0; i < N; ++i) {
    unsigned int value;
    std::stringstream ss;
    ss << std::hex << hex.substr(2 * i, 2);
    ss >> value;
    out[i] = static_cast<uint8_t>(value);
  }
  return out;
}

template <std::size_t N>
std::string bytes_to_hex(const std::array<uint8_t, N>& data) {
  std::ostringstream oss;
  oss << std::hex << std::setfill('0');
  for (uint8_t byte : data) {
    oss << std::setw(2) << static_cast<unsigned int>(byte);
  }
  return oss.str();
}

std::vector<uint8_t> hex_to_vector(const std::string& hex) {
  if (hex.size() % 2 != 0) {
    throw std::invalid_argument("odd hex length");
  }
  std::vector<uint8_t> out;
  out.reserve(hex.size() / 2);
  for (std::size_t i = 0; i < hex.size(); i += 2) {
    unsigned int value;
    std::stringstream ss;
    ss << std::hex << hex.substr(i, 2);
    ss >> value;
    out.push_back(static_cast<uint8_t>(value));
  }
  return out;
}

std::string hex_string(uint32_t value, unsigned width) {
  std::ostringstream oss;
  oss << std::hex << std::setw(width) << std::setfill('0') << value;
  return oss.str();
}

using Block = std::array<uint8_t, 4>;
using HalfKey = std::array<uint8_t, 3>;
using FullKey = std::array<uint8_t, 6>;

Block encrypt_block(const Block& block, const FullKey& key, int rounds = 32);
Block decrypt_block(const Block& block, const FullKey& key, int rounds = 32);
HalfKey uint24_to_half(uint32_t value);
FullKey combine_halves(const HalfKey& k1, const HalfKey& k2);
uint16_t feistel_f_raw(uint16_t input, const HalfKey& key);

uint16_t load_be16(const uint8_t* ptr) {
  return static_cast<uint16_t>(ptr[0] << 8 | ptr[1]);
}

struct Sample {
  Block plain{};
  Block cipher{};
  uint16_t L = 0;
  uint16_t R = 0;
  uint16_t Lc = 0;
  uint16_t Rc = 0;
  uint16_t delta2 = 0;  // R ^ Rc
};

struct Dataset {
  std::vector<uint8_t> enc_scrambled;
  std::vector<uint8_t> enc_xorkey;
  std::vector<Sample> samples;
};

struct SearchRange {
  uint32_t start = 0;
  uint32_t end = 1u << 24;

  uint32_t span() const { return end - start; }
};

struct K2LookupTable {
  struct CandidateRange {
    const uint32_t* begin = nullptr;
    const uint32_t* end = nullptr;
    bool valid() const { return begin != nullptr; }
    bool empty() const { return begin == end; }
  };

  std::array<uint32_t, 65537> offsets_L0{};
  std::array<uint32_t, 65537> offsets_L1{};
  std::vector<uint32_t> values_L0;
  std::vector<uint32_t> values_L1;
  uint32_t total_keys = 0;

  CandidateRange query(uint16_t L_value, uint16_t target) const {
    if (total_keys == 0) {
      return {nullptr, nullptr};
    }
    const std::array<uint32_t, 65537>* offsets = nullptr;
    const std::vector<uint32_t>* values = nullptr;
    if (L_value == 0) {
      offsets = &offsets_L0;
      values = &values_L0;
    } else if (L_value == 1) {
      offsets = &offsets_L1;
      values = &values_L1;
    } else {
      return {nullptr, nullptr};
    }
    std::size_t t = static_cast<std::size_t>(target);
    uint32_t start = (*offsets)[t];
    uint32_t end = (*offsets)[t + 1];
    const uint32_t* base = values->data();
    return {base + start, base + end};
  }
};

K2LookupTable build_k2_lookup(const SearchRange& range);

struct FeistelCache {
  std::array<uint16_t, 1u << 16> values{};
  std::array<uint32_t, 1u << 16> stamps{};
  uint32_t generation = 0;
  HalfKey key{};

  void set_key(const HalfKey& new_key) {
    key = new_key;
    ++generation;
    if (generation == 0) {
      std::fill(stamps.begin(), stamps.end(), 0);
      generation = 1;
    }
  }

  uint16_t compute(uint16_t input) {
    uint32_t& stamp = stamps[input];
    if (stamp != generation) {
      stamp = generation;
      values[input] = feistel_f_raw(input, key);
    }
    return values[input];
  }
};

Dataset read_dataset(const std::string& path) {
  std::ifstream in(path);
  if (!in) {
    throw std::runtime_error("failed to open dataset: " + path);
  }

  Dataset dataset;
  std::string line;

  if (!std::getline(in, line)) {
    throw std::runtime_error("unexpected EOF reading enc_scrambled");
  }
  dataset.enc_scrambled = hex_to_vector(line);

  if (!std::getline(in, line)) {
    throw std::runtime_error("unexpected EOF reading enc_xorkey");
  }
  dataset.enc_xorkey = hex_to_vector(line);

  if (!std::getline(in, line)) {
    throw std::runtime_error("unexpected EOF reading count");
  }
  std::size_t count = std::stoull(line);
  dataset.samples.reserve(count);

  for (std::size_t i = 0; i < count; ++i) {
    std::string plain_hex, cipher_hex;
    if (!(in >> plain_hex >> cipher_hex)) {
      throw std::runtime_error("unexpected EOF reading sample row");
    }
    Sample s;
    s.plain = hex_to_bytes<4>(plain_hex);
    s.cipher = hex_to_bytes<4>(cipher_hex);
    s.L = load_be16(s.plain.data());
    s.R = load_be16(s.plain.data() + 2);
    s.Lc = load_be16(s.cipher.data());
    s.Rc = load_be16(s.cipher.data() + 2);
    s.delta2 = static_cast<uint16_t>(s.R ^ s.Rc);
    dataset.samples.push_back(s);
  }

  return dataset;
}
K2LookupTable build_k2_lookup(const SearchRange& range) {
  K2LookupTable table;
  table.total_keys = range.span();
  if (table.total_keys == 0) {
    return table;
  }

  struct Outputs {
    uint16_t f0;
    uint16_t f1;
  };

  std::vector<Outputs> outputs;
  outputs.resize(table.total_keys);

  std::array<uint32_t, 65536> counts0{};
  std::array<uint32_t, 65536> counts1{};

  for (uint32_t offset = 0; offset < table.total_keys; ++offset) {
    uint32_t k2 = range.start + offset;
    auto hk = uint24_to_half(k2);
    uint16_t out0 = feistel_f_raw(0, hk);
    uint16_t out1 = feistel_f_raw(1, hk);
    outputs[offset] = Outputs{out0, out1};
    ++counts0[out0];
    ++counts1[out1];
  }

  for (std::size_t i = 0; i < counts0.size(); ++i) {
    table.offsets_L0[i + 1] = table.offsets_L0[i] + counts0[i];
    table.offsets_L1[i + 1] = table.offsets_L1[i] + counts1[i];
  }

  table.values_L0.resize(table.total_keys);
  table.values_L1.resize(table.total_keys);
  std::array<uint32_t, 65536> cursor0{};
  std::array<uint32_t, 65536> cursor1{};
  for (std::size_t i = 0; i < cursor0.size(); ++i) {
    cursor0[i] = table.offsets_L0[i];
    cursor1[i] = table.offsets_L1[i];
  }

  for (uint32_t offset = 0; offset < table.total_keys; ++offset) {
    uint32_t k2 = range.start + offset;
    uint16_t out0 = outputs[offset].f0;
    uint16_t out1 = outputs[offset].f1;
    uint32_t pos0 = cursor0[out0]++;
    uint32_t pos1 = cursor1[out1]++;
    table.values_L0[pos0] = k2;
    table.values_L1[pos1] = k2;
  }

  return table;
}

SearchRange parse_prefix_range(const std::string& prefix) {
  if (prefix.empty()) {
    return {};
  }

  std::string s = prefix;
  if (s.rfind("0x", 0) == 0 || s.rfind("0X", 0) == 0) {
    s = s.substr(2);
  }
  if (s.empty()) {
    return {};
  }
  if (s.size() > 6) {
    throw std::invalid_argument("prefix too long (max 6 hex digits)");
  }
  for (char ch : s) {
    if (!std::isxdigit(static_cast<unsigned char>(ch))) {
      throw std::invalid_argument("prefix contains non-hex characters");
    }
  }
  uint32_t value = static_cast<uint32_t>(std::stoul(s, nullptr, 16));
  unsigned bits = static_cast<unsigned>(s.size() * 4);
  if (bits > 24) {
    throw std::invalid_argument("prefix bits exceed 24");
  }
  if (bits == 0) {
    return {};
  }
  uint32_t mask = (bits == 32) ? 0xFFFFFFFFu : ((1u << bits) - 1);
  if ((value & ~mask) != 0) {
    throw std::invalid_argument("prefix value too large");
  }
  uint32_t start = value << (24 - bits);
  uint32_t span = 1u << (24 - bits);
  return SearchRange{start, start + span};
}

struct PairLookup {
  struct Entry {
    uint32_t key;
    uint32_t index;
  };

  void build(const std::vector<Sample>& samples) {
    entries.clear();
    entries.reserve(samples.size());
    for (std::size_t i = 0; i < samples.size(); ++i) {
      uint32_t key = (static_cast<uint32_t>(samples[i].L) << 16) |
                     static_cast<uint32_t>(samples[i].Rc);
      entries.push_back({key, static_cast<uint32_t>(i)});
    }
    std::sort(entries.begin(), entries.end(),
              [](const Entry& a, const Entry& b) { return a.key < b.key; });
  }

  template <typename Callback>
  void for_each(uint32_t key, Callback&& cb) const {
    auto range = equal_range(key);
    for (auto it = range.first; it != range.second; ++it) {
      if (!cb(it->index)) {
        break;
      }
    }
  }

  std::pair<std::vector<Entry>::const_iterator,
            std::vector<Entry>::const_iterator>
  equal_range(uint32_t key) const {
    auto lower = std::lower_bound(entries.begin(), entries.end(), key,
                                  [](const Entry& e, uint32_t value) {
                                    return e.key < value;
                                  });
    auto upper = std::upper_bound(lower, entries.end(), key,
                                  [](uint32_t value, const Entry& e) {
                                    return value < e.key;
                                  });
    return {lower, upper};
  }

  std::size_t count(uint32_t key) const {
    auto range = equal_range(key);
    return static_cast<std::size_t>(std::distance(range.first, range.second));
  }

 private:
  std::vector<Entry> entries;
};

struct KeyResult {
  uint32_t k1 = 0;
  uint32_t k2 = 0;
  uint32_t seed_index = 0;
  uint32_t pair_index = 0;
  FullKey full_key{};
};

bool verify_full_key(const FullKey& key, const std::vector<Sample>& samples,
                     const std::vector<uint32_t>& indices) {
  for (uint32_t idx : indices) {
    if (idx >= samples.size()) {
      continue;
    }
    auto enc = encrypt_block(samples[idx].plain, key);
    if (enc != samples[idx].cipher) {
      return false;
    }
  }
  return true;
}

void append_unique(std::vector<uint32_t>& container, uint32_t value) {
  if (std::find(container.begin(), container.end(), value) ==
      container.end()) {
    container.push_back(value);
  }
}

std::optional<KeyResult> find_keys_parallel(
    const Dataset& dataset, const PairLookup& lookup,
    const SearchRange& k1_range, const K2LookupTable& k2_lookup,
    std::optional<uint32_t> seed_start_opt,
    std::optional<uint32_t> seed_end_opt) {
  const auto& samples = dataset.samples;
  const uint32_t total_k1 = k1_range.span();
  if (total_k1 == 0) {
    std::cout << "k1 search range is empty; nothing to do.\n";
    return std::nullopt;
  }
  if (k2_lookup.total_keys == 0) {
    std::cout << "k2 lookup is empty; nothing to do.\n";
    return std::nullopt;
  }

  std::vector<uint32_t> sanity_indices;
  const uint32_t sanity_count =
      static_cast<uint32_t>(std::min<std::size_t>(samples.size(), 12));
  for (uint32_t i = 0; i < sanity_count; ++i) {
    sanity_indices.push_back(i);
  }

  std::vector<uint32_t> order;
  uint32_t total_samples = static_cast<uint32_t>(samples.size());
  uint32_t start = seed_start_opt.value_or(0);
  uint32_t end =
      seed_end_opt.value_or(static_cast<uint32_t>(samples.size()));
  if (start > end || end > total_samples) {
    throw std::runtime_error("invalid seed range");
  }
  if (start == 0 && end == total_samples) {
    order.resize(total_samples);
    std::iota(order.begin(), order.end(), 0);
  } else {
    order.reserve(end - start);
    for (uint32_t idx = start; idx < end; ++idx) {
      order.push_back(idx);
    }
  }
  if (seed_start_opt.has_value() || seed_end_opt.has_value()) {
    // already handled by start/end logic
  }

  std::atomic<bool> found{false};
  std::atomic<uint32_t> next_seed{0};
  std::mutex result_mutex;
  std::optional<KeyResult> result;
  std::mutex io_mutex;

  auto log = [&](const std::string& msg) {
    std::lock_guard<std::mutex> lock(io_mutex);
    std::cout << msg;
    std::cout.flush();
  };

  unsigned thread_count = std::thread::hardware_concurrency();
  if (thread_count == 0) {
    thread_count = 4;
  }
  thread_count =
      std::min<unsigned>(thread_count, static_cast<unsigned>(samples.size()));
  if (thread_count == 0) {
    thread_count = 1;
  }

  auto worker = [&]() {
    std::vector<uint32_t> candidate_buffer;
    std::vector<uint32_t> temp_buffer;
    FeistelCache feistel_cache;
    while (!found.load(std::memory_order_acquire)) {
      uint32_t position =
          next_seed.fetch_add(1, std::memory_order_relaxed);
      if (position >= order.size()) {
        break;
      }
      if (found.load(std::memory_order_acquire)) {
        break;
      }
      uint32_t i = order[position];
      const auto& seed = samples[i];

      std::string seed_core = "seed=" + std::to_string(i);
      std::string seed_tag = "[" + seed_core + "]";
      constexpr uint32_t kSeedLogInterval = 1;
      bool seed_logged = false;
      auto log_seed = [&]() {
        std::ostringstream seed_msg;
        seed_msg << seed_tag << " scanning " << total_k1
                 << " k1 values (L=0x" << hex_string(seed.L, 4)
                 << ", R=0x" << hex_string(seed.R, 4) << ", Lc=0x"
                 << hex_string(seed.Lc, 4) << ", Rc=0x"
                 << hex_string(seed.Rc, 4) << ")\n";
        log(seed_msg.str());
      };
      if (position % kSeedLogInterval == 0) {
        log_seed();
        seed_logged = true;
      }

      uint32_t log_counter = 0;
      for (uint32_t offset = 0; offset < total_k1; ++offset) {
        ++log_counter;
        if (found.load(std::memory_order_acquire)) {
          break;
        }
        const uint32_t k1 = k1_range.start + offset;
        auto half_k1 = uint24_to_half(k1);
        feistel_cache.set_key(half_k1);
        uint16_t f_r = feistel_cache.compute(seed.R);
        uint16_t f_lc = feistel_cache.compute(seed.Lc);
        uint16_t need_L = static_cast<uint16_t>(seed.L ^ f_r);
        uint16_t need_Rc = static_cast<uint16_t>(seed.Rc ^ f_lc);
        uint32_t composite_key = (static_cast<uint32_t>(need_L) << 16) |
                                 static_cast<uint32_t>(need_Rc);
        std::string k1_tag = "[" + seed_core + ",k1=" +
                              hex_string(k1, 6) + "]";

        constexpr std::size_t kMaxMatches = 8;
        auto range = lookup.equal_range(composite_key);
        std::size_t match_count =
            static_cast<std::size_t>(std::distance(range.first, range.second));
        if (match_count == 0) {
          continue;
        }
        if (match_count > kMaxMatches) {
          if (seed_logged) {
            log(k1_tag + " skipping (" + std::to_string(match_count) +
                " mates)\n");
          }
          continue;
        }

        struct MateEntry {
          uint32_t index;
          K2LookupTable::CandidateRange range;
          std::size_t count;
        };

        std::vector<MateEntry> mate_entries;
        mate_entries.reserve(match_count);
        for (auto it = range.first; it != range.second; ++it) {
          uint32_t j = it->index;
          if (j == i) {
            continue;
          }
          const auto& mate = samples[j];
          uint16_t target = static_cast<uint16_t>(mate.R ^ seed.R);
          auto candidate_range = k2_lookup.query(mate.L, target);
          if (!candidate_range.valid() || candidate_range.empty()) {
            continue;
          }
          mate_entries.push_back(MateEntry{
              j, candidate_range,
              static_cast<std::size_t>(candidate_range.end - candidate_range.begin)});
        }
        if (mate_entries.empty()) {
          continue;
        }
        std::sort(mate_entries.begin(), mate_entries.end(),
                  [](const MateEntry& a, const MateEntry& b) {
                    return a.count < b.count;
                  });

        for (const auto& entry : mate_entries) {
          if (found.load(std::memory_order_acquire)) {
            break;
          }
          uint32_t j = entry.index;
          const auto& mate_range = entry.range;

          candidate_buffer.clear();
          candidate_buffer.reserve(entry.count);

          std::vector<const uint32_t*> ptrs;
          std::vector<const uint32_t*> ptrs_end;
          ptrs.reserve(mate_entries.size());
          ptrs_end.reserve(mate_entries.size());
          for (const auto& other : mate_entries) {
            if (other.index == j) {
              continue;
            }
            ptrs.push_back(other.range.begin);
            ptrs_end.push_back(other.range.end);
          }

          for (const uint32_t* it = mate_range.begin; it != mate_range.end;
               ++it) {
            uint32_t candidate = *it;
            bool present = true;
            for (std::size_t idx = 0; idx < ptrs.size(); ++idx) {
              const uint32_t*& p = ptrs[idx];
              const uint32_t* end_p = ptrs_end[idx];
              while (p != end_p && *p < candidate) {
                ++p;
              }
              if (p == end_p || *p != candidate) {
                present = false;
                break;
              }
            }
            if (present) {
              candidate_buffer.push_back(candidate);
            }
          }
          if (candidate_buffer.empty()) {
            continue;
          }

          std::size_t candidate_count = candidate_buffer.size();
          constexpr uint32_t kCandidateLogInterval = 64;
          if (!seed_logged && candidate_count <= 8) {
            log_seed();
            seed_logged = true;
          }
          bool should_log_candidates =
              seed_logged &&
              (((log_counter - 1) % kCandidateLogInterval == 0) ||
               (candidate_count <= 8));
          if (should_log_candidates) {
            log(k1_tag + ",mate=" + std::to_string(j) + " candidates=" +
                std::to_string(candidate_count) + "\n");
          }

          for (uint32_t k2 : candidate_buffer) {
            if (found.load(std::memory_order_acquire)) {
              break;
            }
            auto half_k2 = uint24_to_half(k2);
            auto full = combine_halves(half_k1, half_k2);

          std::vector<uint32_t> check_indices = {i, j};
          for (const auto& other : mate_entries) {
            if (other.index == j || other.index == i) {
              continue;
            }
            append_unique(check_indices, other.index);
            if (check_indices.size() >= 4) {
              break;
            }
          }
            for (uint32_t idx : sanity_indices) {
              if (check_indices.size() >= 4) {
                break;
              }
              append_unique(check_indices, idx);
            }

            if (verify_full_key(full, samples, check_indices)) {
              KeyResult candidate{
                  .k1 = k1,
                  .k2 = k2,
                  .seed_index = i,
                  .pair_index = j,
                  .full_key = full,
              };
              bool expected = false;
              if (found.compare_exchange_strong(expected, true,
                                                std::memory_order_acq_rel)) {
                {
                  std::lock_guard<std::mutex> lock(result_mutex);
                  result = candidate;
                }
                log(k1_tag + ",k2=" + hex_string(k2, 6) +
                    " validated on sanity samples\n");
              }
              break;
            }
          }
          if (found.load(std::memory_order_acquire)) {
            break;
          }
        }

        if (found.load(std::memory_order_acquire)) {
          break;
        }
      }

      if (found.load(std::memory_order_acquire)) {
        break;
      }
    }
  };

  std::vector<std::thread> threads;
  threads.reserve(thread_count);
  for (unsigned t = 0; t < thread_count; ++t) {
    threads.emplace_back(worker);
  }
  for (auto& th : threads) {
    th.join();
  }

  return result;
}

HalfKey uint24_to_half(uint32_t value) {
  HalfKey hk{};
  hk[0] = static_cast<uint8_t>((value >> 16) & 0xFF);
  hk[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  hk[2] = static_cast<uint8_t>(value & 0xFF);
  return hk;
}

FullKey combine_halves(const HalfKey& k1, const HalfKey& k2) {
  FullKey key{};
  std::copy(k1.begin(), k1.end(), key.begin());
  std::copy(k2.begin(), k2.end(), key.begin() + 3);
  return key;
}

uint16_t feistel_f_raw(uint16_t input, const HalfKey& key) {
  uint8_t buffer[5];
  buffer[0] = static_cast<uint8_t>((input >> 8) & 0xFF);
  buffer[1] = static_cast<uint8_t>(input & 0xFF);
  buffer[2] = key[0];
  buffer[3] = key[1];
  buffer[4] = key[2];
  uint16_t value = sha1_first16_5bytes(buffer);
  return value;
}

Block feistel_rounds(const Block& in_block, const FullKey& key, int rounds,
                     bool encrypt_mode) {
  HalfKey k1{};
  HalfKey k2{};
  std::copy(key.begin(), key.begin() + 3, k1.begin());
  std::copy(key.begin() + 3, key.end(), k2.begin());

  std::array<uint8_t, 2> L{};
  std::array<uint8_t, 2> R{};
  L[0] = in_block[0];
  L[1] = in_block[1];
  R[0] = in_block[2];
  R[1] = in_block[3];

  for (int r = 0; r < rounds; ++r) {
    const HalfKey& round_key = encrypt_mode ? ((r % 2 == 0) ? k1 : k2)
                                            : ((r % 2 == 0) ? k2 : k1);
    uint8_t input[5];
    input[0] = R[0];
    input[1] = R[1];
    input[2] = round_key[0];
    input[3] = round_key[1];
    input[4] = round_key[2];
    uint16_t fbits = sha1_first16_5bytes(input);
    std::array<uint8_t, 2> new_L = R;
    std::array<uint8_t, 2> new_R{};
    new_R[0] = static_cast<uint8_t>(L[0] ^ static_cast<uint8_t>(fbits >> 8));
    new_R[1] = static_cast<uint8_t>(L[1] ^ static_cast<uint8_t>(fbits & 0xFF));
    L = new_L;
    R = new_R;
  }

  Block out{};
  out[0] = R[0];
  out[1] = R[1];
  out[2] = L[0];
  out[3] = L[1];
  return out;
}

Block encrypt_block(const Block& block, const FullKey& key, int rounds) {
  return feistel_rounds(block, key, rounds, /*encrypt_mode=*/true);
}

Block decrypt_block(const Block& block, const FullKey& key, int rounds) {
  return feistel_rounds(block, key, rounds, /*encrypt_mode=*/false);
}

}  // namespace

int main(int argc, char** argv) {
  {
    const auto key = hex_to_bytes<6>("000102030405");
    const auto plain = hex_to_bytes<4>("00112233");
    const auto expected = hex_to_bytes<4>("1d69ace5");
    auto enc = encrypt_block(plain, key);
    assert(enc == expected);
    auto dec = decrypt_block(enc, key);
    assert(dec == plain);

    const auto plain2 = hex_to_bytes<4>("7ed73119");
    const auto expected2 = hex_to_bytes<4>("b2c85a36");
    auto enc2 = encrypt_block(plain2, key);
    assert(enc2 == expected2);
  }

  std::string dataset_path = "data_local.txt";
  SearchRange k1_range;
  bool k1_range_override = false;

  std::optional<uint32_t> seed_start_opt;
  std::optional<uint32_t> seed_end_opt;

  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--help") {
      std::cout << "Usage: " << argv[0]
                << " [dataset_path] [--k1-prefix=HEX] "
                   "[--seed-range START END]\n";
      return 0;
    } else if (arg.rfind("--k1-prefix=", 0) == 0) {
      std::string value = arg.substr(std::strlen("--k1-prefix="));
      k1_range = parse_prefix_range(value);
      k1_range_override = true;
    } else if (arg == "--k1-prefix") {
      if (i + 1 >= argc) {
        std::cerr << "--k1-prefix requires an argument\n";
        return 1;
      }
      k1_range = parse_prefix_range(argv[++i]);
      k1_range_override = true;
    } else if (arg == "--seed-range") {
      if (i + 2 >= argc) {
        std::cerr << "--seed-range requires START and END indices\n";
        return 1;
      }
      seed_start_opt = static_cast<uint32_t>(std::stoul(argv[++i]));
      seed_end_opt = static_cast<uint32_t>(std::stoul(argv[++i]));
    } else if (!arg.empty() && arg[0] == '-') {
      std::cerr << "Unknown option: " << arg << "\n";
      return 1;
    } else {
      dataset_path = arg;
    }
  }

  try {
    Dataset dataset = read_dataset(dataset_path);
    PairLookup lookup;
    lookup.build(dataset.samples);
    std::cout << "Loaded dataset '" << dataset_path << "' with "
              << dataset.samples.size() << " samples.\n";
    std::cout << "enc_scrambled bytes: " << dataset.enc_scrambled.size()
              << ", enc_xorkey bytes: " << dataset.enc_xorkey.size() << "\n";
    auto print_range = [](const char* label, const SearchRange& range,
                          bool overridden) {
      if (!overridden) {
        std::cout << label << " search range: full 24-bit space\n";
        return;
      }
      std::cout << label << " prefix range: [0x" << std::hex << std::setw(6)
                << std::setfill('0') << range.start << ", 0x" << std::setw(6)
                << range.end << ")\n"
                << std::dec << std::setfill(' ');
    };
    print_range("k1", k1_range, k1_range_override);
    if (seed_start_opt.has_value() || seed_end_opt.has_value()) {
      uint32_t start = seed_start_opt.value_or(0);
      uint32_t end = seed_end_opt.value_or(
          static_cast<uint32_t>(dataset.samples.size()));
      std::cout << "Seed range: [" << start << ", " << end << ")\n";
    }
    SearchRange full_k2_range;
    std::cout << "Building k2 lookup table for "
              << static_cast<uint64_t>(full_k2_range.span()) << " keys...\n";
    auto k2_lookup = build_k2_lookup(full_k2_range);
    std::cout << "k2 lookup ready (avg bucket size ~"
              << std::fixed << std::setprecision(2)
              << (k2_lookup.total_keys == 0
                      ? 0.0
                      : static_cast<double>(k2_lookup.total_keys) / 65536.0)
              << ").\n"
              << std::defaultfloat;

    auto result = find_keys_parallel(dataset, lookup, k1_range, k2_lookup,
                                     seed_start_opt, seed_end_opt);
    if (result.has_value()) {
      const auto& keys = result.value();
      std::cout << "Recovered key halves: k1=" << std::hex << std::setw(6)
                << std::setfill('0') << keys.k1 << ", k2=" << std::setw(6)
                << keys.k2 << std::dec << std::setfill(' ') << "\n";
      std::cout << "Seed index: " << keys.seed_index
                << ", mate index: " << keys.pair_index << "\n";
      if (!dataset.enc_scrambled.empty() && !dataset.enc_xorkey.empty()) {
        std::vector<uint8_t> decrypted_scrambled;
        std::vector<uint8_t> decrypted_xor;
        decrypted_scrambled.reserve(dataset.enc_scrambled.size());
        decrypted_xor.reserve(dataset.enc_xorkey.size());

        for (std::size_t offset = 0; offset + 4 <= dataset.enc_scrambled.size(); offset += 4) {
          Block block{};
          std::copy_n(dataset.enc_scrambled.begin() + offset, 4, block.begin());
          auto plain_block = decrypt_block(block, keys.full_key);
          decrypted_scrambled.insert(decrypted_scrambled.end(), plain_block.begin(), plain_block.end());
        }
        for (std::size_t offset = 0; offset + 4 <= dataset.enc_xorkey.size(); offset += 4) {
          Block block{};
          std::copy_n(dataset.enc_xorkey.begin() + offset, 4, block.begin());
          auto plain_block = decrypt_block(block, keys.full_key);
          decrypted_xor.insert(decrypted_xor.end(), plain_block.begin(), plain_block.end());
        }

        if (decrypted_scrambled.size() == decrypted_xor.size()) {
          std::vector<uint8_t> flag(decrypted_scrambled.size());
          for (std::size_t idx = 0; idx < decrypted_scrambled.size(); ++idx) {
            flag[idx] = static_cast<uint8_t>(decrypted_scrambled[idx] ^ decrypted_xor[idx]);
          }
          std::cout << "Recovered flag: ";
          for (uint8_t ch : flag) {
            if (ch >= 32 && ch <= 126) {
              std::cout << static_cast<char>(ch);
            } else {
              std::cout << '.';
            }
          }
          std::cout << "\n";
        }
      }

    } else {
      std::cout << "No key found.\n";
    }
  } catch (const std::exception& ex) {
    std::cerr << "Error: " << ex.what() << "\n";
    return 1;
  }

  return 0;
}
