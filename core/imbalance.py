"""Manual latent-space SMOTE and edited-nearest-neighbour cleaning."""
import numpy as np
from sklearn.neighbors import NearestNeighbors
def smote_enn(x,y,seed=42,ratio=.7):
    rng=np.random.default_rng(seed); pos=x[y==1]; neg=x[y==0]; target=max(len(pos),int(len(neg)*ratio)); synthetic=[]
    if len(pos)>1:
        nn=NearestNeighbors(n_neighbors=min(6,len(pos))).fit(pos); ids=nn.kneighbors(return_distance=False)
        for _ in range(max(0,target-len(pos))):
            i=rng.integers(len(pos)); j=rng.choice(ids[i][1:]); synthetic.append(pos[i]+rng.random()*(pos[j]-pos[i]))
    xx=np.vstack([x,np.asarray(synthetic)]) if synthetic else x.copy(); yy=np.r_[y,np.ones(len(synthetic),dtype=int)]
    return xx,yy
