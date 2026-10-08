from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import numpy as np
import cv2
from PIL import Image
from .runtime import device
from .model_manager import ModelManager

@dataclass
class Detection:
    label:str
    confidence:float
    box:tuple[float,float,float,float]

@dataclass
class AIAnalysis:
    scene:str="Unknown"
    detections:list[Detection]|None=None
    faces:int=0
    subject_box:tuple[float,float,float,float]|None=None
    sky_fraction:float=0.0
    quality_score:float=0.0
    sharpness:float=0.0
    noise_score:float=0.0
    exposure_score:float=0.0
    composition_score:float=0.0
    suggestions:list[dict[str,Any]]|None=None
    backend:str="heuristic"

def _rgb(image):
    return np.asarray(image.convert("RGB") if hasattr(image,"convert") else Image.open(image).convert("RGB"))

def quality_analysis(image)->dict[str,float]:
    a=_rgb(image); gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY).astype(np.float32)
    lap=float(cv2.Laplacian(gray,cv2.CV_32F).var())
    sharp=float(np.clip(100*np.log1p(lap)/np.log1p(900),0,100))
    noise=float(np.clip(100/(1+np.std(cv2.GaussianBlur(gray,(3,3),0)-gray)),0,100))
    mean=float(gray.mean()); under=float((gray<10).mean()); over=float((gray>245).mean())
    exposure=float(np.clip(100*(1-abs(mean-128)/128)*(1-min(1,under+over)),0,100))
    gx=cv2.Sobel(gray,cv2.CV_32F,1,0); gy=cv2.Sobel(gray,cv2.CV_32F,0,1)
    edge=np.hypot(gx,gy); composition=float(np.clip(np.percentile(edge,75)/2.4,0,100))
    total=sharp*.42+exposure*.35+noise*.08+composition*.15
    return {"quality_score":float(total),"sharpness":sharp,"noise_score":noise,"exposure_score":exposure,"composition_score":composition}

def detect_sky(image)->np.ndarray:
    a=_rgb(image); hsv=cv2.cvtColor(a,cv2.COLOR_RGB2HSV)
    h,s,v=cv2.split(hsv); top=np.zeros(h.shape,np.uint8)
    blue=((h>=85)&(h<=135)&(s>25)&(v>70))
    top[:max(1,int(h.shape[0]*.55))]=blue[:max(1,int(h.shape[0]*.55))].astype(np.uint8)*255
    # keep only components connected to the upper edge
    n,labels,stats,_=cv2.connectedComponentsWithStats(top)
    mask=np.zeros_like(top)
    for i in range(1,n):
        x,y,w,hh,area=stats[i]
        if y<=2 and area>max(30,top.size//5000): mask[labels==i]=255
    return cv2.GaussianBlur(mask,(0,0),1.2)

def analyze_image(image, use_ai=True)->AIAnalysis:
    q=quality_analysis(image); sky=float(detect_sky(image).mean()/255)
    result=AIAnalysis(**q,sky_fraction=sky,suggestions=[])
    a=_rgb(image)
    gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
    face=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    boxes=face.detectMultiScale(gray,1.1,5,minSize=(28,28))
    result.faces=len(boxes)
    detections=[]
    if use_ai:
        try:
            model=ModelManager().load_detector()
            r=model(a,device=device(),verbose=False)[0]
            names=r.names
            if r.boxes is not None:
                for b in r.boxes:
                    conf=float(b.conf[0])
                    if conf<0.30: continue
                    xyxy=[float(x) for x in b.xyxy[0]]
                    detections.append(Detection(str(names[int(b.cls[0])]),conf,
                        (xyxy[0]/a.shape[1],xyxy[1]/a.shape[0],xyxy[2]/a.shape[1],xyxy[3]/a.shape[0])))
            result.backend="yolo+opencv"
        except Exception:
            result.backend="opencv"
    result.detections=detections
    if detections:
        ranked=sorted(detections,key=lambda x:x.conf*(x.box[2]-x.box[0])*(x.box[3]-x.box[1]),reverse=True)
        result.subject_box=ranked[0].box
    elif len(boxes):
        x,y,w,h=max(boxes,key=lambda z:z[2]*z[3]); result.subject_box=(x/a.shape[1],y/a.shape[0],(x+w)/a.shape[1],(y+h)/a.shape[0])
    # Deterministic scene estimate when a VLM is not installed.
    sat=float(cv2.cvtColor(a,cv2.COLOR_RGB2HSV)[...,1].mean())
    result.scene="Landscape" if sky>.08 else ("Portrait" if len(boxes) else ("Low light" if q["exposure_score"]<45 else "General"))
    if q["exposure_score"]<65: result.suggestions.append({"type":"exposure","value":float(np.clip((50-q["exposure_score"])*.55,-25,25))})
    if q["sharpness"]<45: result.suggestions.append({"type":"sharpening","value":12.0})
    if sky>.08: result.suggestions.append({"type":"sky_mask","value":sky})
    if sat<45: result.suggestions.append({"type":"vibrance","value":8.0})
    return result

def analysis_dict(result:AIAnalysis)->dict:
    d=asdict(result); d["detections"]=[asdict(x) for x in (result.detections or [])]; return d
