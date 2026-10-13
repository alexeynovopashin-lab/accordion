import cv2, numpy as np
from find_plates import load, plates
def holes(rgb, bbox, thr=70):
    x,y,w,h=bbox
    g=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)[y:y+h,x:x+w]
    plate=(g<thr).astype(np.uint8)*255
    plate=cv2.morphologyEx(plate,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    inv=255-plate
    n,lab,st,cen=cv2.connectedComponentsWithStats(inv)
    cs=[]
    for i in range(1,n):
        bx,by,bw,bh,a=st[i]
        if 1500<a<9000 and 0.7<bw/bh<1.4 and a/(bw*bh)>0.75: cs.append((cen[i][0]+x,cen[i][1]+y,bw,bh))
    return np.array(cs)
if __name__=='__main__':
    for nm in ['portra400_ev0_frontier.png','portra400_ev0_noritsu.png']:
        rgb=load(nm); lab,pl=plates(rgb)
        for p in pl:
            c=holes(rgb,p[1:5]); print(nm,'plate at',p[1:3],'holes',len(c),'median size',np.median(c[:,2]) if len(c) else None)
