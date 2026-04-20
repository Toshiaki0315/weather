import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os
import io

# 親ディレクトリにある weather.py をインポートできるようにパスを追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from weather import get_area_info, get_weather_forecast

class TestWeatherApp(unittest.TestCase):
    def setUp(self):
        # 1. エリア定義のダミーデータ（東部と西部を両方定義する）
        self.dummy_area_data = {
            "offices": {
                "140000": {"name": "神奈川県"}
            },
            "class10s": {
                "140010": {"name": "東部", "parent": "140000"},
                "140020": {"name": "西部", "parent": "140000"}
            },
            "class15s": {
                "140020_c15": {"name": "横浜・川崎", "parent": "140010"},
                "140030_c15": {"name": "湘南", "parent": "140020"}
            },
            "class20s": {
                "1410000": {"name": "横浜市", "parent": "140020_c15"},
                "1420600": {"name": "小田原市", "parent": "140030_c15"},
                "140040": {"name": "横浜", "parent": "140010"},  # 気温地点
                "140050": {"name": "小田原", "parent": "140020"} # 気温地点
            }
        }

        # 2. 天気予報のダミーデータ（配列のインデックスで東部と西部を並べる）
        self.dummy_forecast_data = [
            {
                "timeSeries": [
                    { # 0: 天気
                        "areas": [
                            {"area": {"name": "東部", "code": "140010"}, "weathers": ["晴れ", "くもり"]},
                            {"area": {"name": "西部", "code": "140020"}, "weathers": ["雨", "雪"]}
                        ]
                    },
                    { # 1: 降水
                        "areas": [
                            {"area": {"name": "東部", "code": "140010"}, "pops": ["0"]},
                            {"area": {"name": "西部", "code": "140020"}, "pops": ["50"]}
                        ]
                    },
                    { # 2: 気温
                        "areas": [
                            {"area": {"name": "横浜", "code": "140040"}, "temps": ["18", "25"]},
                            {"area": {"name": "小田原", "code": "140050"}, "temps": ["15", "20"]}
                        ]
                    }
                ]
            }
        ]

    def mocked_urlopen(self, req):
        mock_response = MagicMock()
        url = req.full_url if hasattr(req, 'full_url') else req
        
        if "area.json" in url:
            data = self.dummy_area_data
        elif "140000.json" in url:
            data = self.dummy_forecast_data
        else:
            data = []
            
        mock_response.read.return_value = json.dumps(data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        return mock_response

    @patch('weather.urllib.request.urlopen')
    def test_get_area_info_returns_tuple(self, mock_urlopen):
        """戻り値が(県コード, 予報区コード, データ)の3点セットであることの検証"""
        mock_urlopen.side_effect = self.mocked_urlopen
        off_code, c10_code, data = get_area_info("横浜市")
        self.assertEqual(off_code, "140000")
        self.assertEqual(c10_code, "140010") # フィルター用コードが正しく東部(140010)になっているか
        self.assertIn("offices", data)

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('weather.urllib.request.urlopen')
    def test_weather_forecast_filtering(self, mock_urlopen, mock_stdout):
        """ピンポイント検索時、不要なエリア（西部など）が非表示になるかの検証"""
        mock_urlopen.side_effect = self.mocked_urlopen

        # 「横浜市」で実行
        get_weather_forecast("横浜市")
        output = mock_stdout.getvalue()

        # 東部の情報は表示されるべき
        self.assertIn("■ 東部", output)
        self.assertIn("[気温] 18℃ / 25℃", output)

        # 西部の情報はフィルターされて消えるべき
        self.assertNotIn("■ 西部", output)
        self.assertNotIn("[気温] 15℃ / 20℃", output)

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('weather.urllib.request.urlopen')
    def test_weather_forecast_no_filtering_for_pref(self, mock_urlopen, mock_stdout):
        """県全域を検索した場合は、フィルターがかからず全て表示されるかの検証"""
        mock_urlopen.side_effect = self.mocked_urlopen

        # 「神奈川県」で実行
        get_weather_forecast("神奈川県")
        output = mock_stdout.getvalue()

        # 東部も西部も両方表示されるべき
        self.assertIn("■ 東部", output)
        self.assertIn("■ 西部", output)

if __name__ == '__main__':
    unittest.main()