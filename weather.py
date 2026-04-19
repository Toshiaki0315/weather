import urllib.request
import json

def get_weather_forecast() -> None:
    # 気象庁APIのエリアコード（140000は神奈川県）
    # ※東京は "130000"、大阪は "270000" などに変更可能です
    AREA_CODE = "140000" 
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{AREA_CODE}.json"

    try:
        # インターネット経由でJSONデータを取得
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            body = response.read()
            data = json.loads(body.decode('utf-8'))

        # データの解析（最初の要素から直近の予報エリアを抽出）
        areas = data[0]["timeSeries"][0]["areas"]
        
        print(f"【天気予報（エリアコード: {AREA_CODE}）】")
        for area in areas:
            area_name = area["area"]["name"]
            weather = area["weathers"][0] # 直近（今日）の天気
            
            # 気象庁のデータには全角スペースが含まれるため、半角スペースに整形
            weather_clean = weather.replace('　', ' ')
            
            print(f"- {area_name}: {weather_clean}")

    except urllib.error.URLError as e:
        print(f"通信エラーが発生しました: {e.reason}")
    except json.JSONDecodeError:
        print("JSONデータの解析に失敗しました。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    get_weather_forecast()
