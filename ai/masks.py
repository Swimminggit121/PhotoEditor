from __future__ import annotations
import numpy as np, cv2
from .analysis import detect_sky, _rgb
from .model_manager import ModelManager
from .runtime import device

def sky_mask(image)->np.ndarray:
    return detect_sky(image)

def subject_mask(image)->np.ndarray:
    a=_rgb(image)
    try:
        model=ModelManager().load_detector()
        r=model(a,device=device(),verbose=False)[0]
        if r.masks is not None and len(r.masks.data):
            scores=[float(x) for x in r.boxes.conf]
            i=int(np.argmax(scores)); m=r.masks.data[i].cpu().numpy()
            return cv2.resize((m>0.35).astype(np.uint8)*255,(a.shape[1],a.shape[0]),interpolation=cv2.INTER_NEAREST)
    except Exception: pass
    # Safe fallback: GrabCut around the visual centre.
    mask=np.full((a.shape[0],a.shape[1]),cv2.GC_PR_BGD,np.uint8)
    h,w=mask.shape; margin=max(2,int(min(h,w)*.08)); mask[margin:h-margin,margin:w-margin]=cv2.GC_PR_FGD
    bgd=np.zeros((1,65),np.float64); fgd=np.zeros((1,65),np.float64)
    cv2.grabCut(a,mask,(margin,margin,w-2*margin,h-2*margin),bgd,fgd,4,cv2.GC_INIT_WITH_RECT)
    return np.where((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD),255,0).astype(np.uint8)

def mask_to_local_adjustment(mask,name="AI Subject"):
    return {"name":name,"type":"ai","mask":mask.tolist(),"invert":False,"feather":8,"density":1.0,
            "local":{"exposure":0.0,"contrast":0.0,"temperature":0.0,"saturation":0.0}}
