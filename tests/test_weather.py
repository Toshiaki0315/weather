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
        # 1. エリア定義のダミーデータ（階層構造を持たせる）
        self.dummy_area_data = {
            "offices": {
                "140000": {"name": "神奈川県"}
            },
            "class10s": {
                "140010": {"name": "東部", "parent": "140000"}
            },
            "class15s": {
                "140020": {"name": "横浜・川崎", "parent": "140010"}
            },
            "class20s": {
                "1410000": {"name": "横浜市", "parent": "140020"},
                "140040": {"name": "横浜", "parent": "140010"} # 気温地点としての横浜
            }
        }

        # 2. 天気予報のダミーデータ（気温地点 140040 を含める）
        self.dummy_forecast_data = [
            {
                "timeSeries": [
                    { # 天気
                        "areas": [{"area": {"name": "東部", "code": "140010"}, "weathers": ["晴れ", "くもり"]}]
                    },
                    { # 降水
                        "areas": [{"area": {"name": "東部", "code": "140010"}, "pops": ["0"]}]
                    },
                    { # 気温（地点コード 140040）
                        "areas": [{"area": {"name": "横浜", "code": "140040"}, "temps": ["18", "25"]}]
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
        """戻り値が(コード, データ)のタプルであることの検証"""
        mock_urlopen.side_effect = self.mocked_urlopen
        code, data = get_area_info("横浜市")
        self.assertEqual(code, "140000")
        self.assertIn("offices", data)

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('weather.urllib.request.urlopen')
    def test_temperature_mapping_logic(self, mock_urlopen, mock_stdout):
        """気温地点(140040)が親の予報区(140010)に正しく紐付くかの検証"""
        mock_urlopen.side_effect = self.mocked_urlopen

        get_weather_forecast("横浜市")
        output = mock_stdout.getvalue()

        # 気温が '--' ではなく、ダミーデータの値になっているか
        self.assertIn("[気温] 18℃ / 25℃", output)

if __name__ == '__main__':
    unittest.main()