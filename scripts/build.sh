#!/usr/bin/env bash
# ============================================================
# build.sh — بناء Bardom AI APK
# يقرأ dashboard/ ويُنشئ APK قابل للتطوير بالملفات فقط
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DASHBOARD_DIR="$PROJECT_DIR/dashboard"
ANDROID_DIR="$PROJECT_DIR/android-project"
BUILD_DIR="$PROJECT_DIR/build"
OUTPUT_APK="$PROJECT_DIR/Universal_App_Generator.apk"

# إعدادات Android SDK
ANDROID_SDK="${ANDROID_HOME:-/home/z/my-project/android-sdk}"
BUILD_TOOLS_VER="${BUILD_TOOLS_VERSION:-34.0.0}"
BUILD_TOOLS="$ANDROID_SDK/build-tools/$BUILD_TOOLS_VER"
PLATFORM="${PLATFORM_VERSION:-android-34}"
PLATFORM_JAR="$ANDROID_SDK/platforms/$PLATFORM/android.jar"
ECJ_JAR="${ECJ_JAR:-$ANDROID_SDK/ecj/ecj.jar}"

# مسار عمل مؤقت بدون مسافات
WORK_ROOT="/tmp/bardom_build_$$"
mkdir -p "$WORK_ROOT"
cleanup() { rm -rf "$WORK_ROOT"; }
trap cleanup EXIT

echo "=== Bardom AI APK Builder ==="
echo "SDK: $ANDROID_SDK"
echo "Build Tools: $BUILD_TOOLS"
echo "Platform: $PLATFORM_JAR"
echo ""

# ---- الخطوة 1: نسخ dashboard إلى assets ----
echo "[1/7] نسخ dashboard إلى assets..."
ASSETS_DIR="$ANDROID_DIR/app/src/main/assets/webapp"
rm -rf "$ASSETS_DIR"
mkdir -p "$ASSETS_DIR"
cp -r "$DASHBOARD_DIR"/* "$ASSETS_DIR/"
echo "   ✅ تم نسخ $(find "$ASSETS_DIR" -type f | wc -l) ملف"

# ---- الخطوة 2: تجميع الموارد ----
echo "[2/7] تجميع الموارد (aapt2 compile)..."
mkdir -p "$BUILD_DIR/gen" "$BUILD_DIR/obj" "$BUILD_DIR/apk" "$BUILD_DIR/libs"
rm -f "$BUILD_DIR/gen/compiled-res.zip"
"$BUILD_TOOLS/aapt2" compile --dir "$ANDROID_DIR/app/src/main/res" -o "$BUILD_DIR/gen/compiled-res.zip"

# ---- الخطوة 3: ربط الموارد ----
echo "[3/7] ربط الموارد (aapt2 link)..."
mkdir -p "$BUILD_DIR/gen/src"
"$BUILD_TOOLS/aapt2" link \
    --manifest "$ANDROID_DIR/app/src/main/AndroidManifest.xml" \
    -I "$PLATFORM_JAR" \
    --java "$BUILD_DIR/gen/src" \
    --min-sdk-version 21 \
    --target-sdk-version 34 \
    --auto-add-overlay \
    -A "$ASSETS_DIR" \
    -o "$BUILD_DIR/apk/base.apk" \
    "$BUILD_DIR/gen/compiled-res.zip"

# ---- الخطوة 4: ترجمة Java ----
echo "[4/7] ترجمة Java..."
# نسخ المصادر إلى مسار مؤقت بدون مسافات
WORK_SRC="$WORK_ROOT/src"
mkdir -p "$WORK_SRC"
cp -rL "$ANDROID_DIR/app/src/main/java"/* "$WORK_SRC/" 2>/dev/null || true
if [ -d "$BUILD_DIR/gen/src" ]; then
    cp -rL "$BUILD_DIR/gen/src"/* "$WORK_SRC/" 2>/dev/null || true
fi

JAVA_COUNT=$(find "$WORK_SRC" -name "*.java" 2>/dev/null | wc -l)
echo "   ملفات Java: $JAVA_COUNT"

if [ "$JAVA_COUNT" -gt 0 ]; then
    mkdir -p "$BUILD_DIR/obj"
    # Try project JDK, system javac, then ECJ
    PROJECT_JDK="/home/z/my-project/jdk17"
    if [ -x "$PROJECT_JDK/bin/javac" ]; then
        "$PROJECT_JDK/bin/javac" -source 11 -target 11 -nowarn -encoding UTF-8 \
            -classpath "$PLATFORM_JAR" -d "$BUILD_DIR/obj" \
            $(find "$WORK_SRC" -name "*.java")
    elif command -v javac &> /dev/null; then
        javac -source 11 -target 11 -nowarn -encoding UTF-8 \
            -classpath "$PLATFORM_JAR" -d "$BUILD_DIR/obj" \
            $(find "$WORK_SRC" -name "*.java")
    elif [ -f "$ECJ_JAR" ]; then
        echo "   استخدام ECJ compiler..."
        java -jar "$ECJ_JAR" -source 11 -target 11 -nowarn -encoding UTF-8 \
            -bootclasspath "$PLATFORM_JAR" \
            -classpath "$PLATFORM_JAR" -d "$BUILD_DIR/obj" \
            $(find "$WORK_SRC" -name "*.java")
    else
        echo "   ⚠️  لا يوجد مترجم Java"
    fi
    echo "   ✅ تمت الترجمة"
else
    echo "   ⚠️  لا توجد ملفات Java"
fi

# ---- الخطوة 5: تحويل إلى DEX ----
echo "[5/7] تحويل إلى DEX (d8)..."
rm -f "$BUILD_DIR/libs/classes.dex"
# نسخ ملفات class إلى مسار مؤقت بدون مسافات
WORK_OBJ="$WORK_ROOT/obj"
mkdir -p "$WORK_OBJ"
cp -rL "$BUILD_DIR/obj"/* "$WORK_OBJ/" 2>/dev/null || true
CLASS_COUNT=$(find "$WORK_OBJ" -name "*.class" 2>/dev/null | wc -l)
if [ "$CLASS_COUNT" -gt 0 ]; then
    mkdir -p "$BUILD_DIR/libs"
    "$BUILD_TOOLS/d8" --min-api 21 --lib "$PLATFORM_JAR" --output "$BUILD_DIR/libs" \
        $(find "$WORK_OBJ" -name "*.class")
    echo "   ✅ تم إنشاء DEX"
else
    echo "   ⚠️  لا توجد ملفات .class"
fi

# ---- الخطوة 6: دمج DEX + zipalign ----
echo "[6/7] دمج وضبط APK..."
UNSIGNED_APK="$BUILD_DIR/apk/app-unsigned.apk"
cp "$BUILD_DIR/apk/base.apk" "$UNSIGNED_APK"
if [ -f "$BUILD_DIR/libs/classes.dex" ]; then
    (cd "$BUILD_DIR/libs" && zip -j -0 "$UNSIGNED_APK" classes.dex)
fi
"$BUILD_TOOLS/zipalign" -f -p 4 "$UNSIGNED_APK" "$BUILD_DIR/apk/app-aligned.apk"

# ---- الخطوة 7: التوقيع ----
echo "[7/7] توقيع APK..."
KEYSTORE="$PROJECT_DIR/release.keystore"
KEY_ALIAS="bardom-release"
STORE_PASS="bardom_release_2026"
KEY_PASS="bardom_release_2026"

if [ ! -f "$KEYSTORE" ]; then
    echo "   إنشاء keystore..."
    keytool -genkey -v -keystore "$KEYSTORE" -alias "$KEY_ALIAS" \
        -keyalg RSA -keysize 2048 -validity 9125 \
        -storepass "$STORE_PASS" -keypass "$KEY_PASS" \
        -dname "CN=BardomPro, OU=Bardom AI, O=Bardom, L=Riyadh, ST=Riyadh, C=SA" 2>/dev/null || true
fi

mkdir -p "$(dirname "$OUTPUT_APK")"
"$BUILD_TOOLS/apksigner" sign \
    --ks "$KEYSTORE" --ks-key-alias "$KEY_ALIAS" \
    --ks-pass "pass:$STORE_PASS" --key-pass "pass:$KEY_PASS" \
    --out "$OUTPUT_APK" "$BUILD_DIR/apk/app-aligned.apk"

# التحقق
echo ""
echo "=== التحقق ==="
"$BUILD_TOOLS/apksigner" verify --verbose "$OUTPUT_APK" 2>&1 | head -5

echo ""
echo "✅ تم بناء APK بنجاح!"
echo "📁 الملف: $OUTPUT_APK"
echo "📏 الحجم: $(du -h "$OUTPUT_APK" | cut -f1)"
echo ""
echo "🔑 لتطوير التطبيق بدون إعادة البناء:"
echo "   1. عدّل الملفات في dashboard/"
echo "   2. أعد تشغيل build.sh لتحديث APK"
echo "   أو: أضف ملف JS في dashboard/js/modules/"
echo "   وأضف اسمه في dashboard/config/app.json → modules[]"