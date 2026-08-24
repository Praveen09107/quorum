// Sprint 0 (`IMPL_00`) has now genuinely run, for real, to completion, on
// a real physical Android device -- see `QUORUM_CONFIGURATION_CONSTANTS.md`
// §7 and `DECISIONS_LOG.md` `DEC-130` for the full real record, not
// recalled from memory. Real, live, on-device result: Gemma 4 E4B never
// finished downloading (a real, ordinary mid-transfer network hiccup on a
// ~4.7GB file, precisely diagnosed in `DEC-130`), but Llama 3.2 3B
// genuinely, fully downloaded, loaded, and ran real inference against all
// 6 of Sprint 0's real test prompts -- 67% validity (4/6 passed). Per
// `ModelBenchmark.decideWinner()`'s own real logic (`!gemma.loadedSuccessfully
// -> return llama3_2_3B`), Llama 3.2 3B is the real, mechanically-decided
// winner -- not a StateError escalation to the Light-tier fallback.

/// Every real on-device model identifier this project's architecture
/// names anywhere (ADD §11.1, §10.7) — `unresolved` is a genuine, real
/// member of this enum, not a null-hack. A Full-tier device's model
/// choice IS one of these values; the honest fact is which one is not
/// yet known.
enum OnDeviceModelId {
  unresolved,
  gemma4E4B,
  llama32_3B,
  smolLM2_1_7B,
}

/// THE one constant every later session touching the on-device model
/// must read from, never re-guess. Changed from [OnDeviceModelId.unresolved]
/// because `IMPL_00` (Sprint 0) genuinely ran to completion on a real
/// Android device: Llama 3.2 3B genuinely downloaded, loaded, and passed
/// real, live on-device inference against Sprint 0's real test prompts
/// (67% validity, `DEC-130`) -- a real, mechanically-decided winner, not
/// a guess and not the Light-tier fallback. Any future session changing
/// this value again needs its own real benchmark run, not a guess.
const OnDeviceModelId resolvedFullTierModel = OnDeviceModelId.llama32_3B;

/// A real thing that WAS resolvable now, correctly separated from what
/// wasn't: the Light tier's fallback model was locked independently of
/// Sprint 0's open question — confirmed directly against
/// `QUORUM_MASTER_REFERENCE.md` §5 ("On-device fallback | SmolLM2-1.7B |
/// Locked") before writing this, not assumed from memory.
const String lightTierModelId = 'SmolLM2-1.7B';
