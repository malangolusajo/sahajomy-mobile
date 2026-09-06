# Flutter registers plugins through generated code. Preserve Flutter embedding
# metadata while allowing R8 to remove unreachable application code.
-keep class io.flutter.** { *; }
-dontwarn io.flutter.embedding.**
