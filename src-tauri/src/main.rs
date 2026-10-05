// Walter desktop: wraps the Walter page in a window, saves to Documents\Walter, and updates itself from GitHub Releases.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_updater::UpdaterExt;

const DATA_FILE: &str = "walter-data.json";
const KEEP_BACKUPS: usize = 30;

/// Documents\Walter (created on first use), with a backups folder inside it.
fn data_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let docs = app.path().document_dir().map_err(|e| e.to_string())?;
    let dir = docs.join("Walter");
    fs::create_dir_all(dir.join("backups")).map_err(|e| e.to_string())?;
    Ok(dir)
}

/// Keep only the newest KEEP_BACKUPS daily copies.
fn prune_backups(dir: &Path) {
    let mut files: Vec<PathBuf> = match fs::read_dir(dir) {
        Ok(rd) => rd
            .flatten()
            .map(|e| e.path())
            .filter(|p| {
                p.file_name()
                    .and_then(|n| n.to_str())
                    .map_or(false, |n| n.starts_with("walter-data-") && n.ends_with(".json"))
            })
            .collect(),
        Err(_) => return,
    };
    files.sort();
    while files.len() > KEEP_BACKUPS {
        let _ = fs::remove_file(files.remove(0));
    }
}

#[tauri::command]
fn save_data(app: AppHandle, contents: String) -> Result<(), String> {
    // Never write something that isn't valid JSON over good data.
    serde_json::from_str::<serde_json::Value>(&contents).map_err(|e| format!("bad data: {e}"))?;
    let dir = data_dir(&app)?;
    let path = dir.join(DATA_FILE);
    // First save of the day: keep yesterday's file as a dated backup.
    if path.exists() {
        let today = chrono::Local::now().format("%Y-%m-%d").to_string();
        let backups = dir.join("backups");
        let copy = backups.join(format!("walter-data-{today}.json"));
        if !copy.exists() {
            let _ = fs::copy(&path, &copy);
            prune_backups(&backups);
        }
    }
    // Write to a temp file, then swap it in, so a crash mid-save can't leave a half-written file.
    let tmp = dir.join(format!("{DATA_FILE}.tmp"));
    fs::write(&tmp, contents.as_bytes()).map_err(|e| e.to_string())?;
    fs::rename(&tmp, &path).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn open_data_folder(app: AppHandle) -> Result<(), String> {
    let dir = data_dir(&app)?;
    #[cfg(target_os = "windows")]
    let opener = "explorer";
    #[cfg(target_os = "macos")]
    let opener = "open";
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    let opener = "xdg-open";
    std::process::Command::new(opener)
        .arg(&dir)
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[derive(serde::Serialize)]
struct UpdateInfo {
    version: String,
    notes: Option<String>,
}

#[tauri::command]
async fn check_update(app: AppHandle) -> Result<Option<UpdateInfo>, String> {
    let update = app
        .updater()
        .map_err(|e| e.to_string())?
        .check()
        .await
        .map_err(|e| e.to_string())?;
    Ok(update.map(|u| UpdateInfo {
        version: u.version.clone(),
        notes: u.body.clone(),
    }))
}

#[tauri::command]
async fn install_update(app: AppHandle) -> Result<(), String> {
    let update = app
        .updater()
        .map_err(|e| e.to_string())?
        .check()
        .await
        .map_err(|e| e.to_string())?;
    if let Some(u) = update {
        u.download_and_install(|_, _| {}, || {})
            .await
            .map_err(|e| e.to_string())?;
        app.restart();
    }
    Ok(())
}

fn main() {
    tauri::Builder::default()
        // A second launch just brings the open window forward, so two copies never fight over the file.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.unminimize();
                let _ = w.set_focus();
            }
        }))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            save_data,
            open_data_folder,
            check_update,
            install_update
        ])
        .setup(|app| {
            let handle = app.handle().clone();
            let dir = data_dir(&handle).ok();
            let file = dir
                .as_ref()
                .and_then(|d| fs::read_to_string(d.join(DATA_FILE)).ok());
            // Hand the saved file to the page before any of its code runs.
            let desk = serde_json::json!({
                "file": file,
                "path": dir.as_ref().map(|d| d.join(DATA_FILE).display().to_string()),
                "version": app.package_info().version.to_string(),
            });
            let init = format!("window.__WALTER_DESK__ = {};", desk);
            WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("Walter")
                .inner_size(1100.0, 860.0)
                .min_inner_size(380.0, 560.0)
                .initialization_script(&init)
                .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Walter");
}
