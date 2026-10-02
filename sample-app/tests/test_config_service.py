import unittest

import yaml

from app.config_service import load_tenant_config

MERGE_DOC = b"""\
defaults: &defaults
  timeout_s: 5
integrations:
  ledger:
    !!merge <<: *defaults
    endpoint: https://ledger.internal.northgate.io/v1
"""

RCE_DOC = b"!!python/object/apply:os.system ['echo pwned']\n"


class LoadTenantConfigTest(unittest.TestCase):
    def test_console_merge_tags_still_resolve(self):
        cfg = load_tenant_config(MERGE_DOC)
        self.assertEqual(cfg["integrations"]["ledger"]["timeout_s"], 5)

    def test_python_constructor_tags_are_rejected(self):
        with self.assertRaises(yaml.constructor.ConstructorError):
            load_tenant_config(RCE_DOC)

    def test_size_cap_enforced(self):
        with self.assertRaises(ValueError):
            load_tenant_config(b"a: 1\n" * 60000)


if __name__ == "__main__":
    unittest.main()
