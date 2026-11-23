"""Asset discovery results must never authorize downloads just by naming a source."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from verseforge_core.asset_catalog import discover_sources

CATALOG=Path(__file__).resolve().parents[1]/"assets"/"sources.json"

class AssetSourcesTests(unittest.TestCase):
    def test_catalog_discovery(self):
        result=discover_sources(CATALOG)
        self.assertGreaterEqual(result['count'],12)
        self.assertTrue(all(not entry['import_authorized'] for entry in result['matches']))
        self.assertTrue(all(not entry['redistribution_authorized'] for entry in result['matches']))
    def test_icon_search(self):
        results=discover_sources(CATALOG,query='lucide',category='icon')
        self.assertEqual([x['name'] for x in results['matches']],['Lucide'])
    def test_reviewed_filter(self):
        results=discover_sources(CATALOG,reviewed_only=True)
        self.assertTrue(results['matches'])
        self.assertTrue(all(x['catalog_status']=='catalog-license-verified-per-asset-check-still-required' for x in results['matches']))
    def test_no_bad_queries(self):
        with self.assertRaises(ValueError):discover_sources(CATALOG,query='\n')
        with self.assertRaises(ValueError):discover_sources(CATALOG,category='weapon')
    def test_duplicate_catalog_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            arr=json.loads(CATALOG.read_text());arr.append(arr[0]);p=Path(t)/'bad.json';p.write_text(json.dumps(arr))
            with self.assertRaises(ValueError):discover_sources(p)
    def test_http_url_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            arr=json.loads(CATALOG.read_text());arr[0]['url']='http://example.com';p=Path(t)/'bad.json';p.write_text(json.dumps(arr))
            with self.assertRaises(ValueError):discover_sources(p)
