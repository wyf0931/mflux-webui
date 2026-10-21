"""模型下载任务，使用各模型仓库 SDK 的默认缓存目录。"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.constants import HF_HUB_CACHE

from .disk_space import check_download_space
from .model_cache import is_mflux_image_model
from .model_registry import configured_sources, get_model_spec


def cache_root(source):
    """返回渠道实际使用的缓存根目录，用于下载前的空间检查。"""
    if source == "modelscope":
        import os

        return Path(os.getenv("MODELSCOPE_CACHE", Path.home() / ".cache" / "modelscope" / "hub" / "models"))
    return Path(HF_HUB_CACHE)


class ModelDownloadManager:
    def __init__(self):
        self._tasks = {}
        self._cancel_events = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="model-download")

    @staticmethod
    def _task_key(source, repo_id):
        return f"{source}:{repo_id}"

    def _set(self, task_key, **updates):
        with self._lock:
            self._tasks[task_key] = {**self._tasks.get(task_key, {}), **updates}

    def list_tasks(self):
        with self._lock:
            return list(self._tasks.values())

    def start(self, repo_id, source="huggingface"):
        if source not in configured_sources():
            raise ValueError(f"当前未启用 {source} 模型渠道")
        spec = get_model_spec(repo_id, source)
        if not spec or not is_mflux_image_model(repo_id):
            raise ValueError("仅支持目录中声明的 mflux 图像模型")
        check_download_space(cache_root(source), int(spec.size_gb * 1024**3))
        task_key = self._task_key(source, repo_id)
        with self._lock:
            active = self._tasks.get(task_key)
            if active and active["status"] in {"queued", "downloading"}:
                return active
            cancel_event = Event()
            task = {"taskId": task_key, "repoId": repo_id, "source": source, "status": "queued",
                    "currentFile": None, "filesDone": 0, "filesTotal": 0, "bytesDone": 0,
                    "bytesTotal": 0, "error": None}
            self._tasks[task_key] = task
            self._cancel_events[task_key] = cancel_event
        self._executor.submit(self._download, task_key, repo_id, source, cancel_event)
        return task

    def cancel(self, repo_id, source="huggingface"):
        task_key = self._task_key(source, repo_id)
        with self._lock:
            task = self._tasks.get(task_key)
            event = self._cancel_events.get(task_key)
            if not task or not event or task["status"] not in {"queued", "downloading"}:
                raise ValueError("没有可取消的下载任务")
            event.set()
        self._set(task_key, status="cancelling")

    def _download(self, task_key, repo_id, source, cancel_event):
        try:
            if source == "modelscope":
                self._set(task_key, status="downloading", currentFile="ModelScope snapshot")
                from modelscope.hub.snapshot_download import snapshot_download
                if cancel_event.is_set():
                    self._set(task_key, status="cancelled", currentFile=None)
                    return
                snapshot_download(repo_id)
            else:
                info = HfApi().model_info(repo_id, files_metadata=True, timeout=20)
                files = [file for file in (info.siblings or []) if file.rfilename]
                total = sum(file.size or 0 for file in files)
                self._set(task_key, status="downloading", filesTotal=len(files), bytesTotal=total)
                bytes_done = 0
                for index, file in enumerate(files, start=1):
                    if cancel_event.is_set():
                        self._set(task_key, status="cancelled", currentFile=None)
                        return
                    self._set(task_key, currentFile=file.rfilename)
                    hf_hub_download(repo_id=repo_id, filename=file.rfilename)
                    bytes_done += file.size or 0
                    self._set(task_key, filesDone=index, bytesDone=bytes_done)
            self._set(task_key, status="completed", currentFile=None)
        except Exception as exc:
            self._set(task_key, status="failed", currentFile=None, error=str(exc))


download_manager = ModelDownloadManager()
