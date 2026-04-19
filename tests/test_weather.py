import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os
import io

# 親ディレクトリにある weather.py をインポートできるようにパスを追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from weather import get_area_code, get_weather_forecast

class TestWeatherApp(unittest.TestCase):
    def setUp(self):
        # 1. エリア定義のダミーデータ（神奈川県横浜市のルート）
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
                "1410000": {"name": "横浜市", "parent": "140020"}
            }
        }

        # 2. 天気予報のダミーデータ（140000.json の中身を模倣）
        self.dummy_forecast_data = [
            { # data[0]: 短期予報（今日・明日）
                "timeSeries": [
                    { # 0: 天気
                        "areas": [
                            {"area": {"name": "東部", "code": "140010"}, "weathers": ["晴れ", "くもり　一時雨"]}
                        ]
                    },
                    { # 1: 降水確率
                        "areas": [
                            {"area": {"name": "東部", "code": "140010"}, "pops": ["10", "20", "30", "40"]}
                        ]
                    },
                    { # 2: 気温
                        "areas": [
                            {"area": {"name": "東部", "code": "140010"}, "temps": ["15", "25"]}
                        ]
                    }
                ]
            },
            { # data[1]: 週間予報
                "timeSeries": [
                    {
                        "areas": [
                            # 要素0, 1は今日明日。要素2, 3, 4が向こう3日間
                            {"area": {"name": "神奈川県", "code": "140010"}, "weathers": ["-", "-", "雨", "雪", "快晴"]}
                        ]
                    }
                ]
            }
        ]

    # アクセス先URLに応じて返すダミーデータを切り替える関数
    def mocked_urlopen(self, req):
        mock_response = MagicMock()
        url = req.full_url if hasattr(req, 'full_url') else req
        
        if "area.json" in url:
            mock_response.read.return_value = json.dumps(self.dummy_area_data).encode('utf-8')
        elif "140000.json" in url:
            mock_response.read.return_value = json.dumps(self.dummy_forecast_data).encode('utf-8')
        else:
            mock_response.read.return_value = json.dumps([]).encode('utf-8')
            
        mock_response.__enter__.return_value = mock_response
        return mock_response

    # --- テストケース ---

    @patch('weather.urllib.request.urlopen')
    def test_get_area_code_success(self, mock_urlopen):
        """エリアコード検索が正しく機能するか"""
        mock_urlopen.side_effect = self.mocked_urlopen
        result = get_area_code("神奈川県横浜市")
        self.assertEqual(result, "140000")

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('weather.urllib.request.urlopen')
    def test_get_weather_forecast_output(self, mock_urlopen, mock_stdout):
        """天気、降水確率、気温、週間天気が正しくパースされフォーマットされるか"""
        # 通信モックの設定
        mock_urlopen.side_effect = self.mocked_urlopen

        # 実行（標準出力は mock_stdout にキャプチャされる）
        get_weather_forecast("横浜市")

        # キャプチャした出力文字列を取得
        output = mock_stdout.getvalue()

        # 各項目がダミーデータから正しく抽出・整形されているか検証
        self.assertIn("【横浜市の天気予報】", output)
        self.assertIn("[今日] 晴れ", output)
        self.assertIn("[明日] くもり 一時雨", output) # 全角スペースが半角に置換されているか
        self.assertIn("[降水] 10% / 20% / 30% / 40%", output)
        self.assertIn("[気温] 15℃ / 25℃", output)
        self.assertIn("[週間] 向こう3日間: 雨 ➔ 雪 ➔ 快晴", output)

if __name__ == '__main__':
    unittest.main()
