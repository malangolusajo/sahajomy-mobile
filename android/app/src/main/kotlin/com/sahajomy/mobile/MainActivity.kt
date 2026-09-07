package com.sahajomy.mobile

import android.os.Bundle
import android.os.Build
import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.app.NotificationManager
import android.provider.Settings
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var notificationResult: MethodChannel.Result? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.sahajomy.mobile/notifications")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "requestPermission" -> {
                        if (notificationResult != null) {
                            result.error("busy", "A permission request is already open.", null)
                        } else if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                            notificationResult = result
                            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 701)
                        } else {
                            val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                            result.success(if (Build.VERSION.SDK_INT < 24 || manager.areNotificationsEnabled()) "granted" else "denied")
                        }
                    }
                    "openSettings" -> {
                        val intent = if (Build.VERSION.SDK_INT >= 26) {
                            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
                        } else {
                            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, android.net.Uri.parse("package:$packageName"))
                        }
                        startActivity(intent)
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 701) {
            notificationResult?.success(if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) "granted" else "denied")
            notificationResult = null
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Parcel, identity, QR, and PIN data must never enter screenshots,
        // screen recordings, or the Android recent-apps thumbnail.
        window.setFlags(
            WindowManager.LayoutParams.FLAG_SECURE,
            WindowManager.LayoutParams.FLAG_SECURE,
        )
    }
}
