"""
Module description:

"""


__version__ = '0.1'
__author__ = 'Vito Walter Anelli, Claudio Pomo, Daniele Malitesta, Antonio Ferrara'
__email__ = 'vitowalter.anelli@poliba.it, claudio.pomo@poliba.it,' \
            'daniele.malitesta@poliba.it, antonio.ferrara@poliba.it'

import pickle
import time

import numpy as np
from tqdm import tqdm

from elliot.dataset.samplers import pointwise_pos_neg_ratings_sampler as pws
from elliot.recommender import test_item_only_filter
from elliot.recommender.base_recommender_model import BaseRecommenderModel
from elliot.recommender.latent_factor_models.FM.factorization_machine_model import FactorizationMachineModel
from elliot.recommender.recommender_utils_mixin import RecMixin
from elliot.utils.write import store_recommendation
from elliot.recommender.base_recommender_model import init_charger
np.random.seed(42)


class FM(RecMixin, BaseRecommenderModel):
    r"""
    Factorization Machines

    For further details, please refer to the `paper <https://ieeexplore.ieee.org/document/5694074>`_

    Args:
        factors: Number of factors of feature embeddings
        lr: Learning rate
        reg: Regularization coefficient
        mf_simplification: mode to avoid involving features in pairwise interactions (much faster)

    To include the recommendation model, add it to the config file adopting the following pattern:

    .. code:: yaml

      models:
        FM:
          meta:
            save_recs: True
          epochs: 10
          batch_size: 512
          factors: 10
          lr: 0.001
          reg: 0.1
          mf_simplification: True
    """

    @init_charger
    def __init__(self, data, config, params, *args, **kwargs):
        self._random = np.random

        self._params_list = [
            ("_factors", "factors", "factors", 10, None, None),
            ("_learning_rate", "lr", "lr", 0.001, None, None),
            ("_l_w", "reg", "reg", 0.1, None, None),
            ("_simplify", "mf_simplification", "mf", False, None, None)
        ]
        self.autoset_params()

        if self._batch_size < 1:
            self._batch_size = self._data.transactions

        self._ratings = self._data.train_dict
        self._sp_i_train = self._data.sp_i_train
        self._i_items_set = list(range(self._num_items))

        if ((not self._simplify) and hasattr(self._data, "nfeatures")) and (hasattr(self._data, "side_information_data")) and (hasattr(self._data.side_information_data, "feature_map")):
            self._nfeatures = self._data.nfeatures
            self._item_array = self.get_item_fragment()
        else:
            self._nfeatures = 0

        self._field_dims = [self._num_users, self._num_items, self._nfeatures]

        self._sampler = pws.Sampler(self._data.i_train_dict, self._data.sp_i_train_ratings)

        self._model = FactorizationMachineModel(self._num_users, self._num_items, self._nfeatures, self._factors,
                                                self._l_w, self._learning_rate)


    @property
    def name(self):
        return "FM" \
               + "_e:" + str(self._epochs) \
               + "_bs:" + str(self._batch_size) \
               + f"_{self.get_params_shortcut()}"

    def predict(self, u: int, i: int):
        pass

    def train(self):
        if self._restore:
            return self.restore_weights()

        best_metric_value = 0
        for it in range(self._epochs):
            loss = 0
            steps = 0
            with tqdm(total=int(self._data.transactions // self._batch_size), disable=not self._verbose) as t:
                for batch in self._sampler.step(self._data.transactions, self._batch_size):
                    steps += 1
                    if self._nfeatures:
                        prepared_batch = self.prepare_fm_transaction(batch)
                        loss += self._model.train_step(prepared_batch)
                    else:
                        u,i,r = batch
                        loss += self._model.train_step(((u, i), r))
                    t.set_postfix({'loss': f'{loss.numpy() / steps:.5f}'})
                    t.update()

            if not (it + 1) % self._validation_rate:
                recs = self.get_recommendations(self.evaluator.get_needed_recommendations())
                result_dict = self.evaluator.eval(recs)
                self._results.append(result_dict)

                time.sleep(1)
                print(f'Epoch {(it + 1)}/{self._epochs} loss {loss  / steps:.3f}')

                if self._results[-1][self._validation_k]["val_results"][self._validation_metric] > best_metric_value:
                    print("******************************************")
                    best_metric_value = self._results[-1][self._validation_k]["val_results"][self._validation_metric]
                    if self._save_weights:
                        self._model.save_weights(self._saving_filepath)
                    if self._save_recs:
                        store_recommendation(recs, self._config.path_output_rec_result + f"{self.name}-it:{it + 1}.tsv")

    def prepare_fm_transaction(self, batch):
        batch_users = np.array(batch[0])
        user_array = np.zeros((batch_users.size, self._num_users), dtype=np.float32)
        user_array[np.arange(batch_users.size), batch_users] = 1
        return np.hstack((user_array, self._item_array[batch[1]])), batch[2]

    def get_item_fragment(self):
        transactions = []

        for item in range(self._num_items):
            item_oh = np.zeros(self._num_items, dtype=np.float32)  # item one-hot encoding
            item_oh[item] = 1
            if self._nfeatures:
                feature_oh = np.zeros(self._data.nfeatures, dtype=np.float32)  # feature(s) one-hot encoding
                i_features = [self._data.public_features[f] for f in
                              self._data.side_information_data.feature_map[self._data.private_items[item]]]
                feature_oh[i_features] = 1
                transactions.append(np.concatenate((item_oh, feature_oh)))
            else:
                transactions.append(item_oh)
        return np.array(transactions, dtype=np.float32)

    def get_user_full_array(self, user):
        user_oh = np.zeros(self._num_users, dtype=np.float32)  # user one-hot encoding
        user_oh[user] = 1
        return np.hstack((np.tile(user_oh, (self._num_items, 1)), self._item_array))

    def get_recommendations(self, k: int = 100):
        local_batch = (self._batch_size)
        predictions_top_k = {}
        for index, offset in enumerate(range(0, self._num_users, local_batch)):
            offset_stop = min(offset + local_batch, self._num_users)

            if self._nfeatures:
                predictions = self._model.get_recs([self.get_user_full_array(u) for u in range(offset, offset_stop)])
            else:
                predictions = self._model.get_recs(
                    (np.repeat(np.array(list(range(offset, offset_stop)))[:, None], repeats=self._num_items, axis=1),
                     np.array([self._i_items_set for _ in range(offset, offset_stop)])))
            v, i = self._model.get_top_k(predictions, self.get_train_mask(offset, offset_stop), k=k)
            items_ratings_pair = [list(zip(map(self._data.private_items.get, u_list[0]), u_list[1]))
                                  for u_list in list(zip(i.numpy(), v.numpy()))]
            predictions_top_k.update(dict(zip(map(self._data.private_users.get,
                                                  range(offset, offset_stop)), items_ratings_pair)))
        return test_item_only_filter(predictions_top_k, self._data.test_dict)

    def restore_weights(self):
        try:
            with open(self._saving_filepath, "rb") as f:
                self._model.set_model_state(pickle.load(f))
            print(f"Model correctly Restored")

            recs = self.get_recommendations(self.evaluator.get_needed_recommendations())
            result_dict = self.evaluator.eval(recs)
            self._results.append(result_dict)

            print("******************************************")
            if self._save_recs:
                store_recommendation(recs, self._config.path_output_rec_result + f"{self.name}.tsv")
            return True

        except Exception as ex:
            print(f"Error in model restoring operation! {ex}")

        return False