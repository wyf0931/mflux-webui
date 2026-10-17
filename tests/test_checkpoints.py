import json
import tempfile
import unittest
from pathlib import Path

from mflux_webui.checkpoints import resolve_krea_checkpoint


class CheckpointTest(unittest.TestCase):
    def test_complete_old_snapshot_is_used_instead_of_partial_main(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "models--owner--krea"
            old = root / "snapshots/old"
            new = root / "snapshots/new"
            for path in (old, new):
                for component in ("vae", "text_encoder"):
                    (path / component).mkdir(parents=True)
                    (path / component / "0.safetensors").touch()
                (path / "tokenizer").mkdir()
                (path / "tokenizer/tokenizer.json").write_text("{}")
                (path / "tokenizer/tokenizer_config.json").write_text("{}")
            (old / "0.safetensors").touch()
            index = old / "model.safetensors.index.json"
            index.write_text(json.dumps({"weight_map": {"weight": "0.safetensors"}}))
            (root / "refs").mkdir()
            (root / "refs/main").write_text("new")
            self.assertEqual(resolve_krea_checkpoint("owner/krea", temporary), str(old))
            index.write_text(json.dumps({"weight_map": {"weight": "missing.safetensors"}}))
            self.assertEqual(resolve_krea_checkpoint("owner/krea", temporary), "owner/krea")
