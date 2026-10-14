# Transfer of film-vs-Portra400 differences between scanners. Run from project root: python3 tools/film_measure/ratio_transfer.py (pure python, reads data/derived/gate1_patches.csv)
import csv,math,random,statistics as st,sys
sys.path.insert(0,'tools/film_measure')
from colorlib import de2000
random.seed(1)
rows=list(csv.DictReader(open('data/derived/gate1_patches.csv')))
T={}
for r in rows:
    try: v=(float(r['L']),float(r['a']),float(r['b']))
    except: continue
    T[(r['scanner'],r['film'],r['ev_or_board'],int(r['row']),int(r['col']))]=v
setof={(r['row'],r['col']):r['set'] for r in rows if r['film']=='Portra400' and r['ev_or_board']=='0' and r['scanner']=='frontier'}
SC=['frontier','noritsu']
FILMS=[('Portra160','1/125'),('Ektar','1/60'),('Ektar30','1/30'),('Ultramax','1/125')]
ref=lambda s,p:T.get((s,'Portra400','0')+p)
allp=[(int(r),int(c)) for (r,c),s in setof.items() if s=='chroma']
allp=sorted(set(allp))
print('chroma patches in reference:',len(allp))
def get(s,f,p): return T.get((s,f[0],f[1])+p)
def pct(x,q):
    x=sorted(x); return x[min(len(x)-1,int(q*len(x)))]
def corr(x,y):
    mx,my=st.mean(x),st.mean(y); sx=math.sqrt(sum((a-mx)**2 for a in x)); sy=math.sqrt(sum((b-my)**2 for b in y))
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/(sx*sy)
def boot(vals,fn,n=500):
    out=[]
    for _ in range(n):
        s=[random.choice(vals) for _ in vals]; out.append(fn(s))
    out.sort(); return out[int(.05*n)],out[int(.95*n)]
# valid patches per film: present in ref both scanners and in film both scanners
def valid(f):
    return [p for p in allp if all(ref(s,p) and get(s,f,p) for s in SC)]
D={}
for f in FILMS:
    for p in valid(f):
        D[(f[0],p)]={s:tuple(get(s,f,p)[i]-ref(s,p)[i] for i in range(3)) for s in SC}
common=[p for p in allp if all((f[0],p) in D for f in FILMS)]
print('valid per film:',{f[0]:len(valid(f)) for f in FILMS},'common',len(common))
def lab_ref(p): # mean ref of both scanners
    return tuple((ref('frontier',p)[i]+ref('noritsu',p)[i])/2 for i in range(3))
out=[]
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.append(s)
for mode in ['ab','Lab']:
    P('\n=== mode',mode,'===')
    for f in FILMS:
        ps=[p for p in common]
        k=(1,2) if mode=='ab' else (0,1,2)
        dF=[D[(f[0],p)]['frontier'] for p in ps]; dN=[D[(f[0],p)]['noritsu'] for p in ps]
        def vec(d): return d[1:] if mode=='ab' else d
        mag=[math.dist(vec(a),vec(b)) for a,b in zip(dF,dN)]
        size=[(math.hypot(*vec(a))+math.hypot(*vec(b)))/2 for a,b in zip(dF,dN)]
        # DE2000 between ref+D1 and ref+D2 (L from ref when ab mode)
        def tr(p,d): r=lab_ref(p); return (r[0]+(0 if mode=='ab' else d[0]), r[1]+d[1], r[2]+d[2])
        de=[de2000(*tr(p,a),*tr(p,b)) for p,a,b in zip(ps,dF,dN)]
        ca=corr([d[1] for d in dF],[d[1] for d in dN]); cb=corr([d[2] for d in dF],[d[2] for d in dN])
        cc=corr([d[1] for d in dF]+[d[2] for d in dF],[d[1] for d in dN]+[d[2] for d in dN])
        P(f"{f[0]:9s} n={len(ps)} corr(da)={ca:.2f} corr(db)={cb:.2f} pooled={cc:.2f} | |D| mean={st.mean(size):.2f} | dE2000(D_Fr vs D_No) med={st.median(de):.2f} p90={pct(de,.9):.2f} | |D_Fr-D_No| med={st.median(mag):.2f}")
        lo,hi=boot(list(range(len(ps))),lambda ix:st.median([de[i] for i in ix])); lo2,hi2=boot(list(range(len(ps))),lambda ix:pct([de[i] for i in ix],.9))
        lo3,hi3=boot(list(range(len(ps))),lambda ix:corr([dF[i][1] for i in ix]+[dF[i][2] for i in ix],[dN[i][1] for i in ix]+[dN[i][2] for i in ix]))
        P(f"          boot90: med dE [{lo:.2f},{hi:.2f}] p90 dE [{lo2:.2f},{hi2:.2f}] pooled corr [{lo3:.2f},{hi3:.2f}]")
    # null: different films across scanners (and same scanner) 
    P('null: D(F1,Frontier) vs D(F2,Noritsu), F1!=F2 (Ektar30 excluded when Ektar present)')
    names=['Portra160','Ektar','Ultramax']
    for i,a in enumerate(names):
        for b in names:
            if a==b: continue
            ps=common
            def vec(d): return d[1:] if mode=='ab' else d
            def tr(p,d): r=lab_ref(p); return (r[0]+(0 if mode=='ab' else d[0]), r[1]+d[1], r[2]+d[2])
            dA=[D[(a,p)]['frontier'] for p in ps]; dB=[D[(b,p)]['noritsu'] for p in ps]
            de=[de2000(*tr(p,x),*tr(p,y)) for p,x,y in zip(ps,dA,dB)]
            cc=corr([d[1] for d in dA]+[d[2] for d in dA],[d[1] for d in dB]+[d[2] for d in dB])
            P(f"  {a:9s}@Fr vs {b:9s}@No: corr={cc:.2f} dE med={st.median(de):.2f} p90={pct(de,.9):.2f}")
    P('same scanner, different films (distinguishability):')
    for s in SC:
        for a,b in [('Ektar','Ultramax'),('Ektar','Portra160'),('Ultramax','Portra160')]:
            def tr(p,d): r=lab_ref(p); return (r[0]+(0 if mode=='ab' else d[0]), r[1]+d[1], r[2]+d[2])
            de=[de2000(*tr(p,D[(a,p)][s]),*tr(p,D[(b,p)][s])) for p in common]
            P(f"  {s}: {a} vs {b}: dE med={st.median(de):.2f} p90={pct(de,.9):.2f}")
# sectors
def lch(a,b): return math.hypot(a,b),math.degrees(math.atan2(b,a))%360
P('\n=== sectors (hue of Portra400 reference, mean of both scanners) ===')
for f in FILMS:
    P(f[0])
    res={}
    for sec in range(6):
        ps=[p for p in common if int(lch(*lab_ref(p)[1:])[1]//60)==sec]
        row={}
        for s in SC:
            hs=[];cr=[]
            for p in ps:
                r=ref(s,p); v=get(s,f,p)
                Cr,hr=lch(r[1],r[2]); Cv,hv=lch(v[1],v[2])
                dh=(hv-hr+180)%360-180; hs.append(dh); cr.append(Cv/Cr)
            row[s]=(st.mean(hs),st.median(cr),hs,cr)
        res[sec]=(len(ps),row)
        if ps:
            P(f"  sec {sec*60:3d}-{sec*60+60:3d} n={len(ps):2d} | Fr dh={row['frontier'][0]:+5.1f}° Cx{row['frontier'][1]:.2f} | No dh={row['noritsu'][0]:+5.1f}° Cx{row['noritsu'][1]:.2f}")
    same=0;tot=0
    for sec,(n,row) in res.items():
        if n<3: continue
        tot+=1
        hF,hN=row['frontier'][0],row['noritsu'][0]; cF,cN=row['frontier'][1],row['noritsu'][1]
        # same sign of hue shift (or both within 1.5deg of 0), chroma ratio on same side of 1 (or both within 3%), magnitudes within factor 2
        sh=(hF*hN>0) or (abs(hF)<1.5 and abs(hN)<1.5)
        sc=((cF-1)*(cN-1)>0) or (abs(cF-1)<.03 and abs(cN-1)<.03)
        mh=max(abs(hF),abs(hN))<1.5 or (min(abs(hF),abs(hN))>0 and max(abs(hF),abs(hN))/min(abs(hF),abs(hN))<=2)
        mc=abs(math.log(cF))<.03 and abs(math.log(cN))<.03 or (abs(math.log(cF))>0 and abs(math.log(cN))>0 and 0.5<=math.log(cF)/math.log(cN)<=2)
        ok=sh and sc and mh and mc
        same+=ok; row['ok']=(sh,sc,mh,mc,ok)
        P(f"    sec {sec*60:3d}: sign_h={sh} sign_c={sc} mag_h(x2)={mh} mag_c(x2)={mc}")
    P(f"  sectors with n>=3 and all four agreeing: {same}/{tot}")
