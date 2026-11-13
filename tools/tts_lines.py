import os
os.makedirs('audio',exist_ok=True)
import json,re,collections
src=open('index.html',encoding='utf-8').read()
def chunks(t,l):
  en=l.startswith('en')
  for x in re.split(r'(?<=[!?])\s+' if en else r'(?<=[。！？；])',t):
    if x.strip(): yield x
items={}  # key -> 1 固定句子；2 隨機出題抽到的句子
def add(t,l,w='',src=1):
  l=l or 'zh-TW'
  for x in chunks(str(t),l):
    k=(x.strip(),l,w)
    if not re.search(r'[\w一-鿿]',k[0]): continue
    items[k]=min(items.get(k,src),src)
# 固定的句子（介面、主角、故事、好朋友…）排在前面先做；隨機出題抽到的句子排後面，額度不夠時先做固定的
for t,l,w in json.load(open('/tmp/tts_raw2.json')): add(t,l,w)
d=json.load(open('/tmp/tts_raw1.json'))
for x in d['out']:
  if x[0]=='P': add(x[1],x[2],'',2)
for t,l in d['spk']: add(t,l,'',2)
if os.path.exists('/tmp/tts_raw3.json'):
  for t,l,w in json.load(open('/tmp/tts_raw3.json')): add(t,l,w)
# 有數字的句子：再把「數字」和「數字中間的字」分開做，題目數字怎麼變都能用 AI 聲音拼起來念
for (t,l,w) in list(items):
  if re.search(r'\d',t):
    for x in re.split(r'(\d+)',t):
      x=x.strip()
      if re.search(r'[\w一-鿿]',x): items[(x,l,w)]=1
for n in range(0,1001): items[(str(n),'zh-TW','')]=1
# literals on lines that call say(
for line in src.split('\n'):
  if 'say(' not in line: continue
  for seg in re.findall(r'say\((.{0,600})',line):
    for a,b2 in re.findall(r"'([^'\n$`]{1,200})'(\s*,\s*'en-US')?",seg):
      if re.search(r'[一-鿿]',a) and '<' not in a: add(a,'zh-TW')
      elif b2 and re.search(r'[A-Za-z]',a): add(a,'en-US')
VO={'':('zh-TW-HsiaoChenNeural','zh-TW','-5%','0%'),'en':('en-US-AnaNeural','en-US','-10%','0%'),
 'b1':('zh-CN-YunxiaNeural','zh-CN','0%','0%'),'g1':('zh-CN-XiaoshuangNeural','zh-CN','0%','0%'),
 'b2':('zh-TW-YunJheNeural','zh-TW','-3%','+8%'),'g2':('zh-TW-HsiaoChenNeural','zh-TW','+8%','+18%'),
 'b3':('zh-CN-YunxiaNeural','zh-CN','-5%','-5%'),'g3':('zh-CN-XiaoshuangNeural','zh-CN','-8%','-5%'),
 'mom':('zh-TW-HsiaoYuNeural','zh-TW','-5%','0%'),'tch':('zh-TW-HsiaoChenNeural','zh-TW','-8%','-3%'),'dad':('zh-TW-YunJheNeural','zh-TW','-5%','-8%'),
 'sleep':('zh-TW-HsiaoChenNeural','zh-TW','-22%','-4%'),'hero':('zh-CN-YunxiaNeural','zh-CN','-5%','+5%'),
 'jin':('zh-TW-HsiaoYuNeural','zh-TW','-10%','-8%'),'ma':('zh-TW-HsiaoChenNeural','zh-TW','-18%','-22%'),'niu':('zh-TW-YunJheNeural','zh-TW','-10%','-18%')}
M=(1<<32)-1
def imul(a,b): return (a*b)&M
def cyrb53(s,seed=0):
  h1=0xdeadbeef^seed; h2=0x41c6ce57^seed
  for ch in s.encode('utf-16-le').decode('utf-16-le'):
    pass
  units=[]
  for ch in s:
    o=ord(ch)
    if o>0xFFFF: o-=0x10000; units+= [0xD800+(o>>10),0xDC00+(o&0x3FF)]
    else: units.append(o)
  for c in units:
    h1=imul(h1^c,2654435761); h2=imul(h2^c,1597334677)
  h1=imul(h1^(h1>>16),2246822507); h1^=imul(h2^(h2>>13),3266489909)
  h2=imul(h2^(h2>>16),2246822507); h2^=imul(h1^(h1>>13),3266489909)
  return 4294967296*(2097151&h2)+(h1&M)
def b36(n):
  s=''
  while n: s='0123456789abcdefghijklmnopqrstuvwxyz'[n%36]+s; n//=36
  return s or '0'
# 隨機出題抽到的新句子（數字、顏色組合幾千種）每次上傳最多只做 RAND_NEW 字，避免吃光每月額度；
# 已經做好的照樣保留。網站只會出「有 AI 語音」的題目，沒做到的組合不會出現。
try: DONE=set(json.load(open('audio/v/index.json')))
except Exception: DONE=set()
RAND_NEW=int(os.environ.get('RAND_NEW','4000')); rand_used=0; rand_skip=0
rows=[];ids={};chars=collections.Counter()
for (t,l,w) in sorted(items, key=lambda k:(items[k],k)):
  key=f'{w}|{l}|{t}'; i=b36(cyrb53(key))
  if items[(t,l,w)]==2 and i not in DONE:
    if rand_used+len(t)>RAND_NEW: rand_skip+=1; continue
    rand_used+=len(t)
  if i in ids: print('COLLIDE',key,ids[i]); continue
  ids[i]=key
  v=VO[w] if w else (VO['en'] if l.startswith('en') else VO[''])
  rows.append([i,v[0],v[1],t,v[2],v[3]]); chars[w or l]+=len(t)
json.dump(rows,open('audio/lines.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(len(rows),sum(len(r[3]) for r in rows),dict(chars))
print('隨機新句子：這次做',rand_used,'字，略過',rand_skip,'句')
