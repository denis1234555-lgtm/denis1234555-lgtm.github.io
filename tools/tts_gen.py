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
GAP = 3000  # 句子之間的停頓（毫秒）
last_req = [0.0]


def post(ssml):
    for k in range(8):
        wait = 3.1 - (time.time() - last_req[0])  # 每分鐘最多約 19 次
        if wait > 0: time.sleep(wait)
        last_req[0] = time.time()
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


def prosody(t, rate, pitch):
    return f'<prosody rate="{rate}" pitch="{pitch}">{html.escape(t)}</prosody>'


def ssml(voice, lang, parts):
    return f'<speak version="1.0" xml:lang="{lang}"><voice name="{voice}">' + parts + '</voice></speak>'


def enc(src, dst, a=None, b=None):
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src]
    if a is not None: cmd += ['-ss', f'{a:.3f}']
    if b is not None: cmd += ['-to', f'{b:.3f}']
    cmd += ['-ac', '1', '-ar', '24000', '-c:a', 'libmp3lame', '-b:a', '40k', dst]
    subprocess.run(cmd, check=True)


def split(mp3, n):
    """回傳 n 段 (起, 迄) 秒數；找不到剛好 n-1 個長停頓就回傳 None"""
    r = subprocess.run(['ffmpeg', '-i', mp3, '-af', 'silencedetect=noise=-42dB:d=1.6', '-f', 'null', '-'], capture_output=True, text=True).stderr
    dur = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r)
    dur = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else None
    ss = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r)]
    se = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r)]
    sil = [(a, b) for a, b in zip(ss, se) if a > 0.05 and (dur is None or b < dur - 0.05)]
    if len(sil) != n - 1: return None
    edges = [0.0] + [x for p in sil for x in p] + [dur or 1e9]
    return [(max(0, edges[2 * i] - (0.12 if i else 0)), edges[2 * i + 1] + 0.18) for i in range(n)]


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
        if len(rows) > 4:  # 切不準就分兩半再試
            h = len(rows) // 2
            return batch(rows[:h]) + batch(rows[h:])
        return [one(r) for r in rows]
    for r, (a, b) in zip(rows, seg): enc(f.name, f'{OUT}/{r[0]}.mp3', a, b)
    os.unlink(f.name)
    return [True] * len(rows)


def write_index():
    ids = sorted(x[:-4] for x in os.listdir(OUT) if x.endswith('.mp3'))
    json.dump(ids, open(f'{OUT}/index.json', 'w'), separators=(',', ':'))
    return len(ids)


def save(msg):
    n = write_index()
    subprocess.run('git add audio && (git diff --cached --quiet || git commit -q -m "AI 語音音檔 ' + msg + '") && git pull -q --rebase && git push -q', shell=True)
    print('saved', n)


rows = json.load(open('audio/lines.json', encoding='utf-8'))
todo = [r for r in rows if not os.path.exists(f'{OUT}/{r[0]}.mp3')]
print('全部', len(rows), '要做', len(todo), '字數', sum(len(r[3]) for r in todo))
groups = {}
for r in todo: groups.setdefault((r[1], r[2], r[4], r[5]), []).append(r)
jobs = []
for g in groups.values():
    cur, cc = [], 0
    for r in g:
        if cur and (len(cur) >= 30 or cc + len(r[3]) > 700): jobs.append(cur); cur, cc = [], 0
        cur.append(r); cc += len(r[3])
    if cur: jobs.append(cur)
print('請求批次', len(jobs))
done = fail = 0; since = 0
USE = 'audio/usage.json'
use = json.load(open(USE)) if os.path.exists(USE) else {}
month = time.strftime('%Y-%m'); CAP = int(os.environ.get('CAP', '450000'))
print('本月已用字數', use.get(month, 0), '上限', CAP)
for k, job in enumerate(jobs):
    if time.time() - T0 > BUDGET: print('時間到，下次繼續'); break
    n = sum(len(r[3]) for r in job)
    if use.get(month, 0) + n > CAP: print('本月免費字數快用完了，先停在這裡，下個月再繼續'); break
    use[month] = use.get(month, 0) + n; json.dump(use, open(USE, 'w'))
    res = batch(job)
    done += sum(res); fail += len(res) - sum(res); since += sum(res)
    if k % 20 == 0: print(f'{k + 1}/{len(jobs)} 完成 {done} 失敗 {fail}')
    if since >= 2500: save('（進行中）'); since = 0
save('（全站）')
left = len([r for r in rows if not os.path.exists(f'{OUT}/{r[0]}.mp3')])
print('完成', done, '失敗', fail, '剩下', left)
open('/tmp/left', 'w').write(str(left if time.time() - T0 > BUDGET else 0))
