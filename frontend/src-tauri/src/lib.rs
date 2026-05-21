// رصد — Tauri 2.x entry point
//
// نقطة الدخول للبنية المكتبية. الأوامر المخصّصة (`#[tauri::command]`) تُسجَّل هنا
// عند الحاجة لتوسيع التطبيق بقدرات native (تخزين محلي مشفّر، نظام الملفات…).

#[tauri::command]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![version])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
