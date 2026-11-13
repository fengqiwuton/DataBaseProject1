import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ImporterTest(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('importer', ROOT / 'tools/generate_import.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_identity_and_atomic_data(self):
        m = self.module.load_model(ROOT / 'source-data/Archive.zip', ROOT / 'config/data-rules.json')
        self.assertEqual([len(m[k]) for k in ['district', 'station', 'metro_line', 'line_station', 'station_exit', 'exit_landmark']], [10, 439, 29, 567, 1304, 3271])
        liyuan = [s for s in m['station'] if s[2] == '梨园']
        self.assertEqual(len(liyuan), 2)
        self.assertNotEqual(liyuan[0][1], liyuan[1][1])
        self.assertEqual(sum(not r['landmark'] for r in m['sources']['exits']), 3)
        self.assertEqual(len(m['source_mapping']['station_rows']), 567)
        self.assertEqual(len(m['source_mapping']['exit_rows']), 1276)

    def test_exit_parsing_is_conservative(self):
        self.assertEqual(self.module.parse_exits('2-6号'), ['2号','3号','4号','5号','6号'])
        self.assertEqual(self.module.parse_exits('3a、3b、5'), ['3a','3b','5'])
        self.assertEqual(self.module.parse_exits('E1/E2'), ['E1','E2'])
        self.assertEqual(self.module.parse_exits('A-B'), ['A-B'])

    def test_reproducible_standalone_sql(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            self.module.build(target, ROOT / 'source-data/Archive.zip', ROOT / 'config/data-rules.json')
            first = (target / 'sql/import.sql').read_bytes()
            self.module.build(target, ROOT / 'source-data/Archive.zip', ROOT / 'config/data-rules.json')
            self.assertEqual(first, (target / 'sql/import.sql').read_bytes())
            text = first.decode('utf-8')
            self.assertIn('BEGIN;', text)
            self.assertIn('COMMIT;', text)
            self.assertIn("Xin''an", text)
            self.assertIn('INSERT INTO project1.station', text)
            self.assertNotIn('\\copy', text)
        self.assertEqual(text.count('\nINSERT INTO project1.'), 6)
        self.assertIn('DO $project1_import$', text)
        self.assertIn('ANALYZE project1.district, project1.station', text)


if __name__ == '__main__':
    unittest.main()
