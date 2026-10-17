#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{mpsc, Mutex};
use std::time::{Duration, Instant};
use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons};
use tauri_plugin_opener::OpenerExt;

#[derive(Clone, Serialize)]
struct LaunchStatus {
    phase: String,
    message: String,
}

struct Backend {
    child: Option<Child>,
    attempt: u64,
    port: Option<u16>,
    stopping: bool,
    status: LaunchStatus,
}

struct DesktopState {
    backend: Mutex<Backend>,
    data_dir: PathBuf,
    log_dir: PathBuf,
}

fn stop_child(backend: &mut Backend) {
    if let Some(mut child) = backend.child.take() {
        let _ = child.kill();
        let _ = child.wait();
    }
    backend.port = None;
}

#[tauri::command]
fn desktop_status(state: tauri::State<DesktopState>) -> LaunchStatus {
    state.backend.lock().unwrap().status.clone()
}

#[tauri::command]
fn desktop_retry(app: tauri::AppHandle) {
    start_backend(&app);
}

#[tauri::command]
fn desktop_open_logs(
    app: tauri::AppHandle,
    state: tauri::State<DesktopState>,
) -> Result<(), String> {
    app.opener()
        .open_path(state.log_dir.to_string_lossy(), None::<&str>)
        .map_err(|error| error.to_string())
}

fn backend_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    #[cfg(debug_assertions)]
    {
        let _ = app;
        Ok(
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("../build/desktop/backend/mflux-backend"),
        )
    }
    #[cfg(not(debug_assertions))]
    {
        app.path()
            .resource_dir()
            .map(|path| path.join("backend/mflux-backend"))
            .map_err(|error| error.to_string())
    }
}

fn fail(app: &tauri::AppHandle, attempt: u64, message: String) {
    let state = app.state::<DesktopState>();
    let mut backend = state.backend.lock().unwrap();
    if backend.attempt != attempt || backend.stopping {
        return;
    }
    let was_ready = backend.port.is_some();
    stop_child(&mut backend);
    backend.status = LaunchStatus {
        phase: "failed".into(),
        message: message.clone(),
    };
    drop(backend);
    if was_ready {
        let mut dialog = app
            .dialog()
            .message(message)
            .title("本地服务已停止")
            .buttons(MessageDialogButtons::OkCancelCustom(
                "重新启动".into(),
                "退出".into(),
            ));
        if let Some(window) = app.get_webview_window("main") {
            dialog = dialog.parent(&window);
        }
        let restart = dialog.blocking_show();
        if restart {
            app.restart();
        } else {
            app.exit(0);
        }
    }
}

fn start_backend(app: &tauri::AppHandle) {
    let state = app.state::<DesktopState>();
    let mut backend = state.backend.lock().unwrap();
    stop_child(&mut backend);
    backend.attempt += 1;
    let attempt = backend.attempt;
    backend.status = LaunchStatus {
        phase: "starting".into(),
        message: "正在准备本地图像生成环境，请稍候。".into(),
    };
    drop(backend);
    let app = app.clone();
    std::thread::spawn(move || {
        if let Err(error) = launch_and_monitor(&app, attempt) {
            fail(
                &app,
                attempt,
                format!("本地服务启动失败：{error}。可以重试或打开日志目录。"),
            );
        }
    });
}

fn launch_and_monitor(app: &tauri::AppHandle, attempt: u64) -> Result<(), String> {
    let state = app.state::<DesktopState>();
    let token = format!(
        "{}{}",
        uuid::Uuid::new_v4().simple(),
        uuid::Uuid::new_v4().simple()
    );
    let log_path = state.log_dir.join("backend.log");
    let stderr = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .map_err(|error| error.to_string())?;
    let mut child = Command::new(backend_path(app)?)
        .current_dir(&state.data_dir)
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(stderr)
        .spawn()
        .map_err(|error| error.to_string())?;
    let stdout = child.stdout.take().unwrap();
    let config = serde_json::json!({"token": token, "dataDir": state.data_dir});
    if let Err(error) = writeln!(child.stdin.as_mut().unwrap(), "{config}") {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error.to_string());
    }
    {
        let mut backend = state.backend.lock().unwrap();
        if backend.attempt != attempt || backend.stopping {
            let _ = child.kill();
            let _ = child.wait();
            return Ok(());
        }
        backend.child = Some(child);
    }

    let (sender, receiver) = mpsc::channel();
    std::thread::spawn(move || {
        let mut log = OpenOptions::new().append(true).open(log_path).ok();
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(&line) {
                if value["event"] == "ready" {
                    let _ = sender.send(value["port"].as_u64());
                    continue;
                }
            }
            if let Some(log) = log.as_mut() {
                let _ = writeln!(log, "{line}");
            }
        }
    });

    let deadline = Instant::now() + Duration::from_secs(90);
    let port = loop {
        match receiver.recv_timeout(Duration::from_millis(200)) {
            Ok(Some(port)) if port > 0 && port <= u16::MAX as u64 => break port as u16,
            Ok(_) => return Err("后端返回了无效端口".into()),
            Err(mpsc::RecvTimeoutError::Disconnected) => return Err("后端在启动期间退出".into()),
            Err(mpsc::RecvTimeoutError::Timeout) => {}
        }
        let backend = state.backend.lock().unwrap();
        if backend.attempt != attempt || backend.stopping {
            return Ok(());
        }
        if Instant::now() > deadline {
            return Err("启动等待超过 90 秒".into());
        }
    };
    {
        let mut backend = state.backend.lock().unwrap();
        if backend.attempt != attempt || backend.stopping {
            return Ok(());
        }
        backend.port = Some(port);
        backend.status = LaunchStatus {
            phase: "ready".into(),
            message: "本地服务已就绪。".into(),
        };
    }
    let url = format!("http://127.0.0.1:{port}/desktop/bootstrap?token={token}");
    app.get_webview_window("main")
        .ok_or("主窗口已关闭")?
        .navigate(
            url.parse::<tauri::Url>()
                .map_err(|error| error.to_string())?,
        )
        .map_err(|error| error.to_string())?;

    loop {
        std::thread::sleep(Duration::from_secs(1));
        let mut backend = state.backend.lock().unwrap();
        if backend.attempt != attempt || backend.stopping {
            return Ok(());
        }
        if let Some(child) = backend.child.as_mut() {
            if let Some(status) = child.try_wait().map_err(|error| error.to_string())? {
                return Err(format!("本地服务意外退出（{status}）"));
            }
        }
    }
}

fn is_backend_url(app: &tauri::AppHandle, url: &tauri::Url) -> bool {
    url.scheme() == "http"
        && url.host_str() == Some("127.0.0.1")
        && url.port() == app.state::<DesktopState>().backend.lock().unwrap().port
}

fn open_external(app: &tauri::AppHandle, url: &tauri::Url) {
    if matches!(url.scheme(), "https" | "http") {
        let _ = app.opener().open_url(url.as_str(), None::<&str>);
    }
}

fn open_image(app: &tauri::AppHandle, url: &tauri::Url) -> bool {
    if !is_backend_url(app, url) {
        return false;
    }
    let Some(filename) = url.path().strip_prefix("/static/images/") else {
        return false;
    };
    if filename.contains(['/', '\\']) || !filename.ends_with(".png") {
        return false;
    }
    let image = app
        .state::<DesktopState>()
        .data_dir
        .join("images")
        .join(filename);
    if image.is_file() {
        let _ = app
            .opener()
            .open_path(image.to_string_lossy(), None::<&str>);
    }
    true
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            desktop_status,
            desktop_retry,
            desktop_open_logs
        ])
        .setup(|app| {
            let data_dir = app.path().app_data_dir()?;
            let log_dir = data_dir.join("logs");
            fs::create_dir_all(&log_dir)?;
            app.manage(DesktopState {
                backend: Mutex::new(Backend {
                    child: None,
                    attempt: 0,
                    port: None,
                    stopping: false,
                    status: LaunchStatus {
                        phase: "starting".into(),
                        message: "正在启动。".into(),
                    },
                }),
                data_dir,
                log_dir,
            });
            let navigation_app = app.handle().clone();
            let new_window_app = app.handle().clone();
            let window =
                WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                    .title("mflux WebUI")
                    .inner_size(1200.0, 820.0)
                    .min_inner_size(760.0, 600.0)
                    .initialization_script("document.addEventListener('click', event => { const link = event.target.closest?.('a[target=\"_blank\"]'); if (link) { event.preventDefault(); location.assign(link.href); } }, true);")
                    .on_navigation(move |url| {
                        if open_image(&navigation_app, url) {
                            return false;
                        }
                        if url.scheme() == "tauri"
                            || url.host_str() == Some("tauri.localhost")
                            || is_backend_url(&navigation_app, url)
                        {
                            return true;
                        }
                        open_external(&navigation_app, url);
                        false
                    })
                    .on_new_window(move |url, _features| {
                        if !open_image(&new_window_app, &url) {
                            open_external(&new_window_app, &url);
                        }
                        tauri::webview::NewWindowResponse::Deny
                    })
                    .build()?;
            let close_app = app.handle().clone();
            window.on_window_event(move |event| {
                if matches!(event, tauri::WindowEvent::CloseRequested { .. }) {
                    close_app.exit(0);
                }
            });
            start_backend(app.handle());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("无法创建 mflux WebUI 桌面应用");
    app.run(|app, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            let state = app.state::<DesktopState>();
            let mut backend = state.backend.lock().unwrap();
            backend.stopping = true;
            stop_child(&mut backend);
        }
    });
}
