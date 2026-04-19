import urllib.request
import json
import argparse
import sys

# 日本全国の都道府県と主要都市から気象庁エリアコードへのマッピング
AREA_MAP = {
    "北海道": "016000", "札幌": "016000",
    "青森": "020000", "岩手": "030000", "宮城": "040000", "仙台": "040000",
    "秋田": "050000", "山形": "060000", "福島": "070000",
    "茨城": "080000", "栃木": "090000", "群馬": "100000",
    "埼玉": "110000", "千葉": "120000", "東京": "130000", 
    "神奈川": "140000", "横浜": "140000",
    "新潟": "150000", "富山": "160000", "石川": "170000", "金沢": "170000",
    "福井": "180000", "山梨": "190000", "長野": "200000",
    "岐阜": "210000", "静岡": "220000", "愛知": "230000", "名古屋": "230000",
    "三重": "240000", "滋賀": "250000", "京都": "260000",
    "大阪": "270000", "兵庫": "280000", "神戸": "280000",
    "奈良": "290000", "和歌山": "300000",
    "鳥取": "310000", "島根": "320000", "岡山": "330000",
    "広島": "340000", "山口": "350000",
    "徳島": "360000", "香川": "370000", "高松": "370000",
    "愛媛": "380000", "松山": "380000", "高知": "390000",
    "福岡": "400000", "佐賀": "410000", "長崎": "420000",
    "熊本": "430000", "大分": "440000", "宮崎": "450000",
    "鹿児島": "460100", "沖縄": "471000", "那覇": "471000"
}

def get_weather_forecast(location_name: str) -> None:
    # 入力された地名を正規化（「県」や「府」などを削除してマッチングしやすくする）
    clean_name = location_name.replace("都", "").replace("府", "").replace("県", "")
    
    # 辞書からエリアコードを取得
    area_code = AREA_MAP.get(clean_name)
    
    if not area_code:
        print(f"エラー: 「{location_name}」に対応するエリアコードが見つかりません。")
        print("都道府県名、または主要都市名（例: 東京, 大阪, 横浜, 札幌）を指定してください。")
        sys.exit(1)

    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            body = response.read()
            data = json.loads(body.decode('utf-8'))

        areas = data[0]["timeSeries"][0]["areas"]
        
        print(f"【{location_name}の天気予報】")
        for area in areas:
            area_name = area["area"]["name"]
            weather = area["weathers"][0]
            weather_clean = weather.replace('　', ' ')
            
            print(f"- {area_name}: {weather_clean}")

    except urllib.error.URLError as e:
        print(f"通信エラーが発生しました: {e.reason}")
    except json.JSONDecodeError:
        print("JSONデータの解析に失敗しました。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    # argparseを使ってコマンドライン引数を処理
    parser = argparse.ArgumentParser(description="気象庁のデータから指定した場所の天気予報を取得します。")
    parser.add_argument(
        "location", 
        nargs="?", 
        default="横浜", 
        help="天気を取得したい場所（例: 東京, 北海道, 横浜, 大阪）。省略した場合は横浜の天気を取得します。"
    )
    
    args = parser.parse_args()
    get_weather_forecast(args.location)
