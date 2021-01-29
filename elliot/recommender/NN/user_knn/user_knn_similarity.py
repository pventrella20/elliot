
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity




class Similarity(object):
    """
    Simple kNN class
    """

    def __init__(self, data, num_neighbors, similarity):
        self._data = data
        self._ratings = data.train_dict
        self._num_neighbors = num_neighbors
        self._similarity = similarity

        self._users = self._data.users
        self._items = self._data.items
        self._private_users = self._data.private_users
        self._public_users = self._data.public_users
        self._private_items = self._data.private_items
        self._public_items = self._data.public_items

    def initialize(self):
        """
        This function initialize the data model
        """

        self._user_ratings = {}
        for u, user_items in self._ratings.items():
            for i, v in user_items.items():
                self._user_ratings.setdefault(u, {}).update({i: v})

        self._transactions = self._data.transactions

        self._similarity_matrix = np.empty((len(self._users), len(self._users)))

        self.process_similarity(self._similarity)

        self.compute_neighbors()

        del self._similarity_matrix

    def compute_neighbors(self):
        self._neighbors = {}
        for x in range(self._similarity_matrix.shape[0]):
            arr = np.concatenate((self._similarity_matrix[0:x, x], [-np.inf], self._similarity_matrix[x, x+1:]))
            top_indices = np.argpartition(arr, -self._num_neighbors)[-self._num_neighbors:]
            arr = arr[top_indices]
            self._neighbors[self._private_users[x]] = {self._private_users[i]: arr[p] for p, i in enumerate(top_indices)}

    def get_user_neighbors(self, item):
        return self._neighbors.get(item, {})

    def process_similarity(self, similarity):
        if similarity == "cosine":
            self.process_cosine()
        else:
            raise Exception("Not implemented similarity")

    def process_cosine(self):
        x, y = np.triu_indices(self._similarity_matrix.shape[0], k=1)
        g = np.vectorize(self.compute_cosine)
        g(x, y)
        # for item_row in range(self._similarity_matrix.shape[0]):
        #     for item_col in range(item_row + 1, self._similarity_matrix.shape[1]):
        #         self._similarity_matrix[item_row, item_col] = self.compute_cosine(
        #             self._item_ratings.get(self._private_items[item_row],{}), self._item_ratings.get(self._private_items[item_col], {}))

    def compute_cosine(self, i_index, j_index):
        u_dict = self._user_ratings.get(self._private_users[i_index],{})
        v_dict = self._user_ratings.get(self._private_users[j_index],{})
        union_keyset = set().union(*[u_dict, v_dict])
        u: np.ndarray = np.array([[u_dict.get(x, 0) for x in union_keyset]])
        v: np.ndarray = np.array([[v_dict.get(x, 0) for x in union_keyset]])
        self._similarity_matrix[i_index, j_index] = cosine_similarity(u, v)[0, 0]

    def get_transactions(self):
        return self._transactions

    def get_user_recs(self, u, k):
        user_items = self._ratings[u].keys()
        predictions = {i: self.score_item(self.get_user_neighbors(u), self._data.sp_i_train[:, i].nonzero()[0])
                       for i in self._data.items if i not in user_items}
        indices, values = zip(*predictions.items())
        indices = np.array(indices)
        values = np.array(values)
        partially_ordered_preds_indices = np.argpartition(values, -k)[-k:]
        real_values = values[partially_ordered_preds_indices]
        real_indices = indices[partially_ordered_preds_indices]
        local_top_k = real_values.argsort()[::-1]
        return [(real_indices[item], real_values[item]) for item in local_top_k]

    @staticmethod
    def score_item(neighs, user_neighs_items):
        num = sum([v for k, v in neighs.items() if k in user_neighs_items])
        den = sum(np.power(list(neighs.values()), 1))
        return num/den if den != 0 else 0

    def get_model_state(self):
        saving_dict = {}
        saving_dict['_neighbors'] = self._neighbors
        saving_dict['_similarity'] = self._similarity
        saving_dict['_num_neighbors'] = self._num_neighbors
        return saving_dict

    def set_model_state(self, saving_dict):
        self._neighbors = saving_dict['_neighbors']
        self._similarity = saving_dict['_similarity']
        self._num_neighbors = saving_dict['_num_neighbors']
