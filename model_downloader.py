"""Hugging Face 模型下载任务。下载进入 Hugging Face 默认缓存目录。"""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

from huggingface_hub import HfApi, hf_hub_download

from model_cache import is_mflux_image_model
from model_registry import get_model_spec


class ModelDownloadManager:
    def __init__(self):
        self._tasks = {}
        self._cancel_events = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="model-download")

    def _set(self, repo_id, **updates):
        with self._lock:
            self._tasks[repo_id] = {**self._tasks.get(repo_id, {}), **updates}

    def list_tasks(self):
        with self._lock:
            return list(self._tasks.values())

    def start(self, repo_id):
        if not get_model_spec(repo_id) or not is_mflux_image_model(repo_id):
            raise ValueError("仅支持 mflux 兼容的 Krea 2、Z-Image 与 FLUX.2 Klein 模型")
        with self._lock:
            active = self._tasks.get(repo_id)
            if active and active["status"] in {"queued", "downloading"}:
                return active
            cancel_event = Event()
            task = {"repoId": repo_id, "status": "queued", "currentFile": None,
                    "filesDone": 0, "filesTotal": 0, "bytesDone": 0, "bytesTotal": 0, "error": None}
            self._tasks[repo_id] = task
            self._cancel_events[repo_id] = cancel_event
        self._executor.submit(self._download, repo_id, cancel_event)
        return task

    def cancel(self, repo_id):
        with self._lock:
            task = self._tasks.get(repo_id)
            event = self._cancel_events.get(repo_id)
            if not task or not event or task["status"] not in {"queued", "downloading"}:
                raise ValueError("没有可取消的下载任务")
            event.set()
        self._set(repo_id, status="cancelling")

    def _download(self, repo_id, cancel_event):
        try:
            info = HfApi().model_info(repo_id, files_metadata=True, timeout=20)
            files = [file for file in (info.siblings or []) if file.rfilename]
            total = sum(file.size or 0 for file in files)
            self._set(repo_id, status="downloading", filesTotal=len(files), bytesTotal=total)
            bytes_done = 0
            for index, file in enumerate(files, start=1):
                if cancel_event.is_set():
                    self._set(repo_id, status="cancelled", currentFile=None)
                    return
                self._set(repo_id, currentFile=file.rfilename)
                hf_hub_download(repo_id=repo_id, filename=file.rfilename)
                bytes_done += file.size or 0
                self._set(repo_id, filesDone=index, bytesDone=bytes_done)
            self._set(repo_id, status="completed", currentFile=None)
        except Exception as exc:
            self._set(repo_id, status="failed", currentFile=None, error=str(exc))


download_manager = ModelDownloadManager()
