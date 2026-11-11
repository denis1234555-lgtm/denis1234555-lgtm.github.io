# 動動腦小學堂：用 Azure 語音產生全站音檔
# 讀 audio/lines.json（[id, voice, lang, text, rate, pitch]），輸出 audio/v/<id>.mp3 與 audio/v/index.json
# 為了省下請求次數（免費版每分鐘只能 20 次），同一個聲音的句子會合併成一次請求，
# 句子之間插入 3 秒停頓，再用 ffmpeg 依靜音切開；切出來的段數不對就改成一句一句做。
import json, os, sys, time, html, re, subprocess, tempfile, urllib.request, urllib.error, functools
print = functools.partial(print, flush=True)

key = os.environ['KEY'].strip()
region = os.environ['REGION'].strip().lower()
if '://' in region: region = region.split('://', 1)[1]
region = region.split('/')[0].split('.')[0].replace(' ', '').replace('-', '')
if not key: print('AZURE_SPEECH_KEY 是空的'); sys.exit(1)
if not region or len(region) > 30 or not region.isalnum(): print('AZURE_SPEECH_REGION 填錯了：請填區域名稱，例如 eastasia'); sys.exit(1)
BUDGET = float(os.environ.get('BUDGET_MIN', '320')) * 60
T0 = time.time()
URL = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
OUT = 'audio/v'
os.makedirs(OUT, exist_ok=True)
FF = os.environ.get('FFMPEG') or 'ffmpeg'
GAP = 3000  # 句子之間的停頓（毫秒）
last_req = [0.0]
spent = [0]
diag = [0]


def post(ssml):
    for k in range(8):
        wait = 3.1 - (time.time() - last_req[0])  # 每分鐘最多約 19 次
        if wait > 0: time.sleep(wait)
        last_req[0] = time.time()
        spent[0] += len(re.sub(r'<[^>]+>', '', ssml))
        try:
            req = urllib.request.Request(URL, data=ssml.encode('utf-8'), headers={
                'Ocp-Apim-Subscription-Key': key, 'Content-Type': 'application/ssml+xml',
                'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3', 'User-Agent': 'ddn-tts'})
            return urllib.request.urlopen(req, timeout=120).read()
        except urllib.error.HTTPError as e:
            body = e.read()[:200]
            print('HTTP', e.code, body)
            if e.code in (401, 403): print('金鑰或區域不對，或是免費額度用完了'); sys.exit(1)
            if e.code == 400: return None
            time.sleep(int(e.headers.get('Retry-After') or 0) or 20 * (k + 1))
        except Exception as e:
            print('retry', e); time.sleep(5 * (k + 1))
    return None


ZY_NAME = {'ㄅ': 'ㄅㄛ', 'ㄆ': 'ㄆㄛ', 'ㄇ': 'ㄇㄛ', 'ㄈ': 'ㄈㄛ', 'ㄉ': 'ㄉㄜ', 'ㄊ': 'ㄊㄜ', 'ㄋ': 'ㄋㄜ', 'ㄌ': 'ㄌㄜ', 'ㄍ': 'ㄍㄜ', 'ㄎ': 'ㄎㄜ', 'ㄏ': 'ㄏㄜ', 'ㄐ': 'ㄐㄧ', 'ㄑ': 'ㄑㄧ', 'ㄒ': 'ㄒㄧ'}
# 破音字：句子太短、AI 猜不出來的，直接指定念法
POLY = {'長': [('長', 'ㄔㄤˊ')], '最長': [('長', 'ㄔㄤˊ')], '格長': [('長', 'ㄔㄤˊ')], '重': [('重', 'ㄓㄨㄥˋ')], '機長': [('長', 'ㄓㄤˇ')], '船長': [('長', 'ㄓㄤˇ')], '樂樂': [('樂', 'ㄌㄜˋ')], '小樂': [('樂', 'ㄌㄜˋ')]}
POLY_CORE = lambda t: re.sub(r'[。！？，、\s]', '', t)
TOK = re.compile(r'⟦([^|⟧]*)\|?([^⟧]*)⟧|([\u3105-\u3129][\u3105-\u3129ˊˇˋ˙]*)')


def mark(t):
    """注音符號和 ⟦IPA|字⟧ 改成 <phoneme>，讓 AI 念出正確的音"""
    pc = POLY.get(POLY_CORE(t))
    if pc:
        mp = dict(pc)
        return ''.join(f'<phoneme alphabet="sapi" ph="{html.escape(mp[c])}">{html.escape(c)}</phoneme>' if c in mp else html.escape(c) for c in t)
    out, i = [], 0
    for m in TOK.finditer(t):
        out.append(html.escape(t[i:m.start()])); i = m.end()
        if m.group(3):
            z = m.group(3); core = re.sub('[ˊˇˋ˙]', '', z)
            ph = ZY_NAME.get(z, z) if len(core) == 1 and z == core else z
            out.append(f'<phoneme alphabet="sapi" ph="{html.escape(ph)}">{html.escape(z)}</phoneme>')
        else:
            out.append(f'<phoneme alphabet="ipa" ph="{html.escape(m.group(1))}">{html.escape(m.group(2) or m.group(1))}</phoneme>')
    out.append(html.escape(t[i:]))
    return ''.join(out)


def prosody(t, rate, pitch):
    return f'<prosody rate="{rate}" pitch="{pitch}">{mark(t)}</prosody>'


def ssml(voice, lang, parts):
    # 注音的 sapi 念法只有台灣華語的聲音認得；其他聲音（例如角色用的 zh-CN 童聲）拿掉，免得整批失敗
    if lang == 'zh-CN':  # 大陸聲音用拼音
        PY = {'ㄌㄜˋ': 'le 4', 'ㄔㄤˊ': 'chang 2', 'ㄓㄨㄥˋ': 'zhong 4', 'ㄓㄤˇ': 'zhang 3'}
        parts = re.sub(r'<phoneme alphabet="sapi" ph="([^"]*)">([^<]*)</phoneme>', lambda m: f'<phoneme alphabet="sapi" ph="{PY[m[1]]}">{m[2]}</phoneme>' if m[1] in PY else m[2], parts)
    elif lang != 'zh-TW': parts = re.sub(r'<phoneme alphabet="sapi" ph="[^"]*">([^<]*)</phoneme>', r'\1', parts)
    return f'<speak version="1.0" xml:lang="{lang}"><voice name="{voice}">' + parts + '</voice></speak>'


def enc(src, dst, a=None, b=None):
    cmd = [FF, '-v', 'error', '-y', '-i', src]
    if a is not None: cmd += ['-ss', f'{a:.3f}']
    if b is not None: cmd += ['-to', f'{b:.3f}']
    cmd += ['-ac', '1', '-ar', '24000', '-c:a', 'libmp3lame', '-b:a', '40k', dst]
    subprocess.run(cmd, check=True)


def split(mp3, n):
    """回傳 n 段 (起, 迄) 秒數（念不出聲音的句子是 None）；對不上就回傳 None"""
    r = subprocess.run([FF, '-i', mp3, '-af', 'silencedetect=noise=-40dB:d=1.5', '-f', 'null', '-'], capture_output=True, text=True).stderr
    dur = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r)
    dur = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else 1e9
    ss = [float(x) for x in re.findall(r'silence_start: (-?[\d.]+)', r)]
    se = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r)]
    sil = [(a, b) for a, b in zip(ss, se) if a > 0.05 and b < dur - 0.05]
    # 很長的停頓 = 中間有句子沒有聲音（例如只有符號），一個停頓算好幾個
    gaps = []
    for a, b in sil:
        m = max(1, round((b - a) / (GAP / 1000 + 0.25)))
        gaps.append((a, b, m))
    if sum(g[2] for g in gaps) != n - 1:
        if diag[0] < 6:
            diag[0] += 1
            print('切不準：要', n - 1, '個停頓，找到', [(round(a, 2), round(b, 2)) for a, b in sil], '總長', round(dur, 2))
        return None
    out, start = [], 0.0
    for a, b, m in gaps:
        out.append((max(0, start - (0.12 if out else 0)), a + 0.18))
        out += [None] * (m - 1)
        start = b
    out.append((max(0, start - 0.12), dur))
    return out


def one(row):
    i, voice, lang, text, rate, pitch = row
    data = post(ssml(voice, lang, prosody(text, rate, pitch)))
    if not data: return False
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f: f.write(data)
    enc(f.name, f'{OUT}/{i}.mp3'); os.unlink(f.name)
    return True


def batch(rows):
    voice, lang = rows[0][1], rows[0][2]
    body = f'<break time="{GAP}ms"/>'.join(prosody(r[3], r[4], r[5]) for r in rows)
    data = post(ssml(voice, lang, body))
    if not data: return [one(r) for r in rows]
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f: f.write(data)
    seg = split(f.name, len(rows))
    if not seg:
        os.unlink(f.name)
        if len(rows) > 6:  # 切不準就分兩半再試
            h = len(rows) // 2
            return batch(rows[:h]) + batch(rows[h:])
        return [one(r) for r in rows]
    res = []
    for r, g in zip(rows, seg):
        if g: enc(f.name, f'{OUT}/{r[0]}.mp3', g[0], g[1])
        res.append(bool(g))
    os.unlink(f.name)
    return res


def write_index():
    ids = sorted(x[:-4] for x in os.listdir(OUT) if x.endswith('.mp3'))
    json.dump(ids, open(f'{OUT}/index.json', 'w'), separators=(',', ':'))
    return len(ids)


def save(msg):
    n = write_index()
    use[month] = base + spent[0]; json.dump(use, open(USE, 'w'))
    subprocess.run('git add audio && (git diff --cached --quiet || git commit -q -m "AI 語音音檔 ' + msg + '") && git pull -q --rebase && git push -q', shell=True)
    print('saved', n)


rows = json.load(open('audio/lines.json', encoding='utf-8'))
# 一次性：以前沒有用正確符號音念的注音句子，重新做一次
if not os.path.exists('audio/zyfix.txt'):
    redo = [r for r in rows if re.search('[\u3105-\u3129]', r[3]) and os.path.exists(f'{OUT}/{r[0]}.mp3')]
    for r in redo: os.remove(f'{OUT}/{r[0]}.mp3')
    open('audio/zyfix.txt', 'w').write(str(len(redo)))
    print('注音句子重做', len(redo))
# 第二次：破音字指定念法，重新做這幾句
if not os.path.exists('audio/zyfix2.txt'):
    redo = [r for r in rows if POLY_CORE(r[3]) in POLY and os.path.exists(f'{OUT}/{r[0]}.mp3')]
    for r in redo: os.remove(f'{OUT}/{r[0]}.mp3')
    open('audio/zyfix2.txt', 'w').write(str(len(redo)))
    print('破音字重做', len(redo))
todo = [r for r in rows if not os.path.exists(f'{OUT}/{r[0]}.mp3')]
print('全部', len(rows), '要做', len(todo), '字數', sum(len(r[3]) for r in todo))
# 優先清單：固定會念的句子先做，而且用實際字數計算（不乘 2），把本月剩下的額度留給它們
PRI = set(json.load(open('audio/priority.json', encoding='utf-8'))) if os.path.exists('audio/priority.json') else set()
pri_rows = [r for r in todo if r[3] in PRI]; todo = [r for r in todo if r[3] not in PRI]
print('優先句子', len(pri_rows), '字數', sum(len(r[3]) for r in pri_rows))
groups = {}
for r in todo: groups.setdefault((r[1], r[2], r[4], r[5]), []).append(r)
pgroups = {}
for r in pri_rows: pgroups.setdefault((r[1], r[2], r[4], r[5]), []).append(r)
jobs = []
for g in list(pgroups.values()) + list(groups.values()):
    cur, cc = [], 0
    for r in g:
        if cur and (len(cur) >= 30 or cc + len(r[3]) > 700): jobs.append(cur); cur, cc = [], 0
        cur.append(r); cc += len(r[3])
    if cur: jobs.append(cur)
NPRI = sum(1 for j in jobs if j[0][3] in PRI)
print('請求批次', len(jobs), '其中優先', NPRI)
MAXJOBS = int(os.environ.get('MAXJOBS', '0'))
done = fail = 0; since = 0
USE = 'audio/usage.json'
use = json.load(open(USE)) if os.path.exists(USE) else {}
month = time.strftime('%Y-%m'); CAP = int(os.environ.get('CAP', '450000'))
base = use.get(month, 0)
print('本月已用字數', base, '上限', CAP)
for k, job in enumerate(jobs):
    if time.time() - T0 > BUDGET: print('時間到，下次繼續'); break
    n = sum(len(r[3]) for r in job)
    if base + spent[0] + n * (1 if k < NPRI else 2) > CAP:
        if k < NPRI: continue
        print('本月免費字數快用完了，先停在這裡，下個月再繼續'); break
    if MAXJOBS and k >= MAXJOBS: print('測試完成'); break
    res = batch(job)
    done += sum(res); fail += len(res) - sum(res); since += sum(res)
    if k % 10 == 0 or MAXJOBS: print(f'{k + 1}/{len(jobs)} 完成 {done} 失敗 {fail} 已用字數 {spent[0]}')
    if since >= 2500: save('（進行中）'); since = 0
save('（全站）')
left = len([r for r in rows if not os.path.exists(f'{OUT}/{r[0]}.mp3')])
print('完成', done, '失敗', fail, '剩下', left)
open('/tmp/left', 'w').write(str(left if time.time() - T0 > BUDGET else 0))
