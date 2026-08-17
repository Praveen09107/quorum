# Quorum Mobile

Flutter/Riverpod/Drift app. See
`specs/tier3_verification/STATUS_INDEX.md` for real current status.

## Local setup

```
cd mobile
flutter pub get
cp .env.example .env   # fill in real values only if you have them
```

## Running tests

```
dart test
flutter analyze
```

Note: these commands need a real Flutter/Dart SDK. Every mobile
session document in this project was written and structurally
verified without one — confirm results here before merging.