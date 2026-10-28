package vn.hoanguyen.quanlynhatro;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.provider.MediaStore;
import android.util.Base64;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public class MainActivity extends AppCompatActivity {

    private static final int REQ_OPEN_BACKUP_JSON = 1001;
    private static final int REQ_SAVE_BACKUP_JSON = 1002;
    private static final int REQ_WEBVIEW_FILE_CHOOSER = 1003;

    private WebView webView;
    private ValueCallback<Uri[]> filePathCallback;
    private String pendingExportJsonContent = null;
    private final ExecutorService printerExecutor = Executors.newCachedThreadPool();

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 1. Đồng bộ màu Thanh công cụ trạng thái phía trên (Status Bar) trùng khớp màu Xanh Cổ Vịt (#0F766E) của App
        Window window = getWindow();
        if (window != null) {
            window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS);
            window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            window.setStatusBarColor(Color.parseColor("#0F766E"));
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                View decor = window.getDecorView();
                // Giữ icon đồng hồ, pin, WiFi màu trắng nổi bật trên nền xanh #0F766E
                decor.setSystemUiVisibility(decor.getSystemUiVisibility() & ~View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
            }
        }

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#0F766E"));
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

        // Đăng ký cầu nối JavaScript -> Native Android (In WiFi 9100 nguyên mẫu Xem QR + Xuất/Nhập file sao lưu .json)
        webView.addJavascriptInterface(new AndroidPrinterBridge(this), "AndroidPrinterBridge");

        // Hỗ trợ chọn file <input type="file"> trực tiếp trong WebView Android
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(
                    WebView webView,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams
            ) {
                if (MainActivity.this.filePathCallback != null) {
                    MainActivity.this.filePathCallback.onReceiveValue(null);
                }
                MainActivity.this.filePathCallback = filePathCallback;

                try {
                    Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("*/*");
                    startActivityForResult(
                            Intent.createChooser(intent, "Chọn File Sao Lưu (.json)"),
                            REQ_WEBVIEW_FILE_CHOOSER
                    );
                } catch (Exception e) {
                    MainActivity.this.filePathCallback = null;
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
         * Gửi trực tiếp mảng byte lệnh ESC/POS & Bitmap Xem QR (Base64) qua Raw TCP Socket tới cổng 9100 của máy in nhiệt WiFi
         */
        @JavascriptInterface
        public String printRawEscPos(final String ip, final int port, final String base64Payload) {
            Callable<String> task = () -> {
                try (Socket socket = new Socket()) {
                    socket.connect(new InetSocketAddress(ip.trim(), port), 4500);
                    socket.setSoTimeout(15000);
                    byte[] rawBytes = Base64.decode(base64Payload, Base64.DEFAULT);
                    OutputStream out = socket.getOutputStream();

                    // Gửi theo từng gói 4KB giúp máy in nhiệt nhận mượt toàn bộ ảnh phiếu Xem QR + mã VietQR
                    int offset = 0;
                    int chunkSize = 4096;
                    while (offset < rawBytes.length) {
                        int len = Math.min(chunkSize, rawBytes.length - offset);
                        out.write(rawBytes, offset, len);
                        out.flush();
                        offset += len;
                        if (offset < rawBytes.length) {
                            Thread.sleep(8);
                        }
                    }
                    Thread.sleep(200);
                    return "OK";
                } catch (Exception e) {
                    return "ERROR: " + e.getMessage();
                }
            };
            try {
                Future<String> future = printerExecutor.submit(task);
                return future.get(16000, TimeUnit.MILLISECONDS);
            } catch (Exception e) {
                return "ERROR: " + e.getMessage();
            }
        }

        /**
         * Tải ảnh mã VietQR về dạng Data URL Base64 ngay trong tầng Native để vẽ vào phiếu in Xem QR không bị chặn CORS
         */
        @JavascriptInterface
        public String fetchImageBase64(final String imageUrl) {
            Callable<String> task = () -> {
                HttpURLConnection conn = null;
                try {
                    URL url = new URL(imageUrl);
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setConnectTimeout(3500);
                    conn.setReadTimeout(4500);
                    conn.setDoInput(true);
                    conn.connect();
                    try (InputStream is = conn.getInputStream();
                         ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
                        byte[] buf = new byte[4096];
                        int n;
                        while ((n = is.read(buf)) != -1) {
                            baos.write(buf, 0, n);
                        }
                        String b64 = Base64.encodeToString(baos.toByteArray(), Base64.NO_WRAP);
                        return "data:image/png;base64," + b64;
                    }
                } catch (Exception e) {
                    return "";
                } finally {
                    if (conn != null) conn.disconnect();
                }
            };
            try {
                Future<String> future = printerExecutor.submit(task);
                return future.get(5000, TimeUnit.MILLISECONDS);
            } catch (Exception e) {
                return "";
            }
        }

        /**
         * Xuất file sao lưu (.json): Lưu trực tiếp vào thư mục Download (Tải xuống) của điện thoại
         * đồng thời mở hộp thoại Lưu file hệ thống Android để người dùng tuỳ chọn nơi lưu.
         */
        @JavascriptInterface
        public String saveBackupJson(final String fileName, final String jsonContent) {
            try {
                final String cleanName = (fileName != null && !fileName.trim().isEmpty())
                        ? fileName.trim()
                        : "SaoLuu_NhaTro.json";
                pendingExportJsonContent = jsonContent;
                byte[] bytes = jsonContent.getBytes(StandardCharsets.UTF_8);

                boolean savedToDownloads = false;
                try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        ContentValues values = new ContentValues();
                        values.put(MediaStore.Downloads.DISPLAY_NAME, cleanName);
                        values.put(MediaStore.Downloads.MIME_TYPE, "application/json");
                        values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
                        ContentResolver resolver = context.getContentResolver();
                        Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                        if (uri != null) {
                            try (OutputStream os = resolver.openOutputStream(uri)) {
                                if (os != null) {
                                    os.write(bytes);
                                    os.flush();
                                    savedToDownloads = true;
                                }
                            }
                        }
                    } else {
                        File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                        if (!dir.exists()) dir.mkdirs();
                        File outFile = new File(dir, cleanName);
                        try (FileOutputStream fos = new FileOutputStream(outFile)) {
                            fos.write(bytes);
                            fos.flush();
                            savedToDownloads = true;
                        }
                    }
                } catch (Exception ignored) {}

                final boolean finalSaved = savedToDownloads;
                runOnUiThread(() -> {
                    if (finalSaved) {
                        Toast.makeText(
                                context,
                                "Đã lưu file vào thư mục Tải xuống (Download): " + cleanName,
                                Toast.LENGTH_LONG
                        ).show();
                    } else {
                        try {
                            Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                            intent.addCategory(Intent.CATEGORY_OPENABLE);
                            intent.setType("application/json");
                            intent.putExtra(Intent.EXTRA_TITLE, cleanName);
                            startActivityForResult(intent, REQ_SAVE_BACKUP_JSON);
                        } catch (Exception e) {
                            Toast.makeText(context, "Lỗi mở trình lưu file: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                        }
                    }
                });

                return "OK";
            } catch (Exception e) {
                return "ERROR: " + e.getMessage();
            }
        }

        /**
         * Mở trình chọn file sao lưu (.json) gốc của Android để khôi phục dữ liệu
         */
        @JavascriptInterface
        public void openBackupFilePicker() {
            runOnUiThread(() -> {
                try {
                    Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("*/*");
                    startActivityForResult(
                            Intent.createChooser(intent, "Chọn File Sao Lưu (.json)"),
                            REQ_OPEN_BACKUP_JSON
                    );
                } catch (Exception e) {
                    Toast.makeText(context, "Không thể mở trình chọn file: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                }
            });
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
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        // 1. Kết quả từ <input type="file"> mặc định của WebView
        if (requestCode == REQ_WEBVIEW_FILE_CHOOSER) {
            if (filePathCallback != null) {
                Uri[] results = null;
                if (resultCode == Activity.RESULT_OK && data != null && data.getData() != null) {
                    results = new Uri[]{data.getData()};
                }
                filePathCallback.onReceiveValue(results);
                filePathCallback = null;
            }
            return;
        }

        // 2. Kết quả khi chọn file sao lưu (.json) qua openBackupFilePicker()
        if (requestCode == REQ_OPEN_BACKUP_JSON && resultCode == Activity.RESULT_OK && data != null && data.getData() != null) {
            Uri uri = data.getData();
            try (InputStream is = getContentResolver().openInputStream(uri);
                 ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
                if (is != null) {
                    byte[] buffer = new byte[4096];
                    int len;
                    while ((len = is.read(buffer)) != -1) {
                        baos.write(buffer, 0, len);
                    }
                    String base64 = Base64.encodeToString(baos.toByteArray(), Base64.NO_WRAP);
                    if (webView != null) {
                        webView.post(() -> webView.evaluateJavascript(
                                "window.onAndroidBackupFileLoaded('" + base64 + "', true);",
                                null
                        ));
                    }
                }
            } catch (Exception e) {
                Toast.makeText(this, "Không thể đọc file sao lưu: " + e.getMessage(), Toast.LENGTH_LONG).show();
            }
            return;
        }

        // 3. Kết quả khi người dùng chọn nơi lưu file sao lưu (.json) qua hộp thoại hệ thống
        if (requestCode == REQ_SAVE_BACKUP_JSON && resultCode == Activity.RESULT_OK && data != null && data.getData() != null) {
            Uri uri = data.getData();
            if (pendingExportJsonContent != null) {
                try (OutputStream os = getContentResolver().openOutputStream(uri)) {
                    if (os != null) {
                        os.write(pendingExportJsonContent.getBytes(StandardCharsets.UTF_8));
                        os.flush();
                        Toast.makeText(this, "Đã lưu file sao lưu thành công!", Toast.LENGTH_LONG).show();
                    }
                } catch (Exception e) {
                    Toast.makeText(this, "Lỗi ghi file: " + e.getMessage(), Toast.LENGTH_LONG).show();
                }
            }
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
