import numpy as np, os, sys
pass
import colorlib as m
from PIL import Image
def lin(a): a=a/255.0; return np.where(a<=0.04045,a/12.92,((a+0.055)/1.055)**2.4)
def enc(l): l=np.clip(l,0,1); return 255*np.where(l<=0.0031308,12.92*l,1.055*l**(1/2.4)-0.055)
def tolab(rgb): return np.array([m.lab(*p) for p in rgb.reshape(-1,3)]).reshape(rgb.shape)
def de(A,B): return np.array([m.de2000(*a,*b) for a,b in zip(A.reshape(-1,3),B.reshape(-1,3))])
C=lambda L: np.hypot(L[...,1],L[...,2])
U=os.environ.get('MIDDLEBURY','data/raw/checker140')+'/'   # Middlebury 'checker140' (smoothed) folder
cams=['NikonD3','NikonD300','CanonEOS5D','FujifilmFinePixS5Pro','SonyDSLR-A100','LeicaM8']
def patches(path,linear):
    a=np.asarray(Image.open(path).convert('RGB')).astype(float); out=np.zeros((10,14,3))
    for j in range(10):
        for i in range(14):
            cy=int((j+.5)*33); cx=int((i+.5)*33); out[j,i]=np.median(a[cy-7:cy+8,cx-7:cx+8].reshape(-1,3),0)
    # linear data -> linear light fraction; sRGB-encoded -> decode
    return out/255.0 if linear else lin(out)      # returns linear light 0..1
fr=np.load('rgb_fr.npy'); no=np.load('rgb_no.npy'); lf=lin(fr); ln=lin(no)
Lf=tolab(fr); Ln=tolab(no)
neu=(C(Ln)<7)&(Ln[...,0]>12)&(C(Lf)<12)
valid=(Ln[...,0]>15)
chrom=valid&(~neu)&(C(Ln)>12)
def curve(x,y):
    o=np.argsort(x); x=np.r_[0,x[o]]; y=np.r_[0,y[o]]; y=np.maximum.accumulate(y)
    ux,ix=np.unique(x,return_index=True); x=ux; y=y[ix]
    sl=(y[-1]-y[-2])/max(x[-1]-x[-2],1e-6)
    return lambda v: np.where(v<=x[-1],np.interp(v,x,y),y[-1]+sl*(v-x[-1]))
def neutralise(l,mask,tgt):
    return np.stack([curve(l[mask][:,c],tgt)(l[...,c]) for c in range(3)],-1)
tgt=ln[neu][:,1]
systems={'Film Frontier':lf,'Film Noritsu':ln}
for c in cams:
    for kind,lin_flag in [('raw',True),('jpg',False)]:
        try: systems[f'{c} {kind}']=patches(f'{U}{c}/wb1i1e3-{kind}.png',lin_flag)
        except Exception as e: print('skip',c,kind,e)
NS={k:neutralise(v,neu,tgt) for k,v in systems.items()}
def colour_only(A,B,mask):
    LA=tolab(enc(A)); LB=tolab(enc(B)); LA[...,0]=LB[...,0]; return de(LA[mask],LB[mask])
ref=NS['Film Noritsu']
print('ΔE2000 (colour only, lightness equalised) vs Film Noritsu, grey ramp matched; chromatic patches n=%d'%chrom.sum())
rows=[]
for k in NS:
    d_raw=de(tolab(enc(systems[k]))[chrom],Ln[chrom]); d=colour_only(NS[k],ref,chrom)
    rows.append((k,np.median(d_raw),np.median(d),np.percentile(d,90)))
    print('  %-28s raw %.1f   normalised %.1f   p90 %.1f'%rows[-1])
# spread between all systems after normalisation: pairwise medians
keys=list(NS); n=len(keys); M=np.zeros((n,n))
for a in range(n):
    for b in range(n): M[a,b]=np.median(colour_only(NS[keys[a]],NS[keys[b]],chrom)) if a!=b else 0
print('\nmedian pairwise ΔE colour-only after grey ramp matching (rows/cols):')
short=[k.replace('Film ','F-').replace('FujifilmFinePixS5Pro','FujiS5').replace('SonyDSLR-A100','A100').replace('CanonEOS5D','5D').replace('NikonD300','D300').replace('NikonD3','D3').replace('LeicaM8','M8') for k in keys]
print(' '*14+' '.join('%7s'%s[:7] for s in short))
for a in range(n): print('%-14s'%short[a][:14]+' '.join('%7.1f'%M[a,b] for b in range(n)))
# digital cams only vs film only: mean of cross distances vs within-digital
dig=[i for i,k in enumerate(keys) if 'raw' in k]; jp=[i for i,k in enumerate(keys) if 'jpg' in k]; fl=[0,1]
def avg(I,J): return np.mean([M[a,b] for a in I for b in J if a!=b])
print('\nmean ΔE: raw-cam vs raw-cam %.1f | jpg-cam vs jpg-cam %.1f | film vs raw-cam %.1f | film vs jpg-cam %.1f | raw vs jpg same camera %.1f'%(avg(dig,dig),avg(jp,jp),avg(fl,dig),avg(fl,jp),np.mean([M[keys.index(c+' raw'),keys.index(c+' jpg')] for c in cams])))
# hue-family behaviour: film (Noritsu) vs average of digital raw, chroma ratio
Lnn=Ln; hn=np.degrees(np.arctan2(Ln[...,2],Ln[...,1]))%360
Cr=[]; 
for k in keys:
    if 'raw' in k: Lk=tolab(enc(NS[k])); Cr.append(C(Lk))
Cdig=np.mean(Cr,0)
print('\nfilm(Noritsu, grey-matched) vs mean of 6 raw cameras (grey-matched): chroma ratio film/digital and hue shift')
Lfd=[tolab(enc(NS[k])) for k in keys if 'raw' in k]
hd=np.degrees(np.arctan2(np.mean([x[...,2] for x in Lfd],0),np.mean([x[...,1] for x in Lfd],0)))%360
dh=((hn-hd+180)%360)-180
for lo,hi,nm in [(0,45,'red-orange'),(45,100,'yellow'),(100,180,'green'),(180,260,'cyan-blue'),(260,330,'violet'),(330,360,'magenta-red')]:
    s=chrom&(hn>=lo)&(hn<hi)
    if s.sum()>=2: print('  %-12s n=%2d  C ratio %.2f   hue shift %+.1f deg'%(nm,s.sum(),np.median(C(Ln)[s]/Cdig[s]),np.median(dh[s])))
