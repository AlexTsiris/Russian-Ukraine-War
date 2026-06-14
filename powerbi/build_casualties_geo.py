# -*- coding: utf-8 -*-
"""
Casualties GEOGRAPHY for Power BI, fully cloud-automatable (no Cloudflare, no API key).

Downloads the open per-region CDN files of the "Russia 200" project (Mediazona + BBC)
and writes the two English lookup tables the model already uses:
  regions.csv     — region_en, region_ru, settlements, total_deaths_full
  settlements.csv — region_en, region_ru, settlement_type, settlement_en,
                    settlement_ru, lat, lon, deaths, district_ru

These are the authoritative geography numbers (exactly what the 200.zona.media map shows);
the `r` field per settlement = confirmed dead from that place. This script is the
cloud-safe half of the casualties pipeline: the per-person detail (branch/rank/death date)
comes from the Cloudflare-protected /api/case and is collected separately, not here.

Dicts/functions are kept 1:1 with geo_regions.py + build_powerbi.py (assembled, not retyped).
Run: python build_casualties_geo.py
"""
import csv
import io
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE
BASE = "https://s3.zona.media/infographics/g200w/regions"
HEADERS = {"User-Agent": "Mozilla/5.0 (research; casualties analytics)"}

# ---------------------------------------------------------------- regions to fetch
REGIONS = [
    "Москва", "Санкт-Петербург", "Республика Адыгея", "Республика Алтай",
    "Алтайский край", "Амурская область", "Архангельская область",
    "Астраханская область", "Республика Башкортостан", "Белгородская область",
    "Брянская область", "Республика Бурятия", "Воронежская область",
    "Владимирская область", "Волгоградская область", "Вологодская область",
    "Республика Дагестан", "Еврейская автономная область", "Забайкальский край",
    "Ивановская область", "Иркутская область", "Республика Ингушетия",
    "Кабардино-Балкарская Республика", "Калининградская область",
    "Республика Калмыкия", "Калужская область", "Камчатский край",
    "Республика Карачаево-Черкесия", "Республика Карелия", "Кемеровская область",
    "Кировская область", "Республика Коми", "Костромская область",
    "Краснодарский край", "Красноярский край", "Курганская область",
    "Курская область", "Ленинградская область", "Липецкая область",
    "Магаданская область", "Республика Марий Эл", "Московская область",
    "Республика Мордовия", "Мурманская область", "Ненецкий автономный округ",
    "Новосибирская область", "Нижегородская область", "Новгородская область",
    "Омская область", "Оренбургская область", "Орловская область",
    "Пензенская область", "Пермский край", "Псковская область",
    "Приморский край", "Ростовская область", "Рязанская область",
    "Самарская область", "Саратовская область", "Сахалинская область",
    "Свердловская область", "Республика Северная Осетия-Алания",
    "Смоленская область", "Ставропольский край", "Тамбовская область",
    "Республика Татарстан", "Тверская область", "Томская область",
    "Тульская область", "Республика Тыва", "Тюменская область",
    "Удмуртская Республика", "Ульяновская область", "Хабаровский край",
    "Республика Хакасия", "Ханты-Мансийский автономный округ - Югра",
    "Челябинская область", "Чеченская Республика", "Чувашская Республика",
    "Чукотский автономный округ", "Республика Саха (Якутия)",
    "Ямало-Ненецкий автономный округ", "Ярославская область", "Байконур",
    "Республика Крым", "Севастополь", "ДНР", "ЛНР",
]


def filename(region):
    """How the app builds the filename: remove brackets, spaces -> '_'."""
    return region.replace("(", "").replace(")", "").replace(" ", "_") + ".csv.br"


def fetch_region(region):
    url = f"{BASE}/{urllib.parse.quote(filename(region))}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")

# ---------------------------------------------------------------- transliteration
_TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def translit(text):
    """Cyrillic -> Latin (deterministic, BGN-like). We don't touch the original."""
    if not text:
        return ""
    out = []
    for ch in text:
        low = ch.lower()
        if low in _TRANSLIT:
            t = _TRANSLIT[low]
            out.append(t.capitalize() if ch.isupper() and t else t)
        else:
            out.append(ch)
    return "".join(out)

# ---------------------------------------------------------------- region names (EN)
REGION_EN = {
    "Республика Башкортостан": "Bashkortostan", "Краснодарский край": "Krasnodar Krai",
    "Свердловская область": "Sverdlovsk Oblast", "Челябинская область": "Chelyabinsk Oblast",
    "Республика Татарстан": "Tatarstan", "Пермский край": "Perm Krai",
    "Московская область": "Moscow Oblast", "Ростовская область": "Rostov Oblast",
    "Красноярский край": "Krasnoyarsk Krai", "Иркутская область": "Irkutsk Oblast",
    "Волгоградская область": "Volgograd Oblast", "Республика Бурятия": "Buryatia",
    "Приморский край": "Primorsky Krai", "Кемеровская область": "Kemerovo Oblast",
    "Самарская область": "Samara Oblast", "Саратовская область": "Saratov Oblast",
    "Оренбургская область": "Orenburg Oblast", "Забайкальский край": "Zabaykalsky Krai",
    "Алтайский край": "Altai Krai", "Ставропольский край": "Stavropol Krai",
    "Новосибирская область": "Novosibirsk Oblast", "Нижегородская область": "Nizhny Novgorod Oblast",
    "Москва": "Moscow", "Удмуртская Республика": "Udmurtia",
    "Омская область": "Omsk Oblast", "Кировская область": "Kirov Oblast",
    "Воронежская область": "Voronezh Oblast", "Республика Дагестан": "Dagestan",
    "Санкт-Петербург": "Saint Petersburg",
    "Ханты-Мансийский автономный округ - Югра": "Khanty-Mansi AO – Yugra",
    "Архангельская область": "Arkhangelsk Oblast", "Белгородская область": "Belgorod Oblast",
    "Ульяновская область": "Ulyanovsk Oblast", "Тюменская область": "Tyumen Oblast",
    "Брянская область": "Bryansk Oblast", "Республика Саха (Якутия)": "Sakha (Yakutia)",
    "Вологодская область": "Vologda Oblast", "Сахалинская область": "Sakhalin Oblast",
    "Ленинградская область": "Leningrad Oblast", "Республика Тыва": "Tuva",
    "Республика Коми": "Komi", "Тверская область": "Tver Oblast",
    "Калининградская область": "Kaliningrad Oblast", "Астраханская область": "Astrakhan Oblast",
    "Республика Крым": "Crimea", "Псковская область": "Pskov Oblast",
    "Хабаровский край": "Khabarovsk Krai", "Ивановская область": "Ivanovo Oblast",
    "Пензенская область": "Penza Oblast", "Чувашская Республика": "Chuvashia",
    "Владимирская область": "Vladimir Oblast", "Курганская область": "Kurgan Oblast",
    "Республика Северная Осетия-Алания": "North Ossetia-Alania", "Липецкая область": "Lipetsk Oblast",
    "Томская область": "Tomsk Oblast", "Курская область": "Kursk Oblast",
    "Республика Марий Эл": "Mari El", "Тамбовская область": "Tambov Oblast",
    "Амурская область": "Amur Oblast", "Республика Карелия": "Karelia",
    "Тульская область": "Tula Oblast", "Мурманская область": "Murmansk Oblast",
    "Ярославская область": "Yaroslavl Oblast", "Республика Хакасия": "Khakassia",
    "Калужская область": "Kaluga Oblast", "Костромская область": "Kostroma Oblast",
    "Рязанская область": "Ryazan Oblast", "Новгородская область": "Novgorod Oblast",
    "Орловская область": "Oryol Oblast", "Смоленская область": "Smolensk Oblast",
    "Республика Мордовия": "Mordovia", "Ямало-Ненецкий автономный округ": "Yamalo-Nenets AO",
    "Республика Алтай": "Altai Republic", "Чеченская Республика": "Chechnya",
    "Камчатский край": "Kamchatka Krai", "Севастополь": "Sevastopol",
    "Кабардино-Балкарская Республика": "Kabardino-Balkaria", "Республика Адыгея": "Adygea",
    "Республика Калмыкия": "Kalmykia", "ДНР": "Donetsk PR (occupied)",
    "Республика Карачаево-Черкесия": "Karachay-Cherkessia", "Магаданская область": "Magadan Oblast",
    "Еврейская автономная область": "Jewish AO", "ЛНР": "Luhansk PR (occupied)",
    "Республика Ингушетия": "Ingushetia", "Чукотский автономный округ": "Chukotka AO",
    "Ненецкий автономный округ": "Nenets AO", "Байконур": "Baikonur",
    # foreign (countries of origin of recruited fighters)
    "Таджикистан": "Tajikistan", "Узбекистан": "Uzbekistan", "Южная Осетия": "South Ossetia",
    "Кыргызстан": "Kyrgyzstan", "Беларусь": "Belarus", "Непал": "Nepal", "Куба": "Cuba",
    "Казахстан": "Kazakhstan", "Абхазия": "Abkhazia", "Азербайджан": "Azerbaijan",
    "Украина": "Ukraine", "Молдова": "Moldova", "Сербия": "Serbia", "Африка": "Africa",
    "Армения": "Armenia", "Туркменистан": "Turkmenistan", "Китай": "China", "Йемен": "Yemen",
    "Гамбия": "Gambia", "Грузия": "Georgia", "Эстония": "Estonia", "Ирак": "Iraq",
    "Индия": "India", "Египет": "Egypt", "Афганистан": "Afghanistan", "Латвия": "Latvia",
    "Украина, Луганская область": "Ukraine, Luhansk Oblast",
    "Украина, Донецкая область": "Ukraine, Donetsk Oblast",
    "Украина, Запорожская область": "Ukraine, Zaporizhzhia Oblast",
    "Украина, Херсонская область": "Ukraine, Kherson Oblast",
    "Украина, Черниговская область": "Ukraine, Chernihiv Oblast",
    "Украина, Полтавская область": "Ukraine, Poltava Oblast",
    "Украина, Харьковская область": "Ukraine, Kharkiv Oblast",
    "###": "Unknown", None: "Unknown", "": "Unknown",
}

# ---------------------------------------------------------------- settlement type
SETTLEMENT_TYPE_EN = {
    "город": "City", "село": "Village", "посёлок": "Settlement",
    "поселок": "Settlement", "деревня": "Village", "станица": "Stanitsa",
    "хутор": "Khutor", "аул": "Aul", "рабочий": "Work settlement",
    "пгт": "Urban-type settlement", "посёлок городского типа": "Urban-type settlement",
}


def split_settlement(display_name):
    """Splits a settlement label, e.g. 'город Барнаул' -> ('City', 'Барнаул')."""
    if not display_name:
        return ("", "")
    parts = display_name.split(" ", 1)
    first = parts[0].lower()
    if first in SETTLEMENT_TYPE_EN and len(parts) > 1:
        return (SETTLEMENT_TYPE_EN[first], parts[1])
    return ("", display_name)


def main():
    os.makedirs(OUT, exist_ok=True)
    settlements = []
    region_totals = []
    failed = []
    for i, region in enumerate(REGIONS, 1):
        try:
            text = fetch_region(region)
        except Exception as e:
            failed.append((region, str(e)))
            print(f"  [{i}/{len(REGIONS)}] {region}: ERROR {e}")
            continue
        reader = csv.DictReader(io.StringIO(text))
        total = 0
        n = 0
        for row in reader:
            try:
                cnt = int(row.get("r") or 0)
            except ValueError:
                cnt = 0
            total += cnt
            n += 1
            settlements.append({
                "region": region,
                "settlement": row.get("display_name", ""),
                "lat": row.get("lat", ""),
                "lon": row.get("lon", ""),
                "deaths": cnt,
                "district": row.get("district", ""),
            })
        region_totals.append({"region": region, "settlements": n, "deaths": total})
        print(f"  [{i}/{len(REGIONS)}] {region}: {n} settlements, {total:,} dead")
        time.sleep(0.2)

    # regions.csv (English lookup + authoritative totals)
    region_totals.sort(key=lambda x: x["deaths"], reverse=True)
    with open(os.path.join(OUT, "regions.csv"), "w", encoding="utf-8-sig", newline="") as g:
        w = csv.writer(g)
        w.writerow(["region_en", "region_ru", "settlements", "total_deaths_full"])
        for r in region_totals:
            ru = r["region"]
            w.writerow([REGION_EN.get(ru, translit(ru)), ru, r["settlements"], r["deaths"]])

    # settlements.csv (English lookup with coordinates for the map)
    with open(os.path.join(OUT, "settlements.csv"), "w", encoding="utf-8-sig", newline="") as g:
        w = csv.writer(g)
        w.writerow(["region_en", "region_ru", "settlement_type", "settlement_en",
                    "settlement_ru", "lat", "lon", "deaths", "district_ru"])
        for s in settlements:
            ru = s["region"]
            stype, sname = split_settlement(s["settlement"])
            w.writerow([REGION_EN.get(ru, translit(ru)), ru, stype, translit(sname),
                        s["settlement"], s["lat"], s["lon"], s["deaths"], s["district"]])

    grand = sum(r["deaths"] for r in region_totals)
    print(f"\nregions.csv    : {len(region_totals)} regions, {grand:,} dead total")
    print(f"settlements.csv: {len(settlements):,} settlements")
    if failed:
        print(f"Failed: {[r for r, _ in failed]}")


if __name__ == "__main__":
    main()
