import cv2, numpy as np, io, os, sys
from PIL import Image, ImageCms
U=os.environ.get('CHARTS_EXTRACT','data/raw/charts_extract')+'/'   # folder made by extract_pdfs.py (+ charts.icc)
icc=ImageCms.ImageCmsProfile(io.BytesIO(open(U+'charts.icc','rb').read())); srgb=ImageCms.createProfile('sRGB')
def load(name):
    im=Image.open(U+name).convert('RGB')
    return np.asarray(ImageCms.profileToProfile(im,icc,srgb,outputMode='RGB'))
def plates(rgb):
    g=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    m=(g<70).astype(np.uint8)*255
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((15,15),np.uint8))
    n,lab,st,cen=cv2.connectedComponentsWithStats(m)
    out=[]
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if a>150000 and w>600 and h>400: out.append((i,x,y,w,h,a))
    return lab,out
if __name__=='__main__':
    for nm in ['portra400_ev0_frontier.png','portra400_ev0_noritsu.png']:
        rgb=load(nm); lab,out=plates(rgb); print(nm,rgb.shape); 
        for o in out: print('  plate',o)
