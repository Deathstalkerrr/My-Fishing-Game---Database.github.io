# -*- coding: utf-8 -*-
"""Приведение сырых упоминаний локаций и наживок к каноническим названиям."""
import json, re, unicodedata

LOCS  = list(json.load(open('/mnt/user-data/uploads/location_levels.json')).keys())
BAITS = list(json.load(open('/mnt/user-data/uploads/bait_weight_class.json')).keys())

def nk(s):
    s = str(s or '').lower().replace('ё', 'е')
    s = re.sub(r'[()\[\]«»"\'.,;:/\\]', ' ', s)   # слэш тоже разделитель
    return re.sub(r'\s+', ' ', s).strip()

# Отсекаем русские окончания, чтобы «ручейника»/«ручейник» и «изумрудном»/«изумрудное» сходились
def stem(w):
    for suf in ('ами','ями','ого','его','ому','ему','ыми','ими','ых','их','ах','ях','ов','ев',
                'ый','ий','ая','яя','ое','ее','ые','ие','ом','ем','ам','ям',
                'у','ю','а','я','о','е','ы','и','й','ь'):
        if len(w) > 4 and w.endswith(suf):
            return w[:-len(suf)]
    return w

def key(s):
    return ' '.join(stem(w) for w in nk(s).split())

# Значимые слова: игнорируем родовые, если они не единственные
GENERIC = {'озер', 'рек', 'залив', 'остров', 'долин', 'пещер', 'берег', 'скал', 'зон', 'личинк', 'живец', 'кас'}

def build(canon):
    idx = {}
    for c in canon:
        idx.setdefault(key(c), []).append(c)
    return idx

LOC_IDX, BAIT_IDX = build(LOCS), build(BAITS)

def _resolve(raw, canon, idx):
    if not raw: return None, 'пусто'
    k = key(raw)
    if k in idx and len(idx[k]) == 1:
        return idx[k][0], 'точное'
    words = [w for w in k.split() if w]
    best, score = None, 0
    for c in canon:
        ck = set(key(c).split())
        common = ck & set(words)
        if not common: continue
        # уникальные (не родовые) слова весят больше
        s = sum(3 if w not in GENERIC else 1 for w in common)
        s = s / (len(ck) ** 0.5)
        if s > score: best, score = c, s
    if best and score >= 1.5:
        rivals = [c for c in canon if c != best and (set(key(c).split()) & set(words))
                  and sum(3 if w not in GENERIC else 1 for w in (set(key(c).split()) & set(words))) / (len(set(key(c).split())) ** 0.5) >= score - 0.3]
        note = f'по ключевым словам (вес {score:.1f})'
        if rivals: note += f' ⚠ неоднозначно, также подходит: {", ".join(rivals[:3])}'
        return best, note
    return None, 'не найдено'

def resolve_location(raw): return _resolve(raw, LOCS, LOC_IDX)

def _cap(s):
    s = str(s or '').strip()
    return s[:1].upper() + s[1:] if s else s

def resolve_bait(raw):
    """Разбираем покомпонентно: «|» — снасть, «/» — равноправные варианты,
    «+» — добавки. Снасти и бренды не трогаем."""
    if not raw: return None, 'пусто'
    notes = []
    def one(chunk):
        c, why = _resolve(chunk, BAITS, BAIT_IDX)
        notes.append(why)
        return c if c else _cap(chunk)
    out = []
    for part in re.split(r'\s*\|\s*', str(raw)):
        if re.search(r'спиннинг|воблер|блесн|поппер|джиг|shake|diver|predator|hunter|wm\s*\d|ns\d',
                     part, re.I):
            out.append(part.strip()); notes.append('снасть — без изменений'); continue
        variants = [' + '.join(one(ch) for ch in re.split(r'\s*\+\s*', v))
                    for v in re.split(r'\s*/\s*', part)]
        out.append(', '.join(variants))
    return ' | '.join(out), '; '.join(sorted(set(notes)))

if __name__ == '__main__':
    tests_loc = ['на изумрудном', 'изумрудное озеро 2', 'Каменный Берег', 'Амазонка',
                 'пещера пашабей / каменный берег', 'белых скалах', 'р. Колорадо', 'вабакими',
                 'холодном озере', 'Река Габи/Таби (неточно)', 'озеро савай', 'Луна']
    print('=== ЛОКАЦИИ ===')
    for t in tests_loc:
        c, why = resolve_location(t)
        print(f'  {t:34s} -> {str(c):22s} [{why}]')
    tests_bait = ['ручейник', 'на ручейника', 'короед', 'живец маленький', 'Кусок Рыбы',
                  'опарыша', 'личинка майского жука', 'майский жук', 'креветка + кровь',
                  'Рак | Спиннинг: Shake Head', 'Воблеры', 'каша перловая', 'мотыля']
    print('\n=== НАЖИВКИ ===')
    for t in tests_bait:
        c, why = resolve_bait(t)
        print(f'  {t:34s} -> {str(c):34s} [{why}]')
