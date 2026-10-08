from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image
from core.photo_intelligence import analyse_image, hamming_distance, _phash
from image.loader import is_supported, load_image

def rank_photos(paths):
    rows=[]
    for p in paths:
        try:
            a=analyse_image(p)
            rows.append({"path":str(p),"score":a.quality_score,"faces":a.faces,"sharpness":a.sharpness,"exposure":a.exposure_score})
        except Exception: pass
    rows.sort(key=lambda x:(x["score"],x["sharpness"],x["exposure"]),reverse=True)
    return rows

def find_duplicate_groups(paths,threshold=7):
    hashes=[]; groups=[]
    for p in paths:
        try: hashes.append((p,_phash(load_image(p))))
        except Exception: continue
    used=set()
    for i,(p,h) in enumerate(hashes):
        if i in used: continue
        group=[p]; used.add(i)
        for j in range(i+1,len(hashes)):
            if j not in used and hamming_distance(h,hashes[j][1])<=threshold:
                group.append(hashes[j][0]);used.add(j)
        if len(group)>1: groups.append(group)
    return groups
