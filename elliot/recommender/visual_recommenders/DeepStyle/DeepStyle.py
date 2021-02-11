"""
Module description:

"""

__version__ = '0.1'
__author__ = 'Vito Walter Anelli, Claudio Pomo, Daniele Malitesta'
__email__ = 'vitowalter.anelli@poliba.it, claudio.pomo@poliba.it, daniele.malitesta@poliba.it'

from evaluation.evaluator import Evaluator
from utils.folder import build_model_folder

import logging as log
from utils import logging
import os

import numpy as np
import tensorflow as tf

from recommender.visual_recommenders.visual_mixins.visual_loader_mixin import VisualLoader
from recommender.latent_factor_models.NNBPRMF.NNBPRMF import NNBPRMF
from recommender.visual_recommenders.DeepStyle.DeepStyle_model import DeepStyle_model

np.random.seed(0)
tf.random.set_seed(0)
log.disable(log.WARNING)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


class DeepStyle(NNBPRMF, VisualLoader):

    def __init__(self, data, config, params, *args, **kwargs):
        super().__init__(data, config, params, *args, **kwargs)
        np.random.seed(42)

        self._params.name = self.name

        self.autoset_params()

        item_indices = [self._data.item_mapping[self._data.private_items[item]] for item in range(self._num_items)]

        self._model = DeepStyle_model(self._params.embed_k,
                                      self._params.lr,
                                      self._params.l_w,
                                      self._data.visual_features[item_indices],
                                      self._data.visual_features.shape[1],
                                      self._num_users,
                                      self._num_items)

        self.evaluator = Evaluator(self._data, self._params)
        self._params.name = self.name
        build_model_folder(self._config.path_output_rec_weight, self.name)
        self._saving_filepath = f'{self._config.path_output_rec_weight}{self.name}/best-weights-{self.name}'
        self.logger = logging.get_logger(self.__class__.__name__)

    @property
    def name(self):
        return "DeepStyle" \
               + "_e:" + str(self._epochs) \
               + "_bs:" + str(self._batch_size) \
               + f"_{self.get_params_shortcut()}"
