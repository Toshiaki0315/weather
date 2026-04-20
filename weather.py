import urllib.request
import json
import argparse
import sys
import re

def get_area_info(input_location: str):
    """地名から「大元の県コード」「フィルター用の予報区コード」「エリア定義データ」を取得する"""
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

    # 内部関数: 検索にヒットした地点が、どの「県(offices)」と「予報区(class10s)」に属するかを辿る
    def get_codes(code: str, level: str):
        off_code = None
        c10_code = None
        if level == "offices":
            off_code = code # 県全体が検索された場合は、予報区フィルター(c10_code)はNoneのまま
        elif level == "class10s":
            c10_code = code
            off_code = area_data["class10s"][code]["parent"]
        elif level == "class15s":
            c10_code = area_data["class15s"][code]["parent"]
            off_code = area_data["class10s"][c10_code]["parent"]
        elif level == "class20s":
            p = area_data["class20s"][code]["parent"]
            c10_code = p if p in area_data["class10s"] else area_data["class15s"].get(p, {}).get("parent")
            if c10_code in area_data["class10s"]:
                off_code = area_data["class10s"][c10_code]["parent"]
        return off_code, c10_code

    def is_valid_pref(office_code: str) -> bool:
        if not expected_pref or not office_code: return True
        office_name = area_data.get("offices", {}).get(office_code, {}).get("name", "")
        if expected_pref in office_name or office_name in expected_pref: return True
        if "北海道" in expected_pref and office_code.startswith("01"): return True
        if "鹿児島" in expected_pref and office_code.startswith("46"): return True
        if "沖縄" in expected_pref and office_code.startswith("47"): return True
        return False

    target_office = None
    target_class10 = None
    
    # 各階層を検索
    for code, info in area_data.get("offices", {}).items():
        if search_target in info["name"] and is_valid_pref(code):
            target_office, target_class10 = get_codes(code, "offices"); break
    if not target_office:
        for code, info in area_data.get("class10s", {}).items():
            if search_target in info["name"]:
                off, c10 = get_codes(code, "class10s")
                if is_valid_pref(off): target_office, target_class10 = off, c10; break
    if not target_office:
        for code, info in area_data.get("class15s", {}).items():
            if search_target in info["name"]:
                off, c10 = get_codes(code, "class15s")
                if is_valid_pref(off): target_office, target_class10 = off, c10; break
    if not target_office:
        exact_match_patterns = [search_target, f"{search_target}市", f"{search_target}区", f"{search_target}町", f"{search_target}村"]
        for code, info in area_data.get("class20s", {}).items():
            if info["name"] in exact_match_patterns:
                off, c10 = get_codes(code, "class20s")
                if is_valid_pref(off): target_office, target_class10 = off, c10; break
    if not target_office:
        for code, info in area_data.get("class20s", {}).items():
            if search_target in info["name"]:
                off, c10 = get_codes(code, "class20s")
                if is_valid_pref(off): target_office, target_class10 = off, c10; break
    if not target_office and not expected_pref:
        for code, info in area_data.get("centers", {}).items():
            if search_target in info["name"]: target_office = info["children"][0]; break

    # 県コード、フィルターコード、元データの3つを返す
    return target_office, target_class10, area_data

def get_weather_forecast(location_name: str) -> None:
    print(f"「{location_name}」の天気を取得中...")
    area_code, filter_code, area_data = get_area_info(location_name)
    
    if not area_code:
        print(f"エラー: 「{location_name}」に対応する地域が見つかりませんでした。")
        sys.exit(1)

    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

        weather_series = data[0]["timeSeries"][0]
        pop_series = next((s for s in data[0]["timeSeries"] if "pops" in s["areas"][0]), None)
        temp_series = next((s for s in data[0]["timeSeries"] if "temps" in s["areas"][0]), None)
        
        weekly_weather_series = data[1]["timeSeries"][0] if len(data) > 1 else None
        weekly_temp_series = next((s for s in data[1]["timeSeries"] if "temps" in s["areas"][0]), None) if len(data) > 1 else None

        print(f"\n========== 【{location_name}の天気予報】 ==========")
        
        for i, w_area in enumerate(weather_series["areas"]):
            area_code_str = w_area["area"]["code"]
            
            # ★ ここがフィルター処理！
            # 検索した地域が特定の予報区(東部など)に属していて、
            # なおかつ現在のループが別の予報区(西部など)のデータだった場合は表示をスキップする
            if filter_code and area_code_str != filter_code:
                continue

            area_name = w_area["area"]["name"]
            
            # 1. 天気
            today_weather = w_area["weathers"][0].replace('　', ' ')
            tomorrow_weather = w_area["weathers"][1].replace('　', ' ') if len(w_area["weathers"]) > 1 else "-"
            
            # 2. 降水確率
            pops_str = "--"
            if pop_series and i < len(pop_series["areas"]):
                p_area = pop_series["areas"][i]
                pops = [p for p in p_area.get("pops", []) if p != ""]
                if pops: pops_str = " / ".join([f"{p}%" for p in pops])
            
            # 3. 気温
            temps_list = []
            if temp_series and i < len(temp_series["areas"]):
                t_area = temp_series["areas"][i]
                valid_temps = [t for t in t_area.get("temps", []) if t and t.strip()]
                if valid_temps:
                    temps_list = valid_temps

            if not temps_list and weekly_temp_series and i < len(weekly_temp_series["areas"]):
                t_area = weekly_temp_series["areas"][i]
                valid_temps = [t for t in t_area.get("temps", []) if t and t.strip()]
                if len(valid_temps) >= 2:
                    temps_list = valid_temps[:2]
            
            temps_str = " / ".join([f"{t}℃" for t in temps_list]) if temps_list else "--"
            
            # 4. 週間天気
            weekly_weather = "--"
            if weekly_weather_series and i < len(weekly_weather_series["areas"]):
                week_area = weekly_weather_series["areas"][i]
                weathers = week_area.get("weathers", [])
                if len(weathers) >= 5:
                    forecasts = [weathers[j].replace('　', ' ') for j in range(2, 5)]
                    weekly_weather = " ➔ ".join(forecasts)

            print(f"■ {area_name}")
            print(f"  [今日] {today_weather}")
            print(f"  [明日] {tomorrow_weather}")
            print(f"  [降水] {pops_str}")
            print(f"  [気温] {temps_str}")
            if weekly_weather != "--":
                print(f"  [週間] 向こう3日間: {weekly_weather}")
            print("-" * 40)

    except Exception as e:
        import traceback
        print(f"エラー詳細:\n{traceback.format_exc()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="気象庁のデータから天気予報を取得します。")
    parser.add_argument("location", nargs="?", default="横浜", help="取得場所")
    args = parser.parse_args()
    get_weather_forecast(args.location)