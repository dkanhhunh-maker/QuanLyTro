package vn.hoanguyen.quanlynhatro;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private final ExecutorService printerExecutor = Executors.newSingleThreadExecutor();
    private ValueCallback<Uri[]> filePathCallback;

    // Mở trình chọn file của Android (dùng cho nút "Nhập file sao lưu")
    private final ActivityResultLauncher<Intent> fileChooserLauncher =
        registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result -> {
            if (filePathCallback == null) return;
            Uri[] uris = null;
            if (result.getResultCode() == RESULT_OK) {
                uris = WebChromeClient.FileChooserParams.parseResult(result.getResultCode(), result.getData());
            }
            filePathCallback.onReceiveValue(uris);
            filePathCallback = null;
        });

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        // Đăng ký cầu nối JavaScript -> Native TCP Socket cho máy in nhiệt WiFi Port 9100
        webView.addJavascriptInterface(new AndroidPrinterBridge(this), "AndroidPrinterBridge");

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = callback;
                try {
                    Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("*/*");
                    fileChooserLauncher.launch(Intent.createChooser(intent, "Chọn file sao lưu (.json)"));
                } catch (Exception e) {
                    filePathCallback = null;
                    callback.onReceiveValue(null);
                    return false;
                }
                return true;
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();
                if (scheme != null && (scheme.equals("tel") || scheme.equals("mailto") || scheme.equals("rawbt") || uri.toString().contains("zalo.me"))) {
                    try {
                        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
                        startActivity(intent);
                    } catch (Exception ignored) {}
                    return true;
                }
                return false;
            }
        });

        webView.loadUrl("file:///android_asset/index.html");
    }

    public class AndroidPrinterBridge {
        private final Context context;

        public AndroidPrinterBridge(Context context) {
            this.context = context;
        }

        /**
         * Kiểm tra kết nối TCP Socket trực tiếp tới máy in nhiệt WiFi (VD: 192.168.2.60:9100)
         */
        @JavascriptInterface
        public String testConnection(final String ip, final int port) {
            Callable<String> task = () -> {
                try (Socket socket = new Socket()) {
                    socket.connect(new InetSocketAddress(ip.trim(), port), 3000);
                    return "OK";
                } catch (Exception e) {
                    return "ERROR: " + e.getMessage();
                }
            };
            try {
                Future<String> future = printerExecutor.submit(task);
                return future.get(3500, TimeUnit.MILLISECONDS);
            } catch (Exception e) {
                return "ERROR: Timeout kết nối máy in " + ip + ":" + port;
            }
        }

        /**
         * Gửi trực tiếp mảng byte lệnh ESC/POS (Base64) qua Raw TCP Socket tới cổng 9100 của máy in nhiệt WiFi
         */
        @JavascriptInterface
        public String printRawEscPos(final String ip, final int port, final String base64Payload) {
            Callable<String> task = () -> {
                try (Socket socket = new Socket()) {
                    socket.connect(new InetSocketAddress(ip.trim(), port), 3500);
                    socket.setSoTimeout(4000);
                    byte[] rawBytes = Base64.decode(base64Payload, Base64.DEFAULT);
                    OutputStream out = socket.getOutputStream();
                    out.write(rawBytes);
                    out.flush();
                    Thread.sleep(150);
                    return "OK";
                } catch (Exception e) {
                    return "ERROR: " + e.getMessage();
                }
            };
            try {
                Future<String> future = printerExecutor.submit(task);
                return future.get(4500, TimeUnit.MILLISECONDS);
            } catch (Exception e) {
                return "ERROR: " + e.getMessage();
            }
        }

        /**
         * Lưu file (VD: file sao lưu .json) vào thư mục Download của điện thoại.
         * Trả về "OK" nếu thành công, hoặc "ERROR: ..." nếu lỗi.
         */
        @JavascriptInterface
        public String saveFile(final String fileName, final String mimeType, final String base64Data) {
            try {
                byte[] data = Base64.decode(base64Data, Base64.DEFAULT);
                String safeName = fileName.replaceAll("[\\\\/:*?\"<>|]", "_");
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    ContentValues values = new ContentValues();
                    values.put(MediaStore.Downloads.DISPLAY_NAME, safeName);
                    values.put(MediaStore.Downloads.MIME_TYPE, mimeType);
                    values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
                    Uri uri = context.getContentResolver()
                        .insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                    if (uri == null) return "ERROR: Không tạo được file";
                    try (OutputStream out = context.getContentResolver().openOutputStream(uri)) {
                        if (out == null) return "ERROR: Không mở được file";
                        out.write(data);
                        out.flush();
                    }
                } else {
                    File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                    if (!dir.exists()) dir.mkdirs();
                    try (FileOutputStream out = new FileOutputStream(new File(dir, safeName))) {
                        out.write(data);
                        out.flush();
                    }
                }
                return "OK";
            } catch (Exception e) {
                return "ERROR: " + e.getMessage();
            }
        }

        /**
         * Mở trình in hệ thống của Android nếu người dùng chọn chế độ SYSTEM_PRINT
         */
        @JavascriptInterface
        public void openAndroidSystemPrint() {
            runOnUiThread(() -> {
                PrintManager printManager = (PrintManager) getSystemService(Context.PRINT_SERVICE);
                if (printManager != null && webView != null) {
                    PrintDocumentAdapter adapter = webView.createPrintDocumentAdapter("PhieuThu_NhaTro_HoaNguyen");
                    printManager.print("PhieuThu_NhaTro_HoaNguyen", adapter, new PrintAttributes.Builder().build());
                }
            });
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
