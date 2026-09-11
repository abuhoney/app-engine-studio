package com.bardom.ai.ui;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;
import java.io.File;
import java.io.FileOutputStream;

public class MainActivity extends Activity {
    private WebView webView;

    private File getDir() { File d = getExternalFilesDir(null); return d != null ? d : getFilesDir(); }

    protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS, WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS);
        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setDatabaseEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());
        webView.addJavascriptInterface(this, "AndroidBridge");
        FrameLayout root = new FrameLayout(this);
        root.addView(webView, new FrameLayout.LayoutParams(-1, -1));
        setContentView(root);
        webView.loadUrl("file:///android_asset/webapp/index.html");
    }

    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @JavascriptInterface public String getPlatform() { return "android"; }
    @JavascriptInterface public String getVersion() { return "9.0.0"; }
    @JavascriptInterface public String getFilesDirPath() { return getDir().getAbsolutePath(); }
    @JavascriptInterface public boolean saveFile(String name, String content) { try { File d = getDir(); if (!d.exists()) d.mkdirs(); FileOutputStream w = new FileOutputStream(new File(d, name)); w.write(content.getBytes("UTF-8")); w.close(); return true; } catch (Exception e) { return false; } }
    @JavascriptInterface public String readFile(String path) { try { File f = new File(getDir(), path); if (!f.exists()) return ""; return new String(java.nio.file.Files.readAllBytes(f.toPath()), "UTF-8"); } catch (Exception e) { return ""; } }
    @JavascriptInterface public String listFiles(String dir) { try { File d = new File(getDir(), dir); if (!d.exists()) return "[]"; File[] files = d.listFiles(); StringBuilder sb = new StringBuilder("["); for (int i = 0; files != null && i < files.length; i++) { if (i > 0) sb.append(","); sb.append("{\"name\":\"").append(files[i].getName()).append("\",\"isDir\":").append(files[i].isDirectory()).append("}"); } sb.append("]"); return sb.toString(); } catch (Exception e) { return "[]"; } }
    @JavascriptInterface public boolean deleteFile(String path) { try { return new File(getDir(), path).delete(); } catch (Exception e) { return false; } }
    @JavascriptInterface public boolean existsFile(String path) { try { return new File(getDir(), path).exists(); } catch (Exception e) { return false; } }
    @JavascriptInterface public void showToast(String msg) { Toast.makeText(this, msg, Toast.LENGTH_SHORT).show(); }
    @JavascriptInterface public void installApk(String path) { try { File apk = new File(getDir(), path); if (!apk.exists()) { Toast.makeText(this, "File not found", Toast.LENGTH_SHORT).show(); return; } Intent intent = new Intent(Intent.ACTION_VIEW); intent.setDataAndType(Uri.fromFile(apk), "application/vnd.android.package-archive"); intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); startActivity(intent); } catch (Exception e) { Toast.makeText(this, "Error: " + e.getMessage(), Toast.LENGTH_LONG).show(); } }
    @JavascriptInterface public long getFreeSpace() { return getDir().getFreeSpace(); }
    @JavascriptInterface public String getDeviceInfo() { return "{\"brand\":\"" + android.os.Build.BRAND + "\",\"model\":\"" + android.os.Build.MODEL + "\",\"sdk\":" + android.os.Build.VERSION.SDK_INT + ",\"version\":\"" + android.os.Build.VERSION.RELEASE + "\"}"; }
    @JavascriptInterface public void toast(String m) { Toast.makeText(this, m, Toast.LENGTH_SHORT).show(); }
    @JavascriptInterface public void openUrl(String u) { try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(u))); } catch (Exception e) {} }
    @JavascriptInterface public void shareText(String t) { try { Intent i = new Intent(Intent.ACTION_SEND); i.setType("text/plain"); i.putExtra(Intent.EXTRA_TEXT, t); startActivity(Intent.createChooser(i, "Share")); } catch (Exception e) {} }
    @JavascriptInterface public void requestPermission(String p) { try { if (android.os.Build.VERSION.SDK_INT >= 23) { String perm; if ("camera".equals(p)) perm = android.Manifest.permission.CAMERA; else if ("storage".equals(p)) perm = android.Manifest.permission.WRITE_EXTERNAL_STORAGE; else if ("location".equals(p)) perm = android.Manifest.permission.ACCESS_FINE_LOCATION; else if ("notifications".equals(p)) perm = android.Manifest.permission.POST_NOTIFICATIONS; else return; if (checkSelfPermission(perm) != 0) requestPermissions(new String[]{perm}, 1001); } } catch (Exception e) {} }
}
