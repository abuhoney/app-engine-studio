package com.bardom.ai.ui;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.*;
import android.webkit.WebView;
import android.widget.Toast;
import java.io.*;
import org.json.JSONObject;

/**
 * النشاط الرئيسي - قشرة WebView تحمل لوحة التحكم
 * جميع الوظائف في ملفات dashboard/ — هذا الملف لا يتغير
 */
public class MainActivity extends Activity {

    private WebView webView;
    private static final String HOME_URL = "file:///android_asset/webapp/index.html";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // إعداد WebView
        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setDatabaseEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setSupportZoom(false);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setMediaPlaybackRequiresUserGesture(false);

        // ربط JavaScript Bridge
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");

        // معالج أخطاء التحميل
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, int code, String desc, String url) {
                // محاولة تحميل من التخزين الداخلي
            }
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                view.loadUrl(url);
                return true;
            }
        });

        setContentView(webView);
        webView.loadUrl(HOME_URL);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        webView.destroy();
        super.onDestroy();
    }

    /**
     * جسر Android-JavaScript
     * يُعرض لوظائف JavaScript كـ window.AndroidBridge
     * لإضافة وظيفة جديدة: أضف طريقة هنا مع @JavascriptInterface
     * لا حاجة لإعادة بناء APK لو تم تنفيذها في JavaScript
     */
    public class AndroidBridge {

        @JavascriptInterface
        public String getPlatform() { return "android"; }

        @JavascriptInterface
        public String getVersion() { return "1.0.0"; }

        @JavascriptInterface
        public String getFilesDir() {
            java.io.File dir = getExternalFilesDir(null);
            return dir != null ? dir.getAbsolutePath() : "";
        }

        @JavascriptInterface
        public String readFile(String path) {
            try {
                File f = new File(getExternalFilesDir(null), path);
                if (!f.exists()) return "";
                BufferedReader r = new BufferedReader(new FileReader(f));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = r.readLine()) != null) sb.append(line).append("\n");
                r.close();
                return sb.toString();
            } catch (Exception e) { return ""; }
        }

        @JavascriptInterface
        public boolean saveFile(String name, String content) {
            try {
                File dir = getExternalFilesDir(null);
                if (dir == null) return false;
                File f = new File(dir, name);
                FileWriter w = new FileWriter(f);
                w.write(content);
                w.close();
                return true;
            } catch (Exception e) { return false; }
        }

        @JavascriptInterface
        public String listFiles(String dir) {
            try {
                File d = new File(getExternalFilesDir(null), dir);
                if (!d.exists() || !d.isDirectory()) return "[]";
                File[] files = d.listFiles();
                if (files == null) return "[]";
                StringBuilder sb = new StringBuilder("[");
                for (File f : files) {
                    if (sb.length() > 1) sb.append(",");
                    sb.append("{\"name\":\"").append(f.getName()).append("\",\"isDir\":").append(f.isDirectory()).append("}");
                }
                sb.append("]");
                return sb.toString();
            } catch (Exception e) { return "[]"; }
        }

        @JavascriptInterface
        public boolean deleteFile(String path) {
            File f = new File(getExternalFilesDir(null), path);
            return f.delete();
        }

        @JavascriptInterface
        public boolean existsFile(String path) {
            File f = new File(getExternalFilesDir(null), path);
            return f.exists();
        }

        @JavascriptInterface
        public void showToast(String msg) {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, msg, Toast.LENGTH_SHORT).show());
        }

        @JavascriptInterface
        public void installApk(String path) {
            runOnUiThread(() -> {
                try {
                    java.io.File apkFile = new java.io.File(getExternalFilesDir(null), path);
                    if (!apkFile.exists()) {
                        Toast.makeText(MainActivity.this, "الملف غير موجود", Toast.LENGTH_SHORT).show();
                        return;
                    }
                    android.content.Intent intent = new android.content.Intent(android.content.Intent.ACTION_VIEW);
                    intent.setDataAndType(android.net.Uri.fromFile(apkFile), "application/vnd.android.package-archive");
                    intent.addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION | android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(intent);
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "فشل التثبيت: " + e.getMessage(), Toast.LENGTH_LONG).show();
                }
            });
        }

        @JavascriptInterface
        public long getFreeSpace() {
            java.io.File dir = getExternalFilesDir(null);
            return dir != null ? dir.getFreeSpace() : 0;
        }

        @JavascriptInterface
        public String getDeviceInfo() {
            try {
                JSONObject info = new JSONObject();
                info.put("brand", android.os.Build.BRAND);
                info.put("model", android.os.Build.MODEL);
                info.put("sdk", android.os.Build.VERSION.SDK_INT);
                info.put("version", android.os.Build.VERSION.RELEASE);
                return info.toString();
            } catch (Exception e) { return "{}"; }
        }
    }
}
