import urllib.request
import json
import argparse
import sys

def get_area_code(location_name: str) -> str:
    """気象庁のエリア定義JSONから、地名に対応するエリアコードを動的に検索して返す"""
    area_url = "https://www.jma.go.jp/bosai/common/const/area.json"
    
    try:
        req = urllib.request.Request(area_url)
        with urllib.request.urlopen(req) as response:
            area_data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"エリア定義データの取得に失敗しました: {e}")
        sys.exit(1)

    # 1. offices (府県予報区: 東京都、神奈川県など) から検索
    for code, info in area_data.get("offices", {}).items():
        if location_name in info["name"]:
            return code
            
    # 2. class10s (一次細分区域: 渡島地方、西部など) から検索
    for code, info in area_data.get("class10s", {}).items():
        if location_name in info["name"]:
            return info["parent"] # 親であるofficesコードを返す
            
    # 3. class20s (市町村: 函館市、横浜市など) から検索
    for code, info in area_data.get("class20s", {}).items():
        if location_name in info["name"]:
            # 市町村 -> 一次細分区域 -> 府県予報区 と親階層を遡る
            class10_code = info["parent"]
            if class10_code in area_data.get("class10s", {}):
                return area_data["class10s"][class10_code]["parent"]

    # 4. centers (地方: 北海道地方など) から検索
    for code, info in area_data.get("centers", {}).items():
        if location_name in info["name"]:
            return info["children"][0] # その地方に属する最初の府県予報区を返す

    return None

def get_weather_forecast(location_name: str) -> None:
    print(f"「{location_name}」のエリアコードを検索中...")
    area_code = get_area_code(location_name)
    
    if not area_code:
        print(f"エラー: 「{location_name}」に対応する地域が気象庁のデータに見つかりませんでした。")
        sys.exit(1)

    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

        areas = data[0]["timeSeries"][0]["areas"]
        
        print(f"【{location_name}の天気予報 (内部エリアコード: {area_code})】")
        for area in areas:
            area_name = area["area"]["name"]
            weather = area["weathers"][0].replace('　', ' ')
            print(f"- {area_name}: {weather}")

    except Exception as e:
        print(f"天気予報の取得中にエラーが発生しました: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="気象庁のデータから指定した場所の天気予報を取得します。")
    parser.add_argument(
        "location", 
        nargs="?", 
        default="横浜", 
        help="天気を取得したい場所（例: 東京, 函館, 横浜, 大阪）。省略した場合は横浜の天気を取得します。"
    )
    
    args = parser.parse_args()
    get_weather_forecast(args.location)
