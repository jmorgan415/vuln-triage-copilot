"""Guards the Jinja2/MarkupSafe removal: every module still imports without them."""
import importlib
import pkgutil
import sys
import unittest

import app

REMOVED_PACKAGES = ("jinja2", "markupsafe")


class AppImportsTest(unittest.TestCase):
    def test_every_app_module_imports_without_removed_packages(self):
        modules = [m.name for m in pkgutil.iter_modules(app.__path__, "app.")]
        self.assertIn("app.main", modules)
        for name in modules:
            with self.subTest(module=name):
                importlib.import_module(name)
        for pkg in REMOVED_PACKAGES:
            self.assertNotIn(pkg, sys.modules, f"{pkg} is still imported somewhere")

    def test_worker_handles_offline_job_kinds(self):
        import base64

        from app.main import handle_job

        cfg = base64.b64encode(b"notify:\n  channel: ops-alerts\n").decode()
        self.assertEqual(handle_job({"kind": "tenant_config", "config_b64": cfg}), {"ok": True})
        self.assertEqual(
            handle_job({"kind": "slow_query_lookup", "sql_snippet": "select 1"}),
            {"query": "SELECT 1"},
        )


if __name__ == "__main__":
    unittest.main()
