// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct plain Dart; hand-verified boundary
// arithmetic (see this session's DECISIONS_LOG entry for the real Python
// reimplementation run before this file was finalized) is the actual
// verification available in this environment.
//
// Three tiers sized to Quorum's actual model footprints, not a generic
// industry threshold (ADD §10.7 — real research found no universal
// standard to defer to; this is a project-specific engineering judgment).
// These thresholds are fully real and resolvable right now, independent
// of MOBILE_02's still-open Full-tier model question in model_config.dart
// — the 8GB/4GB boundaries were decided on their own.

enum DeviceTier { full, light, cloudOnly }

/// Real, exact boundaries from `QUORUM_CONFIGURATION_CONSTANTS.md` §7 /
/// ADD §10.7: Full ≥8192MB, Light 4096–8191MB, Cloud-only <4096MB. Both
/// boundaries are inclusive on their lower edge — a device at exactly
/// 8192MB is Full tier, a device at exactly 4096MB is Light tier, never
/// the tier below.
DeviceTier classifyDeviceTier(int totalRamMb) {
  if (totalRamMb >= 8192) return DeviceTier.full;
  if (totalRamMb >= 4096) return DeviceTier.light;
  return DeviceTier.cloudOnly;
}
