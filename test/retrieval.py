import os

from aws.retrieval import Retrieval
from aws.data import Profiles

try:
    from IPython import get_ipython
    ip = get_ipython()
    ip.magic("%load_ext autoreload")
    ip.magic("%autoreload 2")
except:
    pass

try:
    path = os.path.dirname(__file__)
except:
    path = "."

data_provider = Profiles(os.path.join(path, "..", "data", "test_data.mat"))

retrieval.setup()
retrieval = Retrieval(data_provider)