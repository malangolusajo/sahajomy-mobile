import Flutter
import UIKit
import UserNotifications

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    NotificationCenter.default.addObserver(
      self,
      selector: #selector(screenCaptureChanged),
      name: UIScreen.capturedDidChangeNotification,
      object: nil
    )
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  @objc private func screenCaptureChanged() {
    let coverTag = 947201
    for scene in UIApplication.shared.connectedScenes {
      guard let windowScene = scene as? UIWindowScene else { continue }
      for window in windowScene.windows {
        window.viewWithTag(coverTag)?.removeFromSuperview()
        if windowScene.screen.isCaptured {
          let cover = UIVisualEffectView(
            effect: UIBlurEffect(style: .systemChromeMaterialDark)
          )
          cover.tag = coverTag
          cover.frame = window.bounds
          cover.autoresizingMask = [.flexibleWidth, .flexibleHeight]
          window.addSubview(cover)
        }
      }
    }
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    guard let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "SahajomyNotifications") else { return }
    let channel = FlutterMethodChannel(name: "com.sahajomy.mobile/notifications", binaryMessenger: registrar.messenger())
    channel.setMethodCallHandler { call, result in
      switch call.method {
      case "requestPermission":
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { allowed, error in
          DispatchQueue.main.async {
            if error != nil { result(FlutterError(code: "permission", message: "Unable to request notification permission.", details: nil)) }
            else { result(allowed ? "granted" : "denied") }
          }
        }
      case "openSettings":
        guard let url = URL(string: UIApplication.openSettingsURLString) else { result(false); return }
        UIApplication.shared.open(url) { opened in
          if opened { result(nil) }
          else { result(FlutterError(code: "settings", message: "Unable to open settings.", details: nil)) }
        }
      default: result(FlutterMethodNotImplemented)
      }
    }
  }
}
