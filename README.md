# sahajomy_mobile

A new Flutter project.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Flutter learning resources](https://docs.flutter.dev/reference/learning-resources)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.

## Android release bundle

Create a signed, versioned Play Store bundle with:

```powershell
.\tool\build_release.ps1
```

The script reads `version` from `pubspec.yaml` and produces a file such as
`build\app\outputs\bundle\release\Sahajomy-v1.0.0+1.aab`.

Create an installable signed APK with:

```powershell
.\tool\build_release.ps1 -Format apk
```
