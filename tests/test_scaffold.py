from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class ScaffoldTest(unittest.TestCase):
    def test_package_scaffold_exists(self) -> None:
        self.assertTrue((ROOT / "openclaw_video_summary" / "__init__.py").exists())
        self.assertTrue((ROOT / "openclaw_video_summary" / "interfaces" / "__init__.py").exists())
        self.assertTrue((ROOT / "pyproject.toml").exists())
        self.assertTrue((ROOT / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
