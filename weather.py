import urllib.request
import json
import argparse
import sys
import re

def get_area_code(input_location: str) -> str:
    """気象庁のエリア定義JSONから、地名に対応するエリアコードを動的に検索して返す"""
    
    normalized_name = input_location.replace(' ', '').replace('　', '')
    match = re.match(r'^(東京都|北海道|(?:京都|大阪)府|.{2,3}県)(.+)', normalized_name)
    
    if match:
        expected_pref = match.group(1) # 例: "青森県"
        search_target = match.group(2) # 例: "横浜市"
    else:
        expected_pref = None
        search_target = normalized_name

    area_url = "https://www.jma.go.jp/bosai/common/const/area.json"
    try:
        req = urllib.request.Request(area_url)
        with urllib.request.urlopen(req) as response:
            area_data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"エリア定義データの取得に失敗しました: {e}")
        sys.exit(1)

    # --- ヘルパー関数 ---
    def resolve_office_code(code: str, level: str) -> str:
        """任意の階層のコードから、大元である府県予報区(offices)のコードまで遡る"""
        if level == "offices":
            return code
        if level == "class10s":
            return area_data["class10s"][code]["parent"]
        if level == "class15s":
            c10 = area_data["class15s"][code]["parent"]
            return area_data["class10s"][c10]["parent"] if c10 in area_data["class10s"] else None
        if level == "class20s":
            parent = area_data["class20s"][code]["parent"]
            if parent in area_data["class15s"]:
                parent = area_data["class15s"][parent]["parent"]
            return area_data["class10s"][parent]["parent"] if parent in area_data["class10s"] else None
        return None

    def is_valid_pref(office_code: str) -> bool:
        """見つかった府県コードが、入力された都道府県(expected_pref)と矛盾していないか検証する"""
        if not expected_pref or not office_code:
            return True # 都道府県の指定がない場合は常にOKとする
            
        office_name = area_data.get("offices", {}).get(office_code, {}).get("name", "")
        
        # 直接一致（例: "青森県" in "青森県"）
        if expected_pref in office_name or office_name in expected_pref:
            return True
            
        # 気象庁特有の「県名」と「予報区名」が異なるケースへの対応
        if "北海道" in expected_pref and office_code.startswith("01"): return True
        if "鹿児島" in expected_pref and office_code.startswith("46"): return True
        if "沖縄" in expected_pref and office_code.startswith("47"): return True
        
        return False
    # --------------------

    # 1. offices (府県予報区) から検索
    for code, info in area_data.get("offices", {}).items():
        if search_target in info["name"]:
            if is_valid_pref(code): return code
            
    # 2. class10s (一次細分区域) から検索
    for code, info in area_data.get("class10s", {}).items():
        if search_target in info["name"]:
            off_code = resolve_office_code(code, "class10s")
            if is_valid_pref(off_code): return off_code
            
    # 3. class15s (市町村等をまとめた地域) から検索
    for code, info in area_data.get("class15s", {}).items():
        if search_target in info["name"]:
            off_code = resolve_office_code(code, "class15s")
            if is_valid_pref(off_code): return off_code

    # 4. class20s (市町村) から検索
    exact_match_patterns = [
        search_target, 
        f"{search_target}市", 
        f"{search_target}区", 
        f"{search_target}町", 
        f"{search_target}村"
    ]
    
    # 4-1. 完全一致パス
    for code, info in area_data.get("class20s", {}).items():
        if info["name"] in exact_match_patterns:
            off_code = resolve_office_code(code, "class20s")
            if is_valid_pref(off_code): return off_code

    # 4-2. 部分一致パス
    for code, info in area_data.get("class20s", {}).items():
        if search_target in info["name"]:
            off_code = resolve_office_code(code, "class20s")
            if is_valid_pref(off_code): return off_code

    # 5. centers (地方) から検索 ※都道府県の指定がない場合のみ
    if not expected_pref:
        for code, info in area_data.get("centers", {}).items():
            if search_target in info["name"]:
                return info["children"][0]

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
        
        print(f"\n【{location_name}の天気予報 (内部エリアコード: {area_code})】")
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
        help="天気を取得したい場所（例: 神奈川県横浜市, 青森県横浜町, 北海道函館市）。"
    )
    
    args = parser.parse_args()
    get_weather_forecast(args.location)
