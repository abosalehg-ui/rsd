// منع نافذة console الإضافية على ويندوز في وضع release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    rsd_lib::run()
}
