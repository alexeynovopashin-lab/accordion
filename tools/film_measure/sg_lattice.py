import numpy as np, cv2, sys
pass
from find_plates import load, plates
from holes import holes
from scipy.spatial import cKDTree
import colorlib as m
def lattice(rgb):
    lab,pl=plates(rgb); p=sorted(pl,key=lambda p:p[1])[0]; c=holes(rgb,p[1:5]); pts=c[:,:2]; size=np.median(c[:,2])
    t=cKDTree(pts); d,i=t.query(pts,k=5); v=[]
    for a in range(len(pts)):
        for k in range(1,5):
            if d[a,k]<1.5*np.median(d[:,1]): dv=pts[i[a,k]]-pts[a]; v.append(np.arctan2(dv[1],dv[0]))
    v=np.array(v); ang=np.rad2deg(((v+np.pi/4)%(np.pi/2))-np.pi/4); th=np.deg2rad(np.median(ang))
    R=np.array([[np.cos(th),np.sin(th)],[-np.sin(th),np.cos(th)]]); P=np.median(d[:,1])
    q=pts@R.T
    x0=q[:,0].min(); y0=q[:,1].min()
    ii=np.round((q[:,0]-x0)/P).astype(int); jj=np.round((q[:,1]-y0)/P).astype(int)
    cnt=np.bincount(jj[(ii>=0)&(ii<=13)],minlength=jj.max()+1)
    dense=[k for k in range(len(cnt)) if cnt[k]>=7]
    # first run of 10 consecutive dense rows (SG has 10 rows); tolerate the bottom row being sparse
    j0=dense[0]
    for k in dense:
        if all(cnt[kk]>=5 for kk in range(k,min(k+9,len(cnt)))) : j0=k; break
    y0=y0+j0*P; jj=jj-j0
    ok=(ii>=0)&(ii<=13)&(jj>=0)&(jj<=9)
    print('rows count',cnt.tolist(),'j0',j0)

    # refine origin by least squares on accepted holes
    x0=np.mean(q[ok,0]-ii[ok]*P); y0=np.mean(q[ok,1]-jj[ok]*P)
    cen=np.zeros((10,14,2)); 
    for j in range(10):
        for i2 in range(14):
            cen[j,i2]=np.array([x0+i2*P,y0+j*P])@R   # back to image coords (R orthonormal: q=pts@R.T -> pts=q@R)
    return cen,size,P,th,int(ok.sum())
def sample(rgb,cen,size,half=0.22):
    h=int(size*half); out=np.zeros((10,14,3))
    for j in range(10):
        for i in range(14):
            x,y=cen[j,i].round().astype(int); r=rgb[y-h:y+h+1,x-h:x+h+1].reshape(-1,3)
            out[j,i]=np.median(r,0)
    return out
def overlay(rgb,cen,size,path):
    im=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR).copy()
    h=int(size*0.22)
    for j in range(10):
        for i in range(14):
            x,y=cen[j,i].round().astype(int); cv2.rectangle(im,(x-h,y-h),(x+h,y+h),(0,255,255),2)
    x0=int(cen[:,:,0].min()-80); x1=int(cen[:,:,0].max()+80); y0=int(cen[:,:,1].min()-80); y1=int(cen[:,:,1].max()+80)
    cv2.imwrite(path,cv2.resize(im[y0:y1,x0:x1],None,fx=0.6,fy=0.6))
if __name__=='__main__':
    for nm,tag in [('portra400_ev0_frontier.png','fr'),('portra400_ev0_noritsu.png','no')]:
        rgb=load(nm); cen,size,P,th,n=lattice(rgb); print(nm,'pitch %.1f rot %.2f holes used %d'%(P,np.rad2deg(th),n))
        overlay(rgb,cen,size,f'ov_{tag}.png'); np.save(f'cen_{tag}.npy',cen); np.save(f'rgb_{tag}.npy',sample(rgb,cen,size))
