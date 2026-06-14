# -*- coding: utf-8 -*-
"""
Prepares the data for Power BI (English names + ISO dates + transliteration)
WITHOUT damaging the source data: the original Cyrillic values are kept
alongside in separate columns (*_ru). Category translation uses exact dictionaries.

Input:  data/all_cases.jsonl (the current snapshot, appended to), data/settlements.csv,
        data/regions_summary.csv
Output: powerbi/casualties.csv   — the fact table (one row per person), in English
        powerbi/regions.csv      — region lookup (+ authoritative totals)
        powerbi/settlements.csv   — settlement lookup with coordinates (for the map)

You can re-run it at any time — it rebuilds from the current snapshot.
It does NOT touch the data download (read only).
"""

import csv
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "powerbi")

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

# ---------------------------------------------------------------- service branch
BRANCH_EN = {
    "заключенные": "Convicts (prison recruits)",
    "добровольцы": "Volunteers (contract)",
    "нет данных": "No data",
    "мобилизованные": "Mobilized",
    "мотострелковые войска": "Motorized rifle troops",
    "ВДВ": "Airborne (VDV)",
    "ЧВК": "PMC (Wagner etc.)",
    "морпехи": "Marines",
    "танковые войска": "Tank troops",
    "артиллерия": "Artillery",
    "спецназ": "Special forces",
    "нацгвардия": "National Guard (Rosgvardia)",
    "инженерные войска": "Engineer troops",
    "моряки": "Navy sailors",
    "военные пилоты": "Military pilots",
    "другие войска": "Other troops",
    "войска связи": "Signal troops",
    "войсковая ПВО": "Ground-forces air defense",
    "ФСБ": "FSB",
    "РХБЗ": "CBRN-defense troops",
    "наземные авиаслужбы": "Ground aviation services",
    "автомобильные": "Motor-transport troops",
    "военмед": "Military medics",
    "МВД": "Interior Ministry (MVD)",
    "ЖД": "Railway troops",
    "военная полиция": "Military police",
    "ФСО": "Federal Protective Service (FSO)",
    "СК": "Investigative Committee",
    None: "Unknown",
    "": "Unknown",
}

# ---------------------------------------------------------------- regions
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

# ---------------------------------------------------------------- ranks
# (priority: longer/more-specific keys come first)
RANK_RULES = [
    ("генерал-лейтенант", "Lieutenant General", "Officer"),
    ("генерал-майор", "Major General", "Officer"),
    ("подполковник", "Lieutenant Colonel", "Officer"),
    ("полковник", "Colonel", "Officer"),
    ("капитан-лейтенант", "Captain-Lieutenant", "Officer"),
    ("капитан 1", "Captain 1st rank", "Officer"),
    ("капитан 2", "Captain 2nd rank", "Officer"),
    ("капитан 3", "Captain 3rd rank", "Officer"),
    ("капитан первого", "Captain 1st rank", "Officer"),
    ("капитан второго", "Captain 2nd rank", "Officer"),
    ("капитан третьего", "Captain 3rd rank", "Officer"),
    ("капитан", "Captain", "Officer"),
    ("майор", "Major", "Officer"),
    ("старший лейтенант", "Senior Lieutenant", "Officer"),
    ("ст. лейтенант", "Senior Lieutenant", "Officer"),
    ("ст лейтенант", "Senior Lieutenant", "Officer"),
    ("страший лейтенант", "Senior Lieutenant", "Officer"),
    ("младший лейтенант", "Junior Lieutenant", "Officer"),
    ("мл. лейтенант", "Junior Lieutenant", "Officer"),
    ("мл лейтенант", "Junior Lieutenant", "Officer"),
    ("младщий лейтенант", "Junior Lieutenant", "Officer"),
    ("лейтенант", "Lieutenant", "Officer"),
    ("офицер", "Officer (unspecified)", "Officer"),
    ("старший прапорщик", "Senior Warrant Officer", "NCO"),
    ("ст. прапорщик", "Senior Warrant Officer", "NCO"),
    ("ст прапорщик", "Senior Warrant Officer", "NCO"),
    ("прапорщик", "Warrant Officer (Praporshchik)", "NCO"),
    ("старший мичман", "Senior Michman", "NCO"),
    ("мичман", "Michman (naval WO)", "NCO"),
    ("главный корабельный старшина", "Chief Ship Petty Officer", "NCO"),
    ("главный старшина", "Chief Petty Officer", "NCO"),
    ("корабельный старшина", "Ship Petty Officer", "NCO"),
    ("старшина 1", "Petty Officer 1st class", "NCO"),
    ("старшина 2", "Petty Officer 2nd class", "NCO"),
    ("старшина перв", "Petty Officer 1st class", "NCO"),
    ("старшина втор", "Petty Officer 2nd class", "NCO"),
    ("старшина i", "Petty Officer 1st class", "NCO"),
    ("старшина", "Sergeant Major (Starshina)", "NCO"),
    ("старший сержант", "Senior Sergeant", "NCO"),
    ("ст. сержант", "Senior Sergeant", "NCO"),
    ("ст сержант", "Senior Sergeant", "NCO"),
    ("сташий сержант", "Senior Sergeant", "NCO"),
    ("младший сержант", "Junior Sergeant", "NCO"),
    ("мл. сержант", "Junior Sergeant", "NCO"),
    ("мл сержant", "Junior Sergeant", "NCO"),
    ("мл сержант", "Junior Sergeant", "NCO"),
    ("младший срежант", "Junior Sergeant", "NCO"),
    ("младший сержнт", "Junior Sergeant", "NCO"),
    ("млажший сержант", "Junior Sergeant", "NCO"),
    ("сержант", "Sergeant", "NCO"),
    ("старший матрос", "Senior Seaman", "Enlisted"),
    ("ст. матрос", "Senior Seaman", "Enlisted"),
    ("ст матрос", "Senior Seaman", "Enlisted"),
    ("матрос", "Seaman", "Enlisted"),
    ("ефрейтор", "Lance Corporal (Yefreitor)", "Enlisted"),
    ("старший стрелок", "Senior Rifleman", "Enlisted"),
    ("стрелок", "Rifleman", "Enlisted"),
    ("разведчик", "Scout (rifleman)", "Enlisted"),
    ("срочник", "Conscript", "Enlisted"),
    ("рядовой", "Private", "Enlisted"),
]


def norm_rank(raw):
    """Returns (rank_en, rank_category). The original is kept separately."""
    if not raw:
        return ("", "Unknown")
    s = raw.lower().replace("гв.", " ").replace("гв ", " ").replace("гвардии", " ")
    for key, en, cat in RANK_RULES:
        if key in s:
            return (en, cat)
    return ("Other / unclear", "Other")

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


def to_iso(date_str):
    """'dd.mm.yyyy' -> 'yyyy-mm-dd'. A bare 'yyyy', garbage, or an impossible
    calendar date (e.g. 31.04 / 30.02) -> '' (so Power BI never sees a bad date)."""
    if not date_str or not isinstance(date_str, str):
        return ""
    p = date_str.split(".")
    if len(p) == 3 and all(x.isdigit() for x in p):
        d, m, y = p
        if len(y) == 4:
            try:
                # datetime validates real days-in-month (rejects 31 Apr, 30 Feb, ...)
                return datetime.date(int(y), int(m), int(d)).isoformat()
            except ValueError:
                return ""
    return ""


MONTHS_EN = ["", "January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]


def build_casualties():
    os.makedirs(OUT, exist_ok=True)
    src = os.path.join(DATA, "all_cases.jsonl")
    rows = []
    for line in open(src, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("_error") or r.get("_notfound"):
            continue

        region_ru = r.get("regionDisplay") or r.get("region")
        death = r.get("death")
        death_iso = to_iso(death)
        # year: from the ISO date, or from a year-only string
        d_year = ""
        d_month = ""
        d_mname = ""
        if death_iso:
            d_year = int(death_iso[:4])
            d_month = int(death_iso[5:7])
            d_mname = MONTHS_EN[d_month]
        elif isinstance(death, str) and death.isdigit() and len(death) == 4:
            d_year = int(death)

        rank_en, rank_cat = norm_rank(r.get("rank"))
        rows.append({
            "uid": r.get("uid"),
            "name_en": translit(r.get("name")),
            "name_ru": r.get("name"),
            "region_en": REGION_EN.get(region_ru, translit(region_ru)),
            "region_ru": region_ru,
            "branch_en": BRANCH_EN.get(r.get("type"), translit(r.get("type"))),
            "branch_ru": r.get("type"),
            "rank_en": rank_en,
            "rank_category": rank_cat,
            "rank_ru": r.get("rank") or "",
            "age": r.get("age") if r.get("age") is not None else "",
            "birth_date": to_iso(r.get("birth")),
            "death_date": death_iso,
            "death_year": d_year,
            "death_month": d_month,
            "death_month_name": d_mname,
            "city_en": translit(r.get("locationName")),
            "city_ru": r.get("locationName") or "",
            "source_url": r.get("source") or "",
        })

    # Performance: export ONLY the columns the model actually uses (visuals + DAX +
    # relationships). High-cardinality text columns (names, uid, source_url, cities,
    # *_ru duplicates) are NOT loaded — they bloat the model with no analytical use.
    # The model derives death_month_start / age_group / war_phase from age & death_date
    # via DAX, so those base columns are enough. (extrasaction="ignore" drops the rest.)
    cols = ["region_en", "branch_en", "rank_category", "age", "death_date"]
    path = os.path.join(OUT, "casualties.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"casualties.csv : {len(rows):,} rows")
    return len(rows)


def build_regions():
    src = os.path.join(DATA, "regions_summary.csv")
    if not os.path.exists(src):
        return
    out = os.path.join(OUT, "regions.csv")
    with open(src, encoding="utf-8") as f, \
            open(out, "w", encoding="utf-8-sig", newline="") as g:
        rd = csv.DictReader(f)
        w = csv.writer(g)
        w.writerow(["region_en", "region_ru", "settlements", "total_deaths_full"])
        n = 0
        for row in rd:
            ru = row["region"]
            w.writerow([REGION_EN.get(ru, translit(ru)), ru,
                        row["settlements"], row["deaths"]])
            n += 1
    print(f"regions.csv    : {n} regions (totals over the full geography)")


def build_settlements():
    src = os.path.join(DATA, "settlements.csv")
    if not os.path.exists(src):
        return
    out = os.path.join(OUT, "settlements.csv")
    with open(src, encoding="utf-8") as f, \
            open(out, "w", encoding="utf-8-sig", newline="") as g:
        rd = csv.DictReader(f)
        w = csv.writer(g)
        w.writerow(["region_en", "region_ru", "settlement_type", "settlement_en",
                    "settlement_ru", "lat", "lon", "deaths", "district_ru"])
        n = 0
        for row in rd:
            ru = row["region"]
            stype, sname = split_settlement(row["settlement"])
            w.writerow([REGION_EN.get(ru, translit(ru)), ru, stype,
                        translit(sname), row["settlement"],
                        row["lat"], row["lon"], row["deaths"], row["district"]])
            n += 1
    print(f"settlements.csv: {n:,} settlements (with coordinates for the map)")


def main():
    print("Preparing the Power BI export (English, ISO dates, originals preserved)...")
    build_casualties()
    build_regions()
    build_settlements()
    print(f"\nDone -> folder: {OUT}")


if __name__ == "__main__":
    main()
