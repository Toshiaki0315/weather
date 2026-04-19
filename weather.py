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
        expected_pref = match.group(1)
        search_target = match.group(2)
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

    def resolve_office_code(code: str, level: str) -> str:
        if level == "offices": return code
        if level == "class10s": return area_data["class10s"][code]["parent"]
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
        if not expected_pref or not office_code: return True
        office_name = area_data.get("offices", {}).get(office_code, {}).get("name", "")
        if expected_pref in office_name or office_name in expected_pref: return True
        if "北海道" in expected_pref and office_code.startswith("01"): return True
        if "鹿児島" in expected_pref and office_code.startswith("46"): return True
        if "沖縄" in expected_pref and office_code.startswith("47"): return True
        return False

    for code, info in area_data.get("offices", {}).items():
        if search_target in info["name"] and is_valid_pref(code): return code
            
    for code, info in area_data.get("class10s", {}).items():
        if search_target in info["name"]:
            off_code = resolve_office_code(code, "class10s")
            if is_valid_pref(off_code): return off_code
            
    for code, info in area_data.get("class15s", {}).items():
        if search_target in info["name"]:
            off_code = resolve_office_code(code, "class15s")
            if is_valid_pref(off_code): return off_code

    exact_match_patterns = [search_target, f"{search_target}市", f"{search_target}区", f"{search_target}町", f"{search_target}村"]
    
    for code, info in area_data.get("class20s", {}).items():
        if info["name"] in exact_match_patterns:
            off_code = resolve_office_code(code, "class20s")
            if is_valid_pref(off_code): return off_code

    for code, info in area_data.get("class20s", {}).items():
        if search_target in info["name"]:
            off_code = resolve_office_code(code, "class20s")
            if is_valid_pref(off_code): return off_code

    if not expected_pref:
        for code, info in area_data.get("centers", {}).items():
            if search_target in info["name"]: return info["children"][0]

    return None

def get_weather_forecast(location_name: str) -> None:
    print(f"「{location_name}」の天気を取得中...")
    area_code = get_area_code(location_name)
    
    if not area_code:
        print(f"エラー: 「{location_name}」に対応する地域が気象庁のデータに見つかりませんでした。")
        sys.exit(1)

    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

        # data[0] は直近の予報（今日・明日・明後日）
        weather_areas = data[0]["timeSeries"][0]["areas"] # 天気
        pop_areas = data[0]["timeSeries"][1]["areas"]     # 降水確率
        temp_areas = data[0]["timeSeries"][2]["areas"]    # 気温
        
        # data[1] は週間予報（存在しない場合もあるため安全に取得）
        weekly_areas = data[1]["timeSeries"][0]["areas"] if len(data) > 1 else []

        print(f"\n========== 【{location_name}の天気予報】 ==========")
        
        for w_area in weather_areas:
            area_name = w_area["area"]["name"]
            area_code_str = w_area["area"]["code"]
            
            # --- 1. 天気の取得 ---
            today_weather = w_area["weathers"][0].replace('　', ' ')
            tomorrow_weather = w_area["weathers"][1].replace('　', ' ') if len(w_area["weathers"]) > 1 else "-"
            
            # --- 2. 降水確率の取得 ---
            pops_str = "--"
            for p_area in pop_areas:
                if p_area["area"]["code"] == area_code_str:
                    pops = [p for p in p_area.get("pops", []) if p != ""]
                    if pops:
                        # 6時間ごとの確率を「/」で結合して表示
                        pops_str = " / ".join([f"{p}%" for p in pops])
                    break
                    
            # --- 3. 気温の取得 ---
            temps_str = "--"
            for t_area in temp_areas:
                if t_area["area"]["code"] == area_code_str:
                    temps = t_area.get("temps", [])
                    if temps:
                        # 取得時間によって配列の数が変わるため、単純に「/」で結合
                        temps_str = " / ".join([f"{t}℃" for t in temps])
                    break
            
            # --- 4. 週間天気の取得 ---
            weekly_weather = "--"
            for week_area in weekly_areas:
                if week_area["area"]["code"] == area_code_str:
                    # 向こう3日間の天気を抜粋（要素0, 1は今日明日のため、2〜4を取得）
                    weathers = week_area.get("weathers", [])
                    if len(weathers) >= 5:
                        forecasts = [weathers[i].replace('　', ' ') for i in range(2, 5)]
                        weekly_weather = " ➔ ".join(forecasts)
                    break

            # ターミナルへの出力（将来的なディスプレイ描画を見据えたレイアウト）
            print(f"■ {area_name}")
            print(f"  [今日] {today_weather}")
            print(f"  [明日] {tomorrow_weather}")
            print(f"  [降水] {pops_str} (6時間ごと)")
            print(f"  [気温] {temps_str} (最低/最高など)")
            if weekly_weather != "--":
                print(f"  [週間] 向こう3日間: {weekly_weather}")
            print("-" * 40)

    except Exception as e:
        print(f"天気予報の取得中にエラーが発生しました: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="気象庁のデータから指定した場所の天気予報を取得します。")
    parser.add_argument("location", nargs="?", default="横浜", help="天気を取得したい場所")
    args = parser.parse_args()
    get_weather_forecast(args.location)
