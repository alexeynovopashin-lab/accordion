import sys, math
from PIL import Image
def lin(c): c/=255; return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
def lab(R,G,B):
    r,g,b=lin(R),lin(G),lin(B)
    X=0.4124564*r+0.3575761*g+0.1804375*b; Y=0.2126729*r+0.7151522*g+0.0721750*b; Z=0.0193339*r+0.1191920*g+0.9503041*b
    M=[[1.0478112,0.0228866,-0.0501270],[0.0295424,0.9904844,-0.0170491],[-0.0092345,0.0150436,0.7521316]]
    X,Y,Z=[M[i][0]*X+M[i][1]*Y+M[i][2]*Z for i in range(3)]
    f=lambda t: t**(1/3) if t>216/24389 else (24389/27*t+16)/116
    fx,fy,fz=f(X/0.96422),f(Y),f(Z/0.82521)
    return 116*fy-16,500*(fx-fy),200*(fy-fz)
def de2000(L1,a1,b1,L2,a2,b2):
    C1=math.hypot(a1,b1);C2=math.hypot(a2,b2);Cb=(C1+C2)/2
    G=0.5*(1-math.sqrt(Cb**7/(Cb**7+25**7)))
    a1p=(1+G)*a1;a2p=(1+G)*a2;C1p=math.hypot(a1p,b1);C2p=math.hypot(a2p,b2)
    h1p=math.degrees(math.atan2(b1,a1p))%360;h2p=math.degrees(math.atan2(b2,a2p))%360
    dL=L2-L1;dC=C2p-C1p
    dh=h2p-h1p
    if C1p*C2p==0: dh=0
    elif dh>180: dh-=360
    elif dh<-180: dh+=360
    dH=2*math.sqrt(C1p*C2p)*math.sin(math.radians(dh/2))
    Lb=(L1+L2)/2;Cbp=(C1p+C2p)/2
    if C1p*C2p==0: hb=h1p+h2p
    elif abs(h1p-h2p)<=180: hb=(h1p+h2p)/2
    elif h1p+h2p<360: hb=(h1p+h2p+360)/2
    else: hb=(h1p+h2p-360)/2
    T=1-0.17*math.cos(math.radians(hb-30))+0.24*math.cos(math.radians(2*hb))+0.32*math.cos(math.radians(3*hb+6))-0.20*math.cos(math.radians(4*hb-63))
    Sl=1+0.015*(Lb-50)**2/math.sqrt(20+(Lb-50)**2);Sc=1+0.045*Cbp;Sh=1+0.015*Cbp*T
    dth=30*math.exp(-((hb-275)/25)**2);Rc=2*math.sqrt(Cbp**7/(Cbp**7+25**7));Rt=-math.sin(math.radians(2*dth))*Rc
    return math.sqrt((dL/Sl)**2+(dC/Sc)**2+(dH/Sh)**2+Rt*(dC/Sc)*(dH/Sh))
def sample(im,x,y,r):
    px=[im.getpixel((x+dx,y+dy)) for dx in range(-r,r+1,2) for dy in range(-r,r+1,2)]
    n=len(px); return tuple(sum(p[i] for p in px)/n for i in range(3))
def lch(L,a,b): return L, math.hypot(a,b), math.degrees(math.atan2(b,a))%360
