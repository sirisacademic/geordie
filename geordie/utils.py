import os
import pickle
import pandas as pd

def cache_new_results(new_results):

    # Checking if tmp_cache already exists, in which case we just update it.
    fpath = 'geordie/data/tmp_cache.pkl'
    if os.path.isfile(fpath):
        tmp_cache=pd.read_pickle(fpath)
        tmp_cache.update(new_results)
        
        with open(fpath, 'wb') as handle:
            pickle.dump(tmp_cache, handle, protocol=pickle.HIGHEST_PROTOCOL)
        return
    
    # Otherwise, tmp_cache is created and updated with first results.
    else:
        with open(fpath, 'wb') as handle:
            pickle.dump(new_results, handle, protocol=pickle.HIGHEST_PROTOCOL)
        return