import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# 親ディレクトリにある weather.py をインポートできるようにパスを追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from weather import get_area_code

class TestWeatherApp(unittest.TestCase):
    def setUp(self):
        # テスト用のダミーエリア定義データ（気象庁データの抜粋・模倣）
        self.dummy_area_data = {
            "offices": {
                "140000": {"name": "神奈川県", "enName": "Kanagawa"},
                "020000": {"name": "青森県", "enName": "Aomori"}
            },
            "class10s": {
                "140010": {"name": "東部", "parent": "140000"},
                "020010": {"name": "下北", "parent": "020000"}
            },
            "class15s": {
                "140020": {"name": "横浜・川崎", "parent": "140010"}
            },
            "class20s": {
                "1410000": {"name": "横浜市", "parent": "140020"},
                "0240800": {"name": "横浜町", "parent": "020010"}
            }
        }

    # urllib.request.urlopen をモック化（実際の通信をブロック）
    @patch('weather.urllib.request.urlopen')
    def test_get_area_code_kanagawa_yokohama(self, mock_urlopen):
        # モックの振る舞いを設定（ダミーのJSONを返すようにする）
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.dummy_area_data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # 実行と検証：神奈川県横浜市 -> 140000になるべき
        result = get_area_code("神奈川県横浜市")
        self.assertEqual(result, "140000")

    @patch('weather.urllib.request.urlopen')
    def test_get_area_code_aomori_yokohamamachi(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.dummy_area_data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # 実行と検証：青森県横浜町 -> 020000になるべき
        result = get_area_code("青森県横浜町")
        self.assertEqual(result, "020000")

    @patch('weather.urllib.request.urlopen')
    def test_get_area_code_invalid_combination(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.dummy_area_data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # 実行と検証：存在しない「青森県横浜市」 -> Noneが返るべき
        result = get_area_code("青森県横浜市")
        self.assertIsNone(result)

    @patch('weather.urllib.request.urlopen')
    def test_get_area_code_only_city_name(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.dummy_area_data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # 実行と検証：都道府県なしの「横浜市」 -> 神奈川県(140000)として解決されるべき
        result = get_area_code("横浜市")
        self.assertEqual(result, "140000")

if __name__ == '__main__':
    unittest.main()
