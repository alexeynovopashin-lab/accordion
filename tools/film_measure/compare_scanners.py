import numpy as np, sys
pass
import colorlib as m
def lin(a): a=a/255.0; return np.where(a<=0.04045,a/12.92,((a+0.055)/1.055)**2.4)
def enc(l): l=np.clip(l,0,1); return 255*np.where(l<=0.0031308,12.92*l,1.055*l**(1/2.4)-0.055)
def tolab(rgb): return np.array([m.lab(*p) for p in rgb.reshape(-1,3)]).reshape(rgb.shape)
def de(A,B): return np.array([m.de2000(*a,*b) for a,b in zip(A.reshape(-1,3),B.reshape(-1,3))])
fr=np.load('rgb_fr.npy'); no=np.load('rgb_no.npy'); Lf=tolab(fr); Ln=tolab(no)
C=lambda L: np.hypot(L[...,1],L[...,2])
# the grey patches of SG are the ones that are near-neutral in at least the better-behaved scan
neu=(C(Ln)<7)&(Ln[...,0]>12)&(C(Lf)<12)
print('neutral patches',int(neu.sum()))
o=np.argsort(Ln[...,0][neu]); idx=np.argwhere(neu)[o]
print('  L(N)  L(F) | N: a b | F: a b')
for j,i in idx[::max(1,len(idx)//12)]: print('  %4.0f %4.0f | %+5.1f %+5.1f | %+5.1f %+5.1f'%(Ln[j,i,0],Lf[j,i,0],Ln[j,i,1],Ln[j,i,2],Lf[j,i,1],Lf[j,i,2]))
ln=lin(no); lf=lin(fr)
def curve(x,y):
    o=np.argsort(x); x=np.r_[0,x[o]]; y=np.r_[0,y[o]]; y=np.maximum.accumulate(y)
    # merge duplicates
    ux,ix=np.unique(x,return_index=True); x=ux; y=y[ix]
    sl=(y[-1]-y[-2])/max(x[-1]-x[-2],1e-6)
    return lambda v: np.where(v<=x[-1],np.interp(v,x,y),y[-1]+sl*(v-x[-1]))
tgt=ln[neu][:,1]                        # Noritsu grey level (G channel) at each neutral
fr_n=np.stack([curve(lf[neu][:,c],tgt)(lf[...,c]) for c in range(3)],-1)   # Frontier curves -> Noritsu grey ramp
no_n=ln.copy()
valid=(Lf[...,0]>15)&(Ln[...,0]>15)
chrom=valid&(~neu)&(C(Ln)>12)
def rep(nm,A,B,mask):
    d=de(A[mask],B[mask]); print('%-44s n=%3d median %.2f mean %.2f p90 %.2f'%(nm,mask.sum(),np.median(d),d.mean(),np.percentile(d,90))); return d
print('\n--- chromatic patches only (C>12), neutrals NOT in the error ---')
rep('raw',Lf,Ln,chrom)
Lfn=tolab(enc(fr_n)); Lnn=Ln
rep('Frontier curves matched to Noritsu grey ramp',Lfn,Lnn,chrom)
Lfc=Lfn.copy(); Lfc[...,0]=Lnn[...,0]
dd=rep('...and lightness forced equal (colour only)',Lfc,Lnn,chrom)
# diag WB only (single gain from the mid neutrals) for comparison
mid=neu&(Ln[...,0]>45)&(Ln[...,0]<80)
g=np.array([np.median(lf[mid][:,1]/lf[mid][:,0]),1,np.median(lf[mid][:,1]/lf[mid][:,2])])
Lw=tolab(enc(np.clip(lf*g,0,1))); 
sc=np.median(ln[mid][:,1]/(lf*g)[mid][:,1]); Lw2=tolab(enc(np.clip(lf*g*sc,0,1)))
rep('single WB gain + exposure scale (mid greys)',Lw2,Ln,chrom)
# chroma ratio per hue: is it saturation or hue?
Cf=C(Lfn); Cn=C(Ln); hf=np.degrees(np.arctan2(Lfn[...,2],Lfn[...,1]))%360; hn=np.degrees(np.arctan2(Ln[...,2],Ln[...,1]))%360
dh=((hf-hn+180)%360)-180
print('\nafter grey-ramp match: chroma ratio F/N and hue shift (F-N) by hue family')
for lo,hi,nm in [(0,45,'red-orange'),(45,100,'yellow'),(100,180,'green'),(180,260,'cyan-blue'),(260,330,'violet'),(330,360,'magenta-red')]:
    s=chrom&(hn>=lo)&(hn<hi)
    if s.sum()>=2: print('  %-12s n=%2d  C ratio %.2f   hue shift %+.1f deg   dE(colour only) %.1f'%(nm,s.sum(),np.median(Cf[s]/Cn[s]),np.median(dh[s]),np.median(de(Lfc[s],Lnn[s]))))
np.save('Lfn.npy',Lfn)
