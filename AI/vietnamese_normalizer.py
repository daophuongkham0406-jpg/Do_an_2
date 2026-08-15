import re
import unicodedata


def strip_vietnamese_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def normalize_text(text: str) -> str:
    text = strip_vietnamese_accents(text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


MUSCLE_VI = {
    "abductors": "cơ dạng hông",
    "adductors": "cơ khép đùi",
    "anterior_deltoid": "cơ vai trước",
    "biceps_brachii": "cơ tay trước",
    "brachialis": "cơ cánh tay",
    "brachioradialis": "cơ cánh tay quay",
    "erector_spinae": "cơ dựng sống lưng",
    "forearm_extensors": "cơ duỗi cẳng tay",
    "forearm_flexors": "cơ gấp cẳng tay",
    "gastrocnemius": "cơ bắp chân ngoài",
    "gluteus_maximus": "cơ mông lớn",
    "gluteus_medius": "cơ mông nhỡ",
    "hamstrings": "cơ đùi sau",
    "hip_flexors": "cơ gấp hông",
    "lateral_deltoid": "cơ vai giữa",
    "latissimus_dorsi": "cơ xô",
    "obliques": "cơ liên sườn",
    "pectoralis_major": "cơ ngực",
    "posterior_deltoid": "cơ vai sau",
    "quadratus_lumborum": "cơ vuông thắt lưng",
    "quadriceps": "cơ đùi trước",
    "rectus_abdominis": "cơ bụng thẳng",
    "rhomboids": "cơ trám",
    "serratus_anterior": "cơ răng trước",
    "soleus": "cơ dép",
    "transverse_abdominis": "cơ bụng ngang",
    "trapezius": "cơ cầu vai",
    "triceps_brachii": "cơ tay sau",
}


BODY_PART_VI = {
    "back": "lưng",
    "chest": "ngực",
    "core": "bụng và thân giữa",
    "full_body": "toàn thân",
    "lower_arms": "cẳng tay",
    "lower_legs": "bắp chân",
    "shoulders": "vai",
    "upper_arms": "cánh tay",
    "upper_legs": "đùi và mông",
}


GOAL_VI = {
    "endurance": "tăng sức bền",
    "hypertrophy": "tăng cơ",
    "mobility": "tăng linh hoạt",
    "power": "tăng sức mạnh bùng nổ",
    "rehabilitation": "phục hồi",
    "strength": "tăng sức mạnh",
}


CATEGORY_VI = {
    "cardio": "tim mạch",
    "olympic": "cử tạ Olympic",
    "plyometrics": "bật nhảy/tốc độ",
    "strength": "sức mạnh",
    "stretching": "giãn cơ",
    "strongman": "strongman",
}


DIFFICULTY_VI = {
    "beginner": "người mới",
    "intermediate": "trung cấp",
    "advanced": "nâng cao",
}


SAFETY_TAG_BY_INJURY = {
    "knee": "knee_safe",
    "lower_back": "lower_back_safe",
    "shoulder": "shoulder_safe",
}


ALIASES_VI = {
    "knee": [
        "gối", "dau goi", "chan thuong goi", "khop goi", "dau dau goi",
        "dau khop goi",
    ],
    "lower_back": [
        "lưng dưới", "that lung", "dau lung", "dau lung duoi", "cot song",
        "dau cot song", "lung duoi", "thắt lưng",
    ],
    "shoulder": [
        "vai", "dau vai", "chan thuong vai", "khop vai", "co vai",
    ],
    "elbow": [
        "khuỷu tay", "khuyu tay", "dau khuyu tay", "cui cho", "dau cui cho",
    ],
    "wrist": [
        "cổ tay", "co tay", "dau co tay", "khop co tay",
    ],
    "neck": [
        "cổ", "co", "dau co", "vung co", "gáy", "gay", "dau gay",
    ],
    "chest": ["vùng ngực", "vung nguc"],
    "back": ["lưng", "lung", "co lung"],
    "core": ["vùng bụng", "vung bung", "core", "than giua", "than giữa"],
    "upper_legs": [
        "đùi", "dui", "chan tren",
    ],
    "lower_legs": ["cang chan", "cẳng chân"],
    "upper_arms": [
        "tay", "bắp tay", "bap tay", "cánh tay", "canh tay",
    ],
    "lower_arms": ["cẳng tay", "cang tay"],
}


MUSCLE_ALIASES_VI = {
    "pectoralis_major": ["ngực", "nguc", "co nguc", "ngực giữa", "nguc giua"],
    "latissimus_dorsi": ["xô", "xo", "cơ xô", "co xo", "lưng xô", "lung xo"],
    "trapezius": ["cầu vai", "cau vai", "co cau vai"],
    "rhomboids": ["cơ trám", "co tram", "lưng giữa", "lung giua"],
    "erector_spinae": ["dựng sống lưng", "dung song lung", "lưng dưới", "lung duoi"],
    "quadratus_lumborum": ["vuông thắt lưng", "vuong that lung", "thắt lưng"],
    "rectus_abdominis": ["bụng", "bung", "cơ bụng", "co bung", "six pack"],
    "transverse_abdominis": ["bụng ngang", "bung ngang", "core"],
    "obliques": ["liên sườn", "lien suon", "bụng xiên", "bung xien"],
    "anterior_deltoid": ["vai trước", "vai truoc"],
    "lateral_deltoid": ["vai giữa", "vai giua", "vai bên", "vai ben"],
    "posterior_deltoid": ["vai sau"],
    "biceps_brachii": ["tay trước", "tay truoc", "chuột", "chuot", "biceps"],
    "triceps_brachii": ["tay sau", "triceps"],
    "forearm_flexors": ["cẳng tay", "cang tay", "cơ gấp cẳng tay"],
    "forearm_extensors": ["cẳng tay", "cang tay", "cơ duỗi cẳng tay"],
    "quadriceps": ["đùi trước", "dui truoc", "quad"],
    "hamstrings": ["đùi sau", "dui sau", "hamstring"],
    "gluteus_maximus": ["mông", "mong", "cơ mông", "co mong", "mông lớn"],
    "gluteus_medius": ["mông nhỡ", "mong nho", "hông ngoài", "hong ngoai"],
    "hip_flexors": ["gấp hông", "gap hong", "hông trước", "hong truoc"],
    "adductors": ["khép đùi", "khep dui", "đùi trong", "dui trong"],
    "abductors": ["dạng hông", "dang hong", "đùi ngoài", "dui ngoai"],
    "gastrocnemius": ["bắp chân", "bap chan", "calf"],
    "soleus": ["bắp chân", "bap chan", "cơ dép", "co dep"],
}


def build_alias_index():
    index = {}

    def add(alias, key):
        normalized_alias = normalize_text(alias)
        index.setdefault(normalized_alias, set()).add(key)

    for key, aliases in MUSCLE_ALIASES_VI.items():
        add(key, key)
        for alias in aliases:
            add(alias, key)
    # Injury/body-region aliases win over muscle aliases for safety filtering.
    for key, aliases in ALIASES_VI.items():
        add(key, key)
        for alias in aliases:
            add(alias, key)
    return {alias: sorted(keys) for alias, keys in index.items()}


ALIAS_INDEX = build_alias_index()


def split_user_terms(value):
    if not value:
        return []
    if isinstance(value, str):
        raw_terms = re.split(r"[,;/|]+|\bvà\b|\bva\b", value, flags=re.IGNORECASE)
        return [term.strip() for term in raw_terms if term.strip()]
    return [str(term).strip() for term in value if str(term).strip()]


def normalize_avoid_terms(user_input):
    normalized = []
    unknown = []
    for term in split_user_terms(user_input):
        keys = ALIAS_INDEX.get(normalize_text(term))
        if keys:
            normalized.extend(keys)
        else:
            unknown.append(term)
    return {
        "avoid_keys": sorted(set(normalized)),
        "unknown_terms": unknown,
    }


def display_label(value, kind="muscle"):
    dictionaries = {
        "muscle": MUSCLE_VI,
        "body_part": BODY_PART_VI,
        "goal": GOAL_VI,
        "category": CATEGORY_VI,
        "difficulty": DIFFICULTY_VI,
    }
    return dictionaries.get(kind, {}).get(value, value)


def display_pipe_values(value, kind="muscle"):
    if value is None or value != value:
        return ""
    return ", ".join(display_label(part, kind) for part in str(value).split("|") if part)


def safety_tag_for_avoid_key(key):
    return SAFETY_TAG_BY_INJURY.get(key)
